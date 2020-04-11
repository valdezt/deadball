import pandas as pd
import json
import itertools
from collections import Counter
import numpy as np
import logging

logger = logging.getLogger('draft_results.log')
hdlr = logging.FileHandler('./logs/draft_results.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

default_order = pd.read_csv('default_order.csv')[[
    'player_id',
    'Name',
    'pos',
    'ERA',
    'BA',
    'OBP'
]].set_index('player_id')
default_order['pos'] = default_order.pos.fillna('1B')

# Team requirements
NUM_ROUNDS = 22
NUM_SP = 5
NUM_RP = 5
NUM_BATTERS = 12
NUM_UNIQUE_REQUIRED = 8 + NUM_SP + NUM_RP

class Draft():
    def __init__(self, team_config):
        with open(team_config) as f:
            teams = json.loads(f.read())

        self.teams = {
            team: Team(
                name = team,
                order = pd.read_csv(teams[team]['order']).set_index('player_id'),
                optimization = teams[team]['optimization']
            ) for team in list(teams.keys())
        }
        self.draft_order = [team for team in teams.keys()]
        np.random.shuffle(self.draft_order)

        with open('draft_order.txt', 'w') as f:
            f.write(',\n'.join(self.draft_order))

        self.rounds_left = NUM_ROUNDS

        return

    def round(self):
        """
        Execute one draft round.
        """

        for team in self.draft_order:
            team_obj = self.teams[team]
            picked = team_obj.make_pick()
            player_name = default_order.loc[picked].Name

            logger.info(f'{team} picks {player_name}!')
            for t in self.teams.values():
                t.order.drop(picked, inplace = True)

        self.draft_order.reverse()
        return

    def draft(self):

        while self.rounds_left > 0:
            logger.info(f'******ROUND {NUM_ROUNDS - self.rounds_left + 1}******')
            self.round()
            self.rounds_left -= 1

        for team in self.draft_order:
            self.teams[team].team['pos'] = self.teams[team].team['pos'].apply(','.join)
            self.teams[team].team['BA'] = self.teams[team].team['BA'].fillna(0.135)
            self.teams[team].team['OBP'] = np.where(self.teams[team].team['OBP'].isna(), self.teams[team].team['BA']+0.05, self.teams[team].team['OBP'])
            self.teams[team].team[['Name', 'BA', 'OBP', 'ERA', 'pos']].to_csv(f'{team}.csv')

        self.teams[self.draft_order[0]].order['BA'] = self.teams[self.draft_order[0]].order['BA'].fillna(0.135)
        self.teams[self.draft_order[0]].order['OBP'] = np.where(self.teams[self.draft_order[0]].order['OBP'].isna(), self.teams[self.draft_order[0]].order['BA']+0.05, self.teams[self.draft_order[0]].order['OBP'])
        self.teams[self.draft_order[0]].order['pos'] = self.teams[self.draft_order[0]].order['pos'].apply(','.join)
        self.teams[self.draft_order[0]].order[['Name', 'BA', 'OBP', 'ERA', 'pos']].to_csv('fa.csv')

        return

class Team():
    def __init__(self, name, order = None, optimization = 'active'):
        self.name = name
        if order is None:
            self.order = default_order.copy()
        else:
            self.order = order
        self.order['pos'] = self.order.pos.fillna('1B').apply(lambda x: str(x).split(','))

        self.optimization = optimization
        self.team = pd.DataFrame(
            columns = ['player_id', 'Name', 'pos', 'BA', 'OBP', 'ERA']
        ).set_index('player_id')
        self.batters_remaining = NUM_BATTERS # number of positions to be filled
        self.sp_remaining = NUM_SP # number of sp required
        self.rp_remaining = NUM_RP # number of rp required
        self.total_remaining = (
            8 + self.sp_remaining + self.rp_remaining
        ) # number of unique player positions remaining
        self.picks_left = NUM_ROUNDS

        return

    def find_combo_positions(self, *args):
        combos = list(itertools.product(*args)) # all possible combinations

        return combos

    def count_num_unique(self, positions):
        positions = [pos for pos in positions if ((pos != ["SP"]) and (pos != ["RP"]))]
        return max([
            len(Counter(cp).keys())
                for cp in self.find_combo_positions(*positions)
        ])

    def count_num_players(self):
        """
        Returns the number of active roster spots filled.
        """

        sp_location = (
            self.team.pos.apply(lambda x: "SP" in x)
        )
        rp_location = (
            self.team.pos.apply(lambda x: "RP" in x)
        )
        num_sp = len(self.team.loc[sp_location])
        num_rp = len(self.team.loc[rp_location])
        num_batters = len(self.team) - num_sp - num_rp
        num_unique = self.count_num_unique(self.team.pos)

        return num_sp, num_rp, num_batters, num_unique

    def count_new_num_active(self, x):
        """
        Counts how many active roster spots would be filled if a player with pos
        x was picked.

        Returns the number of active roster spots filled
        OR
        Returns -1 if the pick of a player at position x would make an illegal
        roster.
        """

        assert type(x) == type([])
        assert len(x) > 0

        num_active = NUM_UNIQUE_REQUIRED - self.total_remaining

        if ("SP" in x):
            return -1 if self.sp_remaining == 0 else min(num_active + 1, NUM_UNIQUE_REQUIRED)
        elif ("RP" in x):
            return -1 if self.rp_remaining == 0 else min(num_active + 1, NUM_UNIQUE_REQUIRED)
        else:
            new_unique = (
                self.count_num_unique(list(self.team.pos.values) + [x])
            )

            return -1 if self.batters_remaining == 0 else min(new_unique + 10 - (self.sp_remaining + self.rp_remaining), 18)

        return -1

    def make_pick_active(self, player_list):
        """
        Returns the player_id of the next player that should be picked based on
        the following criteria:
        1) Does not make an illegal roster
        2) Decreases the number of remaining active roster spots open
        3) In order of player_list
        """

        num_active = NUM_UNIQUE_REQUIRED - self.total_remaining

        to_pick = player_list.copy()
        to_pick['new_active'] = to_pick.pos.apply(self.count_new_num_active)
        to_pick = (
            to_pick
            .query('new_active > @num_active')
            .query('new_active > -1')
        )

        return to_pick.iloc[0].name

    def make_pick_best(self, player_list):
        """
        Returns the player_id of the next player that should be picked based on
        the following criteria:
        1) Does not make an illegal roster
        2) The number of remaining rounds >= number of remaining active spots to fill
        3) In order of player_list
        """

        to_pick = player_list.copy()
        to_pick['new_active'] = to_pick.pos.apply(self.count_new_num_active)
        to_pick = (
            to_pick
            .query('(18 - new_active) < @self.picks_left')
            .query('new_active != -1')
        )

        return to_pick.iloc[0].name

    def end_round(self):
        self.picks_left -= 1

        num_sp, num_rp, num_batters, num_unique = self.count_num_players()
        self.sp_remaining = NUM_SP - num_sp
        self.rp_remaining = NUM_RP - num_rp
        self.batters_remaining = NUM_BATTERS - num_batters
        self.total_remaining = NUM_UNIQUE_REQUIRED - num_unique - num_sp - num_rp

        return

    def make_pick(self):

        if (self.optimization == 'active_first') and (self.picks_left > 4):
            to_pick = self.make_pick_active(self.order)
        else:
            to_pick = self.make_pick_best(self.order)

        self.team = self.team.append(self.order.loc[to_pick])

        self.end_round()

        return to_pick

def main():
    draft = Draft('teams.json')
    draft.draft()

if __name__ == '__main__':
    main()

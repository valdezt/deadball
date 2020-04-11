# Deadball Draft

Deadball is an RPG baseball game made by W. M. Akers. To play this game you need a team of baseball players, either fictional or real. The tools found in `draft.py` were used to create 8 teams of 22 baseball players from the MLB using their 2019 stats. Each team had 12 batters, 5 starting pitchers and 5 relief pitchers.

Given a preferred drafting order, each team is able to draft in one of two ways:
- To complete a full lineup before drafting bench players
- To draft the best possible players first while ensuring a full lineup is possible after the last pick

To complete a draft, a drafting order and list of teams is required. Each team is able to use their own preferred drafting order. For an example of what a draft order looks like, see `default_order_ex.csv`. Truly the only columns needed are a unique identifier such as player_id and the positions each player can fill. To draft a larger or smaller team, you only need to tweak a few parameters in the draft file.

Additionally, `schedule.py` will create a round-robin schedule given a list of teams.

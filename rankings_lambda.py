import requests
import json

class Team:
    teams = {}

    def __init__(self, name, is_fbs):
        self.games = {}
        self.wins = 0
        self.losses = 0
        self.name = name
        self.is_fbs = is_fbs
        self.sos = 0
        Team.teams[name] = self

    def add_game(self, opponent, is_win, point_spread):
        self.games[opponent] = point_spread
        if is_win:
            self.wins += 1
        else:
            self.losses += 1

    def calculate_initial_sos(self):
        if not self.games:
            self.sos = 0
            return

        total_opponent_wins = 0
        total_opponent_losses = 0

        for opponent_name in self.games:
            opponent = Team.teams.get(opponent_name)
            if opponent:
                total_opponent_wins += opponent.wins
                total_opponent_losses += opponent.losses

        total_games = total_opponent_wins + total_opponent_losses
        self.sos = (total_opponent_wins / total_games) if total_games > 0 else 0

    @staticmethod
    def calculate_recursive_sos(iterations=1000):
        for _ in range(iterations):
            for team in Team.teams.values():
                if not team.is_fbs:
                    continue

                total_opponent_sos = 0
                count = 0

                for opponent_name in team.games:
                    opponent = Team.teams.get(opponent_name)
                    if opponent:
                        total_opponent_sos += opponent.sos
                        count += 1

                team.sos = (total_opponent_sos / count) if count > 0 else 0

    def calculate_penalty(self, margin):
        k = 1.0
        capped_margin = min(abs(margin), 28)
        penalty = 1 + k * (capped_margin / 28) ** 2
        return penalty

    def calculate_bonus(self, margin):
        k = 0.2
        capped_margin = min(margin, 7)
        bonus = 1 + k * (capped_margin / 21) ** 2
        return bonus

    def rank_score(self):
        score = 0
        for opponent_name, point_spread in self.games.items():
            opponent_team = Team.teams[opponent_name]

            is_home = self.name in opponent_team.games and opponent_team.games[self.name] < 0

            if point_spread > 0:
                weight = 0.9 if is_home else 1.1
                score += weight * (opponent_team.wins + opponent_team.sos) * self.calculate_bonus(point_spread)
            else:
                weight = 1.1 if is_home else 0.9
                score -= weight * (opponent_team.losses + opponent_team.sos) * self.calculate_penalty(point_spread)

        return (12 / len(self.games)) * score if len(self.games) > 0 else 0

    @staticmethod
    def record_game(home_name, home_fbs, away_name, away_fbs, home_points, away_points):
        home = Team.teams.get(home_name) or Team(home_name, home_fbs)
        away = Team.teams.get(away_name) or Team(away_name, away_fbs)

        home_win = home_points > away_points
        margin = abs(home_points - away_points)

        home.add_game(away_name, home_win, margin if home_win else -margin)
        away.add_game(home_name, not home_win, margin if not home_win else -margin)

    @staticmethod
    def get_rankings():
        for team in Team.teams.values():
            if team.is_fbs:
                team.calculate_initial_sos()

        Team.calculate_recursive_sos(iterations=1000)

        ratings = []
        for team in Team.teams.values():
            if team.is_fbs:
                ratings.append([-team.rank_score(), -team.wins, team.losses, team.name])

        ratings.sort()
        result = []
        for i, rating in enumerate(ratings):
            result.append({
                "rank": i + 1,
                "team": rating[3],
                "wins": -rating[1],
                "losses": rating[2],
                "score": -rating[0]
            })
        return result

def lambda_handler(event, context):
    year = event['year']
    token = event['token']
    
    response = requests.get(
        f'https://api.collegefootballdata.com/games?year={year}&seasonType=regular',
        headers={"Authorization": f"Bearer {token}"}
    )
    games = response.json()

    postseason = requests.get(
        f'https://api.collegefootballdata.com/games?year={year}&seasonType=postseason',
        headers={"Authorization": f"Bearer {token}"}
    )

    games += postseason.json()

    for game in games:
        if game['home_points'] is not None and game['away_points'] is not None:
            Team.record_game(
                game['home_team'],
                game['home_division'] == "fbs",
                game['away_team'],
                game['away_division'] == "fbs",
                game['home_points'],
                game['away_points']
            )

    return {
        "statusCode": 200,
        "body": json.dumps(Team.get_rankings())
    }

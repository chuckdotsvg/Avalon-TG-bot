import bot
from game import Game

def add_game(new_id: int, new_game: Game, games: list[Game]):
    games[new_id] = new_game

def main():
    games: dict[int, Game]

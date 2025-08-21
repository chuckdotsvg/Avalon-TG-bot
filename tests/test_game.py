import pytest
from pytest import fixture, raises

from avalontgbot.constants import (
    MANDATORY_ROLES,
    MAX_PLAYERS,
    MIN_PLAYERS,
    PLAYERS_TO_RULES,
)
from avalontgbot.game import (
    Game,
)
from avalontgbot.gamephase import GamePhase as PHASE
from avalontgbot.player import Player
from avalontgbot.role import Role


@pytest.fixture
def game():
    p = Player(123456789, "Creator")
    return Game(p, 234567891)


@pytest.fixture
def started_game(game: Game, new_players: list[Player]) -> Game:
    add_players_to_game(game, new_players)
    game.start_game()
    return game

@pytest.fixture
def correct_special_roles() -> list[Role]:
    return list(MANDATORY_ROLES | {Role.PERCIVAL, Role.MORGANA})

@pytest.fixture
def too_many_evil_roles() -> list[Role]:
    return list(MANDATORY_ROLES | {Role.MORGANA, Role.PERCIVAL, Role.MORDRED})

# TODO: add more good roles
# def too_many_good_roles() -> list[Role]:

def players(n: int) -> list[Player]:
    players: list[Player] = []
    for i in range(n):
        players.append(Player(123456789 + i, f"Player{i}"))

    return players


@pytest.fixture
def too_many_players() -> list[Player]:
    return players(MAX_PLAYERS)  # already one inside


@pytest.fixture
def few_players() -> list[Player]:
    return players(MIN_PLAYERS - 3)


@pytest.fixture
# exactly MIN_PLAYERS after adding, so it can start
def new_players() -> list[Player]:
    return players(MIN_PLAYERS - 1)


def test_game_initialization(game: Game):
    assert game.creator.userid == 123456789
    assert game.id == 234567891
    assert game.players == [game.creator]
    assert game.phase == PHASE.LOBBY
    assert game.turn == 0
    assert game.votes == {  }
    assert game.missions == [None] * 5
    assert game.leader_idx == -1

    for p in game.players:
        assert p.role is None
        assert p.is_online is True
        assert p.tg_name == "Creator"
        assert p.userid == 123456789


def add_players_to_game(game: Game, players: list[Player]):
    for player in players:
        game.player_join(player)


def test_game_add_player_lobby(game: Game, new_players: list[Player]):
    assert game.phase == PHASE.LOBBY
    add_players_to_game(game, new_players)

    assert len(game.players) == len(new_players) + 1


@pytest.fixture
def test_autostart(game: Game, too_many_players: list[Player]) -> Game:
    assert game.phase == PHASE.LOBBY
    add_players_to_game(game, too_many_players[:-1])

    assert game.phase != PHASE.LOBBY
    assert len(game.players) == MAX_PLAYERS
    assert game.turn == 1

    return game


def test_game_start_few(game: Game, few_players: list[Player]):
    test_game_add_player_lobby(game, few_players)

    assert game.phase == PHASE.LOBBY

    assert raises(KeyError, game.start_game)


def test_game_start(game: Game, new_players: list[Player]):
    test_game_add_player_lobby(game, new_players)

    assert game.phase == PHASE.LOBBY
    assert len(game.players) <= MIN_PLAYERS

    game.start_game()

def test_too_many_evil_special_roles(game: Game, new_players: list[Player], too_many_evil_roles: list[Role]):
    add_players_to_game(game, new_players)

    game.set_special_roles(too_many_evil_roles)
    assert set(game.special_roles) == set(too_many_evil_roles)

    assert raises(ValueError, game.start_game)

def test_correct_special_roles(game: Game, new_players: list[Player], correct_special_roles: list[Role]):
    add_players_to_game(game, new_players)

    game.set_special_roles(correct_special_roles)
    game.start_game()

    assert set(game.special_roles) == set(correct_special_roles)

@pytest.fixture
def game_with_correct_extra_roles(game: Game, new_players: list[Player], correct_special_roles: list[Role]) -> Game:
    test_correct_special_roles(game, new_players, correct_special_roles)

    game.start_game()
    return game

def test_empty_special_roles(game: Game, new_players: list[Player]):
    add_players_to_game(game, new_players)

    game.set_special_roles([])

    assert set(game.special_roles) == set(MANDATORY_ROLES)

@pytest.fixture
def test_game_ongoing(game_with_correct_extra_roles: Game):
    assert game_with_correct_extra_roles.phase != PHASE.LOBBY
    assert game_with_correct_extra_roles.turn != -1
    assert game_with_correct_extra_roles.leader_idx != -1
    np = len(game_with_correct_extra_roles.players)
    assert np >= MIN_PLAYERS
    assert game_with_correct_extra_roles.team_sizes == PLAYERS_TO_RULES[np]["team_sizes"]
    assert len(game_with_correct_extra_roles.evil_list()) == np - PLAYERS_TO_RULES[np]["num_goods"]

    players_roles = set(p.role for p in game_with_correct_extra_roles.players)
    assert None not in players_roles
    # here roles cannot be None, because they are set in start_game
    special_roles = set(x for x in players_roles if x.is_special)   # pyright: ignore[reportOptionalMemberAccess]

    assert set(special_roles) == set(game_with_correct_extra_roles.special_roles)

def test_pass_creator(started_game: Game):
    creator_idx = started_game.players.index(started_game.creator)
    new_creator = started_game.players[creator_idx + 1]

    assert raises(ValueError, started_game.pass_creator, started_game.players[creator_idx])
    assert raises(ValueError, started_game.pass_creator, Player(999999999, "NonExistent"))
    started_game.pass_creator(new_creator)

# def test_game_set_team(test_game_ongoing: Game):
#     assert test_game_ongoing.phase == PHASE.BUILD_TEAM
#
#     # check that the team is set correctly
#     assert started_game.team == [p for p in started_game.players if p.userid in team]

from game import Game
from gamephase import GamePhase as PHASE
from player import Player
import telegram
from telegram import Update


class GameController:
    def __init__(self, game: Game):
        """
        Initialize the GameController with a game instance.
        :param game: The game instance to control.
        """
        self.game = game

    async def handle_create_game(
        self, player: Player, update: Update, existing_games: dict[int, Game]
    ):
        """
        Handle the creation of a new game.
        """
        if not update.message:
            return
        group_id = update.message.chat_id

        # check if there is already a game in the group
        if group_id not in existing_games.keys():
            existing_games[group_id] = Game()
            await update.message.reply_text(
                "Game created!",
                # reply_markup=telegram.ReplyKeyboardRemove(),
            )
        else:
            await update.message.reply_text(
                "There is already a game in this group. Please finish it before creating a new one."
            )

    async def handle_join_game(
        self, update: Update, existing_games: dict[int, Game]
    ):
        """
        Handle a player joining an existing game.
        """
        if not update.message:
            return
        group_id = update.message.chat_id

        # check if there is a game in the group 
        if group_id in existing_games.keys():
            game = existing_games[group_id]

            if not (user := update.effective_user):
                return

            player = Player(user.id, None, False, False)
            game.add_player(player)
            await update.message.reply_html(
                f"{user.mention_html()} has joined the game!"
            )
        else:
            await update.message.reply_text(
                "There is no game in this group. Please create one first."
            )

    async def handle_leave_game(
        self, update: Update, existing_games: dict[int, Game]
    ):
        """
        Handle a player leaving the game.
        """
        if not update.message:
            return
        group_id = update.message.chat_id

        # check if there is a game in the group
        if group_id in existing_games.keys():
            # game = existing_games[group_id]


            # safety check
            if not (user := update.effective_user):
                return

            if (player := game.lookup_player(user.id)) is None:
                await update.message.reply_text(
                    "You are not in the game. Please join first."
                )
            else:
                game.remove_player(player)

                await update.message.reply_html(
                    f"{user.mention_html()} has left the game!"
                )

        else:
            await update.message.reply_text(
                "There is no game in this group. Please create one first."
            )

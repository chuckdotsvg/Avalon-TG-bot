from game import Game
from player import Player
from telegram import Update


async def handle_create_game(update: Update, existingGames: dict[int, Game]) -> None:
    """
    Handle the creation of a new game.
    """
    if not update.message or not update.effective_user:
        return
    group_id = update.message.chat_id

    # check if there is already a game in the group
    if group_id not in existingGames.keys():
        # add new game
        existingGames[group_id] = Game(Player(update.effective_user.id), group_id)

        await update.message.reply_text(
            "Game created! You are alone now... wait for some friends.\n",
            # reply_markup=telegram.ReplyKeyboardRemove(),
        )
    else:
        await update.message.reply_text(
            "There is already a game in this group. Please finish it before creating a new one."
        )


async def handle_join_game(update: Update, existing_games: dict[int, Game]) -> None:
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

        if game.lookup_player(user.id) is None:
            game.add_player(Player(user.id))
            await update.message.reply_html(
                f"{user.mention_html()} has joined the game!"
            )
        else:
            await update.message.reply_text("You are already in the game!")
            return
    else:
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )


async def handle_leave_game(update: Update, existing_games: dict[int, Game]):
    """
    Handle a player leaving the game.
    """
    if not update.message:
        return
    group_id = update.message.chat_id

    # check if there is a game in the group
    if group_id in existing_games.keys():
        game = existing_games[group_id]

        # safety check
        if not (user := update.effective_user):
            return

        if (player := game.lookup_player(user.id)) is None:
            await update.message.reply_text(
                "You are not in the game. Please join first."
            )
        else:
            game.remove_player(player)
            await update.message.reply_html(f"{user.mention_html()} has left the game!")

            # if there are no players left, remove the Game
            if len(game.players) == 0:
                del existing_games[group_id]
                await update.message.reply_text("All players have left the game. The game has been removed.")

    else:
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )

async def handle_start_game(update: Update, existing_games: dict[int, Game]) -> None:
    """
    Handle the start of the game.
    """
    if not update.message or not update.effective_user:
        return
    group_id = update.message.chat_id

    # check if there is a game in the group
    if group_id in existing_games.keys():
        game = existing_games[group_id]

        # check if the requesting user is the creator
        if update.effective_user.id != game.creator.userid:
            await update.message.reply_text(
                "Only the creator can start the game."
            )
            return

        # check if there are enough players
        if len(game.players) < 5:
            await update.message.reply_text(
                "Not enough players to start the game. Minimum 5 players required."
            )
            return

        # start the game
        await update.message.reply_text("Game started!")
        game.start_game()
    else:
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )

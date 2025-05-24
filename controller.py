import json
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    PollAnswer,
    Update,
)
from telegram.ext import (
    ContextTypes,
)

from game import Game
from player import Player
from gamephase import GamePhase as PHASE


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


async def handle_join_game(
    update: Update, context: ContextTypes.DEFAULT_TYPE, existing_games: dict[int, Game]
) -> PHASE:
    """
    Handle a player joining an existing game.
    :return: the new game state after the player has joined
    """
    # suppose lobby isn't full
    new_phase = PHASE.LOBBY
    if not update.message:
        # TODO: handle telegram errors
        return new_phase

    # check if there is a game in the group
    if (group_id := update.message.chat_id) not in existing_games.keys():
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )
        return new_phase

    game = existing_games.get( group_id )

    if not (user := update.effective_user):
        # TODO: handle telegram errors
        return new_phase

    if game.lookup_player(user.id) is None:
        game.add_player(Player(user.id))
        await update.message.reply_html(
            f"{user.mention_html()} has joined the game!"
        )

    if len(game.players) == 10:
        # the game is full, start it automatically
        new_phase = await _routine_start_game(context, game)
    else:
        await update.message.reply_text("You are already in the game!")
        return new_phase

    return new_phase


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
                await update.message.reply_text(
                    "All players have left the game. The game has been removed."
                )

    else:
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )


async def handle_start_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    existing_games: dict[int, Game],
):
    """
    Handle the start of the game.
    """
    if not update.message or not update.effective_user:
        # TODO: handle telegram errors
        return

    # check if there is a game in the group
    if ( group_id := update.message.chat_id ) not in existing_games.keys():
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )
        return

    game = existing_games[group_id]

    # check if the requesting user is the creator
    if update.effective_user.id != game.creator.userid:
        await update.message.reply_text("Only the creator can start the game.")
        return

    # check if there are enough players
    if len(game.players) < 5:
        await update.message.reply_text(
            "Not enough players to start the game. Minimum 5 players required."
        )
        return

    await _routine_start_game(context, game)


async def _routine_start_game(context: ContextTypes.DEFAULT_TYPE, game: Game):
    # start the game
    game.start_game()

    # send to every player their role
    for player in game.players:
        await context.bot.send_message(
            chat_id=player.userid,
            text=f"Your role is: {player.role.name}.\n",
        )

    await context.bot.send_message(
        chat_id=game.id,
        text="The game has started! You can now start building the team.",
    )


async def handle_vote(
    update: Update, context: ContextTypes.DEFAULT_TYPE, existing_games: dict[int, Game]
) -> None:
    """
    Handle team member decision for the mission.
    """
    if not update.message or not update.effective_user:
        return
    group_id = update.message.chat_id

    # check if there is a game in the group
    if group_id in existing_games.keys():
        game = existing_games[group_id]

        # check if the requesting user is a player
        if (player := game.lookup_player(update.effective_user.id)) is None:
            await update.message.reply_text(
                "You are not in the game. Please join first."
            )
            return

        # TODO: check if the game is in the voting phase

        # check if the game is in progress
        # if not game.in_progress:
        #     await update.message.reply_text(
        #         "The game is not in progress. Please start the game first."
        #     )
        #     return

        keyboard = [
            [
                InlineKeyboardButton(
                    vote, callback_data=json.dumps({"vote": vote, "gid": game.id})
                )
                for vote in ["yes", "no"]
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        for player in game.players:
            await context.bot.send_message(
                chat_id=player.userid,
                text="Do you want to make the mission successful?",
                reply_markup=reply_markup,
            )
    else:
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )


async def button_vote_handler(query: CallbackQuery, game: Game) -> None:
    if not query.data or not (voter := game.lookup_player(query.from_user.id)):
        return

    data = json.loads(query.data)
    vote = data.get("vote")
    game.add_player_vote(
        voter,
        # query.data is a string, so we need to convert it to a boolean
        vote == "yes",
    )

    # reply to the user
    await query.edit_message_text(
        text=f"Your vote has been recorded: {vote}, you can go back to the game.",
        reply_markup=None,
    )


async def handle_build_team_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE, existing_games: dict[int, Game]
) -> None:
    """
    Handle a player building a team.
    """
    if not (group_chat := update.effective_chat) or not (
        game := existing_games.get(group_chat.id)
    ):
        return

    message = await context.bot.send_poll(
        game.players[game.leader_idx].userid,
        f"Select a team of {game.team_sizes[game.turn]} players",
        [(await group_chat.get_member(x.userid)).user.full_name for x in game.players],
        is_anonymous=False,
        allows_multiple_answers=True,
    )

    # we associate to each poll the game id that it belongs to
    if not (poll := message.poll):
        return

    context.bot_data[poll.id] = group_chat.id


async def handle_build_team_answer(
    answer_team: PollAnswer, context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Handle the answer to the team building poll.
    """

    leader_userid = game.players[game.leader_idx].userid

    # TODO: replace message with warning
    if (voted_team_size := len(answer_team.option_ids)) != game.team_sizes[game.turn]:
        await context.bot.send_message(
            chat_id=leader_userid,
            text=f"You have selected {voted_team_size} players, but you need to select {game.team_sizes[game.turn]} players.",
        )
        return
    else:
        await context.bot.send_message(
            chat_id=leader_userid,
            text=f"You have selected {voted_team_size} players, which is correct.",
        )

        # player order in poll has the same order as in game.players, so indexing is safe
        game.create_team([game.players[i] for i in answer_team.option_ids])

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
        existingGames[group_id] = Game(
            Player(update.effective_user.id, update.effective_user.full_name), group_id
        )

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

    if not (user := update.effective_user):
        # TODO: handle telegram errors
        return new_phase

    # this can't be None
    if game.lookup_player(user.id) is None:
        new_player = Player(user.id, user.full_name)
        game.add_player(new_player)
        await update.message.reply_html(f"{new_player.tg_name} has joined the game!")

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
                # remove the game from the existing games
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
    Handle the start of the game, checking for conditions such as creator and player count.
    """
    if not update.message or not update.effective_user:
        # TODO: handle telegram errors
        return

    # check if there is a game in the group
    if (group_id := update.message.chat_id) not in existing_games.keys():
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

    # this effectively starts the game
    await _routine_start_game(context, game)


async def _routine_start_game(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to start the game, setting up roles and notifying players.
    """
    game.start_game()

    # TODO: send personalized messages to players
    for player in game.players:
        await context.bot.send_message(
            chat_id=player.userid,
            text=f"Your role is: {player.role.name}.\n",
        )

    # go and do the voting phase stuff
    await context.bot.send_message(
        chat_id=game.id,
        text="The game has started! You can now start building the team.",
    )


async def _routine_pre_team_building(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to prepare the voting phase of the game (i.e. sending the poll to the team leader).
    """
    # notify players in the group about the voting phase
    await context.bot.send_message(
        chat_id=game.id,
        text="The voting phase has started! wait for the team leader to build a team.",
    )

    # send the poll to the team leader
    message = await context.bot.send_poll(
        game.players[game.leader_idx].userid,
        f"Select a team of {game.team_sizes[game.turn]} players",
        [x.tg_name for x in game.players],
        is_anonymous=False,
        allows_multiple_answers=True,
    )

    # we associate to each poll the game id that it belongs to
    # if not (poll := message.poll):
    #     return
    #
    # context.bot_data[poll.id] = game.id


async def handle_build_team_answer(
    answer_team: PollAnswer,
    message_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
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
        # stop the poll if the team size is correct
        await context.bot.stop_poll(
            chat_id=leader_userid,
            # should there be message or poll id?
            message_id=message_id,
            reply_markup=None,
        )

        # player order in poll has the same order as in game.players, so indexing is safe
        game.create_team([game.players[i] for i in answer_team.option_ids])

        # close poll and update game state
        await context.bot.send_message(
            chat_id=leader_userid,
            text=f"Let's see if the others approve the team... go back to the game.",
        )

        # send the result to the group chat
        await context.bot.send_message(
            chat_id=game.id,
            text=f"The voted team is: {', '.join(p.tg_name for p in game.team)}.",
        )

        # go to the team approval phase
        await _routine_pre_team_approval_phase(context, game)


async def _routine_pre_team_approval_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to prepare the voting phase of the team approval (i.e. sending the poll to all players).
    """
    # notify players in the group about the voting phase
    await context.bot.send_message(
        chat_id=game.id,
        text="go to private chat to vote if the team is good or not.",
    )

    _send_pvt_decision_message("Do you approve the team?", game.players, context, game)


async def _send_pvt_decision_message(
    decision_txt: str,
    recipients: list[Player],
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """
    Send a private message to each player to decide if they want to approve the team.
    """

    keyboard = [
        [
            InlineKeyboardButton(
                "Approve", callback_data=json.dumps({"vote": "yes", "gid": game.id})
            ),
            InlineKeyboardButton(
                "Reject", callback_data=json.dumps({"vote": "no", "gid": game.id})
            ),
        ]
    ]

    for player in recipients:
        await context.bot.send_message(
            chat_id=player.userid,
            text=decision_txt,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def _routine_pre_mission_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to prepare the mission phase of the game.
    """
    # notify players in the group about the mission phase
    await context.bot.send_message(
        chat_id=game.id,
        text="The team has been approved! Team, go vote for the success of the mission.",
    )

    _send_pvt_decision_message(
        "Do you want to make the mission successful?", game.team, context, game
    )


async def button_vote_handler(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    if not query.data:
        return

    data = json.loads(query.data)
    vote = data.get("vote")
    is_voting_ended = game.add_player_vote(
        # query.data is a string, so we need to convert it to a boolean
        vote == "yes",
    )

    # reply to the user
    await query.edit_message_text(
        text=f"Your vote has been recorded: {vote}, you can go back to the game.",
        # remove the inline keyboard
        reply_markup=None,
    )

    # repeat the process until the voting is succesful
    if is_voting_ended:
        if game.phase == PHASE.TEAM_BUILD:
            await _routine_post_team_approval_phase(context, game)
        elif game.phase == PHASE.QUEST_PHASE:
            await _routine_post_mission_phase(context, game)


async def _routine_post_team_approval_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to send the correct message after the team approval phase, based on the voting results.
    """

    approval_result = game.update_after_team_decision()

    if game.check_winner() is not None:
        # TODO: handle winner
        pass
    elif approval_result:
        # TODO: go to the mission phase
        _routine_pre_mission_phase(context, game)
        pass
    else:
        # repeat the team building phase
        _routine_pre_team_building(context, game)


async def _routine_post_mission_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to send the correct message after the mission phase, based on the voting results.
    """

    mission_result = game.update_after_mission()
    is_good_winner = game.check_winner()

    if is_good_winner:
        # evil have a last chance to win
        _routine_last_chance_phase(context, game)
    elif not is_good_winner:
        # good lose immediately
        await context.bot.send_message(
            chat_id=game.id,
            text="More than 3 mission failed! The good team loses.",
        )
    else:
        # repeat the team building phase
        _routine_pre_team_building(context, game)


async def _routine_last_chance_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to prepare the last chance phase of the game.
    """
    # notify players in the group about the last chance phase
    await context.bot.send_message(
        chat_id=game.id,
        text="The evil team has a last chance to win the game. Assassin, choose a player to assassinate! If you choose the Merlin, you win the game.",
    )

    # TODO: send the quiz poll to the assassin

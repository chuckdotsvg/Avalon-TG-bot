import json
from typing import Any
from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PollAnswer,
    Update,
)
from telegram.ext import (
    ContextTypes,
)

from game import Game
from player import Player
from gamephase import GamePhase as PHASE
from telegram.constants import PollType as POLLTYPE
from role import Role as ROLE

existingGames: dict[int, Game] = {}


async def handle_create_game(update: Update) -> None:
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


async def handle_join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle a player joining an existing game.
    :return: the new game state after the player has joined
    """
    # suppose lobby isn't full
    if not update.message:
        # TODO: handle telegram errors
        return

    # check if there is a game in the group
    if (group_id := update.message.chat_id) not in existingGames.keys():
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )
        return

    if not (user := update.effective_user):
        # TODO: handle telegram errors
        return

    game = existingGames[group_id]

    # p = game.lookup_player(user.id) or Player(user.id, user.full_name)
    p = game.lookup_player(user.id)

    if p is not None:
        if p.is_online:  # player is already in the game
            await update.message.reply_text("You are already in the game")
        elif not game.is_ongoing():  # player is in the game, but not online
            game.player_join(p)
    else:
        # player is not in the game, so we create a new Player
        p = Player(user.id, user.full_name)
        if game.is_ongoing() or game.phase != PHASE.LOBBY:
            # game already started, cannot join
            await update.message.reply_text(
                "The game has already started. You cannot join now."
            )
        elif game.phase == PHASE.LOBBY:
            game.player_join(p)
            await update.message.reply_html(
                f"{user.mention_html()} has joined the game!",
            )

    # notify the group if everyone is online
    if game.is_ongoing():
        await update.message.reply_text(
            "Everyone is online again, the game can continue!"
        )
    elif len(game.players) == 10:
        await _routine_start_game(context, game)

    return


async def handle_leave_game(update: Update):
    """
    Handle a player leaving the game.
    """
    if not update.message:
        return
    group_id = update.message.chat_id

    # check if there is a game in the group
    if group_id in existingGames.keys():
        game = existingGames[group_id]

        # safety check
        if not (user := update.effective_user):
            return

        if (player := game.lookup_player(user.id)) is None:
            await update.message.reply_text(
                "You are not in the game. Please join first."
            )
        else:
            await update.message.reply_html(f"{user.mention_html()} has left the game!")

            # if there are no players left, remove the Game
            if not game.player_leave(player):
                # remove the game from the existing games
                del existingGames[group_id]

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
):
    """
    Handle the start of the game, checking for conditions such as creator and player count.
    """
    if not update.message or not update.effective_user:
        # TODO: handle telegram errors
        return

    # check if there is a game in the group
    if (group_id := update.message.chat_id) not in existingGames.keys():
        await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )
        return

    game = existingGames[group_id]

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
            text=f"Your role is: {player.role.name}.\n",  # now role can't be None
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
    # await context.bot.send_poll(
    #     game.players[game.leader_idx].userid,
    #     f"Select a team of {game.team_sizes[game.turn]} players",
    #     [x.tg_name for x in game.players],
    #     is_anonymous=False,
    #     allows_multiple_answers=True,
    # )

    message = await _send_people_vote_poll(
        context,
        game,
        [x.tg_name for x in game.players],
        f"Select a team of {game.team_sizes[game.turn]} players",
        POLLTYPE.REGULAR,
        None,
    )

    payload = {
        message.poll.id: message.message_id,
    }
    context.bot_data.update(payload)


async def _send_people_vote_poll(
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
    people_name: list[str],
    poll_msg: str,
    poll_type: POLLTYPE,
    correct_opt_id: int | None,
) -> Message:
    """
    Send a poll to the group chat to vote for the team leader.
    """

    args: list[Any] = []
    args.append(poll_type)
    if correct_opt_id:
        args.append(correct_opt_id)

    msg = await context.bot.send_poll(
        game.players[game.leader_idx].userid,
        poll_msg,
        people_name,
        is_anonymous=False,
        allows_multiple_answers=poll_type == POLLTYPE.REGULAR,
        *args,
    )

    # we associate to each poll the game id that it belongs to
    if not (poll := msg.poll):
        # TODO: handle telegram errors
        return

    context.bot_data[poll.id] = game.id

    return msg


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
    else:
        # stop the poll if the team size is correct
        await context.bot.stop_poll(
            chat_id=leader_userid,
            message_id=message_id,
            reply_markup=None,
        )

        # player order in poll has the same order as in game.players, so indexing is safe
        game.create_team([game.players[i] for i in answer_team.option_ids])

        # close poll and update game state
        await context.bot.send_message(
            chat_id=leader_userid,
            text="Let's see if the others approve the team... go back to the game.",
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


async def _routine_pre_mission_phase(context: ContextTypes.DEFAULT_TYPE, game: Game):
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
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not query.data:
        return

    data = json.loads(query.data)
    vote = data.get("vote")

    if not (game := existingGames.get(data.get("gid"))):
        return

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
        if game.phase == PHASE.BUILD_TEAM:
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

    if game.winner is not None:
        await _routine_end_game(context, game.id)
    elif approval_result:
        # go to the mission phase
        await _routine_pre_mission_phase(context, game)
        pass
    else:
        # repeat the team building phase
        await _routine_pre_team_building(context, game)


async def _routine_post_mission_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to send the correct message after the mission phase, based on the voting results.
    """

    game.update_after_mission()

    if game.winner:
        # evil have a last chance to win
        _routine_last_chance_phase(context, game)
    elif not game.winner:
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

    goods = [x for x in game.players if x.role[1]]
    merlin_idx = [x.role for x in goods].index(ROLE.MERLIN)

    message = await _send_people_vote_poll(
        context,
        game,
        [x.tg_name for x in goods],
        "Assassin, try to kill Merlin... who you want to kill?",
        POLLTYPE.QUIZ,
        merlin_idx,
    )

    payload = {
        message.poll.id: message.message_id,
    }
    context.bot_data.update(payload)


async def handle_assassin_choice(
    msg_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE, game_id: int
):
    if not (assassin := update.effective_user) or not (answer := update.poll_answer):
        return

    assassin_id = assassin.id

    await context.bot.stop_poll(
        chat_id=assassin_id,
        message_id=msg_id,
        reply_markup=None,
    )

    await _routine_end_game(context, game_id)


async def _routine_end_game(context: ContextTypes.DEFAULT_TYPE, game_id: int) -> None:
    await context.bot.send_message(
        chat_id=game_id,
        text=f"{existingGames[game_id].winner and 'Good' or 'Evil'} team wins the game!",
    )

    # cleanup the game
    del existingGames[game_id]

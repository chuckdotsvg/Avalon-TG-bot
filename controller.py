import json

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    PollAnswer,
    Update,
)
from telegram.constants import PollType as POLLTYPE
from telegram.ext import (
    ContextTypes,
)

from constants import MAX_TEAM_REJECTS
from game import Game
from gamephase import GamePhase as PHASE
from player import Player
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

    p = game.lookup_player(user.id)

    if p is not None:
        if p.is_online:  # player is already in the game
            await update.message.reply_text("You are already in the game")
        elif not game.is_ongoing():  # player is in the game, but not online
            game.player_join(p)

            if game.is_ongoing():
                # notify the group if everyone is online
                await update.message.reply_text(
                    "Everyone is online again, the game can continue!"
                )
    else:
        # player is not in the game, so we create a new Player
        p = Player(user.id, user.full_name)
        if game.phase != PHASE.LOBBY:
            # game already started, cannot join
            await update.message.reply_text(
                "The game has already started. You cannot join now."
            )
        else:
            game.player_join(p)
            await update.message.reply_html(
                f"{user.mention_html()} has joined the game!\nRemember to start this bot in private chat",
            )

            if len(game.players) == 10:
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

    if game.is_ongoing():
        await update.message.reply_text("The game is already ongoing.")
    else:
        # this effectively starts the game
        await _routine_start_game(context, game)


async def handle_delete_game(update: Update):
    """
    Handle the deletion of a game.
    """
    if not update.message or not update.effective_user:
        return

    group_id = update.message.chat_id

    # check if there is a game in the group
    if group_id in existingGames.keys():
        game = existingGames[group_id]

        # check if the requesting user is the creator
        if update.effective_user.id != game.creator.userid:
            await update.message.reply_text("Only the creator can delete the game.")
            return

        # remove the game from the existing games
        del existingGames[group_id]

        await update.message.reply_text("The game has been deleted.")
    else:
        await update.message.reply_text("There is no game in this group.")


async def _routine_start_game(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to start the game, setting up roles and notifying players.
    """
    game.start_game()

    evils = [p.tg_name for p in game.players if not p.role[1]]

    for player in game.players:
        text = f"Your role is: {player.role}.\n"  # now role can't be None

        if player.role[1]:
            text += "You are part of the good team. Complete 3 successful missions to win the game!\n\n"
        else:
            text += (
                "You are part of the evil team. Sabotage the missions and prevent the good team from winning!\n"
                f"Your evil teammates are: {', '.join(p for p in evils if p != player.tg_name)}.\n\n"
            )

        text += player.role.description()  # role description

        if player.role == ROLE.MERLIN:
            text += f"Evil team is composed of: {', '.join(evils)}.\n"

        await context.bot.send_message(
            chat_id=player.userid,
            text=text,
        )

    await _routine_pre_team_building(context, game)


async def _routine_pre_team_building(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to prepare the voting phase of the game (i.e. sending the poll to the team leader).
    """
    # notify players in the group about the voting phase
    text = (
        f"Turn {game.turn + 1} has started!\n"
        f"{game.players[game.leader_idx].tg_name} is the team leader for this round.\n"
        "Wait for leader's team porposal"
    )

    await context.bot.send_message(
        chat_id=game.id,
        text=text,
    )

    await _send_people_vote_poll(
        context,
        game.id,
        game.players[game.leader_idx].userid,
        [x.tg_name for x in game.players],
        f"Leader, select a team of {game.team_sizes[game.turn]} players",
        POLLTYPE.REGULAR,
        None,
    )


async def _send_people_vote_poll(
    context: ContextTypes.DEFAULT_TYPE,
    game_id: int,
    recipient: int,
    people_name: list[str],
    poll_msg: str,
    poll_type: POLLTYPE,
    correct_opt_id: int | None,
) -> Message:
    """
    Send a poll to the group chat to vote for the team leader.
    :param context: the context of the bot
    :param game: the game object
    :param recipient: the recipient of the poll (the team leader)
    :param people_name: the names of the players to be included in the poll
    :param poll_msg: the message to be sent with the poll
    :param poll_type: the type of the poll (regular or quiz)
    :param correct_opt_id: the index of the correct option (if any, for quiz polls)
    """

    poll_kwargs = {
        "chat_id": recipient,
        "question": poll_msg,
        "options": people_name,
        "is_anonymous": False,
        "type": poll_type,
        "allows_multiple_answers": True,
    }

    if poll_type == "quiz" and correct_opt_id is not None:
        poll_kwargs["correct_option_id"] = correct_opt_id

    msg = await context.bot.send_poll(**poll_kwargs)

    # msg = await context.bot.send_poll(
    #     chat_id = recipient,
    #     question = poll_msg,
    #     options = people_name,
    #     is_anonymous=False,
    #     type = poll_type,
    #     allows_multiple_answers=True,
    #     correct_option_id=correct_opt_id,
    # )

    payload = {
        msg.poll.id: (msg.message_id, game_id),
    }
    context.bot_data.update(payload)

    return msg


async def handle_build_team_answer(
    answer_team: tuple[int, ...],
    message_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """
    Handle the answer to the team building poll.
    """
    leader_userid = game.players[game.leader_idx].userid

    # TODO: replace message with warning
    if (voted_team_size := len(answer_team)) != game.team_sizes[game.turn]:
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
        game.create_team([game.players[i] for i in answer_team])

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
        text="Go to private chat to vote if the team is good or not.",
    )

    question = (
        f"{game.players[game.leader_idx].tg_name} has proposed the following team:\n"
        f"{', '.join(p.tg_name for p in game.team)}.\n"
        "Do you approve this team?"
    )

    await _send_pvt_decision_message(question, game.players, context, game)
    # await _send_people_vote_poll(
    #     context, game.id, game.id, ["yes", "no"], question, POLLTYPE.REGULAR, None
    # )


async def handle_team_approval_answer(
    answer_team: tuple[int, ...],
    message_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """Handle the answer to the team approval poll."""

    # TODO: replace message with warning
    if (voted_team_size := len(answer_team)) != game.team_sizes[game.turn]:
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
        game.create_team([game.players[i] for i in answer_team])

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

    question = (
        "Do you want to make the mission successful?\n"
        f"Missions so far: {_bool_to_emoji([x for x in game.missions if x is not None])}.\n"
    )

    await _send_pvt_decision_message(question, game.team, context, game)


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
        elif game.phase == PHASE.QUEST:
            await _routine_post_mission_phase(context, game)


async def _routine_post_team_approval_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to send the correct message after the team approval phase, based on the voting results.
    """

    votes = game.votes.copy()

    # this updates the game state
    approval_result = game.update_after_team_decision()

    text = (
        f"The team was {'approved' if approval_result else 'rejected'}!\n"
        f"Votes: {_bool_to_emoji(votes)}.\n"
    )

    if 0 < game.rejection_count < MAX_TEAM_REJECTS:
        text += (
            "Vote will be repeated again.\n"
            "⚠️ If the team is rejected 3 times in a row, evils win!\n"
            f"Remaining attempts: {MAX_TEAM_REJECTS - game.rejection_count}.\n"
        )

    # send the result to the group chat
    await context.bot.send_message(
        chat_id=game.id,
        text=text,
    )

    if game.winner is not None:
        await _routine_end_game(context, game)
    else:
        if approval_result:
            # go to the mission phase
            await _routine_pre_mission_phase(context, game)
        else:
            # repeat the team building phase
            await _routine_pre_team_building(context, game)


async def _routine_post_mission_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to send the correct message after the mission phase, based on the voting results.
    """

    votes = game.votes.copy()

    result = game.update_after_mission()
    text = (
        f"The mission was {'successful' if result else 'failed'}!\n"
        f"Votes: {_bool_to_emoji(votes)}.\n"
        f"Missions so far: {_bool_to_emoji([x for x in game.missions if x is not None])}.\n"
    )
    # send the result to the group chat
    await context.bot.send_message(
        chat_id=game.id,
        text=text,
    )

    if game.winner is None:
        # repeat the team building phase
        await _routine_pre_team_building(context, game)
    elif game.winner:
        # evil have a last chance to win
        await _routine_last_chance_phase(context, game)
    else:
        # good lose immediately
        await context.bot.send_message(
            chat_id=game.id,
            text="3 mission failed!",
        )

        await _routine_end_game(context, game)


async def _routine_last_chance_phase(
    context: ContextTypes.DEFAULT_TYPE, game: Game
) -> None:
    """
    Routine to prepare the last chance phase of the game.
    """
    # notify players in the group about the last chance phase
    await context.bot.send_message(
        chat_id=game.id,
        text="The evil team has a last chance to win the game. Assassin, choose a player to kill! If you choose Merlin, you win the game.",
    )

    goods = [x for x in game.players if x.role[1]]
    merlin_idx = [x.role for x in goods].index(ROLE.MERLIN)
    assassin_tg_id = game.players[
        [x.role for x in game.players].index(ROLE.ASSASSIN)
    ].userid

    await _send_people_vote_poll(
        context,
        game.id,
        assassin_tg_id,
        [x.tg_name for x in goods],
        "Assassin, try to kill Merlin... who you want to kill?",
        POLLTYPE.QUIZ,
        merlin_idx,
    )


async def handle_assassin_choice(
    answer: tuple[int, ...],
    msg_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
):
    if not (assassin := update.effective_user):
        return

    await context.bot.stop_poll(
        chat_id=assassin.id,
        message_id=msg_id,
        reply_markup=None,
    )

    # TODO: handle possible errors
    assassin_guess = answer[0]

    game.update_winner_after_assassination(assassin_guess)

    text = (
        f"{assassin.full_name} has chosen to assassinate {game.players[assassin_guess].tg_name}!\n"
        f"The guess was {'correct' if game.winner else 'incorrect'}!\n"
    )

    await context.bot.send_message(
        chat_id=game.id,
        text=text,
    )
    # TODO: send poll result to the group chat

    await _routine_end_game(context, game)


async def _routine_end_game(context: ContextTypes.DEFAULT_TYPE, game: Game) -> None:
    await context.bot.send_message(
        chat_id=game.id,
        text=f"{game.winner and 'Good' or 'Evil'} team wins the game!",
    )

    # cleanup the game
    del existingGames[game.id]


def _bool_to_emoji(votes: list[bool]) -> str:
    """
    Convert a list of votes to a string representation.
    :param votes: list of boolean votes
    :return: string representation of the votes
    """
    return "".join("✅" if x else "❌" for x in votes)

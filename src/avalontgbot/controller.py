import json
import logging

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    Update,
)
from telegram.constants import PollType as POLLTYPE
from telegram.error import BadRequest
from telegram.ext import (
    ContextTypes,
)

from .constants import MANDATORY_ROLES, MAX_TEAM_REJECTS, MIN_PLAYERS
from .game import Game
from .gamephase import GamePhase as PHASE
from .player import Player
from .role import Role as ROLE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

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

        _ = await update.message.reply_text(
            "Game created! You are alone now... wait for some friends.\n",
            # reply_markup=telegram.ReplyKeyboardRemove(),
        )
    else:
        _ = await update.message.reply_text(
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
        _ = await update.message.reply_text(
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
            _ = await update.message.reply_text("You are already in the game")
        elif not game.is_ongoing:  # player is in the game, but not online
            game.player_join(p)

            if game.is_ongoing:
                # notify the group if everyone is online
                _ = await update.message.reply_text(
                    "Everyone is online again, the game can continue!"
                )
    else:
        # player is not in the game, so we create a new Player
        p = Player(user.id, user.full_name)
        if game.phase != PHASE.LOBBY:
            # game already started, cannot join
            _ = await update.message.reply_text(
                "The game has already started. You cannot join now."
            )
        else:
            game.player_join(p)

            text = (
                f"{user.mention_html()} has joined the game!\n"
                "Remember to start this bot in private chat\n"
                f"Players waiting: {', '.join(str(p) for p in game.players)}"
            )
            _ = await update.message.reply_html(text)

            if len(game.players) == 10:
                await _routine_start_game(context, game)

    return


async def handle_set_roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the setting of roles for the players in the game.
    """
    group_id = update.message.chat_id

    game = existingGames[group_id]

    # check if the requesting user is the creator
    if update.effective_user.id != game.creator.userid:
        _ = await update.message.reply_text("Only the creator can set roles.")
        return

    special_roles_str = list(
        str(x) for x in ROLE if x.is_special and x not in MANDATORY_ROLES
    )

    # set roles for the players
    _ = await _send_selection_poll(
        context,
        game.id,
        game.creator.userid,
        special_roles_str,
        "Select special roles",
        POLLTYPE.REGULAR,
        None,
    )


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
            _ = await update.message.reply_text(
                "You are not in the game. Please join first."
            )
        else:
            # notify the group about the new creator, in case the old one left
            # TODO: highlight the (new) creator
            old_creator_name = str(game.creator)

            # if there are no players left, remove the Game
            if not game.player_leave(player):
                # remove the game from the existing games
                del existingGames[group_id]

                text = "All players have left the game. The game has been removed."

            else:
                text = (
                    f"{user.mention_html()} has left the game!\n"
                    f" Players waiting: {', '.join(str(p) for p in game.players if p.is_online)}\n"
                )
                if old_creator_name != str(game.creator):
                    text += (
                        "The game creator has left!\n"
                        f"{game.creator.mention()} is the new creator.\n"
                    )

            _ = await update.message.reply_html(text)

    else:
        _ = await update.message.reply_text(
            "There is no game in this group. Please create one first."
        )


async def handle_pass_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the passing of the game creator role to another player.
    """

    group_id = update.message.chat_id
    game = existingGames[group_id]

    if game.lookup_player(update.effective_user.id) is not game.creator:
        raise KeyError("Only the creator can pass the host.")

    candidates = [str(x) for x in game.players if x is not game.creator]

    if len(candidates) == 0:
        raise ValueError(
            "There are not enough players to pass the host. At least 2 players are required."
        )
    elif len(candidates) == 1:
        # if there is only one candidate, pass the host immediately
        await _routine_pass_creator(0, game, context)
    else:
        _ = await _send_selection_poll(
            context,
            game.id,
            game.creator.userid,
            candidates,
            "Select a new host",
            POLLTYPE.REGULAR,
            None,
            False,  # only one answer allowed
        )


async def handle_start_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    """
    Handle the start of the game, checking for conditions such as creator and player count.
    """
    # if not update.message or not update.effective_user:
    #     # TODO: handle telegram errors
    #     return

    # # check if there is a game in the group
    # if (group_id := update.message.chat_id) not in existingGames.keys():
    #     _ = await update.message.reply_text(
    #         "There is no game in this group. Please create one first."
    #     )
    #     return

    game = existingGames[update.message.chat_id]

    # check if the requesting user is the creator
    if update.effective_user.id != game.creator.userid:
        raise ValueError("Only the creator can start the game.")

    # check if there are enough players
    if len(game.players) < MIN_PLAYERS:
        raise ValueError(
            "Not enough players to start the game. Minimum 5 players required."
        )

    if game.is_ongoing:
        raise ValueError("The game is already ongoing.")

    # this effectively starts the game
    await _routine_start_game(context, game)


async def handle_delete_game(update: Update):
    """
    Handle the deletion of a game.
    """
    # if not update.message or not update.effective_user:
    #     return
    #
    # group_id = update.message.chat_id
    #
    # # check if there is a game in the group
    # if group_id in existingGames.keys():
    #     game = existingGames[group_id]
    #
    #     # check if the requesting user is the creator
    #     if update.effective_user.id != game.creator.userid:
    #         _ = await update.message.reply_text("Only the creator can delete the game.")
    #         return
    #
    #     # remove the game from the existing games
    #     del existingGames[group_id]
    #
    #     _ = await update.message.reply_text("The game has been deleted.")
    # else:
    #     _ = await update.message.reply_text("There is no game in this group.")

    group_id = update.message.chat_id

    game = existingGames[group_id]

    if update.effective_user.id != game.creator.userid:
        raise ValueError("Only the creator can delete the game.")

    del existingGames[group_id]
    _ = await update.message.reply_text("The game has been deleted.")


async def _routine_start_game(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to start the game, setting up roles and notifying players.
    """
    game.start_game()

    try:
        for player in game.players:
            text = f"Your role is: {player.role}.\n"  # now role can't be None

            text += player.role.description()  # role description

            if not player.is_good():
                text += f"Your teammates are: {', '.join(str(p) for p in game.evil_list() if p != player)}.\n"

            if player.role == ROLE.MERLIN:
                text += f"Evil team is composed of: {', '.join(str(p) for p in game.evil_list())}.\n"

            _ = await context.bot.send_message(
                chat_id=player.userid,
                text=text,
                parse_mode="HTML",
            )
    except BadRequest as e:
        logger.error(f"Error with private message: {e}")
        _ = await context.bot.send_message(
            chat_id=game.id,
            text="Not all players started the bot in private! Game cannot start yet",
        )

    # TODO: wait players to start private chat to send this to public
    info_txt = (
        f"Game started with {len(game.players)} players.\n"
        f"Number of evil players: {len(game.evil_list())}\n"
        f"Number of good players: {len(game.players) - len(game.evil_list())}\n"
    )

    info_txt += "Special roles:\n"
    info_txt += "\n".join(str(role) for role in game.special_roles)

    info_txt += "Team sizes for turns:\n"
    info_txt += "\n".join(f"( {i + 1}:{x} )" for i, x in enumerate(game.team_sizes))

    if len(game.players) >= 7:
        info_txt += "Remember that fourth mission is special, you can make it successful even with a negative vote!\n"

    _ = await context.bot.send_message(
        chat_id=game.id,
        text=info_txt,
    )

    await _routine_pre_team_building(context, game)


async def _routine_pre_team_building(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to prepare the voting phase of the game (i.e. sending the poll to the team leader).
    """
    # notify players in the group about the voting phase
    text = (
        f"Turn {game.turn + 1} has started!\n"
        f"Next leaders will be: {', '.join(str(p) for p in game.players[game.leader_idx + 1 :] + game.players[: game.leader_idx])}\n"
        f"Next team sizes: {', '.join(str(x) for x in game.team_sizes[game.turn :])}\n\n"
        f"{game.players[game.leader_idx].mention()} is the team leader for this round.\n"
        "Wait for leader's team proposal.\n"
    )

    if game.is_special_turn():
        text += "⚠️ This is a special mission, you can make it succesful even with a negative vote!\n"

    _ = await context.bot.send_message(
        chat_id=game.id,
        text=text,
        parse_mode="HTML",
    )

    _ = await _send_selection_poll(
        context,
        game.id,
        game.players[game.leader_idx].userid,
        [str(x) for x in game.players],
        f"Leader, select a team of {game.team_sizes[game.turn]} players",
        POLLTYPE.REGULAR,
        None,
    )


async def _send_selection_poll(
    context: ContextTypes.DEFAULT_TYPE,
    game_id: int,
    recipient: int,
    opts_str: list[str],
    poll_msg: str,
    poll_type: POLLTYPE,
    correct_opt_id: int | None,
    are_multiple_answers: bool = True,
) -> Message:
    """
    Send a poll to the recipient with the given options.
    :param context: the context of the bot
    :param game: the game object
    :param recipient: the recipient of the poll (the team leader)
    :param people_name: the names of the players to be included in the poll
    :param poll_msg: the message to be sent with the poll
    :param poll_type: the type of the poll (regular or quiz)
    :param correct_opt_id: the index of the correct option (if any, for quiz polls)
    :param are_multiple_answers: whether the poll allows multiple answers
    """

    poll_kwargs = {
        "chat_id": recipient,
        "question": poll_msg,
        "options": opts_str,
        "is_anonymous": False,
        "type": poll_type,
        "allows_multiple_answers": are_multiple_answers,
    }

    if poll_type == "quiz" and correct_opt_id is not None:
        poll_kwargs["correct_option_id"] = correct_opt_id

    msg = await context.bot.send_poll(**poll_kwargs)  # pyright: ignore[reportArgumentType]

    payload = {
        msg.poll.id: (msg.poll, msg.message_id, game_id),  # pyright: ignore[reportOptionalMemberAccess]
    }
    context.bot_data.update(payload)

    return msg


async def handle_select_special_roles(
    aswer_roles: tuple[int, ...],
    message_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """
    Handle the selection of special roles for the players.
    """

    selected_roles = [list(ROLE)[i] for i in aswer_roles]

    game.set_special_roles(selected_roles)

    _ = await context.bot.stop_poll(
        chat_id=game.creator.userid,
        message_id=message_id,
        reply_markup=None,
    )

    _ = await context.bot.forward_message(
        chat_id=game.id,
        from_chat_id=game.creator.userid,
        message_id=message_id,
    )
    _ = await context.bot.delete_message(
        chat_id=game.creator.userid,
        message_id=message_id,
    )


async def handle_pass_creator_choice(
    answer: tuple[int, ...],
    message_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """
    Handle the choice of a new game creator.
    """
    await _routine_pass_creator(answer[0], game, context)

    _ = await context.bot.stop_poll(
        chat_id=game.creator.userid,
        message_id=message_id,
        reply_markup=None,
    )

    # delete the original message with the poll
    _ = await context.bot.delete_message(
        chat_id=game.creator.userid,
        message_id=message_id,
    )


async def _routine_pass_creator(
    new_creator_idx: int, game: Game, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Routine to pass the game creator role to a new player.
    """
    candidates = [x for x in game.players if x != game.creator]

    game.pass_creator(candidates[new_creator_idx])

    _ = await context.bot.send_message(
        chat_id=game.id,
        text=f"{game.creator.mention()} is the new host.",
        parse_mode="HTML",
    )


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
    # stop the poll if the team size is correct
    _ = await context.bot.stop_poll(
        chat_id=leader_userid,
        message_id=message_id,
        reply_markup=None,
    )

    # player order in poll has the same order as in game.players, so indexing is safe
    game.create_team([game.players[i] for i in answer_team])

    # close poll and update game state
    _ = await context.bot.send_message(
        text="Let's see if the others approve the team... go back to the game.",
        chat_id=leader_userid,
    )

    # forward the poll to the group chat
    _ = await context.bot.forward_message(
        chat_id=game.id,
        from_chat_id=leader_userid,
        message_id=message_id,
    )

    # delete the original message with the poll
    _ = await context.bot.delete_message(
        chat_id=leader_userid,
        message_id=message_id,
    )

    # go to the team approval phase
    # await _routine_pre_team_approval_phase(context, game)
    await _send_public_decision_message(game.players, context, game)


async def _send_public_decision_message(
    people: list[Player],
    context: ContextTypes.DEFAULT_TYPE,
    game: Game,
) -> None:
    """
    Send a public decision message to the group chat with inline buttons for approval or rejection.
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

    _ = await context.bot.send_message(
        chat_id=game.id,
        text=f"Needs to vote: {', '.join(p.mention() for p in people)}\n",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def _routine_pre_mission_phase(context: ContextTypes.DEFAULT_TYPE, game: Game):
    """
    Routine to prepare the mission phase of the game.
    """
    text = (
        "The team has been approved! Team, go vote for the success of the mission.\n"
        "Do you want to make the mission successful?\n"
        f"Missions so far: {_bool_to_emoji([x for x in game.missions if x is not None])}\n"
    )

    if game.is_special_turn():
        text += "⚠️ This is a special mission, you can make it succesful even with a negative vote!\n"

    # notify players in the group about the mission phase
    _ = await context.bot.send_message(
        chat_id=game.id,
        text=text,
    )

    await _send_public_decision_message(game.team, context, game)


async def button_vote_handler(
    query: CallbackQuery,
    buttons: InlineKeyboardMarkup | None,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    if not query.data:
        return

    data = json.loads(query.data)
    vote = data.get("vote")

    # assume the vote is valid, if not, we will change it later
    alert = "Vote received!"

    if not (game := existingGames.get(data.get("gid"))):
        _ = await query.answer(
            text="Game not found. Please try again later.",
            show_alert=True,
        )
        return

    player = game.lookup_player(query.from_user.id)

    list_to_check = [
        p
        for p in (game.team if game.phase == PHASE.QUEST else game.players)
        if p not in game.votes.keys()
    ]

    if player not in list_to_check:
        is_valid = is_voting_ended = False
        alert = "Vote not allowed"
    else:
        is_valid = True
        is_voting_ended = game.add_player_vote(
            # query.data is a string, so we need to convert it to a boolean
            player,
            vote == "yes",
        )
        # remove the player from the list to check
        list_to_check.remove(player)

    _ = await query.answer(text=alert, show_alert=not is_valid)

    # repeat the process until the voting is succesful
    if is_voting_ended:
        _ = await query.delete_message()
        if game.phase == PHASE.BUILD_TEAM:
            await _routine_post_team_approval_phase(context, game)
        elif game.phase == PHASE.QUEST:
            await _routine_post_mission_phase(context, game)
    elif is_valid:
        _ = await query.edit_message_text(
            text=f"People missing: {', '.join(p.mention() for p in list_to_check)}.\n",
            # remove the inline keyboard if the voting is ended
            reply_markup=buttons,
            parse_mode="HTML",
        )


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
        "The team was "
        f"{'approved' if approval_result else f'rejected (Times rejected: {game.rejection_count})'}!\n"
        f"Votes:\n{_bool_to_emoji(list(votes.values()), list(votes.keys()))}\n"
    )

    if 0 < game.rejection_count < MAX_TEAM_REJECTS:
        text += (
            "Vote will be repeated again.\n"
            f"⚠️ If the team is rejected {MAX_TEAM_REJECTS} times in a row, evil wins!\n"
        )

    # send the result to the group chat
    _ = await context.bot.send_message(
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
        f"Votes: {_bool_to_emoji(list(votes.values()))}\n"
        f"Missions results: {_bool_to_emoji([x for x in game.missions if x is not None])}\n"
    )
    # send the result to the group chat
    _ = await context.bot.send_message(
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
        _ = await context.bot.send_message(
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
    _ = await context.bot.send_message(
        chat_id=game.id,
        text="The evil team has a last chance to win the game. Assassin, choose a player to kill! If you choose Merlin, you win the game.",
    )

    goods = [x for x in game.players if x.is_good()]
    merlin_idx = [x.role for x in goods].index(ROLE.MERLIN)
    assassin_tg_id = game.players[
        [x.role for x in game.players].index(ROLE.ASSASSIN)
    ].userid

    _ = await _send_selection_poll(
        context,
        game.id,
        assassin_tg_id,
        [str(x) for x in goods],
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

    _ = await context.bot.stop_poll(
        chat_id=assassin.id,
        message_id=msg_id,
        reply_markup=None,
    )

    # TODO: handle possible errors
    assassin_guess = answer[0]

    game.update_winner_after_assassination(assassin_guess)

    _ = await assassin.forward_messages_to(
        game.id,
        [msg_id],  # requires sequence of messageIDs
    )

    await _routine_end_game(context, game)


async def _routine_end_game(context: ContextTypes.DEFAULT_TYPE, game: Game) -> None:
    _ = await context.bot.send_message(
        chat_id=game.id,
        text=f"{game.winner and 'Good' or 'Evil'} team wins the game!",
    )

    # send the final game state to the group chat
    final_state = (
        f"Let's reveal the roles!\n"
        "Evil team:\n"
        f"{', '.join(f'{p.role}: {str(p)}' for p in game.players if not p.is_good())}\n\n"
        "Good team:\n"
        f"{', '.join(f'{p.role}: {str(p)}' for p in game.players if p.is_good())}\n\n"
        f"Missions: {_bool_to_emoji([x for x in game.missions if x is not None])}\n"
    )

    _ = await context.bot.send_message(
        chat_id=game.id,
        text=final_state,
    )

    # cleanup the game
    del existingGames[game.id]


def _bool_to_emoji(bs: list[bool], players: list[Player] | None = None) -> str:
    """
    Convert a list of votes to a string representation.
    :param votes: list of boolean votes
    :param players: list of players corresponding to the votes
    :return: string representation of the votes
    """
    if not players:
        div = ""
        ps = ["" for _ in bs]
    else:
        div = "\n"
        ps = [str(p) for p in players]

    pairs = list(zip(bs, ps))

    return div.join(f"{'✅' if x else '❌'}{p}" for x, p in pairs)

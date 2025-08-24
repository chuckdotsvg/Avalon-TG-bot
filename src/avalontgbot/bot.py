import logging
import os
import pathlib

from dotenv import load_dotenv
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
)

from .controller import (
    button_vote_handler,
    handle_assassin_choice,
    handle_build_team_answer,
    handle_create_game,
    handle_delete_game,
    handle_join_game,
    handle_leave_game,
    handle_pass_host,
    handle_pass_host_choice,
    handle_select_special_roles,
    handle_set_roles,
    handle_start_game,
    existingGames,
)
from .gamephase import GamePhase as PHASE
from .role import Role

_ = load_dotenv()
telegram_token = os.getenv("TELEGRAM_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    text = "Hi, I'm your bot for playing The Resistance!\n"
    text += "Add me to a group chat to play with friends!\n"
    text += "Use /help to see the available commands."

    await message.reply_text(text) if message else None


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""

    text = "In order to use this bot, add it to a group chat and use the commands below.\n\n"

    # open commands.txt and read the content
    path = pathlib.Path(__file__).parent.parent.parent / "resources/commands.txt"
    if not path.exists():
        text += "Commands not found"
    else:
        text += path.read_text(encoding="utf-8").strip()

    await update.message.reply_text(text) if update.message else None

async def inforoles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message with the roles information considering the name given."""
    try:
        role_name = context.args[0].lower()
        role = next(r for r in Role if r.name.lower() == role_name)
        _ = await update.effective_message.reply_text(text=role.description(), parse_mode="HTML")
    except (IndexError, ValueError):
        logger.error(f"Error in inforoles: No role name provided")
        txt = ("Please provide a role name after the command, e.g. /inforoles Merlin\n"
            f"Available roles: {', '.join([str(r) for r in Role])}"
               )
        _ = await update.effective_message.reply_text(txt)
    except StopIteration as e:
        logger.error(f"Error in inforoles: {e}")
        _ = await update.effective_message.reply_text("Role not found. Please check the role name and try again.")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message with the rules of the game."""
    path = pathlib.Path(__file__).parent.parent.parent / "resources/rules.html"
    if not path.exists():
        text = "Rules not found"
    else:
        text = path.read_text(encoding="utf-8").strip()

    await update.message.reply_html(text) if update.message else None


async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await handle_create_game(update)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in create_game: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await handle_join_game(update, context)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in join_game: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await handle_leave_game(update)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in leave_game: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await handle_start_game(update, context)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in start_game: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def delete_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        await handle_delete_game(update)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in delete_game: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def set_roles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set roles for the game."""
    try:
        await handle_set_roles(update, context)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in set_roles: {e}")
        _ = await update.effective_message.reply_text(
            "An error occurred while setting roles. Please try again."
        )


async def pass_host(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set roles for the game."""
    try:
        await handle_pass_host(update, context)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in set_roles: {e}")
        _ = await update.effective_message.reply_text(str(e))


async def button_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    if not (query := update.callback_query):
        return

    msg = update.effective_message

    buttons = msg.reply_markup if msg else None

    await button_vote_handler(query, buttons, context)


async def receive_poll_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle poll answers."""
    try:
        answer = update.poll_answer
        # no options selected => vote retracted => no action
        if len(answer.option_ids) != 0:
            poll, poll_msg_id, game_id = context.bot_data[answer.poll_id]  # pyright: ignore[reportAny]

            # check if the poll is in the bot data, shouldn't happen
            game = existingGames[game_id]

            if not poll.allows_multiple_answers:
                await handle_pass_host_choice(
                    answer.option_ids, poll_msg_id, context, game
                )
            elif game.phase == PHASE.BUILD_TEAM:
                await handle_build_team_answer(
                    answer.option_ids, poll_msg_id, context, game
                )
            elif game.phase == PHASE.LAST_CHANCE:
                await handle_assassin_choice(
                    answer.option_ids, poll_msg_id, update, context, game
                )
            elif game.phase == PHASE.LOBBY:
                await handle_select_special_roles(
                    answer.option_ids, poll_msg_id, context, game
                )
    except BadRequest as e:
        logger.error(f"BadRequest in receive_poll_answer: {e}")
        _ = await context.bot.delete_message(
            # polls are private, so we send the message to the user
            chat_id=update.effective_sender.id,
            # if unbound is because the bot was restarted and the poll is not in bot_data anymore
            message_id=poll_msg_id,  # pyright: ignore[reportPossiblyUnboundVariable]
        )
    except (ValueError, Exception) as e:
        logger.error(f"Error in receive_poll_answer: {e}")
        _ = await context.bot.send_message(
            # polls are private, so we send the message to the user
            chat_id=update.effective_sender.id,
            text=str(e),
        )


def main() -> None:
    application = ApplicationBuilder().token(telegram_token).build()

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_game))
    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(CommandHandler("delete", delete_game))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("setroles", set_roles))
    application.add_handler(CommandHandler("passhost", pass_host))
    application.add_handler(CommandHandler("inforoles", inforoles))

    application.add_handler(CallbackQueryHandler(button_vote))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

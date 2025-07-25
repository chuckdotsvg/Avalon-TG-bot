import logging
import os
import pathlib

from dotenv import load_dotenv
from telegram import Update
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
    handle_select_special_roles,
    handle_set_roles,
    handle_start_game,
    existingGames,
)
from .gamephase import GamePhase as PHASE

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

    text = (
        "In order to use this bot, add it to a group chat and use the commands below.\n"
    )
    text += "Here are the available commands:\n"

    text += "suca"

    await update.message.reply_text(text) if update.message else None


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message with the rules of the game."""
    path = pathlib.Path(__file__).parent.parent.parent / "resources/rules.html"
    if not path.exists():
        text = "Rules not found"
    else:
        text = path.read_text(encoding="utf-8").strip()

    await update.message.reply_html(text) if update.message else None


async def pass_creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message:
        return

    args = context.args

    if not args or len(args) != 1:
        _ = await update.effective_message.reply_text(
            "Usage: /passcreator <user mention>"
        )
        return

    if user := update.effective_message.parse_entities().get("MENTION"):
        uid = await context.bot.get_chat(user)
        reply_text = f"Userid for {user} is: {uid.id}\n"
        _ = await update.effective_message.reply_text(reply_text)
    else:
        _ = await update.effective_message.reply_text(
            "Please mention a user to get their userid."
        )

    # show the entities in the message
    # entities = update.effective_message.parse_entities()
    # for entity_type, entity in entities.items():
    #     _ = await update.effective_message.reply_text(
    #             f"{entity_type}: {entity}"
    #     )

    return

    await handle_pass_creator(update.effective_message, context)


async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_create_game(update)


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_join_game(update, context)


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_leave_game(update)


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_start_game(update, context)


async def delete_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_delete_game(update)


async def set_roles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set roles for the game."""
    try:
        await handle_set_roles(update, context)
    except (ValueError, KeyError) as e:
        logger.error(f"Error in set_roles: {e}")
        _ = await update.effective_message.reply_text(
            "An error occurred while setting roles. Please try again."
        )


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
            poll_msg_id, game_id = context.bot_data[answer.poll_id]

            # check if the poll is in the bot data, shouldn't happen
            game = existingGames[game_id]

            if game.phase == PHASE.BUILD_TEAM:
                await handle_build_team_answer(answer.option_ids, poll_msg_id, context, game)
            elif game.phase == PHASE.LAST_CHANCE:
                await handle_assassin_choice(
                    answer.option_ids, poll_msg_id, update, context, game
                )
            elif game.phase == PHASE.LOBBY:
                await handle_select_special_roles(answer.option_ids, poll_msg_id, context, game)
    except Exception as e:
        logger.error(f"KeyError in receive_poll_answer: {e}")
        _ = await update.effective_message.reply_text(
            "An error occurred while processing your answer. Please try again."
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
    application.add_handler(CommandHandler("passcreator", pass_creator))
    # application.add_handler(CommandHandler("privatepoll", private_poll_test))
    application.add_handler(CallbackQueryHandler(button_vote))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

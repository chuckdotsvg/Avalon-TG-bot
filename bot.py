import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
)

import controller
from controller import (
    button_vote_handler,
    handle_build_team_answer,
    handle_create_game,
    handle_join_game,
    handle_leave_game,
    handle_start_game,
)
from gamephase import GamePhase as PHASE

_ = load_dotenv()
telegram_token = os.getenv("TELEGRAM_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

existingGames = controller.existingGames

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message

    text = "Hi, I'm your bot for playing The Resistance!\n"
    text += "Add me to a group chat to play with friends!\n"
    text += "Use /help to see the available commands."

    await message.reply_text(text) if message else None


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""

    text = "In order to use this bot, add it to a group chat and use the commands below.\n"
    text += "Here are the available commands:\n"

    for c, _ in COMMANDS:
        text += f"/{c.command} - {c.description}\n"

    await update.message.reply_text(text) if update.message else None


async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_create_game(update)


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_join_game(update, context)


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_leave_game(update)


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_start_game(update, context)


# async def test_private_msg_broadcast(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> None:
#     """Send a message when the command /test is issued."""
#     for user in existingGames[update.effective_chat.id].players:
#         await context.bot.send_message(
#             chat_id=user.userid,
#             text="This is a test message to all players in the game.",
#         )

async def build_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_build_team_request(update, context)


async def test_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_vote(update, context)


async def button_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    if not (query := update.callback_query):
        return

    await query.answer()

    if not query.message or not query.message.chat:
        return

    await button_vote_handler(query, context)


async def receive_poll_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle poll answers."""
    if not (answer := update.poll_answer) or not (msg := update.message):
        return

    if len(answer.option_ids) == 0:
        # no options selected => vote retracted => no action
        return

    # check if the poll is in the bot data
    if not (game := existingGames.get(int(context.bot_data.get(answer.poll_id) or 0))):
        return

    if game.phase == PHASE.BUILD_TEAM:
        await handle_build_team_answer(answer, msg.id, context, game)
    elif game.phase == PHASE.LAST_CHANCE:
        await handle_assassin_choice(msg.id, context, game.id)


# async def unknown_command_in_state(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> PHASE:
#     """Handle unknown commands in a state."""
#     if not (message := update.message) or not (chat := message.chat):
#         # error in telegram: restart
#         return PHASE.LOBBY
#
#     if not (game := existingGames.get(chat.id)):
#         return PHASE.LOBBY
#
#     await message.reply_text("You can't use this command now!")
#     return game.phase


COMMANDS = [
    (BotCommand("start", "Start the bot"), start),
    (BotCommand("help", "Show help message"), help_command),
    (BotCommand("create", "Create a new game"), create_game),
    (BotCommand("join", "Join an existing game"), join_game),
    (BotCommand("leave", "Leave the current game"), leave_game),
    (BotCommand("startgame", "Start the current game"), start_game),
]

def main() -> None:
    application = ApplicationBuilder().token(telegram_token).build()

    # application.add_handler(CommandHandler("pvtbroadcast", test_private_msg_broadcast))
    # application.add_handler(CommandHandler("testvote", test_vote))
    # application.add_handler(CommandHandler("buildteam", receive_poll_request))

    bot = application.bot
    _ = bot.set_my_commands([x[0] for x in COMMANDS])

    for c, handler in COMMANDS:
        application.add_handler(CommandHandler(c.command, handler))

    application.add_handler(CallbackQueryHandler(button_vote))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

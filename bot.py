import logging
import os
import json

import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

import controller
from controller import (
    button_vote_handler,
    handle_build_team_request,
    handle_create_game,
    handle_join_game,
    handle_leave_game,
    handle_start_game,
    handle_vote,
)
from game import Game

_ = load_dotenv()
telegram_token = os.getenv("TELEGRAM_TOKEN", "")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.WARNING
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message

    if message is None or user is None:
        return

    await message.reply_markdown_v2(
        rf"Hi {user.mention_markdown_v2()}\!",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""

    await update.message.reply_text("Help!")


async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_create_game(update, existingGames)


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_join_game(update, existingGames)


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_leave_game(update, existingGames)


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_start_game(update, context, existingGames)


async def test_private_msg_broadcast(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send a message when the command /test is issued."""
    for user in existingGames[update.effective_chat.id].players:
        await context.bot.send_message(
            chat_id=user.userid,
            text="This is a test message to all players in the game.",
        )


async def build_team(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_build_team_request(update, context, existingGames)


async def test_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_vote(update, context, existingGames)


async def button_vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses."""
    if not (query := update.callback_query):
        return

    await query.answer()

    data = json.loads(query.data)

    if (
        not query.message
        or not query.message.chat
        or not (game := existingGames.get(data["gid"]))
    ):
        return

    await button_vote_handler(query, game)


existingGames: dict[int, Game] = {}


def main() -> None:
    application = (
        ApplicationBuilder().token(telegram_token).build()
    )

    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(CommandHandler("create", create_game))
    application.add_handler(CommandHandler("start", start_game))
    application.add_handler(CommandHandler("pvtbroadcast", test_private_msg_broadcast))
    application.add_handler(CommandHandler("testvote", test_vote))

    application.add_handler(CallbackQueryHandler(button_vote))
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

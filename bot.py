import logging
import os

import telegram
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

import controller
from controller import handle_create_game, handle_join_game
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
    await handle_create_game(existingGames, update, context)

async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_join_game(update, existingGames)

async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await controller.handle_leave_game(update, existingGames)

existingGames: dict[int, Game] = {}

def main() -> None:
    application = ApplicationBuilder().token(telegram_token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CommandHandler("leave", join_game))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("creategame", create_game))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


async def ask_for_vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not user:
        return

    _ = await context.bot.send_message(
        chat_id=user.id,
        text="Please vote for the best option:\n1. Option A\n2. Option B\n3. Option C",
        reply_markup=telegram.ReplyKeyboardMarkup(
            keyboard=[
                [telegram.KeyboardButton(text="Option A")],
                [telegram.KeyboardButton(text="Option B")],
                [telegram.KeyboardButton(text="Option C")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )

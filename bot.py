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
    handle_assassin_choice,
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

    text = (
        "In order to use this bot, add it to a group chat and use the commands below.\n"
    )
    text += "Here are the available commands:\n"

    text += "suca"

    await update.message.reply_text(text) if update.message else None


async def create_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_create_game(update)


async def join_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_join_game(update, context)


async def leave_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_leave_game(update)


async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_start_game(update, context)


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
    if not (answer := update.poll_answer):
        return

    if len(answer.option_ids) == 0:
        # no options selected => vote retracted => no action
        return

    poll_msg_id, game_id = context.bot_data[answer.poll_id]

    # check if the poll is in the bot data
    if not (game := existingGames.get(game_id)):
        return

    if game.phase == PHASE.BUILD_TEAM:
        await handle_build_team_answer(answer.option_ids, poll_msg_id, context, game)
    elif game.phase == PHASE.LAST_CHANCE:
        await handle_assassin_choice(poll_msg_id, update, context, game.id)


async def receive_poll_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poll answers for testing purposes."""
    if not (answer := update.poll_answer):
        return

    msg_id = context.bot_data.get(answer.poll_id)

    if len(answer.option_ids) == 0:
        # no options selected => vote retracted => no action
        return
    elif len(answer.option_ids) == 2:
        # For testing, stop the poll if two options are selected
        await context.bot.stop_poll(chat_id=update.effective_user.id, message_id=msg_id)

        # await msg.stop_poll()
        # send message informing what options were selected
        msg = await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"You selected options: {', '.join(map(str, answer.option_ids))}. The poll has been stopped.",
        )

    else:
        # warning message
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="You can only select two options for this test poll. Please try again.",
        )


async def private_poll_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test command for private polls."""
    if not update.effective_message:
        return

    # Create a poll with options
    question = "Choose your favorite option:"
    options = ["Option 1", "Option 2", "Option 3"]

    # Send the poll to the user
    message = await context.bot.send_poll(
        chat_id=update.effective_user.id,  # Send to the user privately
        question=question,
        options=options,
        is_anonymous=False,  # Set to False to allow public voting
        allows_multiple_answers=True,  # Set to True if you want multiple answers
    )

    payload = {
        message.poll.id: message.message_id,
    }
    context.bot_data.update(payload)


def main() -> None:
    application = ApplicationBuilder().token(telegram_token).build()

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_game))
    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(CommandHandler("startgame", start_game))
    # application.add_handler(CommandHandler("privatepoll", private_poll_test))
    application.add_handler(CallbackQueryHandler(button_vote))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    # _ = application.bot.delete_webhook(drop_pending_updates=True)

    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()

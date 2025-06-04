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
    ConversationHandler,
    MessageHandler,
    PollAnswerHandler,
    filters,
)

import controller
from controller import (
    _handle_assassin_choice,
    button_vote_handler,
    handle_build_team_answer,
    handle_build_team_request,
    handle_create_game,
    handle_join_game,
    handle_leave_game,
    handle_start_game,
    handle_vote,
)
from game import Game
from gamephase import GamePhase as PHASE

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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""

    await update.message.reply_text("Help!") if update.message else None


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

    if (
        not query.message
        or not query.message.chat
    ):
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
    if not (
        game := existingGames.get(int(context.bot_data.get(answer.poll_id) or 0))
    ):
        return

    game_id = int(context.bot_data.get(answer.poll_id) or 0)

    if game.phase == PHASE.BUILD_TEAM:
        await handle_build_team_answer(answer, msg.id, context, game.id)
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




def main() -> None:
    application = ApplicationBuilder().token(telegram_token).build()

    # application.add_handler(CommandHandler("pvtbroadcast", test_private_msg_broadcast))
    # application.add_handler(CommandHandler("testvote", test_vote))
    # application.add_handler(CommandHandler("buildteam", receive_poll_request))

    application.add_handler(CallbackQueryHandler(button_vote))
    application.add_handler(CommandHandler("create", create_game))
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("join", join_game))
    application.add_handler(CommandHandler("leave", leave_game))
    application.add_handler(PollAnswerHandler(receive_poll_answer))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

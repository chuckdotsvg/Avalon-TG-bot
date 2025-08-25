# Avalon: The Resistance - Telegram Bot

A Telegram bot that implements the social deduction game **Avalon: The Resistance** online.

## Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/chuckdotsvg/Avalon-TG-bot
   cd Avalon-TG-bot
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Telegram bot:

   * Create a bot on Telegram via BotFather.
   * Add your bot token in the `.env` file.
   * Run the bot:

   ```bash
   cd src
   python -m avalontgbot
   ```

## How to Play

* **Start a Game**: A user types `/newgame`.
* **Join the Game**: Other players type `/join`.
* **Game Start**: The game starts automatically after reaching 10 players, or manually with `/startgame`.
* **Role Assignment**: Each player privately receives their role (Loyal Servant of Arthur or Minion of Mordred or many others, with possible special abilities).
* **Quest Phase**: A leader selects a team for a quest. All players vote to approve or reject the team.
* **Quest Outcome**: Selected team members secretly decide whether the quest succeeds or fails (Loyal Servants can only choose "success," Minions can also choose "fail").
* **Victory**: Loyal Servants win after 3 successful quests; Minions win after 3 failed quests. However, if Loyal Servants win, the Assassin gets a chance to identify Merlin: if successful, the Minions win instead.

## Available Roles

* **Loyal Servant of Arthur**: No special ability, must deduce roles.
* **Merlin**: Knows the Minions of Mordred (except Mordred himself), but must remain hidden from the Assassin.
* **Percival**: Knows who could be Merlin but may be confused by Morgana.
* **Minions of Mordred**: Know each other and try to sabotage quests.
* **Morgana**: Appears as Merlin to Percival.
* **Mordred**: Hidden from Merlin.
* **Assassin**: At the end of the game, may attempt to identify Merlin.
* **Oberon**: A Minion who does not reveal himself to other Minions.

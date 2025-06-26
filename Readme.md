# Binance P2P Telegram Bot

This is a Telegram bot that tracks Binance P2P trading opportunities between USDT and AZN. It scans prices, notifies you of profit chances, and helps you record trades.

---

## How to Use

1. **Deploy on Railway**

   - Fork or clone this repo.
   - Make sure you have a Telegram bot token (get one from [BotFather](https://t.me/BotFather)).
   - Go to [Railway.app](https://railway.app) and create a new project.
   - Connect your GitHub repo.
   - Add an environment variable called `BOT_TOKEN` with your Telegram bot token.
   - Deploy the project.
   - Wait until it’s live and visit the Railway URL to confirm the bot is running.

2. **Start the Bot**

   - Open Telegram and send `/start` to your bot.
   - You will get a menu with options like Daily Stats, Weekly Stats, and toggling scanning.

3. **Commands and Features**

   - The bot checks Binance P2P prices at an interval you can set.
   - If it finds a good buy-sell profit opportunity, it notifies you.
   - You can record if you took the trade and the amount invested.
   - View your trade stats by day, week, or month.

---

## Running Locally

If you want to run the bot on your own machine:

- Make sure Python 3.11+ is installed.
- Install dependencies:

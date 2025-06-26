import os
import time
import threading
import json
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Flask app to keep Railway happy
app = Flask(__name__)

@app.route('/')
def home():
    return "Binance Bot Alive"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# Load Telegram bot token from env var
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable not set")
    exit(1)

scan_interval = 60
target_yield = 0.01
last_found = None
running = False
user_chat_id = None  # Will be set on /start command

trades_file = "trades.json"

def load_trades():
    try:
        with open(trades_file, 'r') as f:
            return json.load(f)
    except:
        return []

def save_trades(trades):
    with open(trades_file, 'w') as f:
        json.dump(trades, f, indent=2)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Daily Stats", callback_data='stats_daily'),
         InlineKeyboardButton("📈 Weekly Stats", callback_data='stats_weekly')],
        [InlineKeyboardButton("📅 Monthly Stats", callback_data='stats_monthly'),
         InlineKeyboardButton("📋 All Trades", callback_data='all_trades')],
        [InlineKeyboardButton("✅ Check Now", callback_data='check'),
         InlineKeyboardButton("⚙️ Settings", callback_data='settings')],
        [InlineKeyboardButton("🔁 Toggle Scanning", callback_data='toggle')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu():
    keyboard = [
        [InlineKeyboardButton("⏱ Change Interval", callback_data='change_interval'),
         InlineKeyboardButton("🎯 Change Yield", callback_data='change_yield')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_trade_decision_menu(buy_price, sell_price, profit):
    keyboard = [
        [InlineKeyboardButton("✅ Bought", callback_data=f'bought_{buy_price}_{sell_price}_{profit}'),
         InlineKeyboardButton("❌ Didn't Buy", callback_data='not_bought')],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

def calculate_stats(trades, days):
    cutoff_date = datetime.now() - timedelta(days=days)
    filtered_trades = [t for t in trades if datetime.fromisoformat(t['date']) >= cutoff_date]
    
    if not filtered_trades:
        return "No trades found for this period."
    
    total_trades = len(filtered_trades)
    total_investment = sum(t['amount'] for t in filtered_trades)
    total_profit = sum(t['profit'] for t in filtered_trades)
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    roi = (total_profit / total_investment * 100) if total_investment > 0 else 0

    return (f"📊 Stats ({days} days):\n"
            f"🔢 Total trades: {total_trades}\n"
            f"💰 Total invested: {total_investment:.2f} AZN\n"
            f"📈 Total profit: {total_profit:.2f} AZN\n"
            f"📊 Average profit: {avg_profit:.2f} AZN\n"
            f"📊 ROI: {roi:.2f}%")

def scan_binance():
    global last_found, user_chat_id
    try:
        buy_resp = requests.post("https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search", json={
            "page": 1,
            "rows": 5,
            "payTypes": [],
            "asset": "USDT",
            "fiat": "AZN",
            "tradeType": "BUY"
        }).json()

        sell_resp = requests.post("https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search", json={
            "page": 1,
            "rows": 5,
            "payTypes": [],
            "asset": "USDT",
            "fiat": "AZN",
            "tradeType": "SELL"
        }).json()

        best_buy = float(buy_resp["data"][0]["adv"]["price"])
        best_sell = float(sell_resp["data"][0]["adv"]["price"])

        profit = round(best_sell - best_buy, 3)
        last_found = (best_buy, best_sell, profit)

        if profit >= target_yield and user_chat_id:
            message = (f"💰 Opportunity Found!\n\n"
                       f"🟢 Buy at: {best_buy} AZN\n"
                       f"🔴 Sell at: {best_sell} AZN\n"
                       f"📈 Profit: {profit} AZN\n\n"
                       "Did you take this trade?")
            reply_markup = get_trade_decision_menu(best_buy, best_sell, profit)
            telegram_app.bot.send_message(chat_id=user_chat_id, text=message, reply_markup=reply_markup)

    except Exception as e:
        print("Error while scanning:", e)

def scanner_loop():
    global running
    while running:
        scan_binance()
        time.sleep(scan_interval)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_chat_id
    user_chat_id = update.effective_chat.id
    status = "🟢 Running" if running else "🔴 Stopped"
    message = (f"👋 Welcome to Binance P2P Bot!\n\n"
               f"Status: {status}\n"
               f"Interval: {scan_interval}s\n"
               f"Yield Target: {target_yield} AZN")
    await update.message.reply_text(message, reply_markup=get_main_menu())

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scan_interval, target_yield, running

    query = update.callback_query
    await query.answer()

    if query.data == 'main_menu':
        status = "🟢 Running" if running else "🔴 Stopped"
        message = (f"🏠 Main Menu\n\n"
                   f"Status: {status}\n"
                   f"Interval: {scan_interval}s\n"
                   f"Yield Target: {target_yield} AZN")
        await query.edit_message_text(message, reply_markup=get_main_menu())
    
    elif query.data == 'settings':
        message = (f"⚙️ Settings\n\n"
                   f"Current interval: {scan_interval}s\n"
                   f"Current yield target: {target_yield} AZN")
        await query.edit_message_text(message, reply_markup=get_settings_menu())
    
    elif query.data.startswith('stats_'):
        trades = load_trades()
        period = query.data.split('_')[1]
        days_map = {'daily': 1, 'weekly': 7, 'monthly': 30}
        days = days_map.get(period, 1)
        stats = calculate_stats(trades, days)
        stats += f"\n\n🕐 Updated: {datetime.now().strftime('%H:%M:%S')}"
        await query.edit_message_text(stats, reply_markup=get_main_menu())
    
    elif query.data == 'all_trades':
        trades = load_trades()
        if not trades:
            message = "📋 No trades recorded yet."
        else:
            message = "📋 All Trades:\n\n"
            for i, trade in enumerate(trades[-10:], 1):
                date = datetime.fromisoformat(trade['date']).strftime("%m/%d %H:%M")
                message += f"{i}. {date} - {trade['amount']:.2f} AZN → +{trade['profit']:.2f} AZN\n"
            if len(trades) > 10:
                message += f"\n... and {len(trades)-10} more trades"
        await query.edit_message_text(message, reply_markup=get_main_menu())
    
    elif query.data == 'check':
        scan_binance()
        if last_found:
            message = (f"✅ Manual Check:\n"
                       f"🟢 Buy: {last_found[0]} AZN\n"
                       f"🔴 Sell: {last_found[1]} AZN\n"
                       f"📈 Profit: {last_found[2]} AZN\n\n"
                       f"🕐 {datetime.now().strftime('%H:%M:%S')}")
            if last_found[2] >= target_yield:
                message += "\n\nDid you take this trade?"
                reply_markup = get_trade_decision_menu(last_found[0], last_found[1], last_found[2])
            else:
                reply_markup = get_main_menu()
            await query.edit_message_text(message, reply_markup=reply_markup)
        else:
            await query.edit_message_text(f"❌ No data available\n🕐 {datetime.now().strftime('%H:%M:%S')}", reply_markup=get_main_menu())
    
    elif query.data == 'change_interval':
        await query.edit_message_text("⏱ Send new interval in seconds:", reply_markup=get_settings_menu())
        context.user_data['changing'] = 'interval'
    
    elif query.data == 'change_yield':
        await query.edit_message_text("🎯 Send new yield (e.g. 0.02):", reply_markup=get_settings_menu())
        context.user_data['changing'] = 'yield'
    
    elif query.data == 'toggle':
        running = not running
        if running:
            threading.Thread(target=scanner_loop, daemon=True).start()
            message = "🟢 Scanning started."
        else:
            message = "🔴 Scanning stopped."
        await query.edit_message_text(message, reply_markup=get_main_menu())
    
    elif query.data.startswith('bought_'):
        parts = query.data.split('_')
        buy_price, sell_price, profit = float(parts[1]), float(parts[2]), float(parts[3])
        await query.edit_message_text("💰 Enter the amount you invested (in AZN):")
        context.user_data['pending_trade'] = {
            'buy_price': buy_price,
            'sell_price': sell_price,
            'profit_per_unit': profit
        }
    
    elif query.data == 'not_bought':
        await query.edit_message_text("✅ Trade not taken. Continuing to monitor...", reply_markup=get_main_menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global scan_interval, target_yield
    mode = context.user_data.get('changing')
    pending_trade = context.user_data.get('pending_trade')

    if mode == 'interval':
        try:
            scan_interval = int(update.message.text)
            await update.message.reply_text(f"✅ Interval set to {scan_interval} seconds.", reply_markup=get_settings_menu())
        except:
            await update.message.reply_text("❌ Invalid number.", reply_markup=get_settings_menu())
        context.user_data['changing'] = None

    elif mode == 'yield':
        try:
            target_yield = float(update.message.text)
            await update.message.reply_text(f"✅ Yield threshold set to {target_yield} AZN.", reply_markup=get_settings_menu())
        except:
            await update.message.reply_text("❌ Invalid number.", reply_markup=get_settings_menu())
        context.user_data['changing'] = None

    elif pending_trade:
        try:
            amount = float(update.message.text)
            profit = (amount / pending_trade['buy_price']) * pending_trade['profit_per_unit']
            
            trade = {
                'date': datetime.now().isoformat(),
                'buy_price': pending_trade['buy_price'],
                'sell_price': pending_trade['sell_price'],
                'amount': amount,
                'profit': profit
            }
            
            trades = load_trades()
            trades.append(trade)
            save_trades(trades)
            
            message = (f"✅ Trade recorded!\n"
                       f"💰 Amount: {amount:.2f} AZN\n"
                       f"📈 Profit: {profit:.2f} AZN")
            await update.message.reply_text(message, reply_markup=get_main_menu())
            context.user_data['pending_trade'] = None
        except:
            await update.message.reply_text("❌ Invalid amount. Please enter a number:", reply_markup=get_main_menu())

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CallbackQueryHandler(handle_buttons))
telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))

keep_alive()

print("✅ Bot is running...")
telegram_app.run_polling()

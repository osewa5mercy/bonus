import os
import logging
import datetime
import random
from telebot import TeleBot, types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
if not BOT_TOKEN:
    logging.error("TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

bot = TeleBot(BOT_TOKEN)

# Simple in-memory storage (for production, use a database)
user_data = {}  # user_id: {"bonus": 0, "last_claim": None, "streak": 0, "total_claimed": 0}

# Bonus amounts
BONUS_RANGES = {"min": 5, "max": 50}

# Streak multipliers
STREAK_MULTIPLIERS = {
    0: 1.0, 1: 1.0, 2: 1.1, 3: 1.2, 4: 1.3,
    5: 1.5, 7: 2.0, 10: 2.5, 15: 3.0, 30: 5.0
}

# Bonus levels
BONUS_LEVELS = {
    0: "⭐ Starter",
    100: "🥉 Bronze",
    300: "🥈 Silver",
    600: "🥇 Gold",
    1000: "💎 Platinum",
    1500: "👑 Diamond",
    2500: "🌟 Legendary"
}

# --- Helper Functions ---

def get_streak_multiplier(streak):
    """Get multiplier based on streak length"""
    if streak >= 30:
        return STREAK_MULTIPLIERS[30]
    elif streak >= 15:
        return STREAK_MULTIPLIERS[15]
    elif streak >= 10:
        return STREAK_MULTIPLIERS[10]
    elif streak >= 7:
        return STREAK_MULTIPLIERS[7]
    elif streak >= 5:
        return STREAK_MULTIPLIERS[5]
    elif streak >= 3:
        return STREAK_MULTIPLIERS[3]
    elif streak >= 2:
        return STREAK_MULTIPLIERS[2]
    else:
        return STREAK_MULTIPLIERS[0]

def get_bonus_level(total_bonus):
    """Get user level based on total bonus"""
    level = "⭐ Starter"
    for threshold, name in sorted(BONUS_LEVELS.items(), reverse=True):
        if total_bonus >= threshold:
            level = name
            break
    return level

def can_claim_bonus(user_id):
    """Check if user can claim bonus today"""
    if user_id not in user_data:
        return True, None
    
    last_claim = user_data[user_id].get("last_claim")
    if not last_claim:
        return True, None
    
    today = datetime.datetime.now().date()
    last_date = datetime.datetime.fromisoformat(last_claim).date()
    
    if today > last_date:
        return True, None
    elif today == last_date:
        return False, "✅ You already claimed today's bonus!"
    else:
        return True, None

def calculate_bonus(user_id):
    """Calculate bonus amount with streak multiplier"""
    base_bonus = random.randint(BONUS_RANGES["min"], BONUS_RANGES["max"])
    streak = user_data.get(user_id, {}).get("streak", 0)
    multiplier = get_streak_multiplier(streak)
    bonus = int(base_bonus * multiplier)
    
    # Random bonus (15% chance)
    if random.random() < 0.15:
        bonus = bonus * 2
        return bonus, "🎉 DOUBLE BONUS!"
    
    return bonus, ""

def format_bonus_message(user_id, bonus_amount, bonus_type):
    """Format the bonus claiming message"""
    user_name = user_data[user_id].get("name", "User")
    total_bonus = user_data[user_id]["bonus"]
    streak = user_data[user_id]["streak"]
    level = get_bonus_level(total_bonus)
    
    message = (
        f"🎁 **Bonus Claimed!**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {user_name}\n"
        f"💰 **Bonus:** +{bonus_amount} points\n"
        f"{bonus_type}\n"
        f"🔥 **Streak:** {streak} days\n"
        f"📊 **Total:** {total_bonus} points\n"
        f"🏅 **Level:** {level}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
    )
    
    # Motivational messages
    if streak >= 30:
        message += "\n🏆 **LEGENDARY!** 30-day streak!"
    elif streak >= 15:
        message += "\n🌟 **AMAZING!** 15 days strong!"
    elif streak >= 7:
        message += "\n⭐ **GREAT!** One week streak!"
    elif streak >= 3:
        message += "\n💪 **Keep going!**"
    elif streak == 1:
        message += "\n🎯 **Day 1!** Come back tomorrow!"
    
    return message

def get_leaderboard():
    """Get top 10 users by bonus"""
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["bonus"], reverse=True)
    return sorted_users[:10]

# --- Command Handlers ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Welcome message"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id not in user_data:
        user_data[user_id] = {
            "bonus": 0,
            "last_claim": None,
            "streak": 0,
            "total_claimed": 0,
            "name": user_name
        }
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎁 Claim Bonus", callback_data="claim_bonus"),
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
    )
    markup.add(
        InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard"),
        InlineKeyboardButton("ℹ️ About", callback_data="about")
    )
    
    welcome_text = (
        f"👋 Welcome, {user_name}!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🎁 **Bonus Bot**\n\n"
        f"Collect free virtual bonuses daily!\n"
        f"• 🎁 Daily bonus claims\n"
        f"• 🔥 Streak multipliers\n"
        f"• 🏅 Level up system\n"
        f"• 🏆 Leaderboard competition\n\n"
        f"**Start earning now:**"
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.message_handler(commands=['bonus'])
def claim_bonus_command(message):
    """Claim bonus via command"""
    handle_claim_bonus(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show stats via command"""
    handle_stats(message.chat.id, message.from_user.id)

@bot.message_handler(commands=['leaderboard'])
def leaderboard_command(message):
    """Show leaderboard via command"""
    handle_leaderboard(message.chat.id)

@bot.message_handler(commands=['help'])
def send_help(message):
    """Help command"""
    help_text = (
        "📖 **Commands**\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "• `/start` - Main menu\n"
        "• `/bonus` - Claim daily bonus\n"
        "• `/stats` - Your stats\n"
        "• `/leaderboard` - Top users\n"
        "• `/help` - This message\n\n"
        "🎁 **How it works:**\n"
        "Claim daily bonus points\n"
        "Build streaks for multipliers\n"
        "Level up through ranks\n"
        "Compete on leaderboard\n\n"
        "📌 **No real money. Just fun!**"
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Handle any other messages"""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📂 Menu", callback_data="start"))
    
    response = (
        "💡 **Use commands or buttons:**\n\n"
        "• `/start` - Main menu\n"
        "• `/bonus` - Claim bonus\n"
        "• `/stats` - Your stats\n"
        "• `/leaderboard` - Top users"
    )
    bot.reply_to(message, response, parse_mode='Markdown', reply_markup=markup)

# --- Handler Functions ---

def handle_claim_bonus(chat_id, user_id):
    """Handle bonus claiming"""
    if user_id not in user_data:
        bot.send_message(chat_id, "⚠️ Use /start first!", parse_mode='Markdown')
        return
    
    can_claim, message = can_claim_bonus(user_id)
    if not can_claim:
        last_claim = user_data[user_id]["last_claim"]
        last_date = datetime.datetime.fromisoformat(last_claim).date()
        next_date = last_date + datetime.timedelta(days=1)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 My Stats", callback_data="my_stats"))
        
        bot.send_message(
            chat_id,
            f"⏰ {message}\n"
            f"📅 **Next bonus:** {next_date.strftime('%B %d, %Y')}",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return
    
    bonus_amount, bonus_type = calculate_bonus(user_id)
    
    user_data[user_id]["bonus"] += bonus_amount
    user_data[user_id]["total_claimed"] += bonus_amount
    user_data[user_id]["last_claim"] = datetime.datetime.now().isoformat()
    user_data[user_id]["streak"] += 1
    user_data[user_id]["name"] = user_data[user_id].get("name", "User")
    
    result_message = format_bonus_message(user_id, bonus_amount, bonus_type)
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats"),
        InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")
    )
    markup.add(InlineKeyboardButton("🎁 Claim Again Tomorrow", callback_data="claim_bonus"))
    
    bot.send_message(
        chat_id,
        result_message,
        parse_mode='Markdown',
        reply_markup=markup
    )

def handle_stats(chat_id, user_id):
    """Show user stats"""
    if user_id not in user_data:
        bot.send_message(chat_id, "⚠️ Use /start first!", parse_mode='Markdown')
        return
    
    data = user_data[user_id]
    streak = data["streak"]
    total_bonus = data["bonus"]
    total_claimed = data["total_claimed"]
    level = get_bonus_level(total_bonus)
    multiplier = get_streak_multiplier(streak)
    
    sorted_users = sorted(user_data.items(), key=lambda x: x[1]["bonus"], reverse=True)
    rank = next((i+1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), "N/A")
    
    # Next level progress
    next_level = None
    next_threshold = None
    for threshold, name in sorted(BONUS_LEVELS.items()):
        if total_bonus < threshold:
            next_level = name
            next_threshold = threshold
            break
    
    progress_text = ""
    if next_level and next_threshold:
        progress = int((total_bonus / next_threshold) * 100)
        progress_text = f"📈 **Next Level:** {next_level} ({progress}%)"
    
    stats_text = (
        f"📊 **Your Stats**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 **User:** {data['name']}\n"
        f"🎁 **Total Bonus:** {total_bonus}\n"
        f"📈 **Total Claimed:** {total_claimed}\n"
        f"🏅 **Level:** {level}\n"
        f"{progress_text}\n"
        f"🔥 **Streak:** {streak} days\n"
        f"📈 **Multiplier:** {multiplier}x\n"
        f"🏆 **Rank:** #{rank} of {len(user_data)}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎁 Claim Bonus", callback_data="claim_bonus"),
        InlineKeyboardButton("🔙 Menu", callback_data="start")
    )
    
    bot.send_message(chat_id, stats_text, parse_mode='Markdown', reply_markup=markup)

def handle_leaderboard(chat_id):
    """Show leaderboard"""
    top_users = get_leaderboard()
    
    if not top_users:
        leaderboard_text = "🏆 **Leaderboard**\n━━━━━━━━━━━━━━━━━━━━\n\nNo users yet. Be the first!"
    else:
        leaderboard_text = "🏆 **Leaderboard**\n━━━━━━━━━━━━━━━━━━━━\n\n"
        for i, (user_id, data) in enumerate(top_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            name = data.get("name", "User")
            bonus = data["bonus"]
            level = get_bonus_level(bonus)
            streak = data.get("streak", 0)
            leaderboard_text += f"{medal} **{name}** - {bonus} pts ({level} 🔥{streak}d)\n"
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎁 Claim Bonus", callback_data="claim_bonus"),
        InlineKeyboardButton("📊 My Stats", callback_data="my_stats")
    )
    markup.add(InlineKeyboardButton("🔙 Menu", callback_data="start"))
    
    bot.send_message(chat_id, leaderboard_text, parse_mode='Markdown', reply_markup=markup)

# --- Callback Handlers ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle button clicks"""
    try:
        if call.data == "start":
            send_welcome(call.message)
            bot.answer_callback_query(call.id)
            
        elif call.data == "claim_bonus":
            handle_claim_bonus(call.message.chat.id, call.from_user.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "my_stats":
            handle_stats(call.message.chat.id, call.from_user.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "leaderboard":
            handle_leaderboard(call.message.chat.id)
            bot.answer_callback_query(call.id)
            
        elif call.data == "about":
            about_text = (
                "🤖 **About Bonus Bot**\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Free daily virtual bonuses!\n\n"
                "✅ Claim daily bonuses\n"
                "✅ Build streaks\n"
                "✅ Level up through ranks\n"
                "✅ Compete on leaderboard\n\n"
                "📌 **No real money**\n"
                "🎯 **Just for fun!**\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"👥 {len(user_data)} users"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔙 Menu", callback_data="start"))
            
            bot.edit_message_text(
                about_text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown',
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        logging.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, text="❌ Error", show_alert=True)

# --- Main Execution ---

if __name__ == '__main__':
    logging.info("🚀 Bonus Bot is starting...")
    logging.info(f"✅ Bot online! Users: {len(user_data)}")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logging.error(f"Bot polling failed: {e}")

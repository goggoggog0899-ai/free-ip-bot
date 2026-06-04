import logging
import sqlite3
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Config
BOT_TOKEN = "8216212884:AAGHjg4_oGmP06U8W5IovjEupqh0CYFpofw"
ADMIN_ID = 7219908425
BOT_NAME = "FREE IP BOT"

REQUIRED_CHANNEL_URL = "https://t.me/your_channel_username" 
REQUIRED_GROUP_URL = "https://t.me/+uRJNemDkh2FiOGY1"      
PAYMENT_CHANNEL = "@your_payment_channel" 

SUPPORT_MSG, BROADCAST_MSG, ADD_IP, ADMIN_REPLY = range(4)
DB_FILE = 'bot_database.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            balance REAL DEFAULT 0.0,
            refers INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

main_menu_keyboard = [["👥 Refer & Earn 👥", "💼 My Wallet"], ["🏪 Withdraw", "📞 Support"]]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)

admin_keyboard = [["📢 Broadcast Message", "➕ Add IP Stock"], ["📊 Total Users", "🔙 Main Menu"]]
admin_markup = ReplyKeyboardMarkup(admin_keyboard, resize_keyboard=True)

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, balance, refers, is_verified FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"name": row[0], "balance": row[1], "refers": row[2], "is_verified": bool(row[3])}
    return None

def add_user(user_id, name):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def update_user_balance_and_ref(user_id, balance_add, ref_add):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ?, refers = refers + ? WHERE user_id = ?", (balance_add, ref_add, user_id))
    conn.commit()
    conn.close()

def set_user_verified(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_verified = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_total_users_count():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_user_ids():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_ip_to_db(ip):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ip_stock (ip_address) VALUES (?)", (ip,))
    conn.commit()
    conn.close()

def pop_ip_from_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, ip_address FROM ip_stock LIMIT 1")
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM ip_stock WHERE id = ?", (row[0],))
        conn.commit()
        conn.close()
        return row[1]
    conn.close()
    return None

def get_ip_stock_count():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM ip_stock")
    count = cursor.fetchone()[0]
    conn.close()
    return count

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = user.id
    
    user_data = get_user(chat_id)
    if not user_data:
        add_user(chat_id, user.first_name)
        if context.args:
            try:
                referrer_id = int(context.args[0])
                referrer_data = get_user(referrer_id)
                if referrer_data and referrer_id != chat_id:
                    update_user_balance_and_ref(referrer_id, 100.0, 1)
                    try:
                        await context.bot.send_message(chat_id=referrer_id, text="🎉 আপনার আমন্ত্রণে একজন নতুন সদস্য যুক্ত হয়েছে! +100 MB যুক্ত হয়েছে।")
                    except: pass
            except ValueError: pass

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=REQUIRED_CHANNEL_URL)],
        [InlineKeyboardButton("💬 Join Our Group", url=REQUIRED_GROUP_URL)],
        [InlineKeyboardButton("🟢 Joined & Verified ✅", callback_data="verify_join")]
    ]
    await update.message.reply_text(
        "🔒 বটের মেইন মেনু আনলক করতে আমাদের চ্যানেল এবং গ্রুপে জয়েন করে নিচের ভেরিফাই বাটনে চাপ দিন।",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def verify_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    set_user_verified(user_id)
    try:
        await query.message.delete() 
    except: pass
    await context.bot.send_message(chat_id=user_id, text="🌳 Welcome To Main Menu", reply_markup=main_menu_markup)

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    
    user_data = get_user(user_id)
    if not user_data or not user_data["is_verified"]:
        await update.message.reply_text("দয়া করে প্রথমে /start দিয়ে টাস্ক পূরণ করুন।")
        return

    if text == "👥 Refer & Earn 👥":
        invite_link = f"https://t.me/{context.bot.username}?start={user_id}"
        ref_count = user_data["refers"]
        msg = f"🙌 Total Refers = {ref_count} User(s)\n\n🙌 Your Invite Link = {invite_link}\n\n🔀 Refer Now. 100 MB per referral"
        await update.message.reply_text(msg)

    elif text == "💼 My Wallet":
        msg = f"👤 User = : {user_data['name']}\n\n💰 Balance : {user_data['balance']} MB\n\n⚠️ Note: Share with your friends now to earn more."
        await update.message.reply_text(msg)

    elif text == "🏪 Withdraw":
        stock_count = get_ip_stock_count()
        await update.message.reply_text(f"📊 বর্তমানে বটের স্টকে {stock_count} টি আইপি লাইভ আছে।")
        if user_data["balance"] >= 200.0 and user_data["refers"] >= 2:
            if stock_count > 0:
                allocated_ip = pop_ip_from_db()
                update_user_balance_and_ref(user_id, -200.0, 0)
                await update.message.reply_text(f"🎉 আপনার উইথড্র সফল হয়েছে! আপনার আইপি নিচে দেওয়া হলো:\n\n🔑 ` {allocated_ip} `")
                remaining_stock = get_ip_stock_count()
                if remaining_stock <= 5:
                    try:
                        await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ **স্টক অ্যালার্ট!** স্টকে আর মাত্র {remaining_stock} টি আইপি আছে। দ্রুত আরও স্টক যোগ করুন।")
                    except: pass
                payment_msg = (
                    f"💸 WITHDRAW REQUEST CONFIRMATION\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🆔 User ID: {user_id}\n"
                    f"🔗 Quantity: 1\n"
                    f"💵 Amount: 200.0 MB\n"
                    f"Status: ✅ Withdrawal successful!\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"🔒 Your request has been securely recorded.\n\n"
                    f"🤖 @{context.bot.username}\n"
                    f"Powered By: {BOT_NAME}"
                )
                try: await context.bot.send_message(chat_id=PAYMENT_CHANNEL, text=payment_msg)
                except: pass
            else:
                await update.message.reply_text("😢 দুঃখিত! এই মুহূর্তে আইপি স্টক খালি আছে। অ্যাডমিনকে স্টক যোগ করতে বলুন।")
        else:
            await update.message.reply_text("⚠️ উইথড্র করার জন্য আপনার অন্তত ২০০ MB ব্যালেন্স এবং ২টি সফল রেফার থাকতে হবে।")

    elif text == "📞 Support":
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_menu")]]
        await update.message.reply_text("📝 আপনার সমস্যাটি লিখে পাঠান। সরাসরি অ্যাডমিন উত্তর দেবে।\nবের হতে নিচের বাটনে চাপুন।", reply_markup=InlineKeyboardMarkup(keyboard))
        return SUPPORT_MSG

    elif text == "/admin" and user_id == ADMIN_ID:
        await update.message.reply_text("👋 স্বাগতম অ্যাডমিন প্যানেলে:", reply_markup=admin_markup)
    elif text == "📢 Broadcast Message" and user_id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]]
        await update.message.reply_text("📢 সব ইউজারের উদ্দেশ্যে মেসেজটি লিখুন:", reply_markup=InlineKeyboardMarkup(keyboard))
        return BROADCAST_MSG
    elif text == "➕ Add IP Stock" and user_id == ADMIN_ID:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")]]
        await update.message.reply_text("➕ স্টকে যোগ করার জন্য আইপি (IP) পাঠান:", reply_markup=InlineKeyboardMarkup(keyboard))
        return ADD_IP
    elif text == "📊 Total Users" and user_id == ADMIN_ID:
        total_users = get_total_users_count()
        stock_count = get_ip_stock_count()
        await update.message.reply_text(f"📊 বটের মোট ইউজার: {total_users} জন\n📦 বর্তমান আইপি স্টক: {stock_count} টি")
    elif text == "🔙 Main Menu":
        await update.message.reply_text("🌳 Main Menu", reply_markup=main_menu_markup)

async def receive_support_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    keyboard = [[InlineKeyboardButton("✍️ Reply to User", callback_data=f"reply_{user.id}")]]
    support_report = f"📩 নতুন সাপোর্ট মেসেজ!\nFrom: {user.first_name}\nID: `{user.id}`\n\n💬 মেসেজ: {text}"
    await context.bot.send_message(chat_id=ADMIN_ID, text=support_report, reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.reply_text("✅ আপনার মেসেজটি পাঠানো হয়েছে।", reply_markup=main_menu_markup)
    return ConversationHandler.END

async def handle_admin_reply_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    target_user_id = query.data.split("_")[1]
    context.user_data["reply_to"] = target_user_id
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"ইউজার `{target_user_id}` এর জন্য আপনার রিপ্লাই মেসেজটি লিখুন:")
    return ADMIN_REPLY

async def send_reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_user_id = context.user_data.get("reply_to")
    reply_text = update.message.text
    try:
        await context.bot.send_message(chat_id=target_user_id, text=f"💬 **অ্যাডমিন থেকে রিপ্লাই:**\n\n{reply_text}")
        await update.message.reply_text("✅ রিপ্লাইটি ইউজারের কাছে চলে গেছে।", reply_markup=admin_markup)
    except:
        await update.message.reply_text("❌ মেসেজ পাঠানো যায়নি। হয়তো ইউজার বটটি ব্লক করেছে।", reply_markup=admin_markup)
    return ConversationHandler.END

async def receive_broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    all_users = get_all_user_ids()
    count = 0
    for u_id in all_users:
        try:
            await context.bot.send_message(chat_id=u_id, text=f"📢 **অ্যাডমিন নোটিশ:**\n\n{text}")
            count += 1
        except: pass
    await update.message.reply_text(f"✅ সফলভাবে {count} জন ইউজারের কাছে মেসেজ পাঠানো হয়েছে।", reply_markup=admin_markup)
    return ConversationHandler.END

async def receive_ip_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ip_text = update.message.text
    add_ip_to_db(ip_text)
    stock_count = get_ip_stock_count()
    await update.message.reply_text(f"✅ আইপি স্টকে যুক্ত হয়েছে। মোট স্টক: {stock_count} টি", reply_markup=admin_markup)
    return ConversationHandler.END

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "back_to_menu":
        await query.message.delete()
        await context.bot.send_message(chat_id=query.from_user.id, text="🌳 Main Menu", reply_markup=main_menu_markup)
    elif data == "back_to_admin":
        await query.message.delete()
        await context.bot.send_message(chat_id=query.from_user.id, text="👨‍💼 Admin Menu", reply_markup=admin_markup)
    return ConversationHandler.END

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^📞 Support$'), handle_menu),
            MessageHandler(filters.Regex('^📢 Broadcast Message$'), handle_menu),
            MessageHandler(filters.Regex('^➕ Add IP Stock$'), handle_menu),
            CallbackQueryHandler(handle_admin_reply_click, pattern="^reply_\\d+$")
        ],
        states={
            SUPPORT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_msg)],
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_msg)],
            ADD_IP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ip_stock)],
            ADMIN_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_reply_to_user)]
        },
        fallbacks=[CallbackQueryHandler(cancel_action, pattern="^(back_to_menu|back_to_admin)$")],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(verify_join, pattern="^verify_join$"))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("Bot is running...")
    application.run_polling()

if __name__ == '__main__':
    main()
    

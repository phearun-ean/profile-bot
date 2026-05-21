import os
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID", 0))
BIRD_BOT_LINK = "https://t.me/bird_nest_house_bot"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

CURRENT_MODE = "business"
user_state = {}

# ---------- Keyboards ----------
def business_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛒 Buy Now", url=BIRD_BOT_LINK),
        InlineKeyboardButton("📦 Wholesale Inquiry", callback_data="wholesale"),
        InlineKeyboardButton("❓ Learn More", callback_data="learn"),
        InlineKeyboardButton("💬 Talk to Human", callback_data="human")
    )
    return markup

# ---------- Owner commands ----------
@bot.message_handler(commands=['mode'])
def change_mode(message):
    if message.chat.id != OWNER_ID:
        return
    parts = message.text.split()
    if len(parts) > 1 and parts[1] in ["business", "daily"]:
        global CURRENT_MODE
        CURRENT_MODE = parts[1]
        bot.reply_to(message, f"✅ Mode switched to *{CURRENT_MODE}*", parse_mode="Markdown")

@bot.message_handler(commands=['myid'])
def get_my_id(message):
    bot.reply_to(message, f"Your chat ID: `{message.chat.id}`", parse_mode="Markdown")

# ---------- Helper: process any incoming message ----------
def process_message(message):
    uid = message.chat.id

    # Ignore messages from yourself (the owner)
    if uid == OWNER_ID:
        return

    # If the user is in the middle of a wholesale form
    if uid in user_state:
        handle_wholesale_step(message)
        return

    if CURRENT_MODE == "business":
        bot.send_message(
            uid,
            "👋 *Welcome to Bird’s Nest House!*\n\n"
            "I’m an automated assistant. How can I help you today?",
            parse_mode="Markdown",
            reply_markup=business_keyboard()
        )
    else:
        bot.send_message(
            uid,
            "Hey! I saw your message – I’ll get back to you as soon as I’m free.\n"
            "If it’s urgent, send a 🔥 and I’ll be notified."
        )

# ---------- Normal message handler (private chats) ----------
@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_normal_message(message):
    process_message(message)

# ---------- Business message handler (Secretary Mode / profile) ----------
@bot.business_message_handler(func=lambda m: True, content_types=['text'])
def handle_business_message(message):
    process_message(message)

# ---------- Callback button handler ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    uid = call.message.chat.id

    if call.data == "learn":
        bot.send_message(
            uid,
            "🍃 *Edible Bird’s Nest* is a premium superfood known for:\n"
            "• Boosting immunity\n"
            "• Improving skin complexion\n"
            "• Supporting respiratory health\n\n"
            "All our nests are 100% natural, hand‑cleaned, and sourced sustainably.\n"
            "Ready to try? Tap *Buy Now* to visit our shop!",
            parse_mode="Markdown",
            reply_markup=business_keyboard()
        )
        bot.answer_callback_query(call.id)

    elif call.data == "wholesale":
        user_state[uid] = {"step": "ask_name"}
        bot.send_message(uid, "📋 Let’s set up a wholesale account. First, what’s your full name?")
        bot.answer_callback_query(call.id)

    elif call.data == "human":
        bot.send_message(
            OWNER_ID,
            f"📩 *Human reply requested* by {call.from_user.first_name}"
            f"{(' @' + call.from_user.username) if call.from_user.username else ''}\n"
            f"User ID: `{uid}`",
            parse_mode="Markdown"
        )
        bot.send_message(uid, "Thanks! I’ve notified [Phearun] and they’ll reply personally soon.")
        bot.answer_callback_query(call.id)

# ---------- Wholesale form steps ----------
def handle_wholesale_step(message):
    uid = message.chat.id
    state = user_state.get(uid)
    step = state["step"]

    if step == "ask_name":
        state["name"] = message.text.strip()
        state["step"] = "ask_company"
        bot.reply_to(message, "Great, thanks! What’s your company name?")
    elif step == "ask_company":
        state["company"] = message.text.strip()
        state["step"] = "ask_quantity"
        bot.reply_to(message, "And roughly how many kilograms per month are you looking for?")
    elif step == "ask_quantity":
        state["quantity"] = message.text.strip()
        summary = (
            f"📦 *New Wholesale Lead*\n"
            f"Name: {state.get('name')}\n"
            f"Company: {state.get('company')}\n"
            f"Estimated monthly qty: {state.get('quantity')}\n"
            f"User ID: `{uid}`"
            f"{(' @' + message.from_user.username) if message.from_user.username else ''}"
        )
        bot.send_message(OWNER_ID, summary, parse_mode="Markdown")
        bot.send_message(uid, "✅ Thank you! Your enquiry has been forwarded. [Phearun] will contact you shortly.")
        del user_state[uid]

# ---------- Vercel webhook ----------
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def home():
    return 'Bot is running'
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)
from geopy.distance import geodesic

# --- Configuration ---
BOT_TOKEN = "7270460184:AAG2Btncm-5ybcXTsOhNpX6AytamVHCK5kA"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Data & Localization ---
# A simple database of hospitals in Assam (lat, lon). Expand this list for a real application.
HOSPITALS = {
    "Gauhati Medical College and Hospital (GMCH)": (26.1433, 91.7898),
    "Assam Medical College and Hospital (AMCH), Dibrugarh": (27.4628, 94.9120),
    "Silchar Medical College and Hospital (SMCH)": (24.7826, 92.7938),
    "Fakhruddin Ali Ahmed Medical College, Barpeta": (26.3315, 91.0028),
}

# Text for multi-language support (English and Assamese)
TEXTS = {
    'en': {
        'welcome': "Welcome! Please choose your language.",
        'menu_intro': "How can I assist you today? Please choose an option:",
        'first_aid_prompt': "Please select a topic for first-aid guidance:",
        'find_hospital_prompt': "Please share your location to find nearby hospitals.",
        'share_location_btn': "Share My Location",
        'location_received': "Thank you. Searching for nearby hospitals...",
        'no_hospitals_found': "Sorry, I couldn't find any registered hospitals nearby.",
        'nearby_hospitals_header': "Here are the nearest hospitals:",
        'book_intro': "Let's schedule a free tele-consultation. What is the patient's full name?",
        'ask_age': "Got it. What is the patient's age?",
        'ask_symptoms': "Thank you. Please briefly describe the symptoms.",
        'booking_confirmed': "Thank you! Your consultation is tentatively booked. A representative will contact you soon to confirm the time.\n\nName: {name}\nAge: {age}\nSymptoms: {symptoms}",
        'booking_cancelled': "Booking cancelled.",
        'disclaimer': "⚠️ DISCLAIMER: This is an informational bot and not a substitute for professional medical advice. In case of an emergency, please contact your nearest hospital immediately."
    },
    'as': {
        'welcome': "স্বাগতম! অনুগ্ৰহ কৰি আপোনাৰ ভাষা বাছনি কৰক।",
        'menu_intro': "মই আপোনাক কেনেদৰে সহায় কৰিব পাৰোঁ? অনুগ্ৰহ কৰি এটা বিকল্প বাছনি কৰক:",
        'first_aid_prompt': "প্ৰাথমিক চিকিৎসাৰ বাবে এটা বিষয় বাছনি কৰক:",
        'find_hospital_prompt': "ওচৰৰ চিকিৎসালয় বিচাৰিবলৈ অনুগ্ৰহ কৰি আপোনাৰ অৱস্থান শ্বেয়াৰ কৰক।",
        'share_location_btn': "মোৰ অৱস্থান শ্বেয়াৰ কৰক",
        'location_received': "ধন্যবাদ। ওচৰৰ চিকিৎসালয়সমূহ বিচৰা হৈছে...",
        'no_hospitals_found': "క్షমা কৰিব, মই ওচৰত কোনো পঞ্জীভুক্ত চিকিৎসালয় বিচাৰি নাপালো।",
        'nearby_hospitals_header': "ইয়াত ওচৰৰ চিকিৎসালয়সমূহ আছে:",
        'book_intro': "আহক এটা বিনামূলীয়া টেলি-পৰামৰ্শৰ সময় নিৰ্ধাৰণ কৰোঁ। ৰোগীৰ সম্পূৰ্ণ নাম কি?",
        'ask_age': "বুজিছো। ৰোগীৰ বয়স কিমান?",
        'ask_symptoms': "ধন্যবাদ। অনুগ্ৰহ কৰি লক্ষণসমূহ সংক্ষেপে বৰ্ণনা কৰক।",
        'booking_confirmed': "ধন্যবাদ! আপোনাৰ পৰামৰ্শৰ বাবে অনুৰোধ গ্ৰহণ কৰা হৈছে। আমাৰ প্ৰতিনিধিয়ে সোনকালেই আপোনাক সময় নিশ্চিত কৰিবলৈ যোগাযোগ কৰিব।\n\nনাম: {name}\nবয়স: {age}\nলক্ষণ: {symptoms}",
        'booking_cancelled': "বুকিং বাতিল কৰা হ'ল।",
        'disclaimer': "⚠️ দাবিত্যাগ: এইটো এটা তথ্যমূলক বট আৰু পেছাদাৰী চিকিৎসা পৰামৰ্শৰ বিকল্প নহয়। জৰুৰীকালীন অৱস্থাত, অনুগ্ৰহ কৰি ওচৰৰ চিকিৎসালয়ত সোনকালে যোগাযোগ কৰক।"
    }
}
# First aid data (keep it simple and verified)
FIRST_AID_DATA = {
    'en': {
        'fever': "Fever: 1. Rest. 2. Drink plenty of fluids. 3. Use a cool cloth on the forehead. 4. If fever is high or persists, see a doctor.",
        'burn': "Minor Burn: 1. Cool the burn under cool running water for 10-15 minutes. 2. Cover with a sterile bandage. 3. Do not apply ice or butter. For severe burns, seek medical help immediately.",
        'cut': "Minor Cut: 1. Apply gentle pressure with a clean cloth to stop bleeding. 2. Clean the wound with water. 3. Apply an antiseptic and cover with a sterile bandage."
    },
    'as': {
        'fever': "জ্বৰ: ১. জিৰণি লওক। ২. প্ৰচুৰ পৰিমাণে পানী খাওক। ৩. কপালত ঠাণ্ডা কাপোৰ দিয়ক। ৪. যদি জ্বৰ বেছি হয় বা নেৰে, চিকিৎসকৰ পৰামৰ্শ লওক।",
        'burn': "সৰু পোৰা: ১. পোৰা ঠাইখিনি ১০-১৫ মিনিট ঠাণ্ডা পানীৰ তলত ৰাখক। ২. বীজাণুমুক্ত বেণ্ডেজৰে ঢাকি দিয়ক। ৩. বৰফ বা মাখন নালগাব। গুৰুতৰভাৱে পুৰিলে তৎকালীনভাৱে চিকিৎসকৰ সহায় লওক।",
        'cut': "সৰু কটা: ১. তেজ বন্ধ কৰিবলৈ পৰিষ্কাৰ কাপোৰেৰে লাহেকৈ হেঁচা দিয়ক। ২. ঘা টুকুৰা পানীৰে চাফা কৰক। ৩. এন্টিচেপ্টিক লগাই বীজাণুমুক্ত বেণ্ডেজেৰে ঢাকি দিয়ক।"
    }
}

# --- Conversation States for Booking ---
SELECTING_ACTION, BOOKING_NAME, BOOKING_AGE, BOOKING_SYMPTOMS = range(4)

# --- Bot Functions ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays language selection on /start."""
    keyboard = [
        [InlineKeyboardButton("English", callback_data='lang_en')],
        [InlineKeyboardButton("অসমীয়া (Assamese)", callback_data='lang_as')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(TEXTS['en']['welcome'], reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles all button presses."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get('lang', 'en') # Default to English

    # Language selection
    if query.data.startswith('lang_'):
        lang = query.data.split('_')[1]
        context.user_data['lang'] = lang
        await query.edit_message_text(text=TEXTS[lang]['disclaimer'])
        await show_main_menu(update, context)
        return SELECTING_ACTION

    # First Aid Topic selection
    if query.data.startswith('aid_'):
        topic = query.data.split('_')[1]
        await query.edit_message_text(text=FIRST_AID_DATA[lang][topic])
        await show_main_menu(update, context) # Show menu again
        return SELECTING_ACTION
    
    return SELECTING_ACTION


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the main menu keyboard."""
    lang = context.user_data.get('lang', 'en')
    keyboard = [
        [KeyboardButton("⚕️ " + ("First-Aid Tips" if lang == 'en' else "প্ৰাথমিক চিকিৎসা"))],
        [KeyboardButton("🏥 " + ("Find Nearby Hospital" if lang == 'en' else "ওচৰৰ চিকিৎসালয় বিচাৰক"))],
        [KeyboardButton("📅 " + ("Book Tele-consultation" if lang == 'en' else "টেলি-পৰামৰ্শ বুক কৰক"))],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    # If it's a callback query, send a new message. If it's a regular message, reply to it.
    if update.callback_query:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=TEXTS[lang]['menu_intro'], reply_markup=reply_markup)
    else:
        await update.message.reply_text(TEXTS[lang]['menu_intro'], reply_markup=reply_markup)


async def handle_text_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text choices from the main menu."""
    text = update.message.text
    if "First-Aid" in text or "প্ৰাথমিক চিকিৎসা" in text:
        return await first_aid(update, context)
    if "Find Nearby Hospital" in text or "ওচৰৰ চিকিৎসালয় বিচাৰক" in text:
        return await find_hospital_start(update, context)
    if "Book Tele-consultation" in text or "টেলি-পৰামৰ্শ বুক কৰক" in text:
        return await book_start(update, context)


async def first_aid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows first-aid options."""
    lang = context.user_data.get('lang', 'en')
    keyboard = [
        [InlineKeyboardButton("Fever / জ্বৰ", callback_data='aid_fever')],
        [InlineKeyboardButton("Minor Burn / সৰু পোৰা", callback_data='aid_burn')],
        [InlineKeyboardButton("Minor Cut / সৰু কটা", callback_data='aid_cut')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(TEXTS[lang]['first_aid_prompt'], reply_markup=reply_markup)

async def find_hospital_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Asks for user's location."""
    lang = context.user_data.get('lang', 'en')
    keyboard = [[KeyboardButton(TEXTS[lang]['share_location_btn'], request_location=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(TEXTS[lang]['find_hospital_prompt'], reply_markup=reply_markup)

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receives user location and finds nearest hospitals."""
    lang = context.user_data.get('lang', 'en')
    user_location = (update.message.location.latitude, update.message.location.longitude)
    await update.message.reply_text(TEXTS[lang]['location_received'])

    distances = []
    for name, coords in HOSPITALS.items():
        dist = geodesic(user_location, coords).km
        distances.append((dist, name, coords))

    distances.sort() # Sort by distance, ascending

    if not distances:
        await update.message.reply_text(TEXTS[lang]['no_hospitals_found'])
        return

    response = TEXTS[lang]['nearby_hospitals_header'] + "\n\n"
    for dist, name, coords in distances[:3]: # Show top 3
        maps_link = f"https://www.google.com/maps/search/?api=1&query={coords[0]},{coords[1]}"
        response += f"🏥 *{name}*\n"
        response += f"   - Distance: {dist:.2f} km\n"
        response += f"   - [Open in Maps]({maps_link})\n\n"
        
    await update.message.reply_markdown(response, disable_web_page_preview=True)
    await show_main_menu(update, context)

async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the booking conversation."""
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(TEXTS[lang]['book_intro'])
    return BOOKING_NAME

async def book_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores name and asks for age."""
    context.user_data['booking_name'] = update.message.text
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(TEXTS[lang]['ask_age'])
    return BOOKING_AGE

async def book_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores age and asks for symptoms."""
    context.user_data['booking_age'] = update.message.text
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(TEXTS[lang]['ask_symptoms'])
    return BOOKING_SYMPTOMS

async def book_symptoms(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores symptoms and confirms booking."""
    context.user_data['booking_symptoms'] = update.message.text
    lang = context.user_data.get('lang', 'en')
    
    # In a real app, you would save this data to a database.
    # For now, we just confirm it to the user.
    confirmation_text = TEXTS[lang]['booking_confirmed'].format(
        name=context.user_data['booking_name'],
        age=context.user_data['booking_age'],
        symptoms=context.user_data['booking_symptoms']
    )
    await update.message.reply_text(confirmation_text)
    
    # Clean up user_data
    del context.user_data['booking_name']
    del context.user_data['booking_age']
    del context.user_data['booking_symptoms']
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the booking conversation."""
    lang = context.user_data.get('lang', 'en')
    await update.message.reply_text(TEXTS[lang]['booking_cancelled'])
    await show_main_menu(update, context)
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Conversation handler for booking process
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(📅 Book Tele-consultation|📅 টেলি-পৰামৰ্শ বুক কৰক)$'), book_start)],
        states={
            BOOKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_name)],
            BOOKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_age)],
            BOOKING_SYMPTOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_symptoms)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(conv_handler)
    # These handlers need to be checked after the conversation handler
    application.add_handler(MessageHandler(filters.Regex('^(⚕️ First-Aid Tips|⚕️ প্ৰাথমিক চিকিৎসা)$'), first_aid))
    application.add_handler(MessageHandler(filters.Regex('^(🏥 Find Nearby Hospital|🏥 ওচৰৰ চিকিৎসালয় বিচাৰক)$'), find_hospital_start))
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))
    
    print("Bot is running... Press Ctrl-C to stop.")
    application.run_polling()

if __name__ == '__main__':
    main()

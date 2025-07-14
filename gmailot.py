advanced_gmail_bot.py.wsgi
import os
import logging
import json
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    CallbackQueryHandler, 
    ConversationHandler, 
    MessageHandler, 
    Filters, 
    CallbackContext
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot states for conversation
QUANTITY, COUNTRY, RECOVERY_EMAIL, PASSWORD, TWO_FACTOR, NOTES, CONFIRMATION = range(7)

# Countries available for selection
COUNTRIES = {
    "US": "🇺🇸 USA",
    "DE": "🇩🇪 Germany",
    "UK": "🇬🇧 United Kingdom",
    "MX": "🇲🇽 Mexico",
    "BR": "🇧🇷 Brazil"
}

# Bot configuration
TOKEN = os.getenv("7576472064:AAG557fuTOucK71bV7Esbv-77CrRSGit1hw")
ADMIN_ID = os.getenv("5781612136")  # Your personal Telegram ID for notifications

# Database file (simple JSON for demo)
DB_FILE = "orders.json"

def load_orders():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"orders": []}

def save_order(order):
    orders = load_orders()
    order_id = len(orders["orders"]) + 1
    order["id"] = order_id
    order["created_at"] = datetime.now().isoformat()
    order["status"] = "Pending"
    orders["orders"].append(order)
    with open(DB_FILE, "w") as f:
        json.dump(orders, f, indent=2)
    return order_id

def start(update: Update, context: CallbackContext) -> None:
    """Send welcome message and start order process."""
    user = update.message.from_user
    context.user_data.clear()
    
    welcome = (
        "👋 *Welcome to Gmail Account Creator Bot!*\n\n"
        "I can create custom Gmail accounts for you with specific requirements.\n\n"
        "To start an order, use /order command or click the button below."
    )
    
    keyboard = [[InlineKeyboardButton("📝 Place Order", callback_data='start_order')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        welcome, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def start_order(update: Update, context: CallbackContext) -> int:
    """Begin the order process."""
    query = update.callback_query
    query.answer()
    query.edit_message_text(
        "📦 *Let's create your custom Gmail accounts!*\n\n"
        "First, how many accounts do you need? (1-100)\n\n"
        "_Example: 10_",
        parse_mode='Markdown'
    )
    return QUANTITY

def get_quantity(update: Update, context: CallbackContext) -> int:
    """Get quantity of accounts needed."""
    text = update.message.text
    try:
        quantity = int(text)
        if 1 <= quantity <= 100:
            context.user_data['quantity'] = quantity
            update.message.reply_text(
                "✅ Great! Now select the country for your accounts:",
                reply_markup=country_keyboard()
            )
            return COUNTRY
        else:
            update.message.reply_text("⚠️ Please enter a number between 1 and 100.")
            return QUANTITY
    except ValueError:
        update.message.reply_text("⚠️ Please enter a valid number.")
        return QUANTITY

def country_keyboard():
    """Create country selection keyboard."""
    keyboard = []
    for code, name in COUNTRIES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f'country_{code}')])
    return InlineKeyboardMarkup(keyboard)

def select_country(update: Update, context: CallbackContext) -> int:
    """Handle country selection."""
    query = update.callback_query
    query.answer()
    country_code = query.data.split('_')[1]
    context.user_data['country'] = country_code
    
    query.edit_message_text(
        f"🌎 Selected: {COUNTRIES[country_code]}\n\n"
        "Now please enter the *recovery email* for these accounts.\n\n"
        "_This is the email that will be used to recover the accounts if needed._",
        parse_mode='Markdown'
    )
    return RECOVERY_EMAIL

def get_recovery_email(update: Update, context: CallbackContext) -> int:
    """Get recovery email address."""
    email = update.message.text
    # Basic email validation
    if '@' in email and '.' in email.split('@')[-1]:
        context.user_data['recovery_email'] = email
        update.message.reply_text(
            "📝 Now enter the *password* you want for these accounts.\n\n"
            "_Example: MySecurePassword123_",
            parse_mode='Markdown'
        )
        return PASSWORD
    else:
        update.message.reply_text("⚠️ Please enter a valid email address.")
        return RECOVERY_EMAIL

def get_password(update: Update, context: CallbackContext) -> int:
    """Get password for accounts."""
    password = update.message.text
    if len(password) >= 6:
        context.user_data['password'] = password
        keyboard = [
            [InlineKeyboardButton("✅ Yes", callback_data='2fa_yes')],
            [InlineKeyboardButton("❌ No", callback_data='2fa_no')]
        ]
        update.message.reply_text(
            "🔒 Do you need *Two-Factor Authentication (2FA)* setup?\n\n"
            "This includes:\n"
            "- Phone verification\n"
            "- Backup codes generation\n"
            "- Google Authenticator setup",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TWO_FACTOR
    else:
        update.message.reply_text("⚠️ Password must be at least 6 characters.")
        return PASSWORD

def set_2fa(update: Update, context: CallbackContext) -> int:
    """Set 2FA preference."""
    query = update.callback_query
    query.answer()
    choice = query.data.split('_')[1]
    context.user_data['2fa'] = (choice == 'yes')
    
    query.edit_message_text(
        "📝 Any additional notes or special requests?\n\n"
        "_Example: 'Need accounts created with specific names'_\n"
        "Or type /skip if none",
        parse_mode='Markdown'
    )
    return NOTES

def get_notes(update: Update, context: CallbackContext) -> int:
    """Get additional notes."""
    if update.message.text.lower() != '/skip':
        context.user_data['notes'] = update.message.text
    
    # Show order summary for confirmation
    order = context.user_data
    summary = (
        "📋 *Order Summary*\n\n"
        f"• Quantity: {order.get('quantity', 'N/A')}\n"
        f"• Country: {COUNTRIES.get(order.get('country', ''), 'N/A')}\n"
        f"• Recovery Email: {order.get('recovery_email', 'N/A')}\n"
        f"• Password: ||{order.get('password', 'N/A')}||\n"
        f"• 2FA Setup: {'Yes' if order.get('2fa', False) else 'No'}\n"
        f"• Notes: {order.get('notes', 'None')}\n\n"
        "Please confirm your order:"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Confirm Order", callback_data='confirm_order')],
        [InlineKeyboardButton("❌ Cancel Order", callback_data='cancel_order')]
    ]
    
    update.message.reply_text(
        summary,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRMATION

def skip_notes(update: Update, context: CallbackContext) -> int:
    """Skip notes entry."""
    return get_notes(update, context)

def confirm_order(update: Update, context: CallbackContext) -> int:
    """Finalize and save the order."""
    query = update.callback_query
    query.answer()
    
    if query.data == 'confirm_order':
        # Save order to database
        order = context.user_data
        order_id = save_order(order)
        
        # Notify user
        query.edit_message_text(
            f"🎉 *Order #{order_id} Received!*\n\n"
            "Your order has been placed successfully.\n"
            "We'll notify you when your accounts are ready.\n\n"
            "Estimated completion time: 24-48 hours.",
            parse_mode='Markdown'
        )
        
        # Send notification to admin
        notify_admin(context.bot, order, order_id, query.from_user)
        
        return ConversationHandler.END
    else:
        query.edit_message_text("❌ Order canceled.")
        return ConversationHandler.END

def notify_admin(bot, order, order_id, user):
    """Send order notification to admin."""
    if not ADMIN_ID:
        logger.warning("Admin ID not set - skipping notification")
        return
        
    message = (
        "🚨 *New Gmail Account Order!*\n\n"
        f"• Order ID: #{order_id}\n"
        f"• User: {user.full_name} (@{user.username or 'N/A'})\n"
        f"• User ID: {user.id}\n"
        f"• Quantity: {order['quantity']}\n"
        f"• Country: {COUNTRIES[order['country']]}\n"
        f"• Recovery Email: {order['recovery_email']}\n"
        f"• 2FA Setup: {'Yes' if order.get('2fa', False) else 'No'}\n"
        f"• Notes: {order.get('notes', 'None')}\n\n"
        f"Password: `{order['password']}`"
    )
    
    bot.send_message(
        chat_id=5781612136,
        text=message,
        parse_mode='Markdown'
    )

def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel the current operation."""
    update.message.reply_text('❌ Operation canceled.')
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    # Create the Updater and pass it your bot's token.
    updater = Updater(7576472064:AAG557fuTOucK71bV7Esbv-77CrRSGit1hw)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Conversation handler for orders
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('order', start_order), 
                     CallbackQueryHandler(start_order, pattern='^start_order$')],
        states={
            QUANTITY: [MessageHandler(Filters.text & ~Filters.command, get_quantity)],
            COUNTRY: [CallbackQueryHandler(select_country, pattern='^country_')],
            RECOVERY_EMAIL: [MessageHandler(Filters.text & ~Filters.command, get_recovery_email)],
            PASSWORD: [MessageHandler(Filters.text & ~Filters.command, get_password)],
            TWO_FACTOR: [CallbackQueryHandler(set_2fa, pattern='^2fa_')],
            NOTES: [
                MessageHandler(Filters.text & ~Filters.command, get_notes),
                CommandHandler('skip', skip_notes)
            ],
            CONFIRMATION: [CallbackQueryHandler(confirm_order, pattern='^(confirm_order|cancel_order)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Register commands
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()

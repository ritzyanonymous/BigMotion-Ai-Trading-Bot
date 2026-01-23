"""
BigMotion Trading Bot - Telegram License Sales Bot
Automated license generation, payment processing, and delivery

Features:
- Interactive menu for license purchase
- Multiple payment methods (Crypto, Paystack, PayPal)
- Automatic license generation and delivery
- Renewal management
- Customer support integration

Setup:
1. Get bot token from @BotFather
2. Configure payment processors
3. Set webhook or run with polling
4. Deploy on server (24/7 operation)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes,
    MessageHandler,
    filters
)
import requests

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('LICENSE_BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
LICENSE_SERVER_URL = os.getenv('LICENSE_SERVER_URL', 'https://license.yourdomain.com')
ADMIN_API_KEY = os.getenv('ADMIN_API_KEY', 'YOUR_ADMIN_API_KEY')
ADMIN_CHAT_IDS = [123456789]  # Add your Telegram user IDs

# Payment Configuration
PAYSTACK_SECRET_KEY = os.getenv('PAYSTACK_SECRET_KEY', '')
PAYSTACK_PUBLIC_KEY = os.getenv('PAYSTACK_PUBLIC_KEY', '')
PAYPAL_CLIENT_ID = os.getenv('PAYPAL_CLIENT_ID', '')
PAYPAL_SECRET = os.getenv('PAYPAL_SECRET', '')

# Crypto addresses (for manual verification)
BTC_ADDRESS = "bc1q..."  # Your BTC address
ETH_ADDRESS = "0x..."   # Your ETH address
USDT_TRC20_ADDRESS = "T..."  # Your USDT TRC20 address

# License Tiers & Pricing
LICENSE_TIERS = {
    'TRIAL': {
        'name': '🎯 Trial',
        'price_usd': 0,
        'duration_days': 7,
        'machines': 1,
        'description': '7-day trial to test the bot',
        'features': ['Basic trading', 'ML predictions', '1 machine']
    },
    'BASIC': {
        'name': '📦 Basic',
        'price_usd': 49,
        'duration_days': 30,
        'machines': 1,
        'description': 'Perfect for individual traders',
        'features': ['All trial features', 'Advanced indicators', 'Priority support']
    },
    'PRO': {
        'name': '🚀 Pro',
        'price_usd': 499,
        'duration_days': 365,
        'machines': 3,
        'description': 'Best value for serious traders',
        'features': ['All Basic features', '3 machines', 'Telegram alerts', 'Custom strategies']
    },
    'ENTERPRISE': {
        'name': '💎 Enterprise',
        'price_usd': 2999,
        'duration_days': None,  # Lifetime
        'machines': 10,
        'description': 'Lifetime license for professionals',
        'features': ['All Pro features', '10 machines', 'Lifetime access', 'VIP support', 'Source code access (optional)']
    }
}

# User session storage (in production, use Redis or database)
user_sessions = {}


class LicenseAPI:
    """Interface to license server"""
    
    @staticmethod
    def create_license(tier: str, customer_email: str, customer_name: str) -> Optional[Dict]:
        """Create a new license via API"""
        try:
            response = requests.post(
                f"{LICENSE_SERVER_URL}/api/admin/license/create",
                headers={'X-Admin-Key': ADMIN_API_KEY},
                json={
                    'tier': tier,
                    'customer_email': customer_email,
                    'customer_name': customer_name
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"License creation failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"License creation error: {e}")
            return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_text = f"""
🤖 **Welcome to BigMotion Trading Bot!**

Hi {user.first_name}! 👋

I'm your automated license assistant. I can help you:

✅ Purchase a new license
✅ Renew existing license
✅ Check license status
✅ Get support

**Why BigMotion?**
• 85%+ ML prediction accuracy
• Multi-TP strategy
• 8 currency pairs
• 24/7 automated trading
• Professional risk management

Ready to start? Choose an option below:
"""
    
    keyboard = [
        [InlineKeyboardButton("🆕 Get New License", callback_data='new_license')],
        [InlineKeyboardButton("🔄 Renew License", callback_data='renew_license')],
        [InlineKeyboardButton("📊 View Plans", callback_data='view_plans')],
        [InlineKeyboardButton("❓ Help & Support", callback_data='support')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def view_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all license plans"""
    query = update.callback_query
    await query.answer()
    
    plans_text = "📊 **BigMotion Trading Bot - License Plans**\n\n"
    
    for tier_id, tier_info in LICENSE_TIERS.items():
        if tier_id == 'TRIAL':
            continue  # Skip trial in main plans
            
        plans_text += f"{tier_info['name']}\n"
        plans_text += f"💰 Price: ${tier_info['price_usd']}\n"
        
        if tier_info['duration_days']:
            plans_text += f"⏱️ Duration: {tier_info['duration_days']} days\n"
        else:
            plans_text += f"⏱️ Duration: Lifetime\n"
            
        plans_text += f"💻 Machines: {tier_info['machines']}\n"
        plans_text += f"📝 {tier_info['description']}\n\n"
        
        plans_text += "**Features:**\n"
        for feature in tier_info['features']:
            plans_text += f"  ✅ {feature}\n"
        
        plans_text += "\n" + "─" * 30 + "\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🛒 Purchase Now", callback_data='new_license')],
        [InlineKeyboardButton("« Back", callback_data='back_to_start')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        plans_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def new_license(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start new license purchase flow"""
    query = update.callback_query
    await query.answer()
    
    text = """
🆕 **Get New License**

Choose your license tier:
"""
    
    keyboard = []
    for tier_id, tier_info in LICENSE_TIERS.items():
        if tier_id == 'TRIAL':
            # Trial is auto-enabled on first run
            continue
            
        price_text = f"${tier_info['price_usd']}" if tier_info['price_usd'] > 0 else "FREE"
        button_text = f"{tier_info['name']} - {price_text}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f'select_tier_{tier_id}')])
    
    keyboard.append([InlineKeyboardButton("« Back", callback_data='back_to_start')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def select_tier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle tier selection"""
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace('select_tier_', '')
    tier_info = LICENSE_TIERS[tier_id]
    
    # Store in session
    user_sessions[query.from_user.id] = {
        'tier': tier_id,
        'step': 'selected_tier'
    }
    
    text = f"""
✅ **Selected: {tier_info['name']}**

💰 **Price:** ${tier_info['price_usd']} USD
⏱️ **Duration:** {tier_info['duration_days'] if tier_info['duration_days'] else 'Lifetime'} days
💻 **Machines:** {tier_info['machines']}

**Features:**
"""
    
    for feature in tier_info['features']:
        text += f"  ✅ {feature}\n"
    
    text += "\n**Choose payment method:**"
    
    keyboard = [
        [InlineKeyboardButton("💳 Paystack (Card)", callback_data=f'pay_paystack_{tier_id}')],
        [InlineKeyboardButton("🌍 PayPal", callback_data=f'pay_paypal_{tier_id}')],
        [InlineKeyboardButton("₿ Crypto (BTC/ETH/USDT)", callback_data=f'pay_crypto_{tier_id}')],
        [InlineKeyboardButton("« Back", callback_data='new_license')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def pay_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle crypto payment"""
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace('pay_crypto_', '')
    tier_info = LICENSE_TIERS[tier_id]
    
    text = f"""
₿ **Crypto Payment - {tier_info['name']}**

**Amount:** ${tier_info['price_usd']} USD

**Payment Addresses:**

**Bitcoin (BTC):**
`{BTC_ADDRESS}`

**Ethereum (ETH):**
`{ETH_ADDRESS}`

**USDT (TRC20):**
`{USDT_TRC20_ADDRESS}`

**Instructions:**
1. Send the equivalent of ${tier_info['price_usd']} USD in crypto
2. Take a screenshot of the transaction
3. Send the screenshot here
4. We'll verify and send your license (usually within 10 minutes)

⚠️ **Important:** Send the exact amount. We use current market rates.

**Need help calculating?** Use: coinmarketcap.com
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Payment Sent - Upload Proof", callback_data=f'crypto_proof_{tier_id}')],
        [InlineKeyboardButton("« Back", callback_data=f'select_tier_{tier_id}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def crypto_proof_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request crypto payment proof"""
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace('crypto_proof_', '')
    
    # Update session
    user_sessions[query.from_user.id] = {
        'tier': tier_id,
        'step': 'awaiting_crypto_proof',
        'payment_method': 'crypto'
    }
    
    await query.edit_message_text(
        "📸 **Please send screenshot of your transaction**\n\n"
        "Include the transaction ID/hash clearly visible.\n"
        "We'll verify and send your license within 10 minutes! ⚡",
        parse_mode='Markdown'
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded payment proof"""
    user_id = update.effective_user.id
    session = user_sessions.get(user_id)
    
    if not session or session.get('step') != 'awaiting_crypto_proof':
        await update.message.reply_text("Please start the purchase process first using /start")
        return
    
    tier_id = session['tier']
    tier_info = LICENSE_TIERS[tier_id]
    
    # Forward to admins for verification
    admin_text = f"""
🔔 **NEW CRYPTO PAYMENT**

**User:** {update.effective_user.first_name} (@{update.effective_user.username})
**User ID:** {user_id}
**Tier:** {tier_info['name']}
**Amount:** ${tier_info['price_usd']}
**Payment Method:** Crypto

**Action Required:** Verify payment and approve/reject
"""
    
    # Send to all admins
    for admin_id in ADMIN_CHAT_IDS:
        await context.bot.send_message(
            chat_id=admin_id,
            text=admin_text,
            parse_mode='Markdown'
        )
        await context.bot.send_photo(
            chat_id=admin_id,
            photo=update.message.photo[-1].file_id,
            caption=f"Payment proof from User ID: {user_id}"
        )
        
        # Add approve/reject buttons for admin
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f'admin_approve_{user_id}_{tier_id}'),
                InlineKeyboardButton("❌ Reject", callback_data=f'admin_reject_{user_id}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=admin_id,
            text="👆 Review payment and take action:",
            reply_markup=reply_markup
        )
    
    # Confirm to user
    await update.message.reply_text(
        "✅ **Payment proof received!**\n\n"
        "Our team is verifying your payment.\n"
        "You'll receive your license within 10 minutes! ⚡\n\n"
        "Please wait...",
        parse_mode='Markdown'
    )


async def admin_approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves payment and generates license"""
    query = update.callback_query
    
    # Check if admin
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return
    
    await query.answer()
    
    # Parse data
    parts = query.data.split('_')
    customer_user_id = int(parts[2])
    tier_id = parts[3]
    
    # Generate license
    customer = await context.bot.get_chat(customer_user_id)
    customer_email = f"{customer.username}@telegram.user" if customer.username else f"{customer_user_id}@telegram.user"
    customer_name = customer.first_name or "Customer"
    
    license_data = LicenseAPI.create_license(tier_id, customer_email, customer_name)
    
    if license_data and license_data.get('success'):
        license_key = license_data['license_key']
        tier_name = LICENSE_TIERS[tier_id]['name']
        expiry = license_data.get('expires_at', 'Lifetime')
        
        # Send to customer
        customer_message = f"""
🎉 **Payment Verified! License Activated!**

**License Details:**
🔑 **License Key:** `{license_key}`
🎯 **Tier:** {tier_name}
📅 **Expires:** {expiry}

**Next Steps:**
1. Download BigMotion Trading Bot
2. Run the bot executable
3. When prompted, enter this license key
4. Start trading! 🚀

**Support:** If you need help, use /support

⚠️ **Important:** Save this license key securely!
"""
        
        await context.bot.send_message(
            chat_id=customer_user_id,
            text=customer_message,
            parse_mode='Markdown'
        )
        
        # Confirm to admin
        await query.edit_message_text(
            f"✅ Payment approved!\n"
            f"License {license_key} sent to user {customer_user_id}",
            parse_mode='Markdown'
        )
        
        # Clear session
        if customer_user_id in user_sessions:
            del user_sessions[customer_user_id]
    else:
        await query.edit_message_text(
            "❌ Error generating license. Check server logs.",
            parse_mode='Markdown'
        )


async def admin_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects payment"""
    query = update.callback_query
    
    # Check if admin
    if query.from_user.id not in ADMIN_CHAT_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return
    
    await query.answer()
    
    # Parse data
    customer_user_id = int(query.data.split('_')[2])
    
    # Notify customer
    await context.bot.send_message(
        chat_id=customer_user_id,
        text="❌ **Payment could not be verified**\n\n"
             "Please check the transaction and try again, or contact support.\n"
             "Use /support for assistance.",
        parse_mode='Markdown'
    )
    
    # Confirm to admin
    await query.edit_message_text("❌ Payment rejected and user notified.")
    
    # Clear session
    if customer_user_id in user_sessions:
        del user_sessions[customer_user_id]


async def pay_paystack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Paystack payment"""
    query = update.callback_query
    await query.answer()
    
    tier_id = query.data.replace('pay_paystack_', '')
    tier_info = LICENSE_TIERS[tier_id]
    
    # Generate Paystack payment link
    # This is a placeholder - implement actual Paystack integration
    payment_link = f"https://paystack.com/pay/bigmotion-{tier_id.lower()}"
    
    text = f"""
💳 **Paystack Payment - {tier_info['name']}**

**Amount:** ${tier_info['price_usd']} USD

**Instructions:**
1. Click the payment link below
2. Complete payment with your card
3. Screenshot the confirmation
4. Send screenshot here for verification

**Payment Link:**
{payment_link}

After payment, click "Payment Complete" below.
"""
    
    keyboard = [
        [InlineKeyboardButton("💳 Pay Now", url=payment_link)],
        [InlineKeyboardButton("✅ Payment Complete", callback_data=f'paystack_complete_{tier_id}')],
        [InlineKeyboardButton("« Back", callback_data=f'select_tier_{tier_id}')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='Markdown', reply_markup=reply_markup)


async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support options"""
    query = update.callback_query
    await query.answer()
    
    support_text = """
❓ **Help & Support**

**Common Questions:**

**Q: How do I activate my license?**
A: Run the bot executable. On first run, you'll be prompted to enter your license key.

**Q: Can I use one license on multiple computers?**
A: Depends on your tier:
  • Basic: 1 machine
  • Pro: 3 machines
  • Enterprise: 10 machines

**Q: How does the 3-day trial work?**
A: First time you run the bot, you automatically get 3 days free. No license needed for trial.

**Q: What if I change my computer?**
A: Contact support to deactivate old machine, then activate on new one.

**Q: Payment issues?**
A: Email us at support@bigmotion.ai with:
  • Your Telegram username
  • Payment screenshot
  • Order details

**Need Human Support?**
📧 Email: support@bigmotion.ai
⏰ Response time: Usually within 2 hours
"""
    
    keyboard = [
        [InlineKeyboardButton("« Back to Main Menu", callback_data='back_to_start')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(support_text, parse_mode='Markdown', reply_markup=reply_markup)


async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    welcome_text = f"""
🤖 **BigMotion Trading Bot**

Welcome back, {user.first_name}!

Choose an option:
"""
    
    keyboard = [
        [InlineKeyboardButton("🆕 Get New License", callback_data='new_license')],
        [InlineKeyboardButton("🔄 Renew License", callback_data='renew_license')],
        [InlineKeyboardButton("📊 View Plans", callback_data='view_plans')],
        [InlineKeyboardButton("❓ Help & Support", callback_data='support')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(welcome_text, parse_mode='Markdown', reply_markup=reply_markup)


def main():
    """Start the bot"""
    logger.info("=" * 60)
    logger.info("🤖 BIGMOTION LICENSE BOT STARTING")
    logger.info("=" * 60)
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(view_plans, pattern='^view_plans$'))
    application.add_handler(CallbackQueryHandler(new_license, pattern='^new_license$'))
    application.add_handler(CallbackQueryHandler(select_tier, pattern='^select_tier_'))
    application.add_handler(CallbackQueryHandler(pay_crypto, pattern='^pay_crypto_'))
    application.add_handler(CallbackQueryHandler(pay_paystack, pattern='^pay_paystack_'))
    application.add_handler(CallbackQueryHandler(crypto_proof_upload, pattern='^crypto_proof_'))
    application.add_handler(CallbackQueryHandler(admin_approve_payment, pattern='^admin_approve_'))
    application.add_handler(CallbackQueryHandler(admin_reject_payment, pattern='^admin_reject_'))
    application.add_handler(CallbackQueryHandler(support, pattern='^support$'))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logger.info("✅ Bot handlers registered")
    logger.info("🚀 Starting bot polling...")
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()

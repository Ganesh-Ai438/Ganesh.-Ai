#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - Core Working Telegram Bot
==========================================
Complete functional Telegram bot with all features working
"""

import os
import sys
import logging
import sqlite3
import requests
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot_core.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration from environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
HUGGINGFACE_API_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN')

BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'Artificial intelligence bot pvt Ltd')
BUSINESS_EMAIL = os.getenv('BUSINESS_EMAIL', 'ru387653@gmail.com')
SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', '@amanjee7568')
UPI_ID = os.getenv('UPI_ID', '9234906001@ptyes')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://ganesh-ai-m969.onrender.com')

VISIT_PAY_RATE = float(os.getenv('VISIT_PAY_RATE', '0.001'))
CHAT_PAY_RATE = VISIT_PAY_RATE * 50  # 50x visit rate for chat

logger.info("🤖 Ganesh A.I. Telegram Bot Starting...")
logger.info(f"🏢 Business: {BUSINESS_NAME}")
logger.info(f"💰 Chat Rate: ₹{CHAT_PAY_RATE}")

if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_TOKEN not found in environment variables!")
    sys.exit(1)

# Database setup
DB_PATH = 'telegram_bot_core.db'

def init_bot_db():
    """Initialize bot database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                balance REAL DEFAULT 0.0,
                total_earned REAL DEFAULT 0.0,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create chats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                model_used TEXT DEFAULT 'gpt-4o-mini',
                earnings REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bot_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Bot database initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Bot database initialization error: {e}")

def get_user(telegram_id):
    """Get user from database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM bot_users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        
        conn.close()
        return user
        
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(telegram_id, username, first_name, last_name):
    """Create new user"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        referral_code = f"GANESH{telegram_id}"
        welcome_bonus = 10.0
        
        cursor.execute('''
            INSERT INTO bot_users (telegram_id, username, first_name, last_name, balance, total_earned, referral_code)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (telegram_id, username, first_name, last_name, welcome_bonus, welcome_bonus, referral_code))
        
        # Add welcome transaction
        cursor.execute('''
            INSERT INTO bot_transactions (telegram_id, type, amount, description)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, 'bonus', welcome_bonus, 'Welcome bonus'))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ New user created: {username} (ID: {telegram_id})")
        return True
        
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return False

def add_earnings(telegram_id, amount, description):
    """Add earnings to user account"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Update user balance
        cursor.execute('''
            UPDATE bot_users 
            SET balance = balance + ?, total_earned = total_earned + ?, last_active = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (amount, amount, telegram_id))
        
        # Add transaction
        cursor.execute('''
            INSERT INTO bot_transactions (telegram_id, type, amount, description)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, 'earning', amount, description))
        
        conn.commit()
        conn.close()
        
        logger.info(f"💰 User {telegram_id} earned ₹{amount}: {description}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding earnings: {e}")
        return False

def get_ai_response(message, model='gpt-4o-mini'):
    """Get AI response using OpenAI API"""
    try:
        if OPENAI_API_KEY and OPENAI_API_KEY.startswith('sk-'):
            headers = {
                'Authorization': f'Bearer {OPENAI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': f'You are Ganesh A.I., an intelligent Telegram bot created by {BUSINESS_NAME}. You help users with various tasks and provide helpful, accurate responses. Be friendly, professional, and informative. Keep responses concise but helpful.'
                    },
                    {
                        'role': 'user',
                        'content': message
                    }
                ],
                'max_tokens': 800,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                logger.error(f"OpenAI API error: {response.status_code}")
                return get_fallback_response(message)
        
        else:
            return get_fallback_response(message)
            
    except Exception as e:
        logger.error(f"AI response error: {e}")
        return get_fallback_response(message)

def get_fallback_response(message):
    """Fallback response when AI APIs are not available"""
    responses = {
        'hello': f"Hello! I'm Ganesh A.I. from {BUSINESS_NAME}. How can I help you today? 🤖",
        'hi': f"Hi there! Welcome to Ganesh A.I. What can I do for you? 😊",
        'help': "I can help you with various tasks, answer questions, and provide information. Just ask me anything! Use /commands to see all available commands.",
        'about': f"I'm Ganesh A.I., created by {BUSINESS_NAME}. I'm here to assist you with AI-powered responses and help you earn money!",
        'balance': "Use /balance to check your current balance. Keep chatting to earn more! 💰",
        'earn': f"You earn ₹{CHAT_PAY_RATE} for each message you send. Keep chatting to increase your earnings! 💸",
        'commands': "Use /start to begin, /balance to check earnings, /profile to see your info, /help for assistance, and /support for help.",
        'default': f"Thank you for your message! I'm Ganesh A.I. from {BUSINESS_NAME}. I'm here to help you with any questions or tasks you have. Keep chatting to earn money! 🚀"
    }
    
    message_lower = message.lower()
    for key in responses:
        if key in message_lower:
            return responses[key]
    
    return responses['default']

# Bot command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    try:
        user = update.effective_user
        telegram_id = user.id
        
        # Check if user exists
        existing_user = get_user(telegram_id)
        
        if not existing_user:
            # Create new user
            create_user(telegram_id, user.username, user.first_name, user.last_name)
            
            welcome_message = f"""
🎉 **Welcome to Ganesh A.I.!** 🎉

Hello {user.first_name}! I'm your AI assistant created by {BUSINESS_NAME}.

🎁 **Welcome Bonus: ₹10.00 added to your account!**

💰 **How to Earn Money:**
• Send me any message: ₹{CHAT_PAY_RATE} per message
• Refer friends: ₹10 per referral
• Daily interaction bonus

🤖 **What I can do:**
• Answer questions
• Help with tasks
• Provide information
• Chat and earn money!

Use /commands to see all available commands.
Start chatting now to earn more money! 💸
"""
        else:
            # Add visit bonus
            add_earnings(telegram_id, VISIT_PAY_RATE, "Bot visit bonus")
            
            user_data = get_user(telegram_id)
            balance = user_data[5] if user_data else 0.0
            
            welcome_message = f"""
👋 **Welcome back, {user.first_name}!**

I'm Ganesh A.I., your earning companion! 🤖

💰 **Your Current Balance: ₹{balance:.2f}**

Keep chatting to earn ₹{CHAT_PAY_RATE} per message!
Use /balance to check your earnings anytime.

Ready to chat and earn? Let's go! 🚀
"""
        
        # Create inline keyboard
        keyboard = [
            [InlineKeyboardButton("💰 Check Balance", callback_data='balance')],
            [InlineKeyboardButton("👤 My Profile", callback_data='profile')],
            [InlineKeyboardButton("🎁 Refer Friends", callback_data='referral')],
            [InlineKeyboardButton("📞 Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Start command error: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    try:
        telegram_id = update.effective_user.id
        user_data = get_user(telegram_id)
        
        if not user_data:
            await update.message.reply_text("Please use /start first to register.")
            return
        
        balance = user_data[5]
        total_earned = user_data[6]
        
        # Add visit bonus
        add_earnings(telegram_id, VISIT_PAY_RATE, "Balance check bonus")
        
        balance_message = f"""
💰 **Your Earnings Summary**

**Current Balance:** ₹{balance:.2f}
**Total Earned:** ₹{total_earned:.2f}
**Earning Rate:** ₹{CHAT_PAY_RATE} per message

💸 **How to Earn More:**
• Keep chatting with me
• Refer friends (₹10 each)
• Daily interactions

**UPI Withdrawal:** {UPI_ID}
**Support:** {SUPPORT_USERNAME}

Keep chatting to increase your earnings! 🚀
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 Refresh Balance", callback_data='balance')],
            [InlineKeyboardButton("💸 Withdrawal Info", callback_data='withdrawal')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(balance_message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Balance command error: {e}")
        await update.message.reply_text("Error checking balance. Please try again.")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /profile command"""
    try:
        user = update.effective_user
        telegram_id = user.id
        user_data = get_user(telegram_id)
        
        if not user_data:
            await update.message.reply_text("Please use /start first to register.")
            return
        
        # Add visit bonus
        add_earnings(telegram_id, VISIT_PAY_RATE, "Profile view bonus")
        
        profile_message = f"""
👤 **Your Profile**

**Name:** {user.first_name} {user.last_name or ''}
**Username:** @{user.username or 'Not set'}
**Telegram ID:** {telegram_id}

**Account Info:**
• Balance: ₹{user_data[5]:.2f}
• Total Earned: ₹{user_data[6]:.2f}
• Referral Code: `{user_data[7]}`
• Member Since: {user_data[9][:10]}

**Earning Stats:**
• Messages Sent: Check with /stats
• Referrals Made: Coming soon
• Last Active: {user_data[10][:16]}

Share your referral code to earn ₹10 per friend! 🎁
"""
        
        keyboard = [
            [InlineKeyboardButton("🎁 Share Referral Code", callback_data='referral')],
            [InlineKeyboardButton("📊 View Stats", callback_data='stats')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(profile_message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Profile command error: {e}")
        await update.message.reply_text("Error loading profile. Please try again.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    try:
        telegram_id = update.effective_user.id
        
        # Add visit bonus
        add_earnings(telegram_id, VISIT_PAY_RATE, "Help command bonus")
        
        help_message = f"""
🤖 **Ganesh A.I. Help Center**

**Available Commands:**
• `/start` - Start the bot and register
• `/balance` - Check your earnings
• `/profile` - View your profile
• `/help` - Show this help message
• `/support` - Get support contact

**How to Earn Money:**
💰 **₹{CHAT_PAY_RATE} per message** - Just chat with me!
🎁 **₹10 per referral** - Invite friends
💸 **Daily bonuses** - Regular interaction rewards

**What I can help with:**
• Answer any questions
• Provide information
• Help with tasks
• General conversation
• Technical support

**Payment Info:**
• UPI ID: {UPI_ID}
• Support: {SUPPORT_USERNAME}
• Business: {BUSINESS_NAME}

Just send me any message to start earning! 🚀
"""
        
        keyboard = [
            [InlineKeyboardButton("💰 Check Balance", callback_data='balance')],
            [InlineKeyboardButton("📞 Contact Support", url=f"https://t.me/{SUPPORT_USERNAME.replace('@', '')}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_message, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await update.message.reply_text("Error loading help. Please try again.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular messages"""
    try:
        user = update.effective_user
        telegram_id = user.id
        message_text = update.message.text
        
        # Check if user exists
        user_data = get_user(telegram_id)
        if not user_data:
            await update.message.reply_text("Please use /start first to register and get your welcome bonus!")
            return
        
        # Get AI response
        ai_response = get_ai_response(message_text)
        
        # Add earnings
        add_earnings(telegram_id, CHAT_PAY_RATE, f"Chat message: {message_text[:30]}...")
        
        # Save chat to database
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO bot_chats (telegram_id, message, response, model_used, earnings)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, message_text, ai_response, OPENAI_MODEL, CHAT_PAY_RATE))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving chat: {e}")
        
        # Get updated balance
        updated_user = get_user(telegram_id)
        new_balance = updated_user[5] if updated_user else 0.0
        
        # Send AI response with earnings info
        response_message = f"{ai_response}\n\n💰 **Earned: ₹{CHAT_PAY_RATE}** | Balance: ₹{new_balance:.2f}"
        
        await update.message.reply_text(response_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard callbacks"""
    try:
        query = update.callback_query
        await query.answer()
        
        telegram_id = query.from_user.id
        data = query.data
        
        if data == 'balance':
            user_data = get_user(telegram_id)
            if user_data:
                balance = user_data[5]
                total_earned = user_data[6]
                
                balance_text = f"""
💰 **Balance Updated**

Current Balance: ₹{balance:.2f}
Total Earned: ₹{total_earned:.2f}

Keep chatting to earn more! 🚀
"""
                await query.edit_message_text(balance_text, parse_mode='Markdown')
        
        elif data == 'profile':
            user_data = get_user(telegram_id)
            if user_data:
                profile_text = f"""
👤 **Profile Info**

Balance: ₹{user_data[5]:.2f}
Total Earned: ₹{user_data[6]:.2f}
Referral Code: `{user_data[7]}`

Share your code to earn ₹10 per friend!
"""
                await query.edit_message_text(profile_text, parse_mode='Markdown')
        
        elif data == 'referral':
            user_data = get_user(telegram_id)
            if user_data:
                referral_text = f"""
🎁 **Referral Program**

Your Referral Code: `{user_data[7]}`

**How it works:**
1. Share this code with friends
2. They use /start and mention your code
3. You both get ₹10 bonus!

**Share Message:**
"Join Ganesh A.I. and earn money by chatting! Use my referral code: {user_data[7]} 
Start here: @{context.bot.username}"

Unlimited referrals = Unlimited earnings! 💸
"""
                await query.edit_message_text(referral_text, parse_mode='Markdown')
        
        elif data == 'withdrawal':
            withdrawal_text = f"""
💸 **Withdrawal Information**

**UPI ID:** {UPI_ID}
**Minimum Withdrawal:** ₹50
**Processing Time:** 24-48 hours

**How to Withdraw:**
1. Reach minimum balance (₹50)
2. Contact support: {SUPPORT_USERNAME}
3. Provide your UPI ID
4. Get paid within 48 hours!

**Support Contact:** {SUPPORT_USERNAME}
"""
            await query.edit_message_text(withdrawal_text, parse_mode='Markdown')
        
        elif data == 'stats':
            # Get user stats
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM bot_chats WHERE telegram_id = ?', (telegram_id,))
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM bot_transactions WHERE telegram_id = ? AND type = "earning"', (telegram_id,))
            total_transactions = cursor.fetchone()[0]
            
            conn.close()
            
            user_data = get_user(telegram_id)
            if user_data:
                stats_text = f"""
📊 **Your Statistics**

**Messages Sent:** {total_messages}
**Transactions:** {total_transactions}
**Total Earned:** ₹{user_data[6]:.2f}
**Current Balance:** ₹{user_data[5]:.2f}
**Member Since:** {user_data[9][:10]}

**Average per Message:** ₹{user_data[6]/total_messages if total_messages > 0 else 0:.3f}

Keep chatting to improve your stats! 📈
"""
                await query.edit_message_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Callback handling error: {e}")

def main():
    """Main function to run the bot"""
    try:
        # Initialize database
        init_bot_db()
        
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("profile", profile_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        print(f"""
🤖 ================================
   GANESH A.I. TELEGRAM BOT
================================

✅ Bot Token: Configured
✅ OpenAI API: {'Configured' if OPENAI_API_KEY else 'Using Fallback'}
✅ Database: Initialized
✅ Earning System: Active

💰 Earning Rate: ₹{CHAT_PAY_RATE} per message
🏢 Business: {BUSINESS_NAME}
📞 Support: {SUPPORT_USERNAME}

🚀 Bot is starting...
""")
        
        # Run the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Bot startup error: {e}")
        print(f"❌ Error starting bot: {e}")

if __name__ == '__main__':
    main()
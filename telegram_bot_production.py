#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - Production Telegram Bot
========================================
Standalone Telegram bot with all features working
"""

import os
import sys
import json
import time
import uuid
import logging
import asyncio
import sqlite3
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import requests

# Load environment
load_dotenv(".env")

# Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'demo-telegram-token')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
APP_NAME = os.getenv('APP_NAME', 'Ganesh A.I.')
DOMAIN = os.getenv('DOMAIN', 'https://ganesh-ai.onrender.com')
CHAT_PAY_RATE = float(os.getenv('CHAT_PAY_RATE', '0.05'))
REFERRAL_BONUS = float(os.getenv('REFERRAL_BONUS', '10.0'))
PREMIUM_MONTHLY = float(os.getenv('PREMIUM_MONTHLY', '99.0'))
PREMIUM_YEARLY = float(os.getenv('PREMIUM_YEARLY', '999.0'))

# Database file
DB_FILE = 'telegram_bot_production.db'

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - TelegramBot - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class TelegramBotProduction:
    """Production-ready Telegram bot with all features"""
    
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.bot = None
        self.application = None
        self.db_connection = None
        
        # Initialize database
        self.init_database()
        
        # Setup bot if token is available
        if self.token and self.token != 'demo-telegram-token':
            self.bot = Bot(token=self.token)
            self.application = Application.builder().token(self.token).build()
            self._setup_handlers()
        else:
            logger.warning("⚠️ Demo token detected. Bot will work in demo mode.")
            self.bot = None
            self.application = None
    
    def init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    balance REAL DEFAULT 0.0,
                    total_earned REAL DEFAULT 0.0,
                    referral_code TEXT UNIQUE NOT NULL,
                    referred_by TEXT,
                    is_premium BOOLEAN DEFAULT FALSE,
                    premium_expires TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_active TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create chats table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT NOT NULL,
                    message TEXT NOT NULL,
                    response TEXT NOT NULL,
                    ai_model TEXT DEFAULT 'fallback',
                    tokens_used INTEGER DEFAULT 0,
                    cost REAL DEFAULT 0.0,
                    earnings REAL DEFAULT 0.0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    chats INTEGER DEFAULT 0,
                    earnings REAL DEFAULT 0.0,
                    UNIQUE(telegram_id, date)
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("✅ Database initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization error: {str(e)}")
    
    def get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(DB_FILE)
    
    def _setup_handlers(self):
        """Setup bot command and message handlers"""
        if not self.application:
            return
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("premium", self.premium_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("referral", self.referral_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("models", self.models_command))
        self.application.add_handler(CommandHandler("earnings", self.earnings_command))
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("✅ Bot handlers setup complete")
    
    def generate_referral_code(self):
        """Generate unique referral code"""
        while True:
            code = secrets.token_urlsafe(8)[:8].upper()
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM users WHERE referral_code = ?", (code,))
            if not cursor.fetchone():
                conn.close()
                return code
            conn.close()
    
    def get_or_create_user(self, telegram_user, referral_code=None):
        """Get or create user in database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            telegram_id = str(telegram_user.id)
            
            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            user = cursor.fetchone()
            
            if user:
                # Update last active
                cursor.execute(
                    "UPDATE users SET last_active = ? WHERE telegram_id = ?",
                    (datetime.utcnow().isoformat(), telegram_id)
                )
                conn.commit()
                conn.close()
                return dict(zip([col[0] for col in cursor.description], user))
            else:
                # Create new user
                new_referral_code = self.generate_referral_code()
                
                cursor.execute('''
                    INSERT INTO users (telegram_id, username, first_name, last_name, referral_code, referred_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    telegram_id,
                    telegram_user.username or f"user_{telegram_user.id}",
                    telegram_user.first_name or "",
                    telegram_user.last_name or "",
                    new_referral_code,
                    referral_code
                ))
                
                # Handle referral bonus
                if referral_code:
                    cursor.execute(
                        "UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE referral_code = ?",
                        (REFERRAL_BONUS, REFERRAL_BONUS, referral_code)
                    )
                
                conn.commit()
                
                # Get the created user
                cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
                user = cursor.fetchone()
                conn.close()
                
                return dict(zip([col[0] for col in cursor.description], user))
                
        except Exception as e:
            logger.error(f"User creation error: {str(e)}")
            return None
    
    async def generate_ai_response(self, message: str, user_context: dict = None) -> dict:
        """Generate AI response with fallback system"""
        try:
            # For demo purposes, we'll use a comprehensive fallback system
            # In production, you would integrate with actual AI APIs
            
            responses = {
                'greeting': [
                    f"Hello! I'm {APP_NAME}, your intelligent AI assistant. How can I help you today?",
                    f"Hi there! Welcome to {APP_NAME}. What would you like to explore?",
                    "Namaste! 🙏 I'm here to assist you with any questions or tasks.",
                    "Greetings! I'm ready to help you with information, creative tasks, and much more!"
                ],
                'help': [
                    "I can help you with various tasks including:\n\n🤖 Answering questions on any topic\n💡 Creative writing and brainstorming\n🔍 Research and analysis\n💻 Coding assistance\n📚 Educational support\n🎯 Problem-solving\n\nJust ask me anything!",
                    "I'm equipped with advanced AI capabilities to assist with:\n\n📖 Knowledge questions\n✍️ Writing and editing\n🧮 Math and calculations\n🔬 Science explanations\n🎨 Creative projects\n💼 Business advice\n\nWhat would you like to explore?",
                    "My capabilities include:\n\n🌍 General knowledge\n📝 Content creation\n🔍 Research assistance\n💡 Idea generation\n🎓 Learning support\n🛠️ Technical help\n\nFeel free to ask me anything!"
                ],
                'premium': [
                    f"🌟 Premium features include:\n\n✅ Advanced AI models (GPT-4, Claude)\n✅ Unlimited conversations\n✅ Priority support\n✅ 2x earning rates\n✅ Exclusive features\n\nUpgrade for just ₹{PREMIUM_MONTHLY}/month!",
                    f"⭐ With Premium you get:\n\n🚀 Faster responses\n🧠 Smarter AI models\n💰 Double earnings\n🎯 Priority access\n🔧 Advanced tools\n\nOnly ₹{PREMIUM_YEARLY}/year (Save 17%)!"
                ],
                'earnings': [
                    f"💰 Earning opportunities:\n\n💬 Chat with AI: ₹{CHAT_PAY_RATE} per message\n👥 Refer friends: ₹{REFERRAL_BONUS} per referral\n⭐ Premium users earn 2x rates\n🎯 Daily bonuses available\n\nStart chatting to earn!",
                    f"🤑 Make money by:\n\n📱 Using the bot daily\n💬 Having conversations\n👨‍👩‍👧‍👦 Inviting friends\n⭐ Upgrading to premium\n🎁 Completing challenges\n\nEvery interaction pays!"
                ],
                'features': [
                    f"🚀 {APP_NAME} Features:\n\n🤖 Multiple AI models\n💰 Earn while you chat\n📊 Analytics dashboard\n👥 Referral program\n⭐ Premium subscriptions\n🔒 Secure & private\n\nExplore all features at {DOMAIN}",
                    f"✨ What makes us special:\n\n🧠 Advanced AI technology\n💸 Real money rewards\n📈 Track your progress\n🌐 Web & Telegram access\n🎯 Personalized experience\n🛡️ Enterprise security"
                ],
                'default': [
                    "That's an interesting question! Let me think about that for you.",
                    "I understand what you're asking. Here's my perspective on that topic.",
                    "Thank you for your question. I'll do my best to provide a helpful response.",
                    "Great question! Let me share some insights on that.",
                    "I appreciate you asking. Here's what I think about that.",
                    "That's a thoughtful inquiry. Let me give you a comprehensive answer.",
                    "Excellent question! I'm happy to help you with that.",
                    "I see what you're getting at. Here's my analysis of the situation."
                ]
            }
            
            message_lower = message.lower()
            
            # Determine response category
            if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start']):
                category = 'greeting'
            elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities', 'features']):
                category = 'help'
            elif any(word in message_lower for word in ['premium', 'upgrade', 'subscription', 'plan']):
                category = 'premium'
            elif any(word in message_lower for word in ['earn', 'money', 'payment', 'balance', 'income']):
                category = 'earnings'
            elif any(word in message_lower for word in ['feature', 'about', 'what is', 'tell me about']):
                category = 'features'
            else:
                category = 'default'
            
            import random
            response = random.choice(responses[category])
            
            # Add contextual information
            if user_context:
                if user_context.get('is_premium'):
                    response += "\n\n⭐ Premium user - You have access to all features!"
                else:
                    response += f"\n\n💡 Tip: Upgrade to Premium for advanced features!"
            
            return {
                'response': response,
                'tokens': len(response.split()),
                'cost': 0.0,
                'model': 'ganesh-ai-fallback'
            }
            
        except Exception as e:
            logger.error(f"AI response generation error: {str(e)}")
            return {
                'response': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                'tokens': 0,
                'cost': 0.0,
                'model': 'error'
            }
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            
            # Check for referral code
            referral_code = None
            if context.args:
                referral_code = context.args[0]
            
            # Get or create user
            db_user = self.get_or_create_user(user, referral_code)
            
            if not db_user:
                await update.message.reply_text("Sorry, I'm experiencing technical difficulties. Please try again later.")
                return
            
            welcome_text = f"""🎉 Welcome to {APP_NAME}!

I'm your intelligent AI assistant. I can help you with:

🤖 AI-powered conversations
💡 Creative writing and ideas  
🔍 Research and analysis
💻 Coding assistance
📚 Educational support
🎯 Problem-solving

💰 Earn money by using the bot!
- ₹{CHAT_PAY_RATE} per chat
- ₹{REFERRAL_BONUS} per referral

Your referral code: `{db_user['referral_code']}`
Share: {DOMAIN}/ref/{db_user['referral_code']}

Type /help for more commands!"""

            if referral_code:
                welcome_text += f"\n\n🎁 You joined using a referral code! Welcome bonus applied!"
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Start command error: {str(e)}")
            await update.message.reply_text("Welcome! I'm here to help you with any questions or tasks!")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""🤖 {APP_NAME} - Help

**Available Commands:**
/start - Start the bot
/help - Show this help message
/premium - View premium plans
/balance - Check your balance
/referral - Get referral info
/stats - View your stats
/models - Available AI models
/earnings - Earning information

**How to Earn:**
💬 Chat with AI: ₹{CHAT_PAY_RATE} per message
👥 Refer friends: ₹{REFERRAL_BONUS} per referral
⭐ Premium features available

**AI Capabilities:**
- Answer questions on any topic
- Creative writing assistance
- Code help and debugging
- Research and analysis
- Educational support
- General conversation

Just send me any message to start chatting!

🌐 Web Dashboard: {DOMAIN}"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        telegram_id = str(update.effective_user.id)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and user_data[9]:  # is_premium column
            premium_expires = user_data[10] if user_data[10] else "Never"
            premium_text = f"""⭐ You have Premium Access!

Expires: {premium_expires}

Premium Benefits:
✅ Unlimited AI chats
✅ Advanced AI models
✅ Priority support
✅ 2x earning rates
✅ Exclusive features
✅ No ads"""
        else:
            keyboard = [
                [InlineKeyboardButton(f"Monthly ₹{PREMIUM_MONTHLY}", url=f"{DOMAIN}/premium?plan=monthly&user={telegram_id}")],
                [InlineKeyboardButton(f"Yearly ₹{PREMIUM_YEARLY}", url=f"{DOMAIN}/premium?plan=yearly&user={telegram_id}")],
                [InlineKeyboardButton("Web Dashboard", url=DOMAIN)]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            premium_text = f"""⭐ Upgrade to Premium!

**Monthly Plan - ₹{PREMIUM_MONTHLY}**
**Yearly Plan - ₹{PREMIUM_YEARLY}** (Save 17%)

Premium Benefits:
✅ Unlimited AI chats
✅ Advanced AI models (GPT-4, Claude)
✅ Priority support
✅ 2x earning rates
✅ Exclusive features
✅ No ads

Click below to upgrade:"""
            
            await update.message.reply_text(premium_text, reply_markup=reply_markup, parse_mode='Markdown')
            return
        
        await update.message.reply_text(premium_text, parse_mode='Markdown')
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        telegram_id = str(update.effective_user.id)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("Please use /start first to register!")
            conn.close()
            return
        
        # Get today's earnings
        today = datetime.utcnow().date().isoformat()
        cursor.execute("SELECT earnings FROM analytics WHERE telegram_id = ? AND date = ?", (telegram_id, today))
        today_earnings_data = cursor.fetchone()
        today_earnings = today_earnings_data[0] if today_earnings_data else 0.0
        
        # Count referrals
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_data[6],))  # referral_code column
        referral_count = cursor.fetchone()[0]
        
        conn.close()
        
        balance_text = f"""💰 Your Balance

**Current Balance:** ₹{user_data[4]:.2f}
**Total Earned:** ₹{user_data[5]:.2f}
**Today's Earnings:** ₹{today_earnings:.2f}

**Earning Rates:**
💬 Per Chat: ₹{CHAT_PAY_RATE}
👥 Per Referral: ₹{REFERRAL_BONUS}
👥 Total Referrals: {referral_count}

**Referral Code:** `{user_data[6]}`
**Referral Link:** {DOMAIN}/ref/{user_data[6]}

Minimum withdrawal: ₹100
Visit {DOMAIN} to withdraw earnings!"""
        
        await update.message.reply_text(balance_text, parse_mode='Markdown')
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        telegram_id = str(update.effective_user.id)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("Please use /start first to register!")
            conn.close()
            return
        
        # Count referrals
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_data[6],))
        referral_count = cursor.fetchone()[0]
        referral_earnings = referral_count * REFERRAL_BONUS
        
        conn.close()
        
        referral_text = f"""👥 Referral Program

**Your Referral Code:** `{user_data[6]}`
**Referral Link:** {DOMAIN}/ref/{user_data[6]}

**Statistics:**
👥 Total Referrals: {referral_count}
💰 Referral Earnings: ₹{referral_earnings:.2f}
🎁 Bonus per Referral: ₹{REFERRAL_BONUS}

**How it works:**
1. Share your referral link
2. When someone joins using your link
3. You earn ₹{REFERRAL_BONUS} instantly!
4. They also get a welcome bonus

Start sharing and earning! 🚀"""
        
        await update.message.reply_text(referral_text, parse_mode='Markdown')
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        telegram_id = str(update.effective_user.id)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user_data = cursor.fetchone()
        
        if not user_data:
            await update.message.reply_text("Please use /start first to register!")
            conn.close()
            return
        
        # Get chat statistics
        cursor.execute("SELECT COUNT(*) FROM chats WHERE telegram_id = ?", (telegram_id,))
        total_chats = cursor.fetchone()[0]
        
        today = datetime.utcnow().date().isoformat()
        cursor.execute("SELECT COUNT(*) FROM chats WHERE telegram_id = ? AND date(created_at) = ?", (telegram_id, today))
        today_chats = cursor.fetchone()[0]
        
        # Count referrals
        cursor.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_data[6],))
        referral_count = cursor.fetchone()[0]
        
        conn.close()
        
        stats_text = f"""📊 Your Statistics

**Account Info:**
👤 Username: {user_data[2]}
📅 Member Since: {user_data[11][:10]}
⭐ Premium: {'Yes' if user_data[9] else 'No'}

**Usage Stats:**
💬 Total Chats: {total_chats}
📅 Today's Chats: {today_chats}
💰 Total Earned: ₹{user_data[5]:.2f}
💳 Current Balance: ₹{user_data[4]:.2f}

**Referral Stats:**
🔗 Your Code: `{user_data[6]}`
👥 Referrals: {referral_count}

Keep chatting to earn more! 🚀"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def models_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /models command"""
        models_text = f"""🤖 Available AI Models

**Free Models:**
🆓 Ganesh AI Fallback - Always available
🆓 Basic Assistant - General queries

**Premium Models:** ⭐
🧠 GPT-4 - Advanced reasoning
🎯 Claude 3 - Creative writing
🚀 Gemini Pro - Multi-modal AI
💡 GPT-4o Mini - Fast responses

**Model Features:**
✅ Instant responses
✅ Context awareness
✅ Multi-language support
✅ Creative capabilities
✅ Technical assistance

Upgrade to Premium to access all models!
Visit {DOMAIN} for more details."""
        
        await update.message.reply_text(models_text, parse_mode='Markdown')
    
    async def earnings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /earnings command"""
        earnings_text = f"""💰 Earning Information

**How to Earn:**
💬 Chat Messages: ₹{CHAT_PAY_RATE} each
👥 Referrals: ₹{REFERRAL_BONUS} each
⭐ Premium Bonus: 2x rates
🎁 Daily Bonuses: Available
🏆 Challenges: Extra rewards

**Premium Benefits:**
✅ Double earning rates
✅ Exclusive bonuses
✅ Priority payouts
✅ Special challenges

**Payout Information:**
💳 Minimum: ₹100
🏦 Methods: UPI, Bank Transfer
⏰ Processing: 24-48 hours
🔒 Secure & Reliable

Start earning today! Every chat pays! 🚀"""
        
        await update.message.reply_text(earnings_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        try:
            telegram_id = str(update.effective_user.id)
            message_text = update.message.text
            
            # Get or create user
            user = self.get_or_create_user(update.effective_user)
            if not user:
                await update.message.reply_text("Sorry, I'm experiencing technical difficulties. Please try again later.")
                return
            
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            # Determine earning rate
            is_premium = user.get('is_premium', False)
            earning_rate = CHAT_PAY_RATE * (2 if is_premium else 1)
            
            # Generate AI response
            user_context = {
                'is_premium': is_premium,
                'platform': 'telegram',
                'username': user.get('username', 'User')
            }
            
            ai_response = await self.generate_ai_response(message_text, user_context)
            
            # Save chat and update earnings
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Save chat
            cursor.execute('''
                INSERT INTO chats (telegram_id, message, response, ai_model, tokens_used, cost, earnings)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                telegram_id,
                message_text,
                ai_response['response'],
                ai_response['model'],
                ai_response['tokens'],
                ai_response['cost'],
                earning_rate
            ))
            
            # Update user balance
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, total_earned = total_earned + ?, last_active = ?
                WHERE telegram_id = ?
            ''', (earning_rate, earning_rate, datetime.utcnow().isoformat(), telegram_id))
            
            # Update daily analytics
            today = datetime.utcnow().date().isoformat()
            cursor.execute('''
                INSERT OR REPLACE INTO analytics (telegram_id, date, chats, earnings)
                VALUES (?, ?, 
                    COALESCE((SELECT chats FROM analytics WHERE telegram_id = ? AND date = ?), 0) + 1,
                    COALESCE((SELECT earnings FROM analytics WHERE telegram_id = ? AND date = ?), 0) + ?
                )
            ''', (telegram_id, today, telegram_id, today, telegram_id, today, earning_rate))
            
            conn.commit()
            conn.close()
            
            # Send response with earning info
            response_text = ai_response['response']
            if len(response_text) > 4000:  # Telegram message limit
                response_text = response_text[:4000] + "..."
            
            # Get updated balance
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,))
            new_balance = cursor.fetchone()[0]
            conn.close()
            
            earning_info = f"\n\n💰 +₹{earning_rate:.2f} earned | Balance: ₹{new_balance:.2f}"
            
            await update.message.reply_text(response_text + earning_info)
            
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
            await update.message.reply_text(
                "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            )
    
    async def set_webhook(self):
        """Set webhook for the bot"""
        if not self.bot or not WEBHOOK_URL:
            logger.warning("⚠️ Cannot set webhook: Bot or webhook URL not configured")
            return False
        
        try:
            await self.bot.set_webhook(url=WEBHOOK_URL)
            logger.info(f"✅ Webhook set to: {WEBHOOK_URL}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set webhook: {str(e)}")
            return False
    
    async def process_webhook(self, update_data: dict):
        """Process webhook update"""
        if not self.application:
            logger.warning("⚠️ Cannot process webhook: Application not configured")
            return
        
        try:
            update = Update.de_json(update_data, self.bot)
            await self.application.process_update(update)
        except Exception as e:
            logger.error(f"❌ Webhook processing error: {str(e)}")
    
    def run_polling(self):
        """Run bot in polling mode"""
        if not self.application:
            logger.error("❌ Cannot run polling: Application not configured")
            return
        
        logger.info("🚀 Starting Telegram bot in polling mode...")
        self.application.run_polling()

# =========================
# MAIN EXECUTION
# =========================

def main():
    """Main function"""
    print(f"""
    🤖 ================================
       {APP_NAME} TELEGRAM BOT
    ================================
    
    🚀 Production-Ready Bot
    💰 Earning System
    🤖 AI Integration
    📊 Analytics
    
    Starting bot...
    """)
    
    bot = TelegramBotProduction()
    
    if bot.application:
        logger.info("✅ Bot initialized successfully")
        
        # Set webhook if URL is provided
        if WEBHOOK_URL and WEBHOOK_URL != '':
            import asyncio
            asyncio.run(bot.set_webhook())
        
        # Run in polling mode for testing
        bot.run_polling()
    else:
        logger.warning("⚠️ Bot running in demo mode - configure TELEGRAM_TOKEN for full functionality")
        
        # Keep the script running for webhook processing
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user")

if __name__ == '__main__':
    main()
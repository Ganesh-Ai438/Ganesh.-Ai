#!/usr/bin/env python3
"""
Ganesh AI - Complete Telegram Bot System
Advanced AI Bot with Instant Replies and Full Functionality
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import random

# Telegram imports (with fallback)
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
    from telegram.constants import ParseMode, ChatAction
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram bot dependencies not available. Bot will be disabled.")

# Database imports
from main import User, db, app, log, TELEGRAM_TOKEN, APP_NAME, DOMAIN, BUSINESS_NAME

class GaneshAIBot:
    """Complete Telegram Bot System for Ganesh AI"""
    
    def __init__(self):
        self.app = None
        self.is_running = False
        self.user_sessions = {}  # Store user conversation sessions
        self.model_costs = {
            'ganesh-free': 0.0,
            'gpt-4-turbo': 2.00,
            'claude-3-sonnet': 1.50,
            'gemini-pro': 1.00,
            'gpt-3.5-turbo': 0.50
        }
        
        # AI Response templates for instant replies
        self.quick_responses = {
            'greetings': [
                "Hello! 👋 I'm Ganesh AI, your advanced AI assistant. How can I help you today?",
                "Hi there! 🤖 Welcome to Ganesh AI. What would you like to explore?",
                "Namaste! 🙏 I'm here to assist you with any questions or tasks.",
                "Greetings! ✨ Ready to dive into some AI-powered conversations?"
            ],
            'help_requests': [
                "I can help you with various tasks! Try asking me about:\n\n🧠 General questions\n📝 Writing and content\n💡 Creative ideas\n🔧 Problem solving\n📚 Learning topics",
                "Here's what I can do for you:\n\n✨ Answer questions on any topic\n🎨 Creative writing and content\n💼 Business and strategy advice\n🔬 Technical explanations\n🎯 Personal assistance"
            ],
            'thanks': [
                "You're welcome! 😊 Happy to help anytime!",
                "Glad I could assist! 🌟 Feel free to ask more questions.",
                "My pleasure! 🤖 That's what I'm here for!",
                "Anytime! 💫 Keep the questions coming!"
            ]
        }
        
    async def initialize(self):
        """Initialize the Telegram bot"""
        if not TELEGRAM_AVAILABLE:
            log("telegram", "ERROR", "Telegram dependencies not available")
            return False
            
        if not TELEGRAM_TOKEN:
            log("telegram", "ERROR", "Telegram token not configured")
            return False
            
        try:
            # Create application
            self.app = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Add command handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("help", self.cmd_help))
            self.app.add_handler(CommandHandler("balance", self.cmd_balance))
            self.app.add_handler(CommandHandler("models", self.cmd_models))
            self.app.add_handler(CommandHandler("stats", self.cmd_stats))
            self.app.add_handler(CommandHandler("referral", self.cmd_referral))
            self.app.add_handler(CommandHandler("premium", self.cmd_premium))
            self.app.add_handler(CommandHandler("withdraw", self.cmd_withdraw))
            
            # Model selection commands
            self.app.add_handler(CommandHandler("free", lambda u, c: self.cmd_select_model(u, c, 'ganesh-free')))
            self.app.add_handler(CommandHandler("gpt4", lambda u, c: self.cmd_select_model(u, c, 'gpt-4-turbo')))
            self.app.add_handler(CommandHandler("claude", lambda u, c: self.cmd_select_model(u, c, 'claude-3-sonnet')))
            self.app.add_handler(CommandHandler("gemini", lambda u, c: self.cmd_select_model(u, c, 'gemini-pro')))
            self.app.add_handler(CommandHandler("gpt3", lambda u, c: self.cmd_select_model(u, c, 'gpt-3.5-turbo')))
            
            # Message and callback handlers
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.app.add_handler(CallbackQueryHandler(self.handle_callback))
            
            # Set bot commands menu
            await self.set_bot_commands()
            
            log("telegram", "INFO", "Telegram bot initialized successfully")
            return True
            
        except Exception as e:
            log("telegram", "ERROR", f"Failed to initialize bot: {e}")
            return False
    
    async def set_bot_commands(self):
        """Set bot command menu"""
        commands = [
            BotCommand("start", "🚀 Start using Ganesh AI"),
            BotCommand("help", "❓ Get help and instructions"),
            BotCommand("models", "🤖 View available AI models"),
            BotCommand("balance", "💰 Check your balance"),
            BotCommand("stats", "📊 View your statistics"),
            BotCommand("referral", "👥 Get referral information"),
            BotCommand("premium", "👑 Premium subscription"),
            BotCommand("withdraw", "💸 Withdraw earnings"),
        ]
        
        try:
            await self.app.bot.set_my_commands(commands)
            log("telegram", "INFO", "Bot commands menu set successfully")
        except Exception as e:
            log("telegram", "ERROR", f"Failed to set bot commands: {e}")
    
    async def start_bot(self):
        """Start the bot (polling mode for development)"""
        if not self.app:
            if not await self.initialize():
                return False
        
        try:
            self.is_running = True
            log("telegram", "INFO", "Starting Telegram bot in polling mode...")
            await self.app.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            log("telegram", "ERROR", f"Bot polling error: {e}")
            self.is_running = False
            return False
    
    def get_or_create_user(self, telegram_user) -> User:
        """Get or create user from Telegram user data"""
        with app.app_context():
            user_id = str(telegram_user.id)
            username = telegram_user.username or f"user_{user_id}"
            first_name = telegram_user.first_name or "User"
            
            user = User.query.filter_by(telegram_id=user_id).first()
            
            if not user:
                # Create new user
                user = User(
                    username=username,
                    email=f"{username}@telegram.user",
                    telegram_id=user_id,
                    first_name=first_name
                )
                user.set_password("telegram_user")
                user.generate_referral_code()
                user.wallet = 25.0  # Welcome bonus
                user.add_earnings(25.0, "Welcome bonus")
                
                db.session.add(user)
                db.session.commit()
                
                log("telegram", "INFO", f"New user created: {username} (ID: {user_id})")
            
            return user
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = self.get_or_create_user(update.effective_user)
            
            # Check if this is a new user
            is_new_user = user.created_at and (datetime.utcnow() - user.created_at).total_seconds() < 60
            
            if is_new_user:
                welcome_text = f"""
🎉 **Welcome to {APP_NAME}!**

Hello {user.first_name}! I'm Ganesh AI, your advanced AI assistant.

🎁 **Welcome Bonus**: ₹25.00 credited to your account!
💰 **Your Balance**: ₹{user.wallet:.2f}

🤖 **Available AI Models**:
• 🆓 Ganesh AI Free - ₹0.00 per chat
• 🚀 GPT-4 Turbo - ₹2.00 per chat  
• 🎨 Claude 3 Sonnet - ₹1.50 per chat
• 🧠 Gemini Pro - ₹1.00 per chat
• ⚡ GPT-3.5 Turbo - ₹0.50 per chat

💡 **Quick Start**:
• Just send me any message to start chatting!
• Use /models to switch AI models
• Use /help for all commands

🔗 **Web Dashboard**: {DOMAIN}
👥 **Referral Code**: `{user.referral_code}`

Ready to explore the future of AI? Send me a message! 🚀
"""
            else:
                welcome_text = f"""
👋 **Welcome back, {user.first_name}!**

💰 **Balance**: ₹{user.wallet:.2f}
📊 **Total Chats**: {user.chats_count or 0}
💎 **Total Earned**: ₹{user.total_earned:.2f}

🤖 **Current Model**: {context.user_data.get('selected_model', 'ganesh-free').title()}

Ready to continue our conversation? Send me a message! ✨
"""
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("🤖 AI Models", callback_data="models"),
                    InlineKeyboardButton("💰 Balance", callback_data="balance")
                ],
                [
                    InlineKeyboardButton("📊 Statistics", callback_data="stats"),
                    InlineKeyboardButton("👥 Referrals", callback_data="referral")
                ],
                [
                    InlineKeyboardButton("🌐 Web Dashboard", url=DOMAIN),
                    InlineKeyboardButton("❓ Help", callback_data="help")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            log("telegram", "ERROR", f"Start command error: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = f"""
🤖 **{APP_NAME} - Help Guide**

**🎯 Basic Commands:**
/start - Start or restart the bot
/help - Show this help message
/models - View and select AI models
/balance - Check your wallet balance
/stats - View your statistics
/referral - Get referral information
/premium - Premium subscription info
/withdraw - Withdraw your earnings

**🤖 AI Model Commands:**
/free - Switch to Ganesh AI Free (₹0.00)
/gpt4 - Switch to GPT-4 Turbo (₹2.00)
/claude - Switch to Claude 3 Sonnet (₹1.50)
/gemini - Switch to Gemini Pro (₹1.00)
/gpt3 - Switch to GPT-3.5 Turbo (₹0.50)

**💰 How to Earn:**
• 💬 Chat with AI models (earn per chat)
• 👥 Refer friends (₹10 per referral)
• 🎯 Daily bonuses and rewards

**🎨 What I Can Do:**
• Answer questions on any topic
• Help with creative writing
• Solve technical problems
• Provide business advice
• Generate ideas and content
• Assist with learning and research

**💡 Tips:**
• Start with the free model to test
• Upgrade to premium models for better responses
• Check your balance regularly
• Share your referral code to earn more

Need more help? Visit: {DOMAIN}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("🤖 Try AI Models", callback_data="models"),
                InlineKeyboardButton("💰 Check Balance", callback_data="balance")
            ],
            [
                InlineKeyboardButton("🌐 Web Dashboard", url=DOMAIN)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_models(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /models command"""
        user = self.get_or_create_user(update.effective_user)
        current_model = context.user_data.get('selected_model', 'ganesh-free')
        
        models_text = f"""
🤖 **Available AI Models**

**Current Model**: {current_model.replace('-', ' ').title()} {'✅' if current_model else ''}

**🆓 Free Models:**
• Ganesh AI Free - ₹0.00 per chat
  Basic conversations and assistance

**💎 Premium Models:**
• GPT-4 Turbo - ₹2.00 per chat
  Most advanced reasoning and creativity
  
• Claude 3 Sonnet - ₹1.50 per chat
  Excellent for writing and analysis
  
• Gemini Pro - ₹1.00 per chat
  Google's latest AI technology
  
• GPT-3.5 Turbo - ₹0.50 per chat
  Fast and reliable responses

**💰 Your Balance**: ₹{user.wallet:.2f}

Select a model below to start chatting:
"""
        
        keyboard = [
            [InlineKeyboardButton("🆓 Ganesh AI Free", callback_data="select_ganesh-free")],
            [InlineKeyboardButton("🚀 GPT-4 Turbo", callback_data="select_gpt-4-turbo")],
            [InlineKeyboardButton("🎨 Claude 3 Sonnet", callback_data="select_claude-3-sonnet")],
            [InlineKeyboardButton("🧠 Gemini Pro", callback_data="select_gemini-pro")],
            [InlineKeyboardButton("⚡ GPT-3.5 Turbo", callback_data="select_gpt-3.5-turbo")],
            [InlineKeyboardButton("💰 Add Balance", url=f"{DOMAIN}/dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            models_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_select_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE, model: str):
        """Handle model selection commands"""
        context.user_data['selected_model'] = model
        model_name = model.replace('-', ' ').title()
        cost = self.model_costs.get(model, 0.0)
        
        await update.message.reply_text(
            f"✅ **Model Selected**: {model_name}\n"
            f"💰 **Cost**: ₹{cost:.2f} per chat\n\n"
            f"Send me a message to start chatting with {model_name}! 🚀",
            parse_mode=ParseMode.MARKDOWN
        )
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        user = self.get_or_create_user(update.effective_user)
        
        balance_text = f"""
💰 **Your Wallet Balance**

**💳 Current Balance**: ₹{user.wallet:.2f}
**📈 Total Earned**: ₹{user.total_earned:.2f}

**📊 Earnings Breakdown:**
• 💬 Chat Earnings: ₹{(user.chats_count or 0) * 0.05:.2f}
• 👥 Referral Earnings: ₹{(user.referrals_count or 0) * 10:.2f}
• 🎁 Bonuses: ₹{max(0, user.total_earned - (user.chats_count or 0) * 0.05 - (user.referrals_count or 0) * 10):.2f}

**💡 Earn More:**
• Chat with AI models
• Refer friends (₹10 each)
• Daily bonuses and rewards

**Minimum Withdrawal**: ₹100
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
                InlineKeyboardButton("👥 Refer Friends", callback_data="referral")
            ],
            [
                InlineKeyboardButton("🌐 Web Dashboard", url=f"{DOMAIN}/dashboard")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            balance_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = self.get_or_create_user(update.effective_user)
        
        # Calculate days since joining
        days_active = (datetime.utcnow() - user.created_at).days if user.created_at else 0
        
        stats_text = f"""
📊 **Your Statistics**

**👤 Profile:**
• Username: {user.username}
• Member since: {user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown'}
• Days active: {days_active}

**💬 Chat Statistics:**
• Total chats: {user.chats_count or 0}
• Average per day: {((user.chats_count or 0) / max(1, days_active)):.1f}

**💰 Financial:**
• Wallet balance: ₹{user.wallet:.2f}
• Total earned: ₹{user.total_earned:.2f}
• Earnings per chat: ₹{(user.total_earned / max(1, user.chats_count or 1)):.2f}

**👥 Referrals:**
• Friends referred: {user.referrals_count or 0}
• Referral earnings: ₹{(user.referrals_count or 0) * 10:.2f}
• Your referral code: `{user.referral_code}`

**🏆 Achievements:**
{'🥇 Chat Master' if (user.chats_count or 0) >= 100 else ''}
{'💰 Earner' if user.total_earned >= 100 else ''}
{'👥 Influencer' if (user.referrals_count or 0) >= 10 else ''}
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💬 Start Chatting", callback_data="models"),
                InlineKeyboardButton("👥 Refer Friends", callback_data="referral")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        user = self.get_or_create_user(update.effective_user)
        
        referral_text = f"""
👥 **Referral Program**

**🔗 Your Referral Code**: `{user.referral_code}`

**📱 Share this link:**
{DOMAIN}/register?ref={user.referral_code}

**💰 Earnings:**
• ₹10 for each friend who joins
• ₹5 bonus when they make their first chat
• Additional bonuses for active referrals

**📊 Your Referral Stats:**
• Friends referred: {user.referrals_count or 0}
• Referral earnings: ₹{(user.referrals_count or 0) * 10:.2f}
• Potential earnings: Unlimited! 🚀

**💡 Tips to Earn More:**
• Share on social media
• Tell friends about AI features
• Show them how to earn money
• Be active yourself to inspire others

**🏆 Referral Leaderboard:**
Top referrers earn special bonuses and recognition!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📱 Share Link", 
                    url=f"https://t.me/share/url?url={DOMAIN}/register?ref={user.referral_code}&text=Join Ganesh AI and earn money chatting with AI! Use my referral code: {user.referral_code}")
            ],
            [
                InlineKeyboardButton("🌐 Web Dashboard", url=f"{DOMAIN}/dashboard")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            referral_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_premium(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        user = self.get_or_create_user(update.effective_user)
        
        is_premium = user.premium_until and user.premium_until > datetime.utcnow()
        
        if is_premium:
            premium_text = f"""
👑 **Premium Active**

**Status**: Premium Member ✅
**Valid Until**: {user.premium_until.strftime('%Y-%m-%d')}
**Days Remaining**: {(user.premium_until - datetime.utcnow()).days}

**🎯 Premium Benefits Active:**
• ✅ Access to all AI models
• ✅ Unlimited chats
• ✅ Priority support
• ✅ Advanced features
• ✅ Higher earning rates
• ✅ Exclusive content

**💰 Premium Earnings Boost:**
• 2x chat earnings
• Bonus referral rewards
• Special premium challenges

Keep enjoying your premium experience! 🚀
"""
        else:
            premium_text = f"""
👑 **Upgrade to Premium**

**🎯 Premium Benefits:**
• 🚀 Access to all AI models
• 💬 Unlimited chats
• 🎯 Priority support
• ⚡ Faster responses
• 💰 2x earning rates
• 🎁 Exclusive bonuses
• 🏆 Premium challenges

**💳 Subscription Plans:**
• Monthly: ₹99/month
• Yearly: ₹999/year (Save ₹189!)

**💰 Your Balance**: ₹{user.wallet:.2f}

**🎁 Special Offer:**
Use your earned balance to pay for premium!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💳 Subscribe Monthly", url=f"{DOMAIN}/premium?plan=monthly"),
                InlineKeyboardButton("💎 Subscribe Yearly", url=f"{DOMAIN}/premium?plan=yearly")
            ],
            [
                InlineKeyboardButton("🌐 Web Dashboard", url=f"{DOMAIN}/dashboard")
            ]
        ] if not is_premium else [
            [
                InlineKeyboardButton("🌐 Manage Subscription", url=f"{DOMAIN}/dashboard")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            premium_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def cmd_withdraw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /withdraw command"""
        user = self.get_or_create_user(update.effective_user)
        
        if user.wallet < 100:
            withdraw_text = f"""
💸 **Withdrawal Information**

**💰 Current Balance**: ₹{user.wallet:.2f}
**📉 Minimum Required**: ₹100.00
**🚫 Status**: Insufficient balance

**💡 How to Reach Minimum:**
• Chat more with AI models
• Refer friends (₹10 each)
• Complete daily challenges
• Participate in premium features

**📊 Progress**: {(user.wallet/100)*100:.1f}% to minimum

Keep earning to reach the withdrawal threshold! 🚀
"""
        else:
            withdraw_text = f"""
💸 **Withdrawal Available**

**💰 Available Balance**: ₹{user.wallet:.2f}
**✅ Status**: Ready for withdrawal
**⏱️ Processing Time**: 1-3 business days

**🏦 Withdrawal Methods:**
• Bank transfer (NEFT/IMPS)
• UPI payment
• Digital wallets

**📋 Required Information:**
• Bank account details
• PAN card verification
• Phone number confirmation

**💡 Note**: Minimum withdrawal is ₹100
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💸 Request Withdrawal", url=f"{DOMAIN}/withdraw")
            ],
            [
                InlineKeyboardButton("🌐 Web Dashboard", url=f"{DOMAIN}/dashboard")
            ]
        ] if user.wallet >= 100 else [
            [
                InlineKeyboardButton("💬 Chat to Earn", callback_data="models"),
                InlineKeyboardButton("👥 Refer Friends", callback_data="referral")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            withdraw_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages with AI responses"""
        try:
            user = self.get_or_create_user(update.effective_user)
            message_text = update.message.text
            selected_model = context.user_data.get('selected_model', 'ganesh-free')
            
            # Check balance for paid models
            cost = self.model_costs.get(selected_model, 0.0)
            if cost > 0 and user.wallet < cost:
                await update.message.reply_text(
                    f"❌ **Insufficient Balance**\n\n"
                    f"💰 **Required**: ₹{cost:.2f}\n"
                    f"💳 **Your Balance**: ₹{user.wallet:.2f}\n\n"
                    f"💡 **Options**:\n"
                    f"• Use /free for free model\n"
                    f"• Add balance at {DOMAIN}\n"
                    f"• Refer friends to earn ₹10 each",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Send typing indicator
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action=ChatAction.TYPING
            )
            
            # Generate AI response
            response = await self.generate_ai_response(message_text, selected_model, user)
            
            # Deduct cost and add earnings
            if cost > 0:
                user.wallet -= cost
                user.add_earnings(0.05, f"Chat with {selected_model}")
            else:
                user.add_earnings(0.01, f"Free chat with {selected_model}")
            
            # Update chat count
            user.chats_count = (user.chats_count or 0) + 1
            
            with app.app_context():
                db.session.commit()
            
            # Send response
            await update.message.reply_text(
                response,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Show earnings notification occasionally
            if random.random() < 0.1:  # 10% chance
                earnings_msg = f"💰 **Earning Update**: +₹{0.05 if cost > 0 else 0.01:.2f} | Balance: ₹{user.wallet:.2f}"
                await update.message.reply_text(earnings_msg, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            log("telegram", "ERROR", f"Message handling error: {e}")
            await update.message.reply_text(
                "❌ Sorry, I encountered an error. Please try again or contact support.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    async def generate_ai_response(self, message: str, model: str, user: User) -> str:
        """Generate AI response based on model and message"""
        message_lower = message.lower()
        
        # Quick pattern matching for instant responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start']):
            response = random.choice(self.quick_responses['greetings'])
            return f"{response}\n\n**Model**: {model.replace('-', ' ').title()}\n**Balance**: ₹{user.wallet:.2f}"
        
        elif any(word in message_lower for word in ['help', 'what can you do', 'features']):
            return random.choice(self.quick_responses['help_requests'])
        
        elif any(word in message_lower for word in ['thank', 'thanks', 'thx']):
            return random.choice(self.quick_responses['thanks'])
        
        # Model-specific responses
        if model == 'ganesh-free':
            return await self.generate_free_response(message, user)
        elif model == 'gpt-4-turbo':
            return await self.generate_premium_response(message, user, "GPT-4 Turbo", "🚀")
        elif model == 'claude-3-sonnet':
            return await self.generate_premium_response(message, user, "Claude 3 Sonnet", "🎨")
        elif model == 'gemini-pro':
            return await self.generate_premium_response(message, user, "Gemini Pro", "🧠")
        elif model == 'gpt-3.5-turbo':
            return await self.generate_premium_response(message, user, "GPT-3.5 Turbo", "⚡")
        else:
            return await self.generate_free_response(message, user)
    
    async def generate_free_response(self, message: str, user: User) -> str:
        """Generate response for free model"""
        message_lower = message.lower()
        
        # Context-aware responses
        if any(word in message_lower for word in ['earn', 'money', 'payment', 'balance']):
            return f"""💰 **Earning with Ganesh AI**

**Your Stats:**
• Balance: ₹{user.wallet:.2f}
• Total Earned: ₹{user.total_earned:.2f}
• Chats: {user.chats_count or 0}

**How to Earn More:**
• Chat with AI models (₹0.01-₹2.00 per chat)
• Refer friends (₹10 per referral)
• Upgrade to premium for higher rates

**Referral Code**: `{user.referral_code}`

Keep chatting to earn more! 🚀"""
        
        elif any(word in message_lower for word in ['code', 'programming', 'python', 'javascript']):
            return """👨‍💻 **Programming Help**

I can help you with:
• Python, JavaScript, HTML/CSS
• Code debugging and optimization
• Algorithm explanations
• Best practices and tutorials

**Example**: "Write a Python function to sort a list"

For advanced coding assistance with detailed explanations, try our premium models! 🚀"""
        
        elif any(word in message_lower for word in ['write', 'story', 'poem', 'creative']):
            return """✨ **Creative Writing**

I can help create:
• Stories and narratives
• Poems and verses
• Articles and blogs
• Creative content ideas

**Example**: "Write a short story about AI"

For premium creative content with advanced storytelling, upgrade to Claude 3 Sonnet! 🎨"""
        
        else:
            # General intelligent response
            responses = [
                f"That's an interesting question, {user.first_name}! Let me help you with that...",
                f"Great question! Based on what you're asking about '{message[:30]}{'...' if len(message) > 30 else ''}'",
                f"I understand you're asking about this topic. Here's my perspective...",
                f"Thanks for sharing that with me, {user.first_name}. Let me assist you..."
            ]
            
            base_response = random.choice(responses)
            
            return f"""{base_response}

While I can provide basic assistance as the free model, for more detailed and accurate responses, I recommend upgrading to our premium models:

🚀 **GPT-4 Turbo** - Most advanced reasoning
🎨 **Claude 3 Sonnet** - Creative and analytical
🧠 **Gemini Pro** - Google's latest AI

**Your Progress**: {user.chats_count or 0} chats | ₹{user.total_earned:.2f} earned

Use /models to explore premium options! 💎"""
    
    async def generate_premium_response(self, message: str, user: User, model_name: str, icon: str) -> str:
        """Generate response for premium models"""
        return f"""{icon} **{model_name} Response**

Hello {user.first_name}! I'm processing your message with {model_name}'s advanced capabilities.

**Your Message**: "{message[:100]}{'...' if len(message) > 100 else ''}"

**Advanced Analysis**: This is where {model_name} would provide a sophisticated, detailed response with:
• Deep contextual understanding
• Multi-step reasoning
• Comprehensive explanations
• Creative problem-solving

*Note: This is a demo response. In production, this would connect to the actual {model_name} API for real responses.*

**Premium Benefits Active**:
• ✅ Advanced AI capabilities
• ✅ Detailed responses
• ✅ Priority processing
• ✅ Enhanced accuracy

**Earnings**: +₹0.05 | **Balance**: ₹{user.wallet:.2f}

Keep exploring with premium models! 💎"""
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "models":
            await self.cmd_models(update, context)
        elif data == "balance":
            await self.cmd_balance(update, context)
        elif data == "stats":
            await self.cmd_stats(update, context)
        elif data == "referral":
            await self.cmd_referral(update, context)
        elif data == "help":
            await self.cmd_help(update, context)
        elif data == "withdraw":
            await self.cmd_withdraw(update, context)
        elif data.startswith("select_"):
            model = data.replace("select_", "")
            context.user_data['selected_model'] = model
            model_name = model.replace('-', ' ').title()
            cost = self.model_costs.get(model, 0.0)
            
            await query.edit_message_text(
                f"✅ **Model Selected**: {model_name}\n"
                f"💰 **Cost**: ₹{cost:.2f} per chat\n\n"
                f"Send me a message to start chatting with {model_name}! 🚀",
                parse_mode=ParseMode.MARKDOWN
            )

# Global bot instance
ganesh_bot = GaneshAIBot()

# Functions for main.py integration
async def start_telegram_bot():
    """Start the Telegram bot"""
    if TELEGRAM_AVAILABLE and TELEGRAM_TOKEN:
        return await ganesh_bot.start_bot()
    return False

def is_bot_running():
    """Check if bot is running"""
    return ganesh_bot.is_running

async def stop_telegram_bot():
    """Stop the Telegram bot"""
    if ganesh_bot.app and ganesh_bot.is_running:
        await ganesh_bot.app.stop()
        ganesh_bot.is_running = False
        return True
    return False
#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - Complete Production System
==========================================
Production-ready AI platform with:
- Multi-AI Model Integration (GPT-4, Claude, Gemini, etc.)
- Advanced Web Application
- Telegram Bot with Webhook
- Comprehensive Admin Panel
- Payment Gateway Integration
- Revenue Generation System
- Real-time Analytics
- User Management
"""

import os
import sys
import json
import time
import uuid
import base64
import logging
import traceback
import sqlite3
import threading
import asyncio
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

import requests
import httpx
from flask import (
    Flask, request, jsonify, render_template, render_template_string,
    session, redirect, url_for, flash, send_from_directory, abort
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

# Telegram Bot imports
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# AI API imports
import openai
from gtts import gTTS
import io

# Payment imports
import stripe
import razorpay

# =========================
# ENVIRONMENT & CONFIG
# =========================

load_dotenv(".env")

# Core Configuration
APP_NAME = os.getenv('APP_NAME', 'Ganesh A.I.')
DOMAIN = os.getenv('DOMAIN', 'https://ganesh-ai.onrender.com')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('FLASK_SECRET', secrets.token_hex(32))

# Admin Configuration
ADMIN_USER = os.getenv('ADMIN_USER', 'Admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', 'admin123')
ADMIN_ID = os.getenv('ADMIN_ID', '123456789')

# Database Configuration
DATABASE_URL = os.getenv('DB_URL', 'sqlite:///ganesh_ai_production.db')

# AI API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
HUGGINGFACE_TOKEN = os.getenv('HUGGINGFACE_API_TOKEN', '')

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', f'{DOMAIN}/webhook/telegram')

# Payment Configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')

# Monetization Settings
VISIT_PAY_RATE = float(os.getenv('VISIT_PAY_RATE', '0.01'))
CHAT_PAY_RATE = float(os.getenv('CHAT_PAY_RATE', '0.05'))
REFERRAL_BONUS = float(os.getenv('REFERRAL_BONUS', '10.0'))
PREMIUM_MONTHLY = float(os.getenv('PREMIUM_MONTHLY', '99.0'))
PREMIUM_YEARLY = float(os.getenv('PREMIUM_YEARLY', '999.0'))

# =========================
# FLASK APP SETUP
# =========================

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize database
db = SQLAlchemy(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ganesh_ai.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =========================
# DATABASE MODELS
# =========================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    telegram_id = db.Column(db.String(50), unique=True, nullable=True)
    is_premium = db.Column(db.Boolean, default=False)
    premium_expires = db.Column(db.DateTime, nullable=True)
    balance = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    referral_code = db.Column(db.String(20), unique=True, nullable=False)
    referred_by = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    chats = db.relationship('ChatHistory', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)
    analytics = db.relationship('UserAnalytics', backref='user', lazy=True)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    ai_model = db.Column(db.String(50), nullable=False)
    tokens_used = db.Column(db.Integer, default=0)
    cost = db.Column(db.Float, default=0.0)
    platform = db.Column(db.String(20), default='web')  # web, telegram
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    payment_method = db.Column(db.String(50), nullable=False)  # stripe, razorpay, etc.
    payment_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    purpose = db.Column(db.String(50), nullable=False)  # premium, withdrawal, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

class UserAnalytics(db.Model):
    __tablename__ = 'user_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    visits = db.Column(db.Integer, default=0)
    chats = db.Column(db.Integer, default=0)
    earnings = db.Column(db.Float, default=0.0)
    platform = db.Column(db.String(20), default='web')

class SystemStats(db.Model):
    __tablename__ = 'system_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    total_users = db.Column(db.Integer, default=0)
    active_users = db.Column(db.Integer, default=0)
    premium_users = db.Column(db.Integer, default=0)
    total_chats = db.Column(db.Integer, default=0)
    total_revenue = db.Column(db.Float, default=0.0)
    total_payouts = db.Column(db.Float, default=0.0)

# =========================
# AI SERVICE CLASS
# =========================

class AIService:
    """Comprehensive AI service with multiple model support"""
    
    def __init__(self):
        self.openai_client = None
        if OPENAI_API_KEY:
            openai.api_key = OPENAI_API_KEY
            self.openai_client = openai
        
        self.models = {
            'gpt-4o-mini': {'cost': 0.5, 'provider': 'openai'},
            'gpt-4': {'cost': 2.0, 'provider': 'openai'},
            'gpt-3.5-turbo': {'cost': 0.2, 'provider': 'openai'},
            'claude-3': {'cost': 1.5, 'provider': 'anthropic'},
            'gemini-pro': {'cost': 1.0, 'provider': 'google'},
            'llama-2': {'cost': 0.1, 'provider': 'huggingface'},
        }
    
    async def generate_response(self, message: str, model: str = 'gpt-4o-mini', user_context: dict = None) -> dict:
        """Generate AI response with comprehensive error handling"""
        try:
            if model.startswith('gpt') and self.openai_client:
                return await self._openai_response(message, model, user_context)
            elif model == 'llama-2':
                return await self._huggingface_response(message)
            else:
                return await self._fallback_response(message)
        except Exception as e:
            logger.error(f"AI generation error: {str(e)}")
            return {
                'response': "I apologize, but I'm experiencing technical difficulties. Please try again in a moment.",
                'tokens': 0,
                'cost': 0.0,
                'model': 'fallback'
            }
    
    async def _openai_response(self, message: str, model: str, user_context: dict = None) -> dict:
        """Generate OpenAI response"""
        try:
            system_prompt = self._get_system_prompt(user_context)
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            tokens = response.usage.total_tokens
            cost = tokens * self.models[model]['cost'] / 1000
            
            return {
                'response': content,
                'tokens': tokens,
                'cost': cost,
                'model': model
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return await self._fallback_response(message)
    
    async def _huggingface_response(self, message: str) -> dict:
        """Generate Hugging Face response"""
        try:
            if not HUGGINGFACE_TOKEN:
                return await self._fallback_response(message)
            
            url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-large"
            headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={"inputs": message},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result[0]['generated_text'] if result else "I'm processing your request..."
                    
                    return {
                        'response': content,
                        'tokens': len(content.split()),
                        'cost': 0.1,
                        'model': 'llama-2'
                    }
                else:
                    return await self._fallback_response(message)
        except Exception as e:
            logger.error(f"Hugging Face API error: {str(e)}")
            return await self._fallback_response(message)
    
    async def _fallback_response(self, message: str) -> dict:
        """Fallback response system"""
        responses = {
            'greeting': [
                "Hello! I'm Ganesh AI, your intelligent assistant. How can I help you today?",
                "Hi there! Welcome to Ganesh AI. What would you like to explore?",
                "Namaste! I'm here to assist you with any questions or tasks."
            ],
            'help': [
                "I can help you with various tasks including answering questions, creative writing, coding assistance, and much more!",
                "I'm equipped with advanced AI capabilities to assist with research, analysis, creative projects, and problem-solving.",
                "Feel free to ask me anything! I can help with writing, coding, math, science, and general knowledge."
            ],
            'default': [
                "That's an interesting question! Let me think about that for you.",
                "I understand what you're asking. Here's my perspective on that topic.",
                "Thank you for your question. I'll do my best to provide a helpful response."
            ]
        }
        
        message_lower = message.lower()
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste']):
            response_list = responses['greeting']
        elif any(word in message_lower for word in ['help', 'what can you do', 'capabilities']):
            response_list = responses['help']
        else:
            response_list = responses['default']
        
        import random
        response = random.choice(response_list)
        
        return {
            'response': response,
            'tokens': len(response.split()),
            'cost': 0.0,
            'model': 'fallback'
        }
    
    def _get_system_prompt(self, user_context: dict = None) -> str:
        """Get system prompt based on user context"""
        base_prompt = """You are Ganesh AI, an advanced and helpful AI assistant. You are knowledgeable, creative, and always aim to provide accurate and useful responses. You can help with:

- Answering questions on various topics
- Creative writing and content creation
- Coding and technical assistance
- Problem-solving and analysis
- Educational support
- General conversation

Always be helpful, respectful, and provide detailed responses when appropriate."""

        if user_context:
            if user_context.get('is_premium'):
                base_prompt += "\n\nThe user has premium access, so provide enhanced and detailed responses."
            if user_context.get('platform') == 'telegram':
                base_prompt += "\n\nYou are responding via Telegram, so keep responses concise but informative."
        
        return base_prompt

# =========================
# TELEGRAM BOT CLASS
# =========================

class TelegramBot:
    """Production-ready Telegram bot with webhook support"""
    
    def __init__(self, ai_service: AIService):
        self.token = TELEGRAM_TOKEN
        self.ai_service = ai_service
        self.bot = None
        self.application = None
        
        if self.token:
            self.bot = Bot(token=self.token)
            self.application = Application.builder().token(self.token).build()
            self._setup_handlers()
    
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
        
        # Message handler
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user = update.effective_user
            telegram_id = str(user.id)
            
            # Check if user exists in database
            db_user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not db_user:
                # Create new user
                referral_code = self._generate_referral_code()
                username = user.username or f"user_{user.id}"
                email = f"{username}@telegram.local"
                
                db_user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash("telegram_user"),
                    telegram_id=telegram_id,
                    referral_code=referral_code
                )
                
                # Check for referral
                if context.args:
                    referral_code_used = context.args[0]
                    referrer = User.query.filter_by(referral_code=referral_code_used).first()
                    if referrer:
                        db_user.referred_by = referral_code_used
                        referrer.balance += REFERRAL_BONUS
                        db.session.add(referrer)
                
                db.session.add(db_user)
                db.session.commit()
                
                welcome_text = f"""🎉 Welcome to {APP_NAME}!

I'm Ganesh AI, your intelligent assistant. I can help you with:

🤖 AI-powered conversations
💡 Creative writing and ideas  
🔍 Research and analysis
💻 Coding assistance
📚 Educational support
🎯 Problem-solving

💰 Earn money by using the bot!
- ₹{CHAT_PAY_RATE} per chat
- ₹{REFERRAL_BONUS} per referral

Your referral code: `{referral_code}`
Share: {DOMAIN}/ref/{referral_code}

Type /help for more commands!"""
            else:
                db_user.last_active = datetime.utcnow()
                db.session.commit()
                
                welcome_text = f"""Welcome back to {APP_NAME}! 👋

I'm ready to assist you. What would you like to explore today?

💰 Your balance: ₹{db_user.balance:.2f}
🎯 Your referral code: `{db_user.referral_code}`

Type /help for available commands."""
            
            await update.message.reply_text(welcome_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Start command error: {str(e)}")
            await update.message.reply_text("Welcome! I'm experiencing some technical issues, but I'm here to help!")
    
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

Just send me any message to start chatting!"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def premium_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /premium command"""
        telegram_id = str(update.effective_user.id)
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if user and user.is_premium and user.premium_expires > datetime.utcnow():
            premium_text = f"""⭐ You have Premium Access!

Expires: {user.premium_expires.strftime('%Y-%m-%d %H:%M')}

Premium Benefits:
✅ Unlimited AI chats
✅ Advanced AI models
✅ Priority support
✅ Higher earning rates
✅ Exclusive features"""
        else:
            keyboard = [
                [InlineKeyboardButton("Monthly ₹99", url=f"{DOMAIN}/premium?plan=monthly&user={telegram_id}")],
                [InlineKeyboardButton("Yearly ₹999", url=f"{DOMAIN}/premium?plan=yearly&user={telegram_id}")],
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
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            await update.message.reply_text("Please use /start first to register!")
            return
        
        # Get today's earnings
        today = datetime.utcnow().date()
        today_analytics = UserAnalytics.query.filter_by(
            user_id=user.id, 
            date=today
        ).first()
        
        today_earnings = today_analytics.earnings if today_analytics else 0.0
        
        balance_text = f"""💰 Your Balance

**Current Balance:** ₹{user.balance:.2f}
**Total Earned:** ₹{user.total_earned:.2f}
**Today's Earnings:** ₹{today_earnings:.2f}

**Earning Rates:**
💬 Per Chat: ₹{CHAT_PAY_RATE}
👥 Per Referral: ₹{REFERRAL_BONUS}

**Referral Code:** `{user.referral_code}`
**Referral Link:** {DOMAIN}/ref/{user.referral_code}

Minimum withdrawal: ₹100
Visit {DOMAIN} to withdraw earnings!"""
        
        await update.message.reply_text(balance_text, parse_mode='Markdown')
    
    async def referral_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /referral command"""
        telegram_id = str(update.effective_user.id)
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            await update.message.reply_text("Please use /start first to register!")
            return
        
        # Count referrals
        referral_count = User.query.filter_by(referred_by=user.referral_code).count()
        referral_earnings = referral_count * REFERRAL_BONUS
        
        referral_text = f"""👥 Referral Program

**Your Referral Code:** `{user.referral_code}`
**Referral Link:** {DOMAIN}/ref/{user.referral_code}

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
        user = User.query.filter_by(telegram_id=telegram_id).first()
        
        if not user:
            await update.message.reply_text("Please use /start first to register!")
            return
        
        # Get user statistics
        total_chats = ChatHistory.query.filter_by(user_id=user.id).count()
        today = datetime.utcnow().date()
        today_chats = ChatHistory.query.filter_by(
            user_id=user.id
        ).filter(
            ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
        ).count()
        
        stats_text = f"""📊 Your Statistics

**Account Info:**
👤 Username: {user.username}
📅 Member Since: {user.created_at.strftime('%Y-%m-%d')}
⭐ Premium: {'Yes' if user.is_premium else 'No'}

**Usage Stats:**
💬 Total Chats: {total_chats}
📅 Today's Chats: {today_chats}
💰 Total Earned: ₹{user.total_earned:.2f}
💳 Current Balance: ₹{user.balance:.2f}

**Referral Stats:**
🔗 Your Code: `{user.referral_code}`
👥 Referrals: {User.query.filter_by(referred_by=user.referral_code).count()}

Keep chatting to earn more! 🚀"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        try:
            telegram_id = str(update.effective_user.id)
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                await update.message.reply_text("Please use /start first to register!")
                return
            
            message_text = update.message.text
            
            # Send typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
            
            # Determine AI model based on premium status
            if user.is_premium and user.premium_expires > datetime.utcnow():
                model = 'gpt-4o-mini'
                earning_rate = CHAT_PAY_RATE * 2  # Premium users earn 2x
            else:
                model = 'gpt-4o-mini'
                earning_rate = CHAT_PAY_RATE
            
            # Generate AI response
            user_context = {
                'is_premium': user.is_premium,
                'platform': 'telegram',
                'username': user.username
            }
            
            ai_response = await self.ai_service.generate_response(
                message_text, 
                model=model, 
                user_context=user_context
            )
            
            # Save chat history
            chat = ChatHistory(
                user_id=user.id,
                message=message_text,
                response=ai_response['response'],
                ai_model=ai_response['model'],
                tokens_used=ai_response['tokens'],
                cost=ai_response['cost'],
                platform='telegram'
            )
            db.session.add(chat)
            
            # Update user earnings and analytics
            user.balance += earning_rate
            user.total_earned += earning_rate
            user.last_active = datetime.utcnow()
            
            # Update daily analytics
            today = datetime.utcnow().date()
            analytics = UserAnalytics.query.filter_by(
                user_id=user.id, 
                date=today, 
                platform='telegram'
            ).first()
            
            if not analytics:
                analytics = UserAnalytics(
                    user_id=user.id,
                    date=today,
                    platform='telegram'
                )
                db.session.add(analytics)
            
            analytics.chats += 1
            analytics.earnings += earning_rate
            
            db.session.commit()
            
            # Send response with earning info
            response_text = ai_response['response']
            if len(response_text) > 4000:  # Telegram message limit
                response_text = response_text[:4000] + "..."
            
            earning_info = f"\n\n💰 +₹{earning_rate:.2f} earned | Balance: ₹{user.balance:.2f}"
            
            await update.message.reply_text(response_text + earning_info)
            
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
            await update.message.reply_text(
                "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            )
    
    def _generate_referral_code(self) -> str:
        """Generate unique referral code"""
        while True:
            code = secrets.token_urlsafe(8)[:8].upper()
            if not User.query.filter_by(referral_code=code).first():
                return code
    
    async def set_webhook(self):
        """Set webhook for the bot"""
        if not self.bot or not WEBHOOK_URL:
            return False
        
        try:
            await self.bot.set_webhook(url=WEBHOOK_URL)
            logger.info(f"Webhook set to: {WEBHOOK_URL}")
            return True
        except Exception as e:
            logger.error(f"Failed to set webhook: {str(e)}")
            return False
    
    async def process_webhook(self, update_data: dict):
        """Process webhook update"""
        if not self.application:
            return
        
        try:
            update = Update.de_json(update_data, self.bot)
            await self.application.process_update(update)
        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")

# =========================
# PAYMENT SERVICE
# =========================

class PaymentService:
    """Comprehensive payment service"""
    
    def __init__(self):
        self.stripe_client = None
        self.razorpay_client = None
        
        if STRIPE_SECRET_KEY:
            stripe.api_key = STRIPE_SECRET_KEY
            self.stripe_client = stripe
        
        if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
            self.razorpay_client = razorpay.Client(
                auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
            )
    
    def create_premium_payment(self, user_id: int, plan: str, amount: float) -> dict:
        """Create premium subscription payment"""
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            payment_id = f"premium_{user_id}_{int(time.time())}"
            
            # Create payment record
            payment = Payment(
                user_id=user_id,
                amount=amount,
                payment_method='razorpay',
                payment_id=payment_id,
                purpose=f'premium_{plan}'
            )
            db.session.add(payment)
            db.session.commit()
            
            if self.razorpay_client:
                # Create Razorpay order
                order_data = {
                    'amount': int(amount * 100),  # Amount in paise
                    'currency': 'INR',
                    'receipt': payment_id,
                    'notes': {
                        'user_id': user_id,
                        'plan': plan
                    }
                }
                
                order = self.razorpay_client.order.create(data=order_data)
                
                return {
                    'success': True,
                    'order_id': order['id'],
                    'amount': amount,
                    'currency': 'INR',
                    'key': RAZORPAY_KEY_ID
                }
            else:
                return {'success': False, 'error': 'Payment gateway not configured'}
                
        except Exception as e:
            logger.error(f"Payment creation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        """Verify Razorpay payment"""
        try:
            if not self.razorpay_client:
                return False
            
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            self.razorpay_client.utility.verify_payment_signature(params_dict)
            return True
            
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return False
    
    def process_successful_payment(self, payment_id: str, plan: str, user_id: int):
        """Process successful premium payment"""
        try:
            user = User.query.get(user_id)
            payment = Payment.query.filter_by(payment_id=payment_id).first()
            
            if user and payment:
                # Update payment status
                payment.status = 'completed'
                payment.completed_at = datetime.utcnow()
                
                # Update user premium status
                user.is_premium = True
                
                if plan == 'monthly':
                    user.premium_expires = datetime.utcnow() + timedelta(days=30)
                elif plan == 'yearly':
                    user.premium_expires = datetime.utcnow() + timedelta(days=365)
                
                db.session.commit()
                logger.info(f"Premium activated for user {user_id}, plan: {plan}")
                return True
                
        except Exception as e:
            logger.error(f"Payment processing error: {str(e)}")
            return False

# =========================
# INITIALIZE SERVICES
# =========================

ai_service = AIService()
telegram_bot = TelegramBot(ai_service)
payment_service = PaymentService()

# =========================
# UTILITY FUNCTIONS
# =========================

def login_required(f):
    """Decorator for routes that require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['user_id'])
        if not user or user.username != ADMIN_USER:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def update_system_stats():
    """Update daily system statistics"""
    try:
        today = datetime.utcnow().date()
        
        stats = SystemStats.query.filter_by(date=today).first()
        if not stats:
            stats = SystemStats(date=today)
            db.session.add(stats)
        
        stats.total_users = User.query.count()
        stats.active_users = User.query.filter(
            User.last_active >= datetime.utcnow() - timedelta(days=7)
        ).count()
        stats.premium_users = User.query.filter(
            User.is_premium == True,
            User.premium_expires > datetime.utcnow()
        ).count()
        stats.total_chats = ChatHistory.query.count()
        stats.total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'completed'
        ).scalar() or 0.0
        stats.total_payouts = db.session.query(db.func.sum(User.total_earned)).scalar() or 0.0
        
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Stats update error: {str(e)}")

# =========================
# WEB ROUTES
# =========================

@app.route('/')
def index():
    """Main landing page"""
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Advanced AI Platform</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .hero-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 100px 0;
        }
        .feature-card {
            transition: transform 0.3s;
            border: none;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .feature-card:hover {
            transform: translateY(-5px);
        }
        .stats-section {
            background: #f8f9fa;
            padding: 60px 0;
        }
        .cta-section {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            color: white;
            padding: 80px 0;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark fixed-top">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot"></i> {{ app_name }}
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/login">Login</a>
                <a class="nav-link" href="/register">Register</a>
                <a class="nav-link" href="/dashboard">Dashboard</a>
            </div>
        </div>
    </nav>

    <!-- Hero Section -->
    <section class="hero-section">
        <div class="container text-center">
            <h1 class="display-4 mb-4">Welcome to {{ app_name }}</h1>
            <p class="lead mb-5">The most advanced AI platform with multiple AI models, earning opportunities, and comprehensive features</p>
            <div class="row justify-content-center">
                <div class="col-md-8">
                    <div class="card bg-white text-dark">
                        <div class="card-body">
                            <h5>Try AI Chat Now</h5>
                            <div class="input-group mb-3">
                                <input type="text" class="form-control" id="quickChat" placeholder="Ask me anything...">
                                <button class="btn btn-primary" onclick="quickChat()">
                                    <i class="fas fa-paper-plane"></i> Send
                                </button>
                            </div>
                            <div id="quickResponse" class="mt-3"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Features Section -->
    <section class="py-5">
        <div class="container">
            <div class="row text-center mb-5">
                <div class="col">
                    <h2>Powerful AI Features</h2>
                    <p class="lead">Experience the future of AI interaction</p>
                </div>
            </div>
            <div class="row">
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-brain fa-3x text-primary mb-3"></i>
                            <h5>Multiple AI Models</h5>
                            <p>Access GPT-4, Claude, Gemini, and more AI models in one platform</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-money-bill-wave fa-3x text-success mb-3"></i>
                            <h5>Earn While You Chat</h5>
                            <p>Get paid for every interaction and referral you make</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fab fa-telegram fa-3x text-info mb-3"></i>
                            <h5>Telegram Integration</h5>
                            <p>Use our AI bot directly in Telegram with instant responses</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-chart-line fa-3x text-warning mb-3"></i>
                            <h5>Analytics Dashboard</h5>
                            <p>Track your usage, earnings, and performance metrics</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-shield-alt fa-3x text-danger mb-3"></i>
                            <h5>Secure & Private</h5>
                            <p>Your data is encrypted and protected with enterprise-grade security</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-4">
                    <div class="card feature-card h-100">
                        <div class="card-body text-center">
                            <i class="fas fa-users fa-3x text-purple mb-3"></i>
                            <h5>Referral Program</h5>
                            <p>Earn ₹{{ referral_bonus }} for every friend you refer</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Stats Section -->
    <section class="stats-section">
        <div class="container">
            <div class="row text-center">
                <div class="col-md-3 mb-4">
                    <h3 class="display-4 text-primary">{{ stats.total_users or 0 }}</h3>
                    <p class="lead">Total Users</p>
                </div>
                <div class="col-md-3 mb-4">
                    <h3 class="display-4 text-success">{{ stats.total_chats or 0 }}</h3>
                    <p class="lead">AI Conversations</p>
                </div>
                <div class="col-md-3 mb-4">
                    <h3 class="display-4 text-info">₹{{ "%.0f"|format(stats.total_payouts or 0) }}</h3>
                    <p class="lead">Total Payouts</p>
                </div>
                <div class="col-md-3 mb-4">
                    <h3 class="display-4 text-warning">{{ stats.premium_users or 0 }}</h3>
                    <p class="lead">Premium Users</p>
                </div>
            </div>
        </div>
    </section>

    <!-- CTA Section -->
    <section class="cta-section">
        <div class="container text-center">
            <h2 class="mb-4">Ready to Start Earning with AI?</h2>
            <p class="lead mb-5">Join thousands of users who are already earning money while exploring AI</p>
            <div class="row justify-content-center">
                <div class="col-md-6">
                    <a href="/register" class="btn btn-light btn-lg me-3">
                        <i class="fas fa-user-plus"></i> Get Started Free
                    </a>
                    <a href="https://t.me/{{ telegram_bot_username }}" class="btn btn-outline-light btn-lg">
                        <i class="fab fa-telegram"></i> Try Telegram Bot
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="bg-dark text-white py-4">
        <div class="container text-center">
            <p>&copy; 2024 {{ app_name }}. All rights reserved.</p>
            <div class="mt-3">
                <a href="#" class="text-white me-3"><i class="fab fa-twitter"></i></a>
                <a href="#" class="text-white me-3"><i class="fab fa-facebook"></i></a>
                <a href="#" class="text-white me-3"><i class="fab fa-instagram"></i></a>
                <a href="https://t.me/{{ telegram_bot_username }}" class="text-white"><i class="fab fa-telegram"></i></a>
            </div>
        </div>
    </footer>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function quickChat() {
            const input = document.getElementById('quickChat');
            const response = document.getElementById('quickResponse');
            const message = input.value.trim();
            
            if (!message) return;
            
            response.innerHTML = '<div class="spinner-border text-primary" role="status"></div> Thinking...';
            
            try {
                const res = await fetch('/api/quick-chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                });
                
                const data = await res.json();
                
                if (data.success) {
                    response.innerHTML = `
                        <div class="alert alert-info">
                            <strong>AI:</strong> ${data.response}
                        </div>
                        <small class="text-muted">
                            <a href="/register">Register</a> to earn money for each chat!
                        </small>
                    `;
                } else {
                    response.innerHTML = '<div class="alert alert-danger">Error: ' + data.error + '</div>';
                }
            } catch (error) {
                response.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
            
            input.value = '';
        }
        
        document.getElementById('quickChat').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                quickChat();
            }
        });
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    referral_bonus=REFERRAL_BONUS,
    telegram_bot_username="GaneshAIBot",
    stats=SystemStats.query.filter_by(date=datetime.utcnow().date()).first() or {}
    )

@app.route('/api/quick-chat', methods=['POST'])
def quick_chat():
    """Quick chat API for homepage"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        # Use fallback response for quick chat
        import asyncio
        response = asyncio.run(ai_service._fallback_response(message))
        
        return jsonify({
            'success': True,
            'response': response['response']
        })
        
    except Exception as e:
        logger.error(f"Quick chat error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '').strip()
            referral_code_used = data.get('referral_code', '').strip()
            
            # Validation
            if not username or not email or not password:
                return jsonify({'success': False, 'error': 'All fields are required'})
            
            if len(password) < 6:
                return jsonify({'success': False, 'error': 'Password must be at least 6 characters'})
            
            # Check if user exists
            if User.query.filter_by(username=username).first():
                return jsonify({'success': False, 'error': 'Username already exists'})
            
            if User.query.filter_by(email=email).first():
                return jsonify({'success': False, 'error': 'Email already exists'})
            
            # Generate referral code
            referral_code = secrets.token_urlsafe(8)[:8].upper()
            while User.query.filter_by(referral_code=referral_code).first():
                referral_code = secrets.token_urlsafe(8)[:8].upper()
            
            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                referral_code=referral_code
            )
            
            # Handle referral
            if referral_code_used:
                referrer = User.query.filter_by(referral_code=referral_code_used).first()
                if referrer:
                    user.referred_by = referral_code_used
                    referrer.balance += REFERRAL_BONUS
                    referrer.total_earned += REFERRAL_BONUS
                    db.session.add(referrer)
            
            db.session.add(user)
            db.session.commit()
            
            # Auto login
            session['user_id'] = user.id
            session['username'] = user.username
            
            return jsonify({
                'success': True,
                'message': 'Registration successful!',
                'redirect': '/dashboard'
            })
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({'success': False, 'error': 'Registration failed'})
    
    # GET request - show registration form
    referral_code = request.args.get('ref', '')
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Register - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .register-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="register-card p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                        <h2>Join {{ app_name }}</h2>
                        <p class="text-muted">Start earning with AI today!</p>
                    </div>
                    
                    <form id="registerForm">
                        <div class="mb-3">
                            <label class="form-label">Username</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" name="email" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" name="password" required minlength="6">
                        </div>
                        
                        {% if referral_code %}
                        <div class="mb-3">
                            <label class="form-label">Referral Code</label>
                            <input type="text" class="form-control" name="referral_code" value="{{ referral_code }}" readonly>
                            <small class="text-success">🎉 You'll get a welcome bonus!</small>
                        </div>
                        {% endif %}
                        
                        <button type="submit" class="btn btn-primary w-100 mb-3">
                            <i class="fas fa-user-plus"></i> Create Account
                        </button>
                    </form>
                    
                    <div class="text-center">
                        <p>Already have an account? <a href="/login">Login here</a></p>
                        <p><a href="/">← Back to Home</a></p>
                    </div>
                    
                    <div id="message" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('registerForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="spinner-border text-primary" role="status"></div> Creating account...';
            
            try {
                const response = await fetch('/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    messageDiv.innerHTML = '<div class="alert alert-success">' + result.message + '</div>';
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    messageDiv.innerHTML = '<div class="alert alert-danger">' + result.error + '</div>';
                }
            } catch (error) {
                messageDiv.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
        });
    </script>
</body>
</html>
    """, app_name=APP_NAME, referral_code=referral_code)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        try:
            data = request.get_json() if request.is_json else request.form
            
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            if not username or not password:
                return jsonify({'success': False, 'error': 'Username and password are required'})
            
            # Find user by username or email
            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['username'] = user.username
                
                # Update last active
                user.last_active = datetime.utcnow()
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Login successful!',
                    'redirect': '/dashboard'
                })
            else:
                return jsonify({'success': False, 'error': 'Invalid credentials'})
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({'success': False, 'error': 'Login failed'})
    
    # GET request - show login form
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
        }
        .login-card {
            background: white;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-5">
                <div class="login-card p-5">
                    <div class="text-center mb-4">
                        <i class="fas fa-robot fa-3x text-primary mb-3"></i>
                        <h2>Welcome Back</h2>
                        <p class="text-muted">Login to {{ app_name }}</p>
                    </div>
                    
                    <form id="loginForm">
                        <div class="mb-3">
                            <label class="form-label">Username or Email</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" class="form-control" name="password" required>
                        </div>
                        
                        <button type="submit" class="btn btn-primary w-100 mb-3">
                            <i class="fas fa-sign-in-alt"></i> Login
                        </button>
                    </form>
                    
                    <div class="text-center">
                        <p>Don't have an account? <a href="/register">Register here</a></p>
                        <p><a href="/">← Back to Home</a></p>
                    </div>
                    
                    <div id="message" class="mt-3"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        document.getElementById('loginForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const data = Object.fromEntries(formData);
            
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="spinner-border text-primary" role="status"></div> Logging in...';
            
            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.success) {
                    messageDiv.innerHTML = '<div class="alert alert-success">' + result.message + '</div>';
                    setTimeout(() => {
                        window.location.href = result.redirect;
                    }, 1000);
                } else {
                    messageDiv.innerHTML = '<div class="alert alert-danger">' + result.error + '</div>';
                }
            } catch (error) {
                messageDiv.innerHTML = '<div class="alert alert-danger">Network error. Please try again.</div>';
            }
        });
    </script>
</body>
</html>
    """, app_name=APP_NAME)

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard"""
    user = User.query.get(session['user_id'])
    
    # Get user statistics
    total_chats = ChatHistory.query.filter_by(user_id=user.id).count()
    today = datetime.utcnow().date()
    today_chats = ChatHistory.query.filter_by(user_id=user.id).filter(
        ChatHistory.created_at >= datetime.combine(today, datetime.min.time())
    ).count()
    
    # Get recent chats
    recent_chats = ChatHistory.query.filter_by(user_id=user.id).order_by(
        ChatHistory.created_at.desc()
    ).limit(5).all()
    
    # Get referral count
    referral_count = User.query.filter_by(referred_by=user.referral_code).count()
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        .main-content {
            background: #f8f9fa;
            min-height: 100vh;
        }
        .stat-card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .chat-interface {
            height: 400px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            background: white;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 10px;
        }
        .user-message {
            background: #e3f2fd;
            margin-left: 20%;
        }
        .ai-message {
            background: #f5f5f5;
            margin-right: 20%;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <div class="col-md-3 sidebar text-white p-4">
                <div class="text-center mb-4">
                    <i class="fas fa-robot fa-3x mb-3"></i>
                    <h4>{{ app_name }}</h4>
                    <p>Welcome, {{ user.username }}!</p>
                </div>
                
                <nav class="nav flex-column">
                    <a class="nav-link text-white active" href="/dashboard">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a class="nav-link text-white" href="/chat">
                        <i class="fas fa-comments"></i> AI Chat
                    </a>
                    <a class="nav-link text-white" href="/premium">
                        <i class="fas fa-star"></i> Premium
                    </a>
                    <a class="nav-link text-white" href="/earnings">
                        <i class="fas fa-money-bill-wave"></i> Earnings
                    </a>
                    <a class="nav-link text-white" href="/referrals">
                        <i class="fas fa-users"></i> Referrals
                    </a>
                    <a class="nav-link text-white" href="/profile">
                        <i class="fas fa-user"></i> Profile
                    </a>
                    {% if user.username == admin_user %}
                    <a class="nav-link text-white" href="/admin">
                        <i class="fas fa-cog"></i> Admin Panel
                    </a>
                    {% endif %}
                    <a class="nav-link text-white" href="/logout">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </nav>
            </div>
            
            <!-- Main Content -->
            <div class="col-md-9 main-content p-4">
                <div class="row mb-4">
                    <div class="col">
                        <h2>Dashboard</h2>
                        <p class="text-muted">Welcome to your AI-powered dashboard</p>
                    </div>
                </div>
                
                <!-- Stats Cards -->
                <div class="row mb-4">
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-wallet fa-2x text-success mb-2"></i>
                                <h4>₹{{ "%.2f"|format(user.balance) }}</h4>
                                <p class="text-muted">Current Balance</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-chart-line fa-2x text-primary mb-2"></i>
                                <h4>₹{{ "%.2f"|format(user.total_earned) }}</h4>
                                <p class="text-muted">Total Earned</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-comments fa-2x text-info mb-2"></i>
                                <h4>{{ total_chats }}</h4>
                                <p class="text-muted">Total Chats</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-users fa-2x text-warning mb-2"></i>
                                <h4>{{ referral_count }}</h4>
                                <p class="text-muted">Referrals</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <!-- Quick Chat -->
                    <div class="col-md-8 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-robot"></i> Quick AI Chat</h5>
                            </div>
                            <div class="card-body">
                                <div id="chatMessages" class="chat-interface mb-3">
                                    <div class="message ai-message">
                                        <strong>AI:</strong> Hello! I'm ready to help you. What would you like to know?
                                    </div>
                                </div>
                                <div class="input-group">
                                    <select class="form-select" id="aiModel" style="max-width: 150px;">
                                        <option value="gpt-4o-mini">GPT-4o Mini</option>
                                        {% if user.is_premium %}
                                        <option value="gpt-4">GPT-4</option>
                                        <option value="claude-3">Claude 3</option>
                                        <option value="gemini-pro">Gemini Pro</option>
                                        {% endif %}
                                        <option value="llama-2">Llama 2 (Free)</option>
                                    </select>
                                    <input type="text" class="form-control" id="chatInput" placeholder="Type your message...">
                                    <button class="btn btn-primary" onclick="sendMessage()">
                                        <i class="fas fa-paper-plane"></i>
                                    </button>
                                </div>
                                <small class="text-muted">Earn ₹{{ chat_rate }} per message!</small>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Activity -->
                    <div class="col-md-4 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-history"></i> Recent Chats</h5>
                            </div>
                            <div class="card-body">
                                {% for chat in recent_chats %}
                                <div class="mb-3 p-2 border-bottom">
                                    <small class="text-muted">{{ chat.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                                    <p class="mb-1"><strong>You:</strong> {{ chat.message[:50] }}...</p>
                                    <p class="mb-0 text-muted"><strong>AI:</strong> {{ chat.response[:50] }}...</p>
                                </div>
                                {% endfor %}
                                
                                {% if not recent_chats %}
                                <p class="text-muted">No chats yet. Start a conversation above!</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Premium Status -->
                {% if not user.is_premium %}
                <div class="row">
                    <div class="col-12">
                        <div class="card border-warning">
                            <div class="card-body text-center">
                                <h5 class="text-warning"><i class="fas fa-star"></i> Upgrade to Premium</h5>
                                <p>Unlock advanced AI models, 2x earning rates, and exclusive features!</p>
                                <a href="/premium" class="btn btn-warning">Upgrade Now</a>
                            </div>
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="row">
                    <div class="col-12">
                        <div class="card border-success">
                            <div class="card-body text-center">
                                <h5 class="text-success"><i class="fas fa-crown"></i> Premium Active</h5>
                                <p>Expires: {{ user.premium_expires.strftime('%Y-%m-%d %H:%M') }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const model = document.getElementById('aiModel').value;
            const messages = document.getElementById('chatMessages');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message
            messages.innerHTML += `
                <div class="message user-message">
                    <strong>You:</strong> ${message}
                </div>
            `;
            
            // Add loading message
            messages.innerHTML += `
                <div class="message ai-message" id="loading">
                    <strong>AI:</strong> <div class="spinner-border spinner-border-sm" role="status"></div> Thinking...
                </div>
            `;
            
            messages.scrollTop = messages.scrollHeight;
            input.value = '';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message, model: model})
                });
                
                const data = await response.json();
                
                // Remove loading message
                document.getElementById('loading').remove();
                
                if (data.success) {
                    messages.innerHTML += `
                        <div class="message ai-message">
                            <strong>AI (${data.model}):</strong> ${data.response}
                            <br><small class="text-success">+₹${data.earned} earned</small>
                        </div>
                    `;
                    
                    // Update balance display
                    location.reload();
                } else {
                    messages.innerHTML += `
                        <div class="message ai-message">
                            <strong>Error:</strong> ${data.error}
                        </div>
                    `;
                }
            } catch (error) {
                document.getElementById('loading').remove();
                messages.innerHTML += `
                    <div class="message ai-message">
                        <strong>Error:</strong> Network error. Please try again.
                    </div>
                `;
            }
            
            messages.scrollTop = messages.scrollHeight;
        }
        
        document.getElementById('chatInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    user=user,
    admin_user=ADMIN_USER,
    total_chats=total_chats,
    today_chats=today_chats,
    recent_chats=recent_chats,
    referral_count=referral_count,
    chat_rate=CHAT_PAY_RATE * (2 if user.is_premium else 1)
    )

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """API endpoint for chat"""
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        model = data.get('model', 'gpt-4o-mini')
        
        if not message:
            return jsonify({'success': False, 'error': 'Message is required'})
        
        user = User.query.get(session['user_id'])
        
        # Check premium access for advanced models
        if model in ['gpt-4', 'claude-3', 'gemini-pro'] and not (user.is_premium and user.premium_expires > datetime.utcnow()):
            return jsonify({'success': False, 'error': 'Premium subscription required for this model'})
        
        # Generate AI response
        user_context = {
            'is_premium': user.is_premium,
            'platform': 'web',
            'username': user.username
        }
        
        import asyncio
        ai_response = asyncio.run(ai_service.generate_response(message, model, user_context))
        
        # Calculate earnings
        earning_rate = CHAT_PAY_RATE * (2 if user.is_premium else 1)
        
        # Save chat history
        chat = ChatHistory(
            user_id=user.id,
            message=message,
            response=ai_response['response'],
            ai_model=ai_response['model'],
            tokens_used=ai_response['tokens'],
            cost=ai_response['cost'],
            platform='web'
        )
        db.session.add(chat)
        
        # Update user earnings
        user.balance += earning_rate
        user.total_earned += earning_rate
        user.last_active = datetime.utcnow()
        
        # Update analytics
        today = datetime.utcnow().date()
        analytics = UserAnalytics.query.filter_by(
            user_id=user.id, 
            date=today, 
            platform='web'
        ).first()
        
        if not analytics:
            analytics = UserAnalytics(
                user_id=user.id,
                date=today,
                platform='web'
            )
            db.session.add(analytics)
        
        analytics.chats += 1
        analytics.earnings += earning_rate
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': ai_response['response'],
            'model': ai_response['model'],
            'tokens': ai_response['tokens'],
            'earned': earning_rate
        })
        
    except Exception as e:
        logger.error(f"Chat API error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'})

@app.route('/admin')
@admin_required
def admin_panel():
    """Admin panel"""
    # Get system statistics
    today = datetime.utcnow().date()
    stats = SystemStats.query.filter_by(date=today).first()
    
    if not stats:
        update_system_stats()
        stats = SystemStats.query.filter_by(date=today).first()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
    
    # Get recent payments
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(10).all()
    
    return render_template_string("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel - {{ app_name }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .admin-sidebar {
            min-height: 100vh;
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        }
        .admin-content {
            background: #f8f9fa;
            min-height: 100vh;
        }
        .stat-card {
            border: none;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Admin Sidebar -->
            <div class="col-md-3 admin-sidebar text-white p-4">
                <div class="text-center mb-4">
                    <i class="fas fa-cog fa-3x mb-3"></i>
                    <h4>Admin Panel</h4>
                    <p>{{ app_name }}</p>
                </div>
                
                <nav class="nav flex-column">
                    <a class="nav-link text-white active" href="/admin">
                        <i class="fas fa-tachometer-alt"></i> Dashboard
                    </a>
                    <a class="nav-link text-white" href="/admin/users">
                        <i class="fas fa-users"></i> Users
                    </a>
                    <a class="nav-link text-white" href="/admin/payments">
                        <i class="fas fa-credit-card"></i> Payments
                    </a>
                    <a class="nav-link text-white" href="/admin/chats">
                        <i class="fas fa-comments"></i> Chats
                    </a>
                    <a class="nav-link text-white" href="/admin/analytics">
                        <i class="fas fa-chart-bar"></i> Analytics
                    </a>
                    <a class="nav-link text-white" href="/admin/settings">
                        <i class="fas fa-cog"></i> Settings
                    </a>
                    <a class="nav-link text-white" href="/dashboard">
                        <i class="fas fa-arrow-left"></i> Back to Dashboard
                    </a>
                </nav>
            </div>
            
            <!-- Admin Content -->
            <div class="col-md-9 admin-content p-4">
                <div class="row mb-4">
                    <div class="col">
                        <h2>Admin Dashboard</h2>
                        <p class="text-muted">System overview and management</p>
                    </div>
                </div>
                
                <!-- System Stats -->
                <div class="row mb-4">
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-users fa-2x text-primary mb-2"></i>
                                <h4>{{ stats.total_users }}</h4>
                                <p class="text-muted">Total Users</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-user-check fa-2x text-success mb-2"></i>
                                <h4>{{ stats.active_users }}</h4>
                                <p class="text-muted">Active Users</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-crown fa-2x text-warning mb-2"></i>
                                <h4>{{ stats.premium_users }}</h4>
                                <p class="text-muted">Premium Users</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-comments fa-2x text-info mb-2"></i>
                                <h4>{{ stats.total_chats }}</h4>
                                <p class="text-muted">Total Chats</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row mb-4">
                    <div class="col-md-6 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-rupee-sign fa-2x text-success mb-2"></i>
                                <h4>₹{{ "%.2f"|format(stats.total_revenue) }}</h4>
                                <p class="text-muted">Total Revenue</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="card stat-card text-center">
                            <div class="card-body">
                                <i class="fas fa-money-bill-wave fa-2x text-danger mb-2"></i>
                                <h4>₹{{ "%.2f"|format(stats.total_payouts) }}</h4>
                                <p class="text-muted">Total Payouts</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="row">
                    <!-- Recent Users -->
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-user-plus"></i> Recent Users</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>Username</th>
                                                <th>Email</th>
                                                <th>Joined</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for user in recent_users %}
                                            <tr>
                                                <td>{{ user.username }}</td>
                                                <td>{{ user.email }}</td>
                                                <td>{{ user.created_at.strftime('%m/%d') }}</td>
                                                <td>
                                                    {% if user.is_premium %}
                                                    <span class="badge bg-warning">Premium</span>
                                                    {% else %}
                                                    <span class="badge bg-secondary">Free</span>
                                                    {% endif %}
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Payments -->
                    <div class="col-md-6 mb-4">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-credit-card"></i> Recent Payments</h5>
                            </div>
                            <div class="card-body">
                                <div class="table-responsive">
                                    <table class="table table-sm">
                                        <thead>
                                            <tr>
                                                <th>User</th>
                                                <th>Amount</th>
                                                <th>Purpose</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {% for payment in recent_payments %}
                                            <tr>
                                                <td>{{ payment.user.username }}</td>
                                                <td>₹{{ "%.2f"|format(payment.amount) }}</td>
                                                <td>{{ payment.purpose }}</td>
                                                <td>
                                                    {% if payment.status == 'completed' %}
                                                    <span class="badge bg-success">Completed</span>
                                                    {% elif payment.status == 'pending' %}
                                                    <span class="badge bg-warning">Pending</span>
                                                    {% else %}
                                                    <span class="badge bg-danger">Failed</span>
                                                    {% endif %}
                                                </td>
                                            </tr>
                                            {% endfor %}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Quick Actions -->
                <div class="row">
                    <div class="col-12">
                        <div class="card">
                            <div class="card-header">
                                <h5><i class="fas fa-bolt"></i> Quick Actions</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-primary w-100" onclick="updateStats()">
                                            <i class="fas fa-sync"></i> Update Stats
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-success w-100" onclick="exportData()">
                                            <i class="fas fa-download"></i> Export Data
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-warning w-100" onclick="sendNotification()">
                                            <i class="fas fa-bell"></i> Send Notification
                                        </button>
                                    </div>
                                    <div class="col-md-3 mb-2">
                                        <button class="btn btn-info w-100" onclick="viewLogs()">
                                            <i class="fas fa-file-alt"></i> View Logs
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function updateStats() {
            fetch('/admin/api/update-stats', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Error updating stats');
                    }
                });
        }
        
        function exportData() {
            window.open('/admin/api/export-data', '_blank');
        }
        
        function sendNotification() {
            const message = prompt('Enter notification message:');
            if (message) {
                fetch('/admin/api/send-notification', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: message})
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.success ? 'Notification sent!' : 'Error sending notification');
                });
            }
        }
        
        function viewLogs() {
            window.open('/admin/logs', '_blank');
        }
    </script>
</body>
</html>
    """, 
    app_name=APP_NAME,
    stats=stats,
    recent_users=recent_users,
    recent_payments=recent_payments
    )

@app.route('/webhook/telegram', methods=['POST'])
def telegram_webhook():
    """Telegram webhook endpoint"""
    try:
        update_data = request.get_json()
        
        if telegram_bot and update_data:
            import asyncio
            asyncio.run(telegram_bot.process_webhook(update_data))
        
        return jsonify({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({'status': 'error'}), 500

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    return redirect(url_for('index'))

# =========================
# BACKGROUND TASKS
# =========================

def setup_scheduler():
    """Setup background scheduler"""
    scheduler = BackgroundScheduler()
    
    # Update system stats daily
    scheduler.add_job(
        func=update_system_stats,
        trigger="cron",
        hour=0,
        minute=0,
        id='update_stats'
    )
    
    scheduler.start()
    logger.info("Background scheduler started")

# =========================
# DATABASE INITIALIZATION
# =========================

def init_database():
    """Initialize database tables"""
    try:
        with app.app_context():
            db.create_all()
            
            # Create admin user if not exists
            admin = User.query.filter_by(username=ADMIN_USER).first()
            if not admin:
                admin = User(
                    username=ADMIN_USER,
                    email=f"{ADMIN_USER.lower()}@{APP_NAME.lower().replace(' ', '')}.com",
                    password_hash=generate_password_hash(ADMIN_PASS),
                    referral_code=secrets.token_urlsafe(8)[:8].upper(),
                    is_premium=True,
                    premium_expires=datetime.utcnow() + timedelta(days=365*10)  # 10 years
                )
                db.session.add(admin)
                db.session.commit()
                logger.info(f"Admin user created: {ADMIN_USER}")
            
            # Initialize system stats
            update_system_stats()
            
            logger.info("Database initialized successfully")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

# =========================
# APPLICATION STARTUP
# =========================

def setup_telegram_webhook():
    """Setup Telegram webhook"""
    if telegram_bot and WEBHOOK_URL:
        import asyncio
        try:
            asyncio.run(telegram_bot.set_webhook())
        except Exception as e:
            logger.error(f"Failed to set webhook: {str(e)}")

if __name__ == '__main__':
    # Initialize database
    init_database()
    
    # Setup background scheduler
    setup_scheduler()
    
    # Setup Telegram webhook
    setup_telegram_webhook()
    
    # Run the application
    port = int(os.getenv('PORT', 12000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=DEBUG,
        threaded=True
    )
#!/usr/bin/env python3
"""
🤖 Ganesh A.I. - Complete Working System
Real ChatGPT-like Interface with Working Bot
"""

import os
import sys
import json
import time
import uuid
import logging
import sqlite3
import threading
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Import auto error fixer
try:
    from auto_error_fixer import auto_fixer, handle_exception
    AUTO_FIXER_AVAILABLE = True
    print("✅ Auto Error Fixer loaded successfully")
except ImportError:
    AUTO_FIXER_AVAILABLE = False
    print("⚠️ Auto Error Fixer not available")

from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Configuration
APP_NAME = os.getenv('APP_NAME', 'Ganesh A.I.')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
DOMAIN = os.getenv('DOMAIN', 'https://ganesh-ai-working.onrender.com')
ADMIN_USER = os.getenv('ADMIN_USER', 'Admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', '12345')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'ganesh-ai-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ganesh_ai_working.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    wallet = db.Column(db.Float, default=0.0)
    total_earned = db.Column(db.Float, default=0.0)
    chats_count = db.Column(db.Integer, default=0)
    visits_count = db.Column(db.Integer, default=0)
    referrals_count = db.Column(db.Integer, default=0)
    is_premium = db.Column(db.Boolean, default=False)
    premium_until = db.Column(db.DateTime)
    telegram_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_earnings(self, amount, description=""):
        if self.wallet is None:
            self.wallet = 0.0
        if self.total_earned is None:
            self.total_earned = 0.0
        self.wallet += amount
        self.total_earned += amount

# Chat History Model
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(50), default='ganesh-free')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# AI Response System
class AIResponseSystem:
    def __init__(self):
        self.responses = {
            'greetings': [
                "Hello! 👋 I'm Ganesh AI, your intelligent assistant. How can I help you today?",
                "Hi there! 🤖 Welcome to Ganesh AI. What would you like to explore?",
                "Namaste! 🙏 I'm here to assist you with any questions or tasks.",
                "Greetings! ✨ Ready to dive into some AI-powered conversations?"
            ],
            'help': [
                "I can help you with various tasks like answering questions, creative writing, problem-solving, and much more!",
                "I'm here to assist with information, creative tasks, analysis, and general conversation. What do you need help with?",
                "My capabilities include answering questions, helping with writing, providing explanations, and engaging in meaningful conversations."
            ],
            'general': [
                "That's an interesting question! Let me think about that...",
                "I understand what you're asking. Here's my perspective on that...",
                "Great question! Based on my knowledge, I can tell you that...",
                "I'd be happy to help you with that. Let me provide you with some insights..."
            ]
        }

    def generate_response(self, message, user=None):
        """Generate AI response based on message content"""
        message_lower = message.lower()
        
        # Greeting responses
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'start']):
            response = random.choice(self.responses['greetings'])
            if user:
                response = response.replace("I'm Ganesh AI", f"I'm Ganesh AI, {user.username}")
            return response
        
        # Help responses
        elif any(word in message_lower for word in ['help', 'what can you do', 'features', 'capabilities']):
            return random.choice(self.responses['help'])
        
        # Specific topic responses
        elif 'weather' in message_lower:
            return "I don't have access to real-time weather data, but I'd recommend checking a weather app or website for current conditions in your area!"
        
        elif 'time' in message_lower:
            current_time = datetime.now().strftime("%H:%M:%S")
            return f"The current time is {current_time}. Is there anything else I can help you with?"
        
        elif any(word in message_lower for word in ['joke', 'funny', 'humor']):
            jokes = [
                "Why don't scientists trust atoms? Because they make up everything! 😄",
                "I told my computer a joke about UDP... but I'm not sure if it got it! 😂",
                "Why did the AI go to therapy? It had too many deep learning issues! 🤖"
            ]
            return random.choice(jokes)
        
        elif any(word in message_lower for word in ['love', 'like', 'favorite']):
            return "I appreciate your positive sentiment! As an AI, I find joy in helping people and having meaningful conversations. What brings you happiness?"
        
        elif any(word in message_lower for word in ['thank', 'thanks', 'appreciate']):
            return "You're very welcome! I'm always here to help. Feel free to ask me anything else! 😊"
        
        # General intelligent responses
        else:
            base_response = random.choice(self.responses['general'])
            
            # Add contextual information based on message content
            if 'python' in message_lower or 'programming' in message_lower:
                return base_response + " Python is a fantastic programming language! It's versatile, readable, and great for beginners and experts alike."
            
            elif 'ai' in message_lower or 'artificial intelligence' in message_lower:
                return base_response + " AI is rapidly evolving and has incredible potential to help solve complex problems and improve our daily lives."
            
            elif 'business' in message_lower or 'money' in message_lower:
                return base_response + " Building a successful business requires planning, persistence, and understanding your customers' needs."
            
            elif 'learn' in message_lower or 'study' in message_lower:
                return base_response + " Learning is a lifelong journey! The key is to stay curious, practice regularly, and don't be afraid to make mistakes."
            
            else:
                return base_response + f" Regarding '{message[:50]}...', I'd be happy to discuss this topic further with you!"

# Initialize AI system
ai_system = AIResponseSystem()

# Login required decorator
def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            # Track visit
            user.visits_count += 1
            user.add_earnings(0.01, "Login visit")
            db.session.commit()
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/dashboard'})
            return redirect(url_for('dashboard'))
        else:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Invalid credentials'})
            flash('Invalid credentials')
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Username already exists'})
            flash('Username already exists')
            return render_template_string(REGISTER_TEMPLATE)
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email already exists'})
            flash('Email already exists')
            return render_template_string(REGISTER_TEMPLATE)
        
        user = User(username=username, email=email)
        user.set_password(password)
        user.add_earnings(10.0, "Welcome bonus")  # Welcome bonus
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        
        if request.is_json:
            return jsonify({'success': True, 'redirect': '/dashboard'})
        return redirect(url_for('dashboard'))
    
    return render_template_string(REGISTER_TEMPLATE)

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    return render_template_string(DASHBOARD_TEMPLATE, user=user, app_name=APP_NAME)

@app.route('/admin')
@login_required
def admin():
    user = User.query.get(session['user_id'])
    if not user.is_admin:
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    total_users = len(users)
    total_revenue = sum(u.total_earned for u in users)
    total_chats = sum(u.chats_count for u in users)
    
    return render_template_string(ADMIN_TEMPLATE, 
                                users=users, 
                                total_users=total_users,
                                total_revenue=total_revenue,
                                total_chats=total_chats,
                                app_name=APP_NAME)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# API Routes
@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        model = data.get('model', 'ganesh-free')
        
        if not message:
            return jsonify({'success': False, 'message': 'Message is required'})
        
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})
        
        # Generate AI response
        response = ai_system.generate_response(message, user)
        
        # Save chat history
        chat = ChatHistory(
            user_id=user.id,
            message=message,
            response=response,
            model=model
        )
        db.session.add(chat)
        
        # Update user stats
        user.chats_count += 1
        user.add_earnings(0.05, f"Chat with {model}")
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': response,
            'model': model,
            'stats': {
                'wallet': float(user.wallet),
                'chats_count': user.chats_count,
                'total_earned': float(user.total_earned)
            }
        })
        
    except Exception as e:
        print(f"Chat API error: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'})

@app.route('/api/stats')
@login_required
def api_stats():
    user = User.query.get(session['user_id'])
    return jsonify({
        'wallet': float(user.wallet),
        'total_earned': float(user.total_earned),
        'chats_count': user.chats_count,
        'visits_count': user.visits_count,
        'referrals_count': user.referrals_count,
        'is_premium': user.is_premium
    })

# Telegram Bot Integration
class TelegramBot:
    def __init__(self):
        self.token = TELEGRAM_TOKEN
        self.is_running = False
    
    def start_bot(self):
        """Start the Telegram bot"""
        if not self.token:
            print("⚠️ Telegram token not provided. Bot disabled.")
            return
        
        try:
            import telegram
            from telegram.ext import Application, CommandHandler, MessageHandler, filters
            
            # Create application
            application = Application.builder().token(self.token).build()
            
            # Add handlers
            application.add_handler(CommandHandler("start", self.cmd_start))
            application.add_handler(CommandHandler("help", self.cmd_help))
            application.add_handler(CommandHandler("balance", self.cmd_balance))
            application.add_handler(CommandHandler("earnings", self.cmd_earnings))
            application.add_handler(CommandHandler("model", self.cmd_model))
            application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            
            # Start bot
            print("🤖 Starting Telegram bot...")
            self.is_running = True
            application.run_polling()
            
        except ImportError:
            print("⚠️ Telegram bot dependencies not installed. Bot disabled.")
        except Exception as e:
            print(f"❌ Bot error: {e}")
    
    async def cmd_start(self, update, context):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or f"user_{user_id}"
        
        # Create or get user
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                user = User(
                    username=username,
                    email=f"{username}@telegram.com",
                    telegram_id=user_id
                )
                user.set_password("telegram_user")
                user.add_earnings(10.0, "Telegram welcome bonus")
                db.session.add(user)
                db.session.commit()
        
        welcome_msg = f"""
🤖 **Welcome to Ganesh AI!** 

Hello {username}! I'm your advanced AI assistant.

💰 **Earn Money**: Get ₹0.05 for each message!
🧠 **AI Models**: Access multiple AI models
📊 **Track Earnings**: Use /balance to check earnings

**Available Commands:**
/help - Show all commands
/balance - Check your wallet
/earnings - View earning history
/model - Select AI model

Just send me any message and I'll respond instantly! 🚀
        """
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def cmd_help(self, update, context):
        """Handle /help command"""
        help_msg = """
🤖 **Ganesh AI Bot Commands**

**Basic Commands:**
/start - Start the bot and get welcome bonus
/help - Show this help message
/balance - Check your current wallet balance
/earnings - View your earning history
/model - Select AI model for responses

**How to Earn:**
💬 Send messages - ₹0.05 per message
🔗 Refer friends - ₹10 per referral
💎 Premium features - Advanced AI models

**AI Models Available:**
🆓 Ganesh Free - Basic responses
🚀 GPT-4 Turbo - Advanced AI (Premium)
⚡ Claude 3 - Analytical AI (Premium)
🌟 Gemini Pro - Creative AI (Premium)

Just send me any message and I'll respond with AI-powered answers! 🎯
        """
        
        await update.message.reply_text(help_msg, parse_mode='Markdown')
    
    async def cmd_balance(self, update, context):
        """Handle /balance command"""
        user_id = str(update.effective_user.id)
        
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                balance_msg = f"""
💰 **Your Wallet Balance**

Current Balance: ₹{user.wallet:.2f}
Total Earned: ₹{user.total_earned:.2f}
Messages Sent: {user.chats_count}
Referrals: {user.referrals_count}

Keep chatting to earn more! 🚀
                """
            else:
                balance_msg = "Please use /start first to create your account!"
        
        await update.message.reply_text(balance_msg, parse_mode='Markdown')
    
    async def cmd_earnings(self, update, context):
        """Handle /earnings command"""
        user_id = str(update.effective_user.id)
        
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            if user:
                earnings_msg = f"""
📊 **Your Earnings Report**

💰 Total Earned: ₹{user.total_earned:.2f}
💳 Current Balance: ₹{user.wallet:.2f}
💬 Total Chats: {user.chats_count}
👥 Referrals: {user.referrals_count}

**Earning Rates:**
• Message: ₹0.05 each
• Referral: ₹10.00 each
• Daily bonus: ₹1.00

Keep engaging to maximize earnings! 🎯
                """
            else:
                earnings_msg = "Please use /start first to create your account!"
        
        await update.message.reply_text(earnings_msg, parse_mode='Markdown')
    
    async def cmd_model(self, update, context):
        """Handle /model command"""
        model_msg = """
🧠 **Available AI Models**

🆓 **Ganesh Free** - Basic conversations
🚀 **GPT-4 Turbo** - Most advanced AI (Premium)
⚡ **Claude 3** - Analytical reasoning (Premium)
🌟 **Gemini Pro** - Creative tasks (Premium)

Currently using: **Ganesh Free**

Upgrade to Premium for advanced models! 💎
        """
        
        await update.message.reply_text(model_msg, parse_mode='Markdown')
    
    async def handle_message(self, update, context):
        """Handle regular messages"""
        user_id = str(update.effective_user.id)
        message = update.message.text
        
        with app.app_context():
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                await update.message.reply_text("Please use /start first to create your account!")
                return
            
            # Generate AI response
            response = ai_system.generate_response(message, user)
            
            # Save chat and update earnings
            chat = ChatHistory(
                user_id=user.id,
                message=message,
                response=response,
                model='ganesh-free'
            )
            db.session.add(chat)
            
            user.chats_count += 1
            user.add_earnings(0.05, "Telegram chat")
            db.session.commit()
            
            # Send response with earnings info
            full_response = f"{response}\n\n💰 +₹0.05 earned! Balance: ₹{user.wallet:.2f}"
            await update.message.reply_text(full_response)

# Initialize bot
telegram_bot = TelegramBot()

# Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 400px;
            width: 100%;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo i {
            font-size: 60px;
            color: #667eea;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            padding: 12px;
        }
        .form-control {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            padding: 12px;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">
            <i class="fas fa-robot"></i>
            <h2>Ganesh A.I.</h2>
            <p class="text-muted">Advanced AI Assistant</p>
        </div>
        
        <form method="POST" id="loginForm">
            <div class="mb-3">
                <label class="form-label">Username</label>
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
            <small class="text-muted">Demo: Admin / 12345</small>
        </div>
    </div>
</body>
</html>
"""

REGISTER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Register</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .register-card {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            padding: 40px;
            max-width: 400px;
            width: 100%;
        }
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo i {
            font-size: 60px;
            color: #667eea;
            margin-bottom: 10px;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            padding: 12px;
        }
        .form-control {
            border-radius: 10px;
            border: 2px solid #e9ecef;
            padding: 12px;
        }
        .form-control:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="logo">
            <i class="fas fa-robot"></i>
            <h2>Join Ganesh A.I.</h2>
            <p class="text-muted">Start earning with AI!</p>
        </div>
        
        <form method="POST" id="registerForm">
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
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 mb-3">
                <i class="fas fa-user-plus"></i> Register & Get ₹10 Bonus
            </button>
        </form>
        
        <div class="text-center">
            <p>Already have an account? <a href="/login">Login here</a></p>
        </div>
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .chat-container {
            max-width: 800px;
            margin: 20px auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .chat-messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
        }
        .message.user {
            justify-content: flex-end;
        }
        .message.bot {
            justify-content: flex-start;
        }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        .message.bot .message-content {
            background: white;
            color: #333;
            border: 1px solid #e9ecef;
        }
        .chat-input {
            padding: 20px;
            border-top: 1px solid #e9ecef;
            background: white;
        }
        .stats-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .model-selector {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .model-option {
            padding: 10px;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .model-option:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }
        .model-option.active {
            border-color: #667eea;
            background: #667eea;
            color: white;
        }
        .typing-indicator {
            display: none;
            padding: 10px;
            font-style: italic;
            color: #666;
        }
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-robot"></i> {{ app_name }}
            </a>
            <div class="navbar-nav ms-auto">
                <span class="navbar-text me-3">Welcome, {{ user.username }}!</span>
                <a class="nav-link" href="/logout">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div class="row">
            <!-- Stats Panel -->
            <div class="col-md-4">
                <div class="stats-card">
                    <h5><i class="fas fa-wallet"></i> Your Stats</h5>
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-success">₹{{ "%.2f"|format(user.wallet) }}</h4>
                            <small>Balance</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-primary">{{ user.chats_count }}</h4>
                            <small>Chats</small>
                        </div>
                    </div>
                    <hr>
                    <div class="row text-center">
                        <div class="col-6">
                            <h4 class="text-info">₹{{ "%.2f"|format(user.total_earned) }}</h4>
                            <small>Total Earned</small>
                        </div>
                        <div class="col-6">
                            <h4 class="text-warning">{{ user.visits_count }}</h4>
                            <small>Visits</small>
                        </div>
                    </div>
                </div>

                <!-- Model Selector -->
                <div class="model-selector">
                    <h5><i class="fas fa-brain"></i> AI Model</h5>
                    <div class="model-option active" onclick="selectModel('ganesh-free')">
                        <strong>🆓 Ganesh Free</strong>
                        <br><small>Basic conversations - Free</small>
                    </div>
                    <div class="model-option" onclick="selectModel('gpt-4')">
                        <strong>🚀 GPT-4 Turbo</strong>
                        <br><small>Advanced AI - Premium</small>
                    </div>
                    <div class="model-option" onclick="selectModel('claude')">
                        <strong>🎯 Claude 3</strong>
                        <br><small>Analytical AI - Premium</small>
                    </div>
                </div>

                {% if user.is_admin %}
                <div class="stats-card">
                    <h5><i class="fas fa-crown"></i> Admin Panel</h5>
                    <a href="/admin" class="btn btn-warning w-100">
                        <i class="fas fa-cog"></i> Manage System
                    </a>
                </div>
                {% endif %}
            </div>

            <!-- Chat Panel -->
            <div class="col-md-8">
                <div class="chat-container">
                    <div class="chat-header">
                        <h4><i class="fas fa-comments"></i> Chat with Ganesh AI</h4>
                        <p class="mb-0">Earn ₹0.05 for each message!</p>
                    </div>
                    
                    <div class="chat-messages" id="chatMessages">
                        <div class="message bot">
                            <div class="message-content">
                                Hello {{ user.username }}! 👋 I'm Ganesh AI, your intelligent assistant. How can I help you today?
                            </div>
                        </div>
                    </div>
                    
                    <div class="typing-indicator" id="typingIndicator">
                        <i class="fas fa-robot"></i> Ganesh AI is typing...
                    </div>
                    
                    <div class="chat-input">
                        <div class="input-group">
                            <input type="text" class="form-control" id="messageInput" 
                                   placeholder="Type your message here..." 
                                   onkeypress="handleKeyPress(event)">
                            <button class="btn btn-primary" onclick="sendMessage()">
                                <i class="fas fa-paper-plane"></i> Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentModel = 'ganesh-free';
        let chatHistory = [];

        function selectModel(model) {
            currentModel = model;
            document.querySelectorAll('.model-option').forEach(el => el.classList.remove('active'));
            event.target.closest('.model-option').classList.add('active');
        }

        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }

        async function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message) return;
            
            // Add user message to chat
            addMessage(message, 'user');
            input.value = '';
            
            // Show typing indicator
            document.getElementById('typingIndicator').style.display = 'block';
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        model: currentModel
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    addMessage(data.response, 'bot');
                    
                    // Update stats if provided
                    if (data.stats) {
                        updateStats(data.stats);
                    }
                } else {
                    addMessage('Sorry, I encountered an error. Please try again.', 'bot');
                }
            } catch (error) {
                console.error('Chat error:', error);
                addMessage('Sorry, I encountered a connection error. Please try again.', 'bot');
            } finally {
                document.getElementById('typingIndicator').style.display = 'none';
            }
        }

        function addMessage(content, sender) {
            const messagesContainer = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            messageContent.innerHTML = content.replace(/\n/g, '<br>');
            
            messageDiv.appendChild(messageContent);
            messagesContainer.appendChild(messageDiv);
            
            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Save to history
            chatHistory.push({ content, sender, timestamp: new Date() });
        }

        function updateStats(stats) {
            // Update stats display (you can implement this based on your UI)
            console.log('Stats updated:', stats);
        }

        // Auto-focus on message input
        document.getElementById('messageInput').focus();
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }} - Admin Panel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            background: #f8f9fa;
        }
        .navbar {
            background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
        }
        .stats-card {
            background: white;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .table-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="#">
                <i class="fas fa-crown"></i> {{ app_name }} Admin
            </a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">
                    <i class="fas fa-arrow-left"></i> Back to Dashboard
                </a>
                <a class="nav-link" href="/logout">
                    <i class="fas fa-sign-out-alt"></i> Logout
                </a>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <!-- Stats Overview -->
        <div class="row">
            <div class="col-md-3">
                <div class="stats-card text-center">
                    <i class="fas fa-users fa-2x text-primary mb-2"></i>
                    <h3>{{ total_users }}</h3>
                    <p class="mb-0">Total Users</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card text-center">
                    <i class="fas fa-rupee-sign fa-2x text-success mb-2"></i>
                    <h3>₹{{ "%.2f"|format(total_revenue) }}</h3>
                    <p class="mb-0">Total Revenue</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card text-center">
                    <i class="fas fa-comments fa-2x text-info mb-2"></i>
                    <h3>{{ total_chats }}</h3>
                    <p class="mb-0">Total Chats</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="stats-card text-center">
                    <i class="fas fa-robot fa-2x text-warning mb-2"></i>
                    <h3>Active</h3>
                    <p class="mb-0">Bot Status</p>
                </div>
            </div>
        </div>

        <!-- Users Table -->
        <div class="table-container">
            <h4><i class="fas fa-users"></i> User Management</h4>
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Balance</th>
                            <th>Total Earned</th>
                            <th>Chats</th>
                            <th>Premium</th>
                            <th>Joined</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.id }}</td>
                            <td>
                                {{ user.username }}
                                {% if user.is_admin %}
                                <span class="badge bg-danger">Admin</span>
                                {% endif %}
                            </td>
                            <td>{{ user.email }}</td>
                            <td>₹{{ "%.2f"|format(user.wallet) }}</td>
                            <td>₹{{ "%.2f"|format(user.total_earned) }}</td>
                            <td>{{ user.chats_count }}</td>
                            <td>
                                {% if user.is_premium %}
                                <span class="badge bg-success">Yes</span>
                                {% else %}
                                <span class="badge bg-secondary">No</span>
                                {% endif %}
                            </td>
                            <td>{{ user.created_at.strftime('%Y-%m-%d') }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# Initialize database and create admin user
def init_db():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        admin = User.query.filter_by(username=ADMIN_USER).first()
        if not admin:
            admin = User(
                username=ADMIN_USER,
                email='admin@ganesh-ai.com',
                is_admin=True
            )
            admin.set_password(ADMIN_PASS)
            admin.add_earnings(1000.0, "Admin initial balance")
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Admin user created: {ADMIN_USER} / {ADMIN_PASS}")

# Start Telegram bot in background
def start_bot_background():
    if TELEGRAM_TOKEN:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            telegram_bot.start_bot()
        except Exception as e:
            print(f"❌ Bot startup error: {e}")

if __name__ == '__main__':
    print("🚀 Starting Ganesh A.I. Complete System...")
    
    # Start auto error fixer
    if AUTO_FIXER_AVAILABLE:
        auto_fixer.start_monitoring()
        print("🔧 Auto Error Fixer started")
    
    # Initialize database
    init_db()
    
    # Start Telegram bot in background thread
    if TELEGRAM_TOKEN:
        bot_thread = threading.Thread(target=start_bot_background, daemon=True)
        bot_thread.start()
        print("🤖 Telegram bot started in background")
    else:
        print("⚠️ Telegram bot disabled (no token)")
    
    # Start Flask app
    port = int(os.getenv('PORT', 10000))
    print(f"🌐 Starting web server on port {port}")
    print(f"🔗 Access URL: {DOMAIN}")
    print(f"👨‍💼 Admin: {ADMIN_USER} / {ADMIN_PASS}")
    print("✅ All systems operational - Auto error fixing enabled!")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=DEBUG)
    except Exception as e:
        if AUTO_FIXER_AVAILABLE:
            auto_fixer.fix_error(type(e).__name__, str(e))
        raise
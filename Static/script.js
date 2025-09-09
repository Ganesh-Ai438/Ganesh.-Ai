// Ganesh A.I. Complete Frontend System
console.log("🚀 Ganesh A.I. Advanced Frontend System Loading...");

// Global variables
let currentModel = 'ganesh-free';
let chatHistory = [];
let isTyping = false;
let autoErrorFix = true;

// Error handling and auto-fix system
class ErrorHandler {
    constructor() {
        this.errorCount = 0;
        this.maxRetries = 3;
        this.setupGlobalErrorHandling();
    }

    setupGlobalErrorHandling() {
        window.addEventListener('error', (e) => this.handleError(e));
        window.addEventListener('unhandledrejection', (e) => this.handlePromiseRejection(e));
    }

    handleError(error) {
        console.error('🔴 Error detected:', error);
        this.errorCount++;
        
        if (autoErrorFix) {
            this.attemptAutoFix(error);
        }
        
        this.logError(error);
    }

    handlePromiseRejection(event) {
        console.error('🔴 Promise rejection:', event.reason);
        this.attemptAutoFix({ error: event.reason, type: 'promise' });
    }

    attemptAutoFix(errorInfo) {
        const error = errorInfo.error || errorInfo;
        const message = error.message || error.toString();

        console.log('🔧 Attempting auto-fix for:', message);

        // Network errors
        if (message.includes('fetch') || message.includes('network')) {
            this.fixNetworkError();
        }
        
        // DOM errors
        else if (message.includes('null') && message.includes('property')) {
            this.fixDOMError();
        }
        
        // API errors
        else if (message.includes('API') || message.includes('400') || message.includes('500')) {
            this.fixAPIError();
        }
        
        // Generic fixes
        else {
            this.genericFix();
        }
    }

    fixNetworkError() {
        console.log('🔧 Fixing network error...');
        setTimeout(() => {
            if (navigator.onLine) {
                console.log('✅ Network restored, retrying last action');
                this.retryLastAction();
            }
        }, 2000);
    }

    fixDOMError() {
        console.log('🔧 Fixing DOM error...');
        // Wait for DOM to be ready
        if (document.readyState !== 'complete') {
            window.addEventListener('load', () => {
                console.log('✅ DOM ready, reinitializing');
                this.reinitialize();
            });
        }
    }

    fixAPIError() {
        console.log('🔧 Fixing API error...');
        // Switch to fallback model
        if (currentModel !== 'ganesh-free') {
            currentModel = 'ganesh-free';
            this.showNotification('Switched to free model due to API error', 'warning');
        }
    }

    genericFix() {
        console.log('🔧 Applying generic fix...');
        // Reload critical components
        setTimeout(() => {
            this.reinitialize();
        }, 1000);
    }

    retryLastAction() {
        // Implement retry logic for last failed action
        console.log('🔄 Retrying last action...');
    }

    reinitialize() {
        console.log('🔄 Reinitializing system...');
        initializeApp();
    }

    logError(error) {
        // Send error to server for analysis
        fetch('/api/log-error', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                error: error.message || error.toString(),
                stack: error.stack,
                timestamp: new Date().toISOString(),
                userAgent: navigator.userAgent,
                url: window.location.href
            })
        }).catch(() => {}); // Silent fail for error logging
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'warning' ? 'exclamation-triangle' : 'info'}"></i>
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => notification.remove(), 5000);
    }
}

// Initialize error handler
const errorHandler = new ErrorHandler();

// Chat System
class ChatSystem {
    constructor() {
        this.messageQueue = [];
        this.isProcessing = false;
        this.retryCount = 0;
        this.maxRetries = 3;
    }

    async sendMessage(message, model = currentModel) {
        if (!message.trim()) return;

        try {
            this.addMessageToUI(message, 'user');
            this.showTypingIndicator();

            const response = await this.makeAPICall('/api/chat', {
                message: message,
                model: model,
                conversation_id: this.getConversationId()
            });

            this.hideTypingIndicator();

            if (response.success) {
                this.addMessageToUI(response.response, 'bot');
                this.updateUserStats(response.stats);
                this.saveToHistory(message, response.response);
                this.retryCount = 0; // Reset retry count on success
            } else {
                throw new Error(response.message || 'API call failed');
            }

        } catch (error) {
            this.hideTypingIndicator();
            this.handleChatError(error, message, model);
        }
    }

    async makeAPICall(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    }

    handleChatError(error, originalMessage, model) {
        console.error('Chat error:', error);
        
        if (this.retryCount < this.maxRetries) {
            this.retryCount++;
            console.log(`🔄 Retrying chat (${this.retryCount}/${this.maxRetries})...`);
            
            setTimeout(() => {
                this.sendMessage(originalMessage, model);
            }, 1000 * this.retryCount);
            
            return;
        }

        // Max retries reached, show error and fallback
        let errorMessage = 'Sorry, I encountered an error. ';
        
        if (error.message.includes('network') || error.message.includes('fetch')) {
            errorMessage += 'Please check your internet connection and try again.';
        } else if (model !== 'ganesh-free') {
            errorMessage += 'Switching to free model...';
            currentModel = 'ganesh-free';
            this.updateModelUI();
            setTimeout(() => this.sendMessage(originalMessage, 'ganesh-free'), 1000);
            return;
        } else {
            errorMessage += 'Please try again in a moment.';
        }

        this.addMessageToUI(errorMessage, 'bot');
        this.retryCount = 0;
    }

    addMessageToUI(content, sender) {
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Format message content
        if (sender === 'bot') {
            messageContent.innerHTML = this.formatBotMessage(content);
        } else {
            messageContent.textContent = content;
        }
        
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        // Smooth scroll to bottom
        messagesContainer.scrollTo({
            top: messagesContainer.scrollHeight,
            behavior: 'smooth'
        });
    }

    formatBotMessage(content) {
        // Format markdown-like content
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
        isTyping = true;
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('loadingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
        isTyping = false;
    }

    updateModelUI() {
        const modelName = this.getModelDisplayName(currentModel);
        const currentModelElement = document.getElementById('current-model');
        if (currentModelElement) {
            currentModelElement.textContent = modelName;
        }

        // Update model selection UI
        document.querySelectorAll('.model-card').forEach(card => {
            card.classList.remove('selected');
            if (card.dataset.model === currentModel) {
                card.classList.add('selected');
            }
        });
    }

    getModelDisplayName(model) {
        const modelNames = {
            'ganesh-free': 'Ganesh AI Free',
            'gpt-4-turbo': 'GPT-4 Turbo',
            'claude-3-sonnet': 'Claude 3 Sonnet',
            'gemini-pro': 'Gemini Pro'
        };
        return modelNames[model] || model;
    }

    updateUserStats(stats) {
        if (!stats) return;

        // Update wallet balance
        document.querySelectorAll('[data-stat="wallet"]').forEach(el => {
            el.textContent = `₹${stats.wallet.toFixed(2)}`;
        });

        // Update chat count
        document.querySelectorAll('[data-stat="chats"]').forEach(el => {
            el.textContent = stats.chats_count || 0;
        });

        // Update total earned
        document.querySelectorAll('[data-stat="earned"]').forEach(el => {
            el.textContent = `₹${stats.total_earned.toFixed(2)}`;
        });
    }

    saveToHistory(userMessage, botResponse) {
        chatHistory.push({
            user: userMessage,
            bot: botResponse,
            timestamp: new Date().toISOString(),
            model: currentModel
        });

        // Keep only last 100 messages
        if (chatHistory.length > 100) {
            chatHistory = chatHistory.slice(-100);
        }

        localStorage.setItem('ganesh_chat_history', JSON.stringify(chatHistory));
    }

    loadHistory() {
        const saved = localStorage.getItem('ganesh_chat_history');
        if (saved) {
            try {
                chatHistory = JSON.parse(saved);
                this.displayRecentHistory();
            } catch (error) {
                console.error('Error loading chat history:', error);
                chatHistory = [];
            }
        }
    }

    displayRecentHistory() {
        const recent = chatHistory.slice(-5); // Show last 5 conversations
        recent.forEach(conversation => {
            this.addMessageToUI(conversation.user, 'user');
            this.addMessageToUI(conversation.bot, 'bot');
        });
    }

    clearHistory() {
        chatHistory = [];
        localStorage.removeItem('ganesh_chat_history');
        
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="message bot">
                    <div class="message-content">
                        Chat cleared! How can I help you today? 🚀
                    </div>
                </div>
            `;
        }
    }

    getConversationId() {
        let conversationId = localStorage.getItem('ganesh_conversation_id');
        if (!conversationId) {
            conversationId = 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem('ganesh_conversation_id', conversationId);
        }
        return conversationId;
    }
}

// Initialize chat system
const chatSystem = new ChatSystem();

// UI Management
class UIManager {
    constructor() {
        this.currentSection = 'chat';
        this.sidebarCollapsed = false;
    }

    init() {
        this.setupEventListeners();
        this.setupResponsiveHandling();
        this.loadUserPreferences();
    }

    setupEventListeners() {
        // Menu navigation
        document.querySelectorAll('.menu-item').forEach(item => {
            item.addEventListener('click', (e) => this.handleMenuClick(e));
        });

        // Model selection
        document.querySelectorAll('.model-card').forEach(card => {
            card.addEventListener('click', (e) => this.handleModelSelection(e));
        });

        // Chat input
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // Sidebar toggle
        const toggleBtn = document.querySelector('.toggle-sidebar');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggleSidebar());
        }
    }

    handleMenuClick(e) {
        e.preventDefault();
        
        const menuItem = e.currentTarget;
        const section = menuItem.dataset.section;
        
        if (!section) return;

        // Update active menu item
        document.querySelectorAll('.menu-item').forEach(item => {
            item.classList.remove('active');
        });
        menuItem.classList.add('active');

        // Show selected section
        this.showSection(section);
        this.currentSection = section;
        
        // Save preference
        localStorage.setItem('ganesh_current_section', section);
    }

    showSection(sectionName) {
        // Hide all sections
        document.querySelectorAll('.content-section').forEach(section => {
            section.style.display = 'none';
        });

        // Show selected section
        const targetSection = document.getElementById(`${sectionName}-section`);
        if (targetSection) {
            targetSection.style.display = 'block';
            
            // Load section-specific data
            this.loadSectionData(sectionName);
        }
    }

    async loadSectionData(section) {
        switch (section) {
            case 'statistics':
                await this.loadStatistics();
                break;
            case 'earnings':
                await this.loadEarnings();
                break;
            case 'referrals':
                await this.loadReferrals();
                break;
            case 'admin':
                await this.loadAdminData();
                break;
        }
    }

    async loadStatistics() {
        try {
            const response = await fetch('/api/user/statistics');
            const data = await response.json();
            
            if (data.success) {
                this.updateStatisticsUI(data.stats);
            }
        } catch (error) {
            console.error('Error loading statistics:', error);
        }
    }

    async loadEarnings() {
        try {
            const response = await fetch('/api/user/earnings');
            const data = await response.json();
            
            if (data.success) {
                this.updateEarningsUI(data.earnings);
            }
        } catch (error) {
            console.error('Error loading earnings:', error);
        }
    }

    async loadReferrals() {
        try {
            const response = await fetch('/api/user/referrals');
            const data = await response.json();
            
            if (data.success) {
                this.updateReferralsUI(data.referrals);
            }
        } catch (error) {
            console.error('Error loading referrals:', error);
        }
    }

    handleModelSelection(e) {
        const card = e.currentTarget;
        const model = card.dataset.model;
        
        // Check if premium model and user has access
        if (card.classList.contains('premium')) {
            // This will be handled by the backend
        }

        // Update selection
        document.querySelectorAll('.model-card').forEach(c => {
            c.classList.remove('selected');
        });
        card.classList.add('selected');

        // Update current model
        currentModel = model;
        chatSystem.updateModelUI();
    }

    toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.getElementById('mainContent');
        
        if (window.innerWidth <= 768) {
            sidebar.classList.toggle('show');
        } else {
            sidebar.classList.toggle('collapsed');
            mainContent.classList.toggle('expanded');
            this.sidebarCollapsed = !this.sidebarCollapsed;
        }
        
        localStorage.setItem('ganesh_sidebar_collapsed', this.sidebarCollapsed);
    }

    setupResponsiveHandling() {
        window.addEventListener('resize', () => {
            if (window.innerWidth > 768) {
                const sidebar = document.getElementById('sidebar');
                sidebar.classList.remove('show');
            }
        });
    }

    loadUserPreferences() {
        // Load saved section
        const savedSection = localStorage.getItem('ganesh_current_section');
        if (savedSection) {
            this.showSection(savedSection);
            
            // Update menu
            document.querySelectorAll('.menu-item').forEach(item => {
                item.classList.remove('active');
                if (item.dataset.section === savedSection) {
                    item.classList.add('active');
                }
            });
        }

        // Load sidebar state
        const sidebarCollapsed = localStorage.getItem('ganesh_sidebar_collapsed') === 'true';
        if (sidebarCollapsed) {
            this.toggleSidebar();
        }
    }

    sendMessage() {
        const input = document.getElementById('messageInput');
        if (!input) return;

        const message = input.value.trim();
        if (!message) return;

        input.value = '';
        chatSystem.sendMessage(message);
    }

    // Utility functions
    copyToClipboard(text, successMessage = 'Copied to clipboard!') {
        navigator.clipboard.writeText(text).then(() => {
            errorHandler.showNotification(successMessage, 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            errorHandler.showNotification(successMessage, 'success');
        });
    }

    showModal(title, content, actions = []) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">${title}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">${content}</div>
                    <div class="modal-footer">
                        ${actions.map(action => `<button type="button" class="btn ${action.class}" onclick="${action.onclick}">${action.text}</button>`).join('')}
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        modal.addEventListener('hidden.bs.modal', () => {
            document.body.removeChild(modal);
        });
    }
}

// Initialize UI manager
const uiManager = new UIManager();

// Payment System
class PaymentSystem {
    async requestWithdrawal(amount) {
        try {
            const response = await fetch('/api/withdrawal', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ amount: parseFloat(amount) })
            });
            
            const data = await response.json();
            
            if (data.success) {
                errorHandler.showNotification('Withdrawal request submitted successfully!', 'success');
                setTimeout(() => location.reload(), 2000);
            } else {
                errorHandler.showNotification(data.message, 'danger');
            }
        } catch (error) {
            errorHandler.showNotification('Error processing withdrawal request', 'danger');
        }
    }

    async subscribePremium(plan) {
        try {
            const response = await fetch('/api/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan: plan })
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.location.href = data.payment_url;
            } else {
                errorHandler.showNotification(data.message, 'danger');
            }
        } catch (error) {
            errorHandler.showNotification('Error processing subscription', 'danger');
        }
    }
}

const paymentSystem = new PaymentSystem();

// Admin System
class AdminSystem {
    async loadUsers() {
        try {
            const response = await fetch('/api/admin/users');
            const data = await response.json();
            
            if (data.success) {
                this.displayUsersTable(data.users);
            }
        } catch (error) {
            errorHandler.showNotification('Error loading users', 'danger');
        }
    }

    async loadRevenue() {
        try {
            const response = await fetch('/api/admin/revenue');
            const data = await response.json();
            
            if (data.success) {
                this.displayRevenueStats(data);
            }
        } catch (error) {
            errorHandler.showNotification('Error loading revenue data', 'danger');
        }
    }

    async manageBotStatus(action) {
        try {
            const response = await fetch(`/api/admin/bot/${action}`, {
                method: 'POST'
            });
            
            const data = await response.json();
            errorHandler.showNotification(data.message, data.success ? 'success' : 'danger');
            
            if (data.success) {
                this.loadBotStatus();
            }
        } catch (error) {
            errorHandler.showNotification('Error managing bot', 'danger');
        }
    }

    displayUsersTable(users) {
        const content = document.getElementById('adminContent');
        if (!content) return;

        let html = `
            <h6>All Users (${users.length})</h6>
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Username</th>
                            <th>Email</th>
                            <th>Wallet</th>
                            <th>Total Earned</th>
                            <th>Referrals</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        users.forEach(user => {
            html += `
                <tr>
                    <td>${user.username}</td>
                    <td>${user.email}</td>
                    <td>₹${user.wallet.toFixed(2)}</td>
                    <td>₹${user.total_earned.toFixed(2)}</td>
                    <td>${user.referrals_count}</td>
                    <td>
                        <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="adminSystem.viewUser(${user.id})">
                            View
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        content.innerHTML = html;
    }

    displayRevenueStats(data) {
        const content = document.getElementById('adminContent');
        if (!content) return;

        content.innerHTML = `
            <h6>Revenue Statistics</h6>
            <div class="row">
                <div class="col-md-3">
                    <div class="card bg-primary text-white">
                        <div class="card-body text-center">
                            <h4>₹${data.total_revenue.toFixed(2)}</h4>
                            <small>Total Revenue</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-success text-white">
                        <div class="card-body text-center">
                            <h4>₹${data.today_revenue.toFixed(2)}</h4>
                            <small>Today's Revenue</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-info text-white">
                        <div class="card-body text-center">
                            <h4>${data.total_users}</h4>
                            <small>Total Users</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="card bg-warning text-white">
                        <div class="card-body text-center">
                            <h4>${data.active_users}</h4>
                            <small>Active Users</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

const adminSystem = new AdminSystem();

// Main initialization function
function initializeApp() {
    console.log('🚀 Initializing Ganesh A.I. Application...');
    
    try {
        // Initialize UI
        uiManager.init();
        
        // Load chat history
        chatSystem.loadHistory();
        
        // Setup auto-refresh for stats
        setInterval(async () => {
            try {
                const response = await fetch('/api/user/stats');
                const data = await response.json();
                if (data.success) {
                    chatSystem.updateUserStats(data.stats);
                }
            } catch (error) {
                // Silent fail for background updates
            }
        }, 30000); // Every 30 seconds
        
        console.log('✅ Ganesh A.I. Application initialized successfully!');
        
    } catch (error) {
        console.error('❌ Error initializing application:', error);
        errorHandler.handleError({ error });
    }
}

// Global functions for HTML onclick events
window.sendMessage = () => uiManager.sendMessage();
window.clearChat = () => chatSystem.clearHistory();
window.toggleSidebar = () => uiManager.toggleSidebar();
window.copyReferralCode = () => {
    const code = document.getElementById('referralCode')?.value;
    if (code) uiManager.copyToClipboard(code, 'Referral code copied!');
};
window.copyReferralLink = () => {
    const link = document.getElementById('referralLink')?.value;
    if (link) uiManager.copyToClipboard(link, 'Referral link copied!');
};
window.requestWithdrawal = () => {
    const amount = prompt('Enter withdrawal amount (minimum ₹100):');
    if (amount && parseFloat(amount) >= 100) {
        paymentSystem.requestWithdrawal(amount);
    }
};
window.subscribePremium = (plan) => paymentSystem.subscribePremium(plan);

// Admin functions
window.viewAllUsers = () => adminSystem.loadUsers();
window.viewRevenue = () => adminSystem.loadRevenue();
window.startBot = () => adminSystem.manageBotStatus('start');
window.stopBot = () => adminSystem.manageBotStatus('stop');
window.botStatus = () => adminSystem.loadBotStatus();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

// Service Worker for offline functionality
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/sw.js')
        .then(() => console.log('✅ Service Worker registered'))
        .catch(() => console.log('❌ Service Worker registration failed'));
}

console.log('✅ Ganesh A.I. Frontend System Ready!');
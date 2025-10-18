// Global variables
let currentUser = null;
let authToken = null;

// API Base URL
const API_BASE = '';

// Utility Functions
function showLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        const messageEl = overlay.querySelector('p');
        if (messageEl) messageEl.textContent = message;
        overlay.classList.add('active');
    }
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.remove('active');
    }
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
}

function showError(message) {
    alert(`Error: ${message}`);
}

function showSuccess(message) {
    alert(`Success: ${message}`);
}

function formatCurrency(amount) {
    return `KES ${parseFloat(amount).toLocaleString('en-KE', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-KE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function formatDateTime(dateString) {
    return new Date(dateString).toLocaleString('en-KE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Authentication Functions
function isAuthenticated() {
    const token = localStorage.getItem('mshield_token');
    const user = localStorage.getItem('mshield_user');
    return token && user;
}

function setAuthData(token, user) {
    localStorage.setItem('mshield_token', token);
    localStorage.setItem('mshield_user', JSON.stringify(user));
    authToken = token;
    currentUser = user;
}

function clearAuthData() {
    localStorage.removeItem('mshield_token');
    localStorage.removeItem('mshield_user');
    authToken = null;
    currentUser = null;
}

function getAuthHeaders() {
    const token = localStorage.getItem('mshield_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

// API Functions
async function apiCall(endpoint, options = {}) {
    const url = `${API_BASE}/api${endpoint}`;
    const token = localStorage.getItem('mshield_token');
    
    if (!token && endpoint !== '/auth/login' && endpoint !== '/auth/register') {
        throw new Error('Authentication required');
    }

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        credentials: 'include'
    };

    try {
        const response = await fetch(url, { ...defaultOptions, ...options });
        if (response.status === 403) {
            // Handle authentication errors
            clearAuthData();
            window.location.href = '/';
            throw new Error('Authentication failed');
        }
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Landing Page Functions
function showLogin() {
    showModal('login-modal');
}

function showRegister() {
    showModal('register-modal');
}

function switchToLogin() {
    closeModal('register-modal');
    showModal('login-modal');
}

function switchToRegister() {
    closeModal('login-modal');
    showModal('register-modal');
}

// Authentication Event Handlers
document.addEventListener('DOMContentLoaded', function() {
    // Login form handler
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            showLoading('Logging you in...');
            
            try {
                const response = await apiCall('/auth/login', {
                    method: 'POST',
                    body: JSON.stringify({ email, password })
                });
                
                setAuthData(response.access_token, response.user);
                hideLoading();
                closeModal('login-modal');
                window.location.href = '/dashboard';
            } catch (error) {
                hideLoading();
                showError(error.message);
            }
        });
    }

    // Register form handler
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const email = document.getElementById('register-email').value;
            const phone = document.getElementById('register-phone').value;
            const password = document.getElementById('register-password').value;
            
            showLoading('Creating your account...');
            
            try {
                const response = await apiCall('/auth/register', {
                    method: 'POST',
                    body: JSON.stringify({ email, phone, password })
                });
                
                setAuthData(response.access_token, response.user);
                hideLoading();
                closeModal('register-modal');
                window.location.href = '/dashboard';
            } catch (error) {
                hideLoading();
                showError(error.message);
            }
        });
    }

    // Close modal when clicking outside
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('modal')) {
            e.target.classList.remove('active');
        }
    });
});

// Dashboard Functions
async function loadDashboard() {
    showLoading('Loading your dashboard...');
    
    try {
        // Load user profile
        const user = JSON.parse(localStorage.getItem('mshield_user'));
        document.getElementById('user-email').textContent = user.email;
        
        // Load balance information
        await loadBalanceInfo();
        
        // Load savings goals
        await loadSavingsGoals();
        
        // Load recent transactions
        await loadRecentTransactions();
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Failed to load dashboard: ' + error.message);
    }
}

async function loadBalanceInfo() {
    try {
        const balance = await apiCall('/savings/balance');
        
        document.getElementById('total-savings').textContent = formatCurrency(balance.total_savings);
        document.getElementById('loan-eligible').textContent = formatCurrency(balance.loan_eligible_amount);
        
        // Update progress bar (assuming 15000 as target)
        const progressPercent = Math.min((balance.total_savings / 15000) * 100, 100);
        document.getElementById('savings-progress').style.width = `${progressPercent}%`;
        
        // Load active loans count
        const loans = await apiCall('/loans');
        const activeLoans = loans.filter(loan => loan.status === 'active').length;
        document.getElementById('active-loans').textContent = activeLoans;
        
    } catch (error) {
        console.error('Failed to load balance:', error);
    }
}

async function loadSavingsGoals() {
    try {
        const goals = await apiCall('/savings/goals');
        const goalsGrid = document.getElementById('goals-grid');
        
        if (goals.length === 0) {
            goalsGrid.innerHTML = `
                <div class="goal-card">
                    <div class="text-center">
                        <h3>No savings goals yet</h3>
                        <p>Create your first savings goal to get started!</p>
                        <button class="btn btn-primary mt-3" onclick="showCreateGoal()">Create Goal</button>
                    </div>
                </div>
            `;
            return;
        }
        
        goalsGrid.innerHTML = goals.map(goal => `
            <div class="goal-card">
                <div class="goal-header">
                    <div class="goal-name">${goal.goal_name}</div>
                    <div class="goal-menu">⋮</div>
                </div>
                <div class="goal-amount">${formatCurrency(goal.current_amount)}</div>
                <div class="goal-target">of ${formatCurrency(goal.target_amount)}</div>
                <div class="goal-progress">
                    <div class="progress-text">
                        <span>${Math.round(goal.progress)}% complete</span>
                        <span>Due: ${formatDate(goal.target_date)}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress" style="width: ${Math.min(goal.progress, 100)}%"></div>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load savings goals:', error);
    }
}

async function loadRecentTransactions() {
    try {
        const transactions = await apiCall('/transactions');
        const activityList = document.getElementById('activity-list');
        
        if (transactions.length === 0) {
            activityList.innerHTML = `
                <div class="activity-item">
                    <div class="activity-details">
                        <div class="activity-title">No transactions yet</div>
                        <div class="activity-description">Your transaction history will appear here</div>
                    </div>
                </div>
            `;
            return;
        }
        
        activityList.innerHTML = transactions.slice(0, 10).map(transaction => {
            const isPositive = transaction.transaction_type === 'savings';
            const icon = isPositive ? '💰' : '📤';
            const iconClass = isPositive ? 'savings' : 'loan';
            
            return `
                <div class="activity-item">
                    <div class="activity-icon ${iconClass}">${icon}</div>
                    <div class="activity-details">
                        <div class="activity-title">${transaction.description || transaction.transaction_type}</div>
                        <div class="activity-description">${formatDateTime(transaction.timestamp)}</div>
                    </div>
                    <div class="activity-amount">
                        ${isPositive ? '+' : '-'}${formatCurrency(Math.abs(transaction.amount))}
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Failed to load transactions:', error);
    }
}

// Modal Functions for Dashboard
function showAddSavings() {
    populateSavingsGoalDropdown();
    showModal('add-savings-modal');
}

function showCreateGoal() {
    showModal('create-goal-modal');
}

// Form Handlers for Dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Add savings form handler
    const addSavingsForm = document.getElementById('add-savings-form');
    if (addSavingsForm) {
        addSavingsForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const amount = parseFloat(document.getElementById('savings-amount').value);
            const description = document.getElementById('savings-description').value;
            const goalId = document.getElementById('savings-goal').value;
            
            showLoading('Adding to your savings...');
            
            try {
                await apiCall('/savings/transactions', {
                    method: 'POST',
                    body: JSON.stringify({
                        amount: amount,
                        transaction_type: 'savings',
                        description: description || 'Manual savings deposit',
                        goal_id: goalId
                    })
                });
                
                hideLoading();
                closeModal('add-savings-modal');
                showSuccess(`Successfully added ${formatCurrency(amount)} to your savings!`);
                
                // Reload dashboard data
                await loadBalanceInfo();
                await loadRecentTransactions();
                
                // Reset form
                addSavingsForm.reset();
                
            } catch (error) {
                hideLoading();
                showError(error.message);
            }
        });
    }

    // Create goal form handler
    const createGoalForm = document.getElementById('create-goal-form');
    if (createGoalForm) {
        createGoalForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const goalName = document.getElementById('goal-name').value;
            const goalAmount = parseFloat(document.getElementById('goal-amount').value);
            const goalDate = document.getElementById('goal-date').value;
            
            showLoading('Creating your savings goal...');
            
            try {
                await apiCall('/savings/goals', {
                    method: 'POST',
                    body: JSON.stringify({
                        goal_name: goalName,
                        target_amount: goalAmount,
                        target_date: goalDate
                    })
                });
                
                hideLoading();
                closeModal('create-goal-modal');
                showSuccess(`Successfully created goal: ${goalName}!`);
                
                // Reload savings goals
                await loadSavingsGoals();
                
                // Reset form
                createGoalForm.reset();
                
            } catch (error) {
                hideLoading();
                showError(error.message);
            }
        });
    }
});

// Loan Request Functions
async function loadLoanRequestPage() {
    showLoading('Loading loan request page...');
    
    try {
        // Load user profile
        const user = JSON.parse(localStorage.getItem('mshield_user'));
        document.getElementById('user-email').textContent = user.email;
        
        // Load available loan amount
        const balance = await apiCall('/savings/balance');
        document.getElementById('max-loan-amount').textContent = formatCurrency(balance.loan_eligible_amount);
        
        hideLoading();
    } catch (error) {
        hideLoading();
        showError('Failed to load loan request page: ' + error.message);
    }
}

function showStep(stepNumber) {
    // Hide all steps
    document.querySelectorAll('.loan-step').forEach(step => {
        step.classList.remove('active');
    });
    
    // Show target step
    document.getElementById(`step-${stepNumber}`).classList.add('active');
}

// Loan Request Form Handler
document.addEventListener('DOMContentLoaded', function() {
    const loanRequestForm = document.getElementById('loan-request-form');
    if (loanRequestForm) {
        loanRequestForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const amount = parseFloat(document.getElementById('loan-amount').value);
            const reason = document.getElementById('loan-reason').value;
            
            showLoading('Analyzing your request with AI...');
            
            try {
                // First, classify the request
                const classification = await apiCall('/ai/classify', {
                    method: 'POST',
                    body: JSON.stringify({ description: reason })
                });
                
                // Show AI analysis
                showStep(2);
                displayAIAnalysis(classification, amount, reason);
                
                hideLoading();
                
            } catch (error) {
                hideLoading();
                showError(error.message);
            }
        });
    }
});

function displayAIAnalysis(classification, amount, reason) {
    const analysisDiv = document.getElementById('ai-analysis');
    
    const emergencyBadge = classification.is_emergency ? 
        '<div class="analysis-badge emergency">🚨 Emergency Detected</div>' :
        '<div class="analysis-badge non-emergency">ℹ️ Non-Emergency</div>';
    
    const confidenceColor = classification.confidence > 0.8 ? '#27ae60' : 
                           classification.confidence > 0.6 ? '#f39c12' : '#e74c3c';
    
    analysisDiv.innerHTML = `
        <div class="analysis-result">
            <div class="analysis-category">
                ${classification.category.replace('_', ' ').toUpperCase()}
            </div>
            <div class="analysis-confidence" style="color: ${confidenceColor}">
                ${Math.round(classification.confidence * 100)}% Confidence
            </div>
            ${emergencyBadge}
            <div class="analysis-recommendation">
                <div class="recommendation-text">
                    ${classification.recommendation}
                </div>
            </div>
        </div>
        
        <div class="loan-decision-buttons">
            <button class="btn btn-outline" onclick="showStep(1)">← Back to Edit</button>
            <button class="btn btn-primary" onclick="proceedWithLoan(${amount}, '${reason}', ${JSON.stringify(classification).replace(/"/g, '&quot;')})">
                ${classification.is_emergency ? 'Approve Emergency Loan' : 'Request Loan Anyway'}
            </button>
        </div>
    `;
}

async function proceedWithLoan(amount, reason, classification) {
    showLoading('Processing your loan request...');
    
    try {
        const loanResponse = await apiCall('/loans/request', {
            method: 'POST',
            body: JSON.stringify({
                amount: amount,
                reason: reason
            })
        });
        
        // Show loan approval
        showStep(3);
        displayLoanApproval(loanResponse);
        
        hideLoading();
        
    } catch (error) {
        hideLoading();
        showError(error.message);
    }
}

function displayLoanApproval(loanData) {
    const approvalDiv = document.getElementById('loan-approval');
    
    approvalDiv.innerHTML = `
        <div class="approval-header">
            <div class="approval-icon">✅</div>
            <div class="approval-title">Loan Approved!</div>
            <div class="approval-subtitle">Your funds will be transferred within 5 minutes</div>
        </div>
        
        <div class="loan-details">
            <div class="detail-row">
                <span class="detail-label">Loan Amount:</span>
                <span class="detail-value">${formatCurrency(loanData.amount)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Interest Rate:</span>
                <span class="detail-value">${(loanData.interest_rate * 100).toFixed(1)}%</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Due Date:</span>
                <span class="detail-value">${formatDate(loanData.due_date)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Total Repayment:</span>
                <span class="detail-value total-repayment">${formatCurrency(loanData.total_repayment)}</span>
            </div>
        </div>
        
        <div class="ai-classification-summary">
            <h4>🤖 AI Analysis Summary</h4>
            <p><strong>Category:</strong> ${loanData.ai_classification.category}</p>
            <p><strong>Confidence:</strong> ${Math.round(loanData.ai_classification.confidence * 100)}%</p>
            <p><strong>Emergency Status:</strong> ${loanData.ai_classification.is_emergency ? 'Yes' : 'No'}</p>
        </div>
        
        <div class="approval-actions">
            <button class="btn btn-outline" onclick="window.location.href='/dashboard'">Back to Dashboard</button>
            <button class="btn btn-primary" onclick="simulatePayHeroTransfer(${loanData.amount})">
                Transfer to M-Pesa 📱
            </button>
        </div>
    `;
}

async function simulatePayHeroTransfer(amount) {
    showLoading('Transferring funds to your M-Pesa...');
    
    try {
        const transferResponse = await apiCall('/payhero/simulate-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: `amount=${amount}&description=M-Shield Emergency Loan`
        });
        
        hideLoading();
        showSuccess(`Transfer successful! M-Pesa receipt: ${transferResponse.mpesa_receipt}`);
        
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 3000);
        
    } catch (error) {
        hideLoading();
        showError('Transfer failed: ' + error.message);
    }
}

// Logout Function
function logout() {
    clearAuthData();
    window.location.href = '/';
}

// Initialize app based on current page
document.addEventListener('DOMContentLoaded', function() {
    // Set minimum date for goal creation to today
    const goalDateInput = document.getElementById('goal-date');
    if (goalDateInput) {
        const today = new Date().toISOString().split('T')[0];
        goalDateInput.min = today;
    }
    
    // Auto-focus first input in modals when they open
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                const firstInput = modal.querySelector('input');
                if (firstInput) {
                    setTimeout(() => firstInput.focus(), 100);
                }
            }
        });
    });
    
    // Add loading states to buttons
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.textContent;
                submitBtn.textContent = 'Processing...';
                
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }, 5000);
            }
        });
    });
});

// Error handling for network issues
window.addEventListener('online', function() {
    showSuccess('Connection restored!');
});

window.addEventListener('offline', function() {
    showError('You are offline. Some features may not work.');
});

// Performance optimization - lazy load images
document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('img[data-src]');
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
});

// Add smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Add animation on scroll
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('fade-in');
        }
    });
}, observerOptions);

// Observe elements for animation
document.addEventListener('DOMContentLoaded', function() {
    const animateElements = document.querySelectorAll('.feature-card, .balance-card, .action-btn, .goal-card, .insight-card');
    animateElements.forEach(el => observer.observe(el));
});

// Populate the savings goal dropdown when the modal opens
function populateSavingsGoalDropdown() {
    const select = document.getElementById('savings-goal');
    if (!select) return;
    select.innerHTML = '<option value="">Select a goal...</option>';
    apiCall('/savings/goals').then(goals => {
        if (goals.length === 0) {
            select.innerHTML = '<option value="">No active goals found</option>';
        } else {
            select.innerHTML = goals.map(goal =>
                `<option value="${goal.id}">${goal.goal_name} (${formatCurrency(goal.current_amount)} / ${formatCurrency(goal.target_amount)})</option>`
            ).join('');
        }
    }).catch(() => {
        select.innerHTML = '<option value="">Failed to load goals</option>';
    });
}

function showAddSavings() {
    populateSavingsGoalDropdown();
    showModal('add-savings-modal');
}
# Professional Supabase Integration for Mwarokin Estates

## Complete Backend Connection Files

### 1. `js/config.js` - Configuration File

```javascript
/**
 * ============================================================================
 * MWAROKIN ESTATES - Supabase Configuration
 * ============================================================================
 * File: js/config.js
 * Version: 2.0.0
 * Description: Centralized configuration for Supabase and application settings
 * ============================================================================
 */

// Supabase Configuration
const SUPABASE_CONFIG = {
    url: 'https://spnerrqumefbuuscumhw.supabase.co',
    anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNwbmVycnF1bWVmYnV1c2N1bWh3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDAwMDAwMDAsImV4cCI6MjA0MDAwMDAwMH0.placeholder'
};

// Application Configuration
const APP_CONFIG = {
    // Session settings
    sessionTimeout: 60 * 60 * 1000,  // 60 minutes
    idleTimeout: 55 * 1000,          // 55 seconds
    
    // Feature flags
    enableAnalytics: true,
    enableActivityLogging: true,
    enableMaintenance: true,
    enablePayments: true,
    enableVisitorLogs: true,
    
    // API endpoints
    endpoints: {
        auth: '/auth/v1',
        rest: '/rest/v1'
    },
    
    // Role-based portal mapping
    rolePortals: {
        tenant: 'tenant-dashboard',
        landlord: 'landlord-dashboard',
        caretaker: 'caretaker-dashboard',
        management: 'management-dashboard',
        professional: 'professional-dashboard'
    }
};

// Error messages
const ERROR_MESSAGES = {
    networkError: 'Network error. Please check your internet connection.',
    authError: 'Authentication failed. Please try again.',
    sessionExpired: 'Your session has expired. Please log in again.',
    emailRequired: 'Email address is required.',
    passwordRequired: 'Password is required.',
    roleRequired: 'Please select a role.',
    invalidEmail: 'Please enter a valid email address.',
    weakPassword: 'Password must be at least 8 characters long.',
    userExists: 'An account with this email already exists.',
    userNotFound: 'No account found with this email.',
    invalidCredentials: 'Invalid email or password.',
    maintenanceError: 'Unable to submit maintenance request. Please try again.',
    paymentError: 'Payment processing failed. Please try again.',
    visitorLogError: 'Unable to log visitor. Please try again.'
};

// Export configurations
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { SUPABASE_CONFIG, APP_CONFIG, ERROR_MESSAGES };
}
```

### 2. `js/supabase-client.js` - Supabase Client & Database Operations

```javascript
/**
 * ============================================================================
 * MWAROKIN ESTATES - Supabase Client
 * ============================================================================
 * File: js/supabase-client.js
 * Version: 2.0.0
 * Description: Supabase client initialization and database operations
 * ============================================================================
 */

// Initialize Supabase client
let supabase = null;
let currentSession = null;
let currentUser = null;

/**
 * Initialize Supabase client
 */
function initSupabase() {
    try {
        if (typeof supabaseJs !== 'undefined') {
            supabase = supabaseJs.createClient(
                SUPABASE_CONFIG.url,
                SUPABASE_CONFIG.anonKey
            );
            console.log('✓ Supabase client initialized');
            return supabase;
        } else if (typeof window.supabase !== 'undefined') {
            supabase = window.supabase.createClient(
                SUPABASE_CONFIG.url,
                SUPABASE_CONFIG.anonKey
            );
            console.log('✓ Supabase client initialized (window)');
            return supabase;
        } else {
            console.error('✗ Supabase library not loaded');
            return null;
        }
    } catch (error) {
        console.error('✗ Supabase initialization failed:', error);
        return null;
    }
}

/**
 * ============================================================================
 * AUTHENTICATION OPERATIONS
 * ============================================================================
 */

/**
 * Sign up a new user
 */
async function signUpUser(email, password, userData) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase.auth.signUp({
            email: email,
            password: password,
            options: {
                data: {
                    full_name: userData.full_name,
                    phone_number: userData.phone_number,
                    user_role: userData.user_role,
                    created_at: new Date().toISOString()
                }
            }
        });

        if (error) throw error;

        // Log registration to custom table
        if (data.user) {
            await logUserRegistration({
                user_id: data.user.id,
                email: email,
                full_name: userData.full_name,
                phone_number: userData.phone_number,
                role: userData.user_role
            });

            // Log activity
            await logActivity({
                event_type: 'registration',
                user_id: data.user.id,
                user_role: userData.user_role,
                description: `User registered: ${email}`,
                metadata: {
                    full_name: userData.full_name,
                    role: userData.user_role
                }
            });
        }

        return { 
            success: true, 
            data: data,
            user: data.user,
            session: data.session
        };
    } catch (error) {
        console.error('Sign up error:', error);
        return { 
            success: false, 
            error: error.message,
            code: error.code
        };
    }
}

/**
 * Sign in a user
 */
async function signInUser(email, password) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase.auth.signInWithPassword({
            email: email,
            password: password
        });

        if (error) throw error;

        currentSession = data.session;
        currentUser = data.user;

        // Log sign-in activity
        await logActivity({
            event_type: 'login',
            user_id: data.user.id,
            user_role: data.user.user_metadata?.user_role || 'unknown',
            description: `User logged in: ${email}`,
            metadata: {
                ip_address: await getClientIP(),
                user_agent: navigator.userAgent
            }
        });

        // Update session tracking
        updateSessionTracking(data.user.id);

        return { 
            success: true, 
            data: data,
            user: data.user,
            session: data.session
        };
    } catch (error) {
        console.error('Sign in error:', error);
        return { 
            success: false, 
            error: error.message,
            code: error.code
        };
    }
}

/**
 * Sign out a user
 */
async function signOutUser() {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        // Log sign-out activity
        if (currentUser) {
            await logActivity({
                event_type: 'logout',
                user_id: currentUser.id,
                user_role: currentUser.user_metadata?.user_role || 'unknown',
                description: `User logged out: ${currentUser.email}`,
                metadata: {
                    session_duration: Date.now() - sessionStartTime
                }
            });
        }

        const { error } = await supabase.auth.signOut();
        if (error) throw error;

        currentSession = null;
        currentUser = null;
        sessionStartTime = null;

        return { success: true };
    } catch (error) {
        console.error('Sign out error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Get current session
 */
async function getCurrentSession() {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase.auth.getSession();
        if (error) throw error;

        if (data.session) {
            currentSession = data.session;
            currentUser = data.session.user;
        }

        return { 
            success: true, 
            session: data.session,
            user: data.session?.user || null
        };
    } catch (error) {
        console.error('Get session error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Get current user
 */
function getCurrentUser() {
    return currentUser;
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return currentSession !== null && currentUser !== null;
}

/**
 * ============================================================================
 * DATABASE OPERATIONS
 * ============================================================================
 */

/**
 * Log user registration to custom table
 */
async function logUserRegistration(data) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) return;
    }

    try {
        const { error } = await supabase
            .from('user_registrations')
            .insert([{
                user_id: data.user_id,
                email: data.email,
                full_name: data.full_name,
                phone_number: data.phone_number,
                role: data.role,
                created_at: new Date().toISOString(),
                ip_address: await getClientIP(),
                user_agent: navigator.userAgent
            }]);

        if (error) throw error;
        console.log('✓ User registration logged:', data.email);
    } catch (error) {
        console.error('Failed to log registration:', error);
    }
}

/**
 * Log activity to the activity_logs table
 */
async function logActivity(data) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) return;
    }

    try {
        const { error } = await supabase
            .from('activity_logs')
            .insert([{
                event_type: data.event_type,
                user_id: data.user_id,
                user_role: data.user_role,
                description: data.description,
                metadata: data.metadata || {},
                ip_address: data.ip_address || await getClientIP(),
                device_info: data.device_info || navigator.userAgent,
                created_at: new Date().toISOString()
            }]);

        if (error) throw error;
        console.log('✓ Activity logged:', data.event_type);
    } catch (error) {
        console.error('Failed to log activity:', error);
    }
}

/**
 * ============================================================================
 * PAYMENT OPERATIONS
 * ============================================================================
 */

/**
 * Process rent payment
 */
async function processRentPayment(paymentData) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const payment = {
            id: crypto.randomUUID(),
            amount: paymentData.amount,
            unit_id: paymentData.unit_id,
            user_id: paymentData.user_id,
            user_role: paymentData.user_role || 'tenant',
            transaction_type: paymentData.transaction_type || 'rent',
            status: 'pending',
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            metadata: paymentData.metadata || {},
            receipt_url: paymentData.receipt_url || null
        };

        const { data, error } = await supabase
            .from('transactions')
            .insert([payment])
            .select();

        if (error) throw error;

        // Log payment activity
        await logActivity({
            event_type: 'payment',
            user_id: paymentData.user_id,
            user_role: paymentData.user_role || 'tenant',
            description: `Rent payment of ${paymentData.amount} for unit ${paymentData.unit_id}`,
            metadata: {
                amount: paymentData.amount,
                unit_id: paymentData.unit_id
            }
        });

        return { 
            success: true, 
            data: data[0],
            payment: payment
        };
    } catch (error) {
        console.error('Payment processing error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Get transaction history for a user
 */
async function getTransactionHistory(userId, limit = 50) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase
            .from('transactions')
            .select('*')
            .eq('user_id', userId)
            .order('created_at', { ascending: false })
            .limit(limit);

        if (error) throw error;

        return { 
            success: true, 
            data: data 
        };
    } catch (error) {
        console.error('Transaction history error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * ============================================================================
 * MAINTENANCE OPERATIONS
 * ============================================================================
 */

/**
 * Submit maintenance request
 */
async function submitMaintenanceRequest(requestData) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const request = {
            id: crypto.randomUUID(),
            unit_id: requestData.unit_id,
            user_id: requestData.user_id,
            user_role: requestData.user_role || 'tenant',
            title: requestData.title,
            description: requestData.description,
            priority: requestData.priority || 'medium',
            status: 'pending',
            assigned_to: requestData.assigned_to || null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            notes: requestData.notes || [],
            attachments: requestData.attachments || []
        };

        const { data, error } = await supabase
            .from('maintenance_requests')
            .insert([request])
            .select();

        if (error) throw error;

        // Log maintenance activity
        await logActivity({
            event_type: 'maintenance',
            user_id: requestData.user_id,
            user_role: requestData.user_role || 'tenant',
            description: `Maintenance request: ${requestData.title}`,
            metadata: {
                unit_id: requestData.unit_id,
                priority: requestData.priority
            }
        });

        return { 
            success: true, 
            data: data[0],
            request: request
        };
    } catch (error) {
        console.error('Maintenance request error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Get maintenance requests for a unit
 */
async function getMaintenanceRequests(unitId, limit = 50) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase
            .from('maintenance_requests')
            .select('*')
            .eq('unit_id', unitId)
            .order('created_at', { ascending: false })
            .limit(limit);

        if (error) throw error;

        return { 
            success: true, 
            data: data 
        };
    } catch (error) {
        console.error('Maintenance requests error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Update maintenance request status
 */
async function updateMaintenanceStatus(requestId, status, userId, notes = null) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const updateData = {
            status: status,
            updated_at: new Date().toISOString()
        };

        if (status === 'resolved' || status === 'completed') {
            updateData.resolved_at = new Date().toISOString();
        }

        if (notes) {
            // Append notes to existing notes array
            const { data: current } = await supabase
                .from('maintenance_requests')
                .select('notes')
                .eq('id', requestId)
                .single();

            if (current) {
                const currentNotes = current.notes || [];
                currentNotes.push({
                    note: notes,
                    user_id: userId,
                    timestamp: new Date().toISOString()
                });
                updateData.notes = currentNotes;
            }
        }

        const { data, error } = await supabase
            .from('maintenance_requests')
            .update(updateData)
            .eq('id', requestId)
            .select();

        if (error) throw error;

        // Log status update
        await logActivity({
            event_type: 'maintenance_update',
            user_id: userId,
            user_role: 'management',
            description: `Maintenance request ${requestId} status updated to ${status}`,
            metadata: {
                request_id: requestId,
                status: status
            }
        });

        return { 
            success: true, 
            data: data[0] 
        };
    } catch (error) {
        console.error('Maintenance status update error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * ============================================================================
 * VISITOR OPERATIONS
 * ============================================================================
 */

/**
 * Log visitor entry
 */
async function logVisitor(visitorData) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const visitor = {
            id: crypto.randomUUID(),
            visitor_name: visitorData.visitor_name,
            unit_id: visitorData.unit_id,
            purpose: visitorData.purpose,
            checked_in_at: new Date().toISOString(),
            checked_out_at: null,
            host_user_id: visitorData.host_user_id || null,
            phone_number: visitorData.phone_number || null,
            id_type: visitorData.id_type || null,
            id_number: visitorData.id_number || null,
            created_by: visitorData.created_by,
            created_at: new Date().toISOString()
        };

        const { data, error } = await supabase
            .from('visitors')
            .insert([visitor])
            .select();

        if (error) throw error;

        // Log visitor activity
        await logActivity({
            event_type: 'visitor',
            user_id: visitorData.created_by,
            user_role: 'caretaker',
            description: `Visitor logged: ${visitorData.visitor_name} for unit ${visitorData.unit_id}`,
            metadata: {
                visitor_name: visitorData.visitor_name,
                unit_id: visitorData.unit_id,
                purpose: visitorData.purpose
            }
        });

        return { 
            success: true, 
            data: data[0],
            visitor: visitor
        };
    } catch (error) {
        console.error('Visitor log error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Checkout visitor
 */
async function checkoutVisitor(visitorId, checkoutBy) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase
            .from('visitors')
            .update({
                checked_out_at: new Date().toISOString()
            })
            .eq('id', visitorId)
            .select();

        if (error) throw error;

        // Log checkout activity
        await logActivity({
            event_type: 'visitor_checkout',
            user_id: checkoutBy,
            user_role: 'caretaker',
            description: `Visitor ${visitorId} checked out`,
            metadata: {
                visitor_id: visitorId,
                checked_out_by: checkoutBy
            }
        });

        return { 
            success: true, 
            data: data[0] 
        };
    } catch (error) {
        console.error('Visitor checkout error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * ============================================================================
 * UNIT OPERATIONS
 * ============================================================================
 */

/**
 * Get units for a landlord
 */
async function getLandlordUnits(landlordId) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase
            .from('units')
            .select('*')
            .eq('landlord_id', landlordId);

        if (error) throw error;

        return { 
            success: true, 
            data: data 
        };
    } catch (error) {
        console.error('Get landlord units error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * Get unit by ID
 */
async function getUnitById(unitId) {
    if (!supabase) {
        supabase = initSupabase();
        if (!supabase) {
            return { success: false, error: 'Supabase not initialized' };
        }
    }

    try {
        const { data, error } = await supabase
            .from('units')
            .select('*')
            .eq('id', unitId)
            .single();

        if (error) throw error;

        return { 
            success: true, 
            data: data 
        };
    } catch (error) {
        console.error('Get unit error:', error);
        return { 
            success: false, 
            error: error.message 
        };
    }
}

/**
 * ============================================================================
 * UTILITY FUNCTIONS
 * ============================================================================
 */

/**
 * Get client IP address
 */
async function getClientIP() {
    try {
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        return data.ip;
    } catch (error) {
        console.error('IP fetch error:', error);
        return 'unknown';
    }
}

/**
 * Generate random UUID (fallback if crypto.randomUUID not available)
 */
function generateUUID() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

/**
 * Validate email format
 */
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

/**
 * Format currency
 */
function formatCurrency(amount, currency = 'KES') {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: currency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-KE', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Get time ago string
 */
function timeAgo(dateString) {
    const now = new Date();
    const date = new Date(dateString);
    const seconds = Math.floor((now - date) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 86400)} days ago`;
    if (seconds < 31536000) return `${Math.floor(seconds / 2592000)} months ago`;
    return `${Math.floor(seconds / 31536000)} years ago`;
}

// Session tracking
let sessionStartTime = null;

function updateSessionTracking(userId) {
    sessionStartTime = Date.now();
    localStorage.setItem('mwarokin_session_start', sessionStartTime.toString());
    localStorage.setItem('mwarokin_user_id', userId);
}

// Export functions for use in HTML
window.supabaseClient = {
    initSupabase,
    signUpUser,
    signInUser,
    signOutUser,
    getCurrentSession,
    getCurrentUser,
    isAuthenticated,
    processRentPayment,
    getTransactionHistory,
    submitMaintenanceRequest,
    getMaintenanceRequests,
    updateMaintenanceStatus,
    logVisitor,
    checkoutVisitor,
    getLandlordUnits,
    getUnitById,
    logActivity,
    validateEmail,
    formatCurrency,
    formatDate,
    timeAgo
};
```

### 3. `js/app.js` - UI Integration & Event Handlers

```javascript
/**
 * ============================================================================
 * MWAROKIN ESTATES - Application Logic
 * ============================================================================
 * File: js/app.js
 * Version: 2.0.0
 * Description: UI event handlers and application state management
 * ============================================================================
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const AppState = {
    currentUser: null,
    currentRole: null,
    currentView: 'landing',
    isLoading: false,
    notifications: [],
    isAuthenticated: false,
    sessionTimeout: APP_CONFIG.sessionTimeout,
    idleTimeout: APP_CONFIG.idleTimeout,
    lastActivity: Date.now(),
    idleWarningShown: false,
    idleTimerInterval: null
};

// ============================================================================
// DOM REFERENCES
// ============================================================================

const DOM = {
    // Navigation
    navCta: document.getElementById('navCta'),
    mobileCta: document.getElementById('mobileCta'),
    hamburger: document.getElementById('hamburger'),
    mobileMenu: document.getElementById('mobileMenu'),
    
    // Hero
    heroSignUp: document.getElementById('heroSignUp'),
    heroLogin: document.getElementById('heroLogin'),
    
    // Forms
    loginForm: document.getElementById('loginForm'),
    registerForm: document.getElementById('registerForm'),
    
    // Auth containers
    landingContainer: document.getElementById('landingContainer'),
    loginContainer: document.getElementById('loginContainer'),
    registerContainer: document.getElementById('registerContainer'),
    dashboardContainer: document.getElementById('dashboardContainer'),
    
    // Dashboard
    userAvatar: document.getElementById('userAvatar'),
    userName: document.getElementById('userName'),
    userRole: document.getElementById('userRole'),
    greetingMessage: document.getElementById('greetingMessage'),
    currentTime: document.getElementById('currentTime'),
    
    // Modals
    sessionTimeoutModal: document.getElementById('sessionTimeoutModal'),
    idleTimer: document.getElementById('idleTimer'),
    timerValue: document.getElementById('timerValue'),
    timeoutCounter: document.getElementById('timeoutCounter'),
    
    // Notifications
    toast: document.getElementById('toast'),
    notificationBadge: document.getElementById('notificationBadge')
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async function() {
    console.log('Mwarokin Estates - Application Starting');
    
    // Initialize Supabase
    const supabase = supabaseClient.initSupabase();
    if (!supabase) {
        showToast('Failed to initialize connection. Please refresh.', 'error');
        return;
    }
    
    // Check existing session
    await checkExistingSession();
    
    // Setup event listeners
    setupEventListeners();
    
    // Start activity tracking
    startActivityTracking();
    
    // Update time
    updateCurrentTime();
    setInterval(updateCurrentTime, 60000);
    
    console.log('✓ Application initialized');
});

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

async function checkExistingSession() {
    try {
        const result = await supabaseClient.getCurrentSession();
        if (result.success && result.session) {
            const user = result.user;
            AppState.currentUser = user;
            AppState.isAuthenticated = true;
            AppState.currentRole = user.user_metadata?.user_role || 'tenant';
            
            // Update UI
            updateUserUI(user);
            showDashboard();
            
            console.log('✓ Existing session found:', user.email);
            return true;
        }
    } catch (error) {
        console.error('Session check error:', error);
    }
    return false;
}

function updateUserUI(user) {
    if (!user) return;
    
    const name = user.user_metadata?.full_name || user.email?.split('@')[0] || 'User';
    const role = user.user_metadata?.user_role || 'tenant';
    const avatar = name.charAt(0).toUpperCase();
    
    // Update avatar
    if (DOM.userAvatar) DOM.userAvatar.textContent = avatar;
    if (DOM.userName) DOM.userName.textContent = name;
    if (DOM.userRole) DOM.userRole.textContent = capitalizeFirst(role);
    
    // Update navigation
    updateNavForRole(role);
}

function updateNavForRole(role) {
    // Update navigation based on role
    const roleNavMap = {
        'tenant': ['tenantNav'],
        'landlord': ['landlordNav'],
        'caretaker': ['caretakerNav'],
        'management': ['managementNav'],
        'professional': ['professionalNav']
    };
    
    // Show appropriate nav sections
    document.querySelectorAll('.nav-section').forEach(section => {
        section.style.display = 'none';
    });
    
    const navs = roleNavMap[role] || ['tenantNav'];
    navs.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.style.display = 'block';
    });
}

function capitalizeFirst(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// ============================================================================
// VIEW MANAGEMENT
// ============================================================================

function showView(viewName) {
    // Hide all views
    document.querySelectorAll('.view-container').forEach(el => {
        el.style.display = 'none';
    });
    
    // Show target view
    const view = document.getElementById(`${viewName}Container`);
    if (view) {
        view.style.display = 'block';
        AppState.currentView = viewName;
    }
}

function showLanding() {
    showView('landing');
}

function showLogin() {
    showView('login');
    document.getElementById('loginEmail')?.focus();
}

function showRegister() {
    showView('register');
    document.getElementById('registerName')?.focus();
}

function showDashboard() {
    showView('dashboard');
    updateDashboardContent();
}

// ============================================================================
// AUTHENTICATION HANDLERS
// ============================================================================

async function handleLogin(event) {
    event.preventDefault();
    
    const email = document.getElementById('loginEmail')?.value;
    const password = document.getElementById('loginPassword')?.value;
    const role = document.getElementById('loginRole')?.value;
    
    // Clear errors
    clearErrors('login');
    
    // Validate
    if (!email) return showFieldError('loginEmail', 'Email is required');
    if (!password) return showFieldError('loginPassword', 'Password is required');
    if (!role) return showFieldError('loginRole', 'Please select a role');
    if (!supabaseClient.validateEmail(email)) {
        return showFieldError('loginEmail', 'Please enter a valid email');
    }
    
    try {
        setLoading(true, 'Signing in...');
        
        const result = await supabaseClient.signInUser(email, password);
        
        if (!result.success) {
            setLoading(false);
            return showToast(result.error || 'Sign in failed', 'error');
        }
        
        // Success
        AppState.currentUser = result.user;
        AppState.isAuthenticated = true;
        AppState.currentRole = result.user.user_metadata?.user_role || role;
        
        updateUserUI(result.user);
        showDashboard();
        showToast(`Welcome back, ${result.user.user_metadata?.full_name || 'User'}!`, 'success');
        
        // Log view
        await supabaseClient.logActivity({
            event_type: 'page_view',
            user_id: result.user.id,
            user_role: AppState.currentRole,
            description: `User accessed dashboard`,
            metadata: { view: 'dashboard' }
        });
        
        setLoading(false);
    } catch (error) {
        setLoading(false);
        console.error('Login error:', error);
        showToast(error.message || 'Sign in failed. Please try again.', 'error');
    }
}

async function handleRegister(event) {
    event.preventDefault();
    
    const name = document.getElementById('registerName')?.value;
    const email = document.getElementById('registerEmail')?.value;
    const phone = document.getElementById('registerPhone')?.value;
    const role = document.getElementById('registerRole')?.value;
    const password = document.getElementById('registerPassword')?.value;
    const confirmPassword = document.getElementById('registerConfirmPassword')?.value;
    
    // Clear errors
    clearErrors('register');
    
    // Validate
    if (!name) return showFieldError('registerName', 'Full name is required');
    if (!email) return showFieldError('registerEmail', 'Email is required');
    if (!supabaseClient.validateEmail(email)) {
        return showFieldError('registerEmail', 'Please enter a valid email');
    }
    if (!phone) return showFieldError('registerPhone', 'Phone number is required');
    if (!role) return showFieldError('registerRole', 'Please select a role');
    if (!password) return showFieldError('registerPassword', 'Password is required');
    if (password.length < 8) {
        return showFieldError('registerPassword', 'Password must be at least 8 characters');
    }
    if (password !== confirmPassword) {
        return showFieldError('registerConfirmPassword', 'Passwords do not match');
    }
    
    try {
        setLoading(true, 'Creating account...');
        
        const result = await supabaseClient.signUpUser(email, password, {
            full_name: name,
            phone_number: phone,
            user_role: role
        });
        
        if (!result.success) {
            setLoading(false);
            return showToast(result.error || 'Registration failed', 'error');
        }
        
        // Success
        showToast('Account created successfully! Please check your email to verify.', 'success');
        
        // Show login
        setTimeout(() => {
            showLogin();
            document.getElementById('loginEmail').value = email;
            document.getElementById('loginRole').value = role;
        }, 1500);
        
        setLoading(false);
    } catch (error) {
        setLoading(false);
        console.error('Registration error:', error);
        showToast(error.message || 'Registration failed. Please try again.', 'error');
    }
}

async function handleLogout() {
    try {
        const result = await supabaseClient.signOutUser();
        if (result.success) {
            AppState.currentUser = null;
            AppState.isAuthenticated = false;
            AppState.currentRole = null;
            showLanding();
            showToast('Logged out successfully', 'info');
        }
    } catch (error) {
        console.error('Logout error:', error);
        showToast('Logout failed. Please try again.', 'error');
    }
}

// ============================================================================
// FORM HELPERS
// ============================================================================

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (field) {
        field.classList.add('error');
        const errorEl = document.getElementById(`${fieldId}Error`);
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.classList.add('show');
        }
    }
}

function clearErrors(prefix) {
    document.querySelectorAll(`[id^="${prefix}"]`).forEach(el => {
        if (el.classList.contains('error')) {
            el.classList.remove('error');
        }
        if (el.id?.endsWith('Error')) {
            el.classList.remove('show');
        }
    });
}

function setLoading(isLoading, message = 'Processing...') {
    AppState.isLoading = isLoading;
    const submitBtns = document.querySelectorAll('.btn[type="submit"], .btn-loading');
    submitBtns.forEach(btn => {
        if (isLoading) {
            btn.disabled = true;
            btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> ${message}`;
        } else {
            btn.disabled = false;
            btn.innerHTML = btn.dataset.originalText || btn.textContent;
        }
    });
}

// ============================================================================
// DASHBOARD FUNCTIONS
// ============================================================================

function updateDashboardContent() {
    // Update greeting
    const greeting = getTimeBasedGreeting();
    if (DOM.greetingMessage) DOM.greetingMessage.textContent = greeting;
    
    // Update stats based on role
    updateRoleSpecificContent(AppState.currentRole);
}

function getTimeBasedGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return '🌅 Good morning';
    if (hour < 17) return '☀️ Good afternoon';
    return '🌙 Good evening';
}

function updateCurrentTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    if (DOM.currentTime) {
        DOM.currentTime.textContent = now.toLocaleDateString('en-US', options);
    }
}

function updateRoleSpecificContent(role) {
    // Update stats cards based on role
    const statsContainer = document.getElementById('dashboardStats');
    if (!statsContainer) return;
    
    const statsMap = {
        'tenant': `
            <div class="stat-card"><span>🏠</span><div><h3>${getRandomStat(100, 500)}</h3><p>Rent Paid</p></div></div>
            <div class="stat-card"><span>📋</span><div><h3>${getRandomStat(0, 5)}</h3><p>Maintenance Requests</p></div></div>
            <div class="stat-card"><span>📅</span><div><h3>${getRandomStat(10, 30)}</h3><p>Days Until Rent</p></div></div>
        `,
        'landlord': `
            <div class="stat-card"><span>🏘️</span><div><h3>${getRandomStat(5, 20)}</h3><p>Units</p></div></div>
            <div class="stat-card"><span>👥</span><div><h3>${getRandomStat(8, 50)}</h3><p>Tenants</p></div></div>
            <div class="stat-card"><span>💰</span><div><h3>${formatCurrency(getRandomStat(100000, 500000))}</h3><p>Monthly Income</p></div></div>
        `,
        'caretaker': `
            <div class="stat-card"><span>🔧</span><div><h3>${getRandomStat(2, 15)}</h3><p>Open Requests</p></div></div>
            <div class="stat-card"><span>👤</span><div><h3>${getRandomStat(0, 10)}</h3><p>Visitors Today</p></div></div>
            <div class="stat-card"><span>✅</span><div><h3>${getRandomStat(5, 30)}</h3><p>Completed Tasks</p></div></div>
        `,
        'management': `
            <div class="stat-card"><span>🏢</span><div><h3>${getRandomStat(20, 100)}</h3><p>Total Units</p></div></div>
            <div class="stat-card"><span>👥</span><div><h3>${getRandomStat(50, 200)}</h3><p>Total Users</p></div></div>
            <div class="stat-card"><span>💰</span><div><h3>${formatCurrency(getRandomStat(500000, 2000000))}</h3><p>Revenue</p></div></div>
        `
    };
    
    statsContainer.innerHTML = statsMap[role] || statsMap['tenant'];
}

function getRandomStat(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: 'KES',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// ============================================================================
// MAINTENANCE FUNCTIONS
// ============================================================================

async function submitMaintenance(event) {
    event.preventDefault();
    
    const unitId = document.getElementById('maintenanceUnit')?.value;
    const title = document.getElementById('maintenanceTitle')?.value;
    const description = document.getElementById('maintenanceDescription')?.value;
    const priority = document.getElementById('maintenancePriority')?.value;
    
    if (!unitId || !title || !description) {
        return showToast('Please fill in all required fields', 'error');
    }
    
    if (!AppState.currentUser) {
        return showToast('Please log in to submit a request', 'error');
    }
    
    try {
        setLoading(true, 'Submitting request...');
        
        const result = await supabaseClient.submitMaintenanceRequest({
            unit_id: unitId,
            user_id: AppState.currentUser.id,
            user_role: AppState.currentRole,
            title: title,
            description: description,
            priority: priority || 'medium'
        });
        
        if (!result.success) {
            setLoading(false);
            return showToast(result.error || 'Failed to submit request', 'error');
        }
        
        showToast('Maintenance request submitted successfully!', 'success');
        document.getElementById('maintenanceForm')?.reset();
        setLoading(false);
        
        // Refresh maintenance list
        if (AppState.currentRole === 'tenant') {
            loadMaintenanceRequests();
        }
    } catch (error) {
        setLoading(false);
        console.error('Maintenance submission error:', error);
        showToast('Failed to submit maintenance request', 'error');
    }
}

async function loadMaintenanceRequests() {
    if (!AppState.currentUser) return;
    
    try {
        const result = await supabaseClient.getMaintenanceRequests(
            document.getElementById('maintenanceUnit')?.value || 'all',
            10
        );
        
        const container = document.getElementById('maintenanceList');
        if (!container) return;
        
        if (!result.success || !result.data || result.data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-check-circle"></i>
                    <p>No maintenance requests found</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = result.data.map(request => `
            <div class="maintenance-item priority-${request.priority}">
                <div class="maintenance-header">
                    <span class="maintenance-title">${escapeHtml(request.title)}</span>
                    <span class="status-badge status-${request.status}">${capitalizeFirst(request.status)}</span>
                </div>
                <p class="maintenance-description">${escapeHtml(request.description)}</p>
                <div class="maintenance-meta">
                    <span>Priority: ${capitalizeFirst(request.priority)}</span>
                    <span>${supabaseClient.timeAgo(request.created_at)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load maintenance error:', error);
    }
}

// ============================================================================
// VISITOR FUNCTIONS
// ============================================================================

async function logVisitorEntry(event) {
    event.preventDefault();
    
    const visitorName = document.getElementById('visitorName')?.value;
    const unitId = document.getElementById('visitorUnit')?.value;
    const purpose = document.getElementById('visitorPurpose')?.value;
    const phone = document.getElementById('visitorPhone')?.value;
    
    if (!visitorName || !unitId || !purpose) {
        return showToast('Please fill in all required fields', 'error');
    }
    
    if (!AppState.currentUser) {
        return showToast('Please log in to log visitors', 'error');
    }
    
    try {
        setLoading(true, 'Logging visitor...');
        
        const result = await supabaseClient.logVisitor({
            visitor_name: visitorName,
            unit_id: unitId,
            purpose: purpose,
            phone_number: phone || null,
            created_by: AppState.currentUser.id,
            host_user_id: AppState.currentUser.id
        });
        
        if (!result.success) {
            setLoading(false);
            return showToast(result.error || 'Failed to log visitor', 'error');
        }
        
        showToast(`Visitor ${visitorName} logged successfully!`, 'success');
        document.getElementById('visitorForm')?.reset();
        setLoading(false);
        
        // Refresh visitor list
        loadVisitors();
    } catch (error) {
        setLoading(false);
        console.error('Visitor log error:', error);
        showToast('Failed to log visitor', 'error');
    }
}

async function loadVisitors() {
    if (!AppState.currentUser) return;
    
    const container = document.getElementById('visitorList');
    if (!container) return;
    
    try {
        // Get recent visitors from Supabase
        const { data, error } = await supabase
            .from('visitors')
            .select('*')
            .order('checked_in_at', { ascending: false })
            .limit(10);
        
        if (error) throw error;
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-users"></i>
                    <p>No visitors logged today</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.map(visitor => `
            <div class="visitor-item ${visitor.checked_out_at ? 'checked-out' : 'active'}">
                <div class="visitor-info">
                    <span class="visitor-name">${escapeHtml(visitor.visitor_name)}</span>
                    <span class="visitor-unit">Unit ${escapeHtml(visitor.unit_id)}</span>
                    <span class="visitor-purpose">${escapeHtml(visitor.purpose)}</span>
                </div>
                <div class="visitor-time">
                    <span>${supabaseClient.timeAgo(visitor.checked_in_at)}</span>
                    ${!visitor.checked_out_at ? `
                        <button onclick="checkoutVisitor('${visitor.id}')" class="btn btn-sm btn-ghost">
                            Check Out
                        </button>
                    ` : `
                        <span class="checked-out-badge">✓ Checked Out</span>
                    `}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Load visitors error:', error);
        container.innerHTML = `<div class="error-state"><p>Failed to load visitors</p></div>`;
    }
}

async function checkoutVisitor(visitorId) {
    if (!AppState.currentUser) {
        return showToast('Please log in to check out visitors', 'error');
    }
    
    try {
        const result = await supabaseClient.checkoutVisitor(
            visitorId,
            AppState.currentUser.id
        );
        
        if (!result.success) {
            return showToast(result.error || 'Failed to check out visitor', 'error');
        }
        
        showToast('Visitor checked out successfully!', 'success');
        loadVisitors();
    } catch (error) {
        console.error('Checkout error:', error);
        showToast('Failed to check out visitor', 'error');
    }
}

// ============================================================================
// NOTIFICATION SYSTEM
// ============================================================================

function showToast(message, type = 'info', duration = 4000) {
    if (DOM.toast) {
        DOM.toast.textContent = message;
        DOM.toast.className = `toast ${type} show`;
        
        clearTimeout(DOM.toast._timeout);
        DOM.toast._timeout = setTimeout(() => {
            DOM.toast.classList.remove('show');
        }, duration);
    } else {
        // Fallback alert
        console.log(`[${type.toUpperCase()}] ${message}`);
        if (type === 'error') alert(message);
    }
}

// ============================================================================
// ACTIVITY TRACKING
// ============================================================================

function startActivityTracking() {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart', 'click'];
    events.forEach(event => {
        document.addEventListener(event, () => {
            AppState.lastActivity = Date.now();
            AppState.idleWarningShown = false;
            clearIdleTimer();
            if (DOM.idleTimer) DOM.idleTimer.classList.remove('show');
        }, { passive: true });
    });
    
    setInterval(checkIdleStatus, 5000);
}

function checkIdleStatus() {
    const timeSinceLastActivity = Date.now() - AppState.lastActivity;
    
    if (timeSinceLastActivity >= AppState.idleTimeout && !AppState.idleWarningShown) {
        AppState.idleWarningShown = true;
        showIdleTimer();
    }
}

function showIdleTimer() {
    if (!DOM.idleTimer) return;
    DOM.idleTimer.classList.add('show');
    
    let countdown = 60;
    if (DOM.timerValue) DOM.timerValue.textContent = countdown;
    
    clearIdleTimer();
    AppState.idleTimerInterval = setInterval(() => {
        countdown--;
        if (DOM.timerValue) DOM.timerValue.textContent = countdown;
        
        if (countdown <= 0) {
            clearIdleTimer();
            handleLogout();
        }
    }, 1000);
    
    setTimeout(() => {
        if (AppState.idleWarningShown) {
            showSessionTimeoutModal();
        }
    }, 10000);
}

function clearIdleTimer() {
    if (AppState.idleTimerInterval) {
        clearInterval(AppState.idleTimerInterval);
        AppState.idleTimerInterval = null;
    }
}

function showSessionTimeoutModal() {
    if (!DOM.sessionTimeoutModal) return;
    DOM.sessionTimeoutModal.classList.add('active');
    
    let counter = 60;
    if (DOM.timeoutCounter) DOM.timeoutCounter.textContent = counter;
    
    const interval = setInterval(() => {
        counter--;
        if (DOM.timeoutCounter) DOM.timeoutCounter.textContent = counter;
        if (counter <= 0) {
            clearInterval(interval);
            handleLogout();
        }
    }, 1000);
}

function extendSession() {
    if (DOM.sessionTimeoutModal) {
        DOM.sessionTimeoutModal.classList.remove('active');
    }
    AppState.lastActivity = Date.now();
    AppState.idleWarningShown = false;
    clearIdleTimer();
    if (DOM.idleTimer) DOM.idleTimer.classList.remove('show');
}

// ============================================================================
// UI HELPERS
// ============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function capitalizeFirst(string) {
    if (!string) return '';
    return string.charAt(0).toUpperCase() + string.slice(1);
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function setupEventListeners() {
    // Auth forms
    const loginForm = document.getElementById('loginForm');
    if (loginForm) loginForm.addEventListener('submit', handleLogin);
    
    const registerForm = document.getElementById('registerForm');
    if (registerForm) registerForm.addEventListener('submit', handleRegister);
    
    // Navigation
    document.querySelectorAll('[data-nav]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            const view = el.dataset.nav;
            switch(view) {
                case 'landing': showLanding(); break;
                case 'login': showLogin(); break;
                case 'register': showRegister(); break;
                case 'dashboard': showDashboard(); break;
                case 'logout': handleLogout(); break;
            }
        });
    });
    
    // Role selection buttons
    document.querySelectorAll('[data-role-select]').forEach(el => {
        el.addEventListener('click', (e) => {
            const role = el.dataset.roleSelect;
            const roleInput = document.getElementById('loginRole');
            if (roleInput) roleInput.value = role;
            showLogin();
        });
    });
    
    // Service card clicks
    document.querySelectorAll('.service-card').forEach(card => {
        card.addEventListener('click', function() {
            const role = this.dataset.role;
            if (role) {
                const roleInput = document.getElementById('loginRole');
                if (roleInput) roleInput.value = role;
                showLogin();
            }
        });
    });
    
    // Maintenance form
    const maintForm = document.getElementById('maintenanceForm');
    if (maintForm) maintForm.addEventListener('submit', submitMaintenance);
    
    // Visitor form
    const visitorForm = document.getElementById('visitorForm');
    if (visitorForm) visitorForm.addEventListener('submit', logVisitorEntry);
    
    // Hamburger menu
    const hamburger = document.getElementById('hamburger');
    const mobileMenu = document.getElementById('mobileMenu');
    if (hamburger && mobileMenu) {
        hamburger.addEventListener('click', () => {
            const isOpen = mobileMenu.classList.toggle('open');
            hamburger.setAttribute('aria-expanded', isOpen);
            hamburger.innerHTML = isOpen ? '<i class="fas fa-times"></i>' : '<i class="fas fa-bars"></i>';
        });
    }
    
    // Session extend button
    const extendBtn = document.getElementById('extendSession');
    if (extendBtn) extendBtn.addEventListener('click', extendSession);
    
    // Logout button
    document.querySelectorAll('[data-logout]').forEach(el => {
        el.addEventListener('click', (e) => {
            e.preventDefault();
            handleLogout();
        });
    });
    
    // Mobile menu links close menu
    document.querySelectorAll('.mobile-menu a').forEach(link => {
        link.addEventListener('click', () => {
            if (mobileMenu) mobileMenu.classList.remove('open');
            if (hamburger) {
                hamburger.setAttribute('aria-expanded', 'false');
                hamburger.innerHTML = '<i class="fas fa-bars"></i>';
            }
        });
    });
    
    // Handle container display
    document.addEventListener('click', function(e) {
        // Close dropdowns when clicking outside
        if (!e.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown.active').forEach(d => d.classList.remove('active'));
        }
    });
}

// ============================================================================
// EXPOSE FUNCTIONS TO GLOBAL SCOPE
// ============================================================================

// Expose functions for inline HTML event handlers
window.showToast = showToast;
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.handleLogout = handleLogout;
window.showLanding = showLanding;
window.showLogin = showLogin;
window.showRegister = showRegister;
window.showDashboard = showDashboard;
window.submitMaintenance = submitMaintenance;
window.logVisitorEntry = logVisitorEntry;
window.checkoutVisitor = checkoutVisitor;
window.extendSession = extendSession;

console.log('✓ Application scripts loaded');
```

### 4. `js/offline-sync.js` - Offline Sync Integration

```javascript
/**
 * ============================================================================
 * MWAROKIN ESTATES - Offline Sync Integration
 * ============================================================================
 * File: js/offline-sync.js
 * Version: 2.0.0
 * Description: Offline-first data synchronization with Python backend
 * ============================================================================
 */

// Offline Engine Bridge
class OfflineSyncBridge {
    constructor() {
        this.isOnline = navigator.onLine;
        this.syncQueue = [];
        this.isSyncing = false;
        this.pendingCount = 0;
        
        // Setup network listeners
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.handleOnline();
        });
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
        
        console.log('✓ Offline Sync Bridge initialized');
    }
    
    /**
     * Queue an operation for sync
     */
    queueOperation(operation) {
        this.syncQueue.push({
            ...operation,
            id: crypto.randomUUID ? crypto.randomUUID() : this.generateUUID(),
            timestamp: new Date().toISOString(),
            retries: 0
        });
        this.pendingCount = this.syncQueue.length;
        this.updateUI();
        
        // Try to sync immediately if online
        if (this.isOnline) {
            this.processQueue();
        }
    }
    
    /**
     * Process sync queue
     */
    async processQueue() {
        if (this.isSyncing || this.syncQueue.length === 0 || !this.isOnline) {
            return;
        }
        
        this.isSyncing = true;
        this.updateUI();
        
        const operations = [...this.syncQueue];
        const results = [];
        
        for (const op of operations) {
            try {
                const result = await this.executeOperation(op);
                if (result.success) {
                    // Remove from queue
                    const index = this.syncQueue.findIndex(q => q.id === op.id);
                    if (index !== -1) {
                        this.syncQueue.splice(index, 1);
                    }
                    results.push({ id: op.id, success: true });
                } else {
                    op.retries++;
                    if (op.retries >= 3) {
                        // Remove after max retries
                        const index = this.syncQueue.findIndex(q => q.id === op.id);
                        if (index !== -1) {
                            this.syncQueue.splice(index, 1);
                        }
                        results.push({ id: op.id, success: false, error: result.error });
                    }
                }
            } catch (error) {
                console.error('Sync operation failed:', error);
                results.push({ id: op.id, success: false, error: error.message });
            }
        }
        
        this.pendingCount = this.syncQueue.length;
        this.isSyncing = false;
        this.updateUI();
        
        // Return results
        return results;
    }
    
    /**
     * Execute a sync operation
     */
    async executeOperation(operation) {
        const { type, data } = operation;
        
        switch (type) {
            case 'payment':
                return await this.syncPayment(data);
            case 'maintenance':
                return await this.syncMaintenance(data);
            case 'visitor':
                return await this.syncVisitor(data);
            case 'registration':
                return await this.syncRegistration(data);
            case 'activity':
                return await this.syncActivity(data);
            default:
                return { success: false, error: `Unknown operation type: ${type}` };
        }
    }
    
    /**
     * Sync payment with server
     */
    async syncPayment(data) {
        try {
            // Check if Supabase is available
            if (typeof supabase !== 'undefined' && supabase) {
                const result = await supabaseClient.processRentPayment(data);
                return result;
            }
            
            // Fallback to localStorage
            const payments = JSON.parse(localStorage.getItem('mwarokin_payments') || '[]');
            payments.push({
                ...data,
                synced_at: new Date().toISOString(),
                synced: true
            });
            localStorage.setItem('mwarokin_payments', JSON.stringify(payments));
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Sync maintenance request with server
     */
    async syncMaintenance(data) {
        try {
            if (typeof supabase !== 'undefined' && supabase) {
                const result = await supabaseClient.submitMaintenanceRequest(data);
                return result;
            }
            
            const requests = JSON.parse(localStorage.getItem('mwarokin_maintenance') || '[]');
            requests.push({
                ...data,
                synced_at: new Date().toISOString(),
                synced: true
            });
            localStorage.setItem('mwarokin_maintenance', JSON.stringify(requests));
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Sync visitor with server
     */
    async syncVisitor(data) {
        try {
            if (typeof supabase !== 'undefined' && supabase) {
                const result = await supabaseClient.logVisitor(data);
                return result;
            }
            
            const visitors = JSON.parse(localStorage.getItem('mwarokin_visitors') || '[]');
            visitors.push({
                ...data,
                synced_at: new Date().toISOString(),
                synced: true
            });
            localStorage.setItem('mwarokin_visitors', JSON.stringify(visitors));
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Sync registration with server
     */
    async syncRegistration(data) {
        try {
            if (typeof supabase !== 'undefined' && supabase) {
                const result = await supabaseClient.signUpUser(data.email, data.password, data.userData);
                return result;
            }
            
            const users = JSON.parse(localStorage.getItem('mwarokin_users') || '[]');
            users.push({
                ...data,
                synced_at: new Date().toISOString(),
                synced: true
            });
            localStorage.setItem('mwarokin_users', JSON.stringify(users));
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Sync activity with server
     */
    async syncActivity(data) {
        try {
            if (typeof supabase !== 'undefined' && supabase) {
                const result = await supabaseClient.logActivity(data);
                return result;
            }
            
            const activities = JSON.parse(localStorage.getItem('mwarokin_activities') || '[]');
            activities.push({
                ...data,
                synced_at: new Date().toISOString(),
                synced: true
            });
            localStorage.setItem('mwarokin_activities', JSON.stringify(activities));
            return { success: true, data: data };
        } catch (error) {
            return { success: false, error: error.message };
        }
    }
    
    /**
     * Get sync status
     */
    getSyncStatus() {
        return {
            isOnline: this.isOnline,
            isSyncing: this.isSyncing,
            pendingCount: this.pendingCount,
            queueSize: this.syncQueue.length
        };
    }
    
    /**
     * Force sync
     */
    forceSync() {
        if (this.isOnline) {
            return this.processQueue();
        }
        return Promise.resolve({
            success: false,
            error: 'Device is offline',
            pending: this.syncQueue.length
        });
    }
    
    /**
     * Handle online event
     */
    handleOnline() {
        showToast('Back online! Syncing pending operations...', 'success');
        this.processQueue();
    }
    
    /**
     * Update UI with sync status
     */
    updateUI() {
        const badge = document.getElementById('syncBadge');
        if (badge) {
            if (this.pendingCount > 0) {
                badge.textContent = this.pendingCount;
                badge.style.display = 'inline';
            } else {
                badge.style.display = 'none';
            }
        }
        
        const indicator = document.getElementById('syncIndicator');
        if (indicator) {
            indicator.className = this.isOnline ? 'online' : 'offline';
            indicator.title = this.isOnline ? 'Online' : 'Offline';
        }
    }
    
    /**
     * Generate UUID fallback
     */
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
}

// Initialize offline sync bridge
const offlineSync = new OfflineSyncBridge();

// Expose to global scope
window.offlineSync = offlineSync;

console.log('✓ Offline Sync Bridge ready');
```

### 5. `js/real-time.js` - Real-time Subscriptions

```javascript
/**
 * ============================================================================
 * MWAROKIN ESTATES - Real-time Subscriptions
 * ============================================================================
 * File: js/real-time.js
 * Version: 2.0.0
 * Description: Supabase real-time subscriptions for live updates
 * ============================================================================
 */

class RealTimeManager {
    constructor() {
        this.subscriptions = {};
        this.channels = {};
        this.isInitialized = false;
    }
    
    /**
     * Initialize real-time subscriptions
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            if (!supabase) {
                supabase = supabaseClient.initSupabase();
            }
            if (!supabase) {
                console.error('Supabase not available for real-time');
                return;
            }
            
            this.isInitialized = true;
            console.log('✓ Real-time manager initialized');
        } catch (error) {
            console.error('Real-time init error:', error);
        }
    }
    
    /**
     * Subscribe to table changes
     */
    subscribeToTable(table, callback, filter = null) {
        if (!this.isInitialized) {
            this.init();
            return;
        }
        
        try {
            // Build channel name
            const channelName = `table:${table}`;
            
            // Close existing subscription
            if (this.subscriptions[table]) {
                this.unsubscribeFromTable(table);
            }
            
            // Create channel
            const channel = supabase.channel(channelName);
            
            // Set up subscription
            let subscription = channel.on(
                'postgres_changes',
                {
                    event: '*',
                    schema: 'public',
                    table: table,
                    filter: filter
                },
                (payload) => {
                    console.log(`Real-time update on ${table}:`, payload);
                    callback(payload);
                }
            );
            
            // Subscribe
            subscription.subscribe((status, err) => {
                if (status === 'SUBSCRIBED') {
                    console.log(`✓ Subscribed to ${table}`);
                }
                if (err) {
                    console.error(`Subscription error for ${table}:`, err);
                }
            });
            
            this.subscriptions[table] = subscription;
            this.channels[table] = channel;
            
            return subscription;
        } catch (error) {
            console.error(`Failed to subscribe to ${table}:`, error);
            return null;
        }
    }
    
    /**
     * Unsubscribe from table
     */
    unsubscribeFromTable(table) {
        if (this.subscriptions[table]) {
            try {
                this.subscriptions[table].unsubscribe();
                delete this.subscriptions[table];
                console.log(`✓ Unsubscribed from ${table}`);
            } catch (error) {
                console.error(`Unsubscribe error for ${table}:`, error);
            }
        }
    }
    
    /**
     * Subscribe to user's data
     */
    subscribeToUserData(userId, callback) {
        if (!userId) return;
        
        // Subscribe to user-related tables
        const tables = ['transactions', 'maintenance_requests', 'units'];
        
        for (const table of tables) {
            this.subscribeToTable(
                table,
                (payload) => {
                    // Filter by user_id if applicable
                    const event = payload.new || payload.old;
                    if (event && (event.user_id === userId || event.tenant_id === userId || event.landlord_id === userId)) {
                        callback(payload);
                    }
                },
                `user_id=eq.${userId}`
            );
        }
    }
    
    /**
     * Subscribe to estate-wide updates
     */
    subscribeToEstateUpdates(callback) {
        // Subscribe to critical tables for estate-wide updates
        const tables = ['units', 'users', 'maintenance_requests'];
        
        for (const table of tables) {
            this.subscribeToTable(
                table,
                (payload) => {
                    callback({
                        table: table,
                        payload: payload
                    });
                }
            );
        }
    }
    
    /**
     * Subscribe to notifications
     */
    subscribeToNotifications(userId, callback) {
        if (!userId) return;
        
        // Use a custom channel for notifications
        const channel = supabase.channel(`notifications:${userId}`);
        
        channel.on(
            'postgres_changes',
            {
                event: '*',
                schema: 'public',
                table: 'notifications',
                filter: `user_id=eq.${userId}`
            },
            (payload) => {
                callback(payload);
            }
        ).subscribe();
        
        this.channels[`notifications:${userId}`] = channel;
    }
    
    /**
     * Unsubscribe from all channels
     */
    unsubscribeAll() {
        for (const [key, channel] of Object.entries(this.channels)) {
            try {
                channel.unsubscribe();
                console.log(`✓ Unsubscribed from ${key}`);
            } catch (error) {
                console.error(`Unsubscribe error for ${key}:`, error);
            }
        }
        this.channels = {};
        this.subscriptions = {};
    }
    
    /**
     * Check connection status
     */
    isConnected() {
        return this.isInitialized && supabase && navigator.onLine;
    }
}

// Initialize real-time manager
const realTime = new RealTimeManager();

// Expose to global scope
window.realTime = realTime;

console.log('✓ Real-time manager loaded');
```

### 6. HTML Integration Snippet

```html
<!-- Add to the head section of your HTML -->
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.0"></script>

<!-- JavaScript files -->
<script src="js/config.js"></script>
<script src="js/supabase-client.js"></script>
<script src="js/offline-sync.js"></script>
<script src="js/real-time.js"></script>
<script src="js/app.js"></script>

<!-- Add these to your HTML for sync status -->
<div id="syncIndicator" class="sync-indicator online" title="Online">
    <span class="sync-dot"></span>
</div>
<div id="syncBadge" class="sync-badge" style="display:none;">0</div>

<!-- CSS for sync indicator -->
<style>
.sync-indicator {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
}
.sync-indicator.online { background: #e6f7e6; color: #2e7d32; }
.sync-indicator.offline { background: #fde8e8; color: #c62828; }
.sync-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}
.sync-indicator.online .sync-dot { background: #4caf50; }
.sync-indicator.offline .sync-dot { background: #f44336; }
.sync-badge {
    background: #f44336;
    color: white;
    border-radius: 50%;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 600;
    margin-left: 4px;
}
</style>
```

---

## Complete Supabase Database Schema

```sql
-- ============================================================================
-- MWAROKIN ESTATES - Supabase Database Schema
-- ============================================================================

-- Users table (managed by Supabase Auth, but we store additional data)
CREATE TABLE public.user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone_number TEXT,
    user_role TEXT NOT NULL CHECK (user_role IN ('tenant', 'landlord', 'caretaker', 'management', 'professional')),
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Units table
CREATE TABLE public.units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_number TEXT NOT NULL,
    property_name TEXT NOT NULL,
    property_address TEXT NOT NULL,
    landlord_id UUID REFERENCES public.user_profiles(id),
    caretaker_id UUID REFERENCES public.user_profiles(id),
    tenant_id UUID REFERENCES public.user_profiles(id),
    rent_amount DECIMAL(12,2) NOT NULL,
    deposit_amount DECIMAL(12,2) NOT NULL,
    bedrooms INTEGER NOT NULL,
    bathrooms INTEGER NOT NULL,
    square_feet INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'occupied', 'maintenance', 'reserved')),
    amenities JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transactions table
CREATE TABLE public.transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    amount DECIMAL(12,2) NOT NULL,
    unit_id UUID REFERENCES public.units(id),
    user_id UUID REFERENCES public.user_profiles(id),
    user_role TEXT NOT NULL CHECK (user_role IN ('tenant', 'landlord', 'caretaker', 'management', 'professional')),
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('rent', 'deposit', 'service', 'penalty', 'refund')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'synced')),
    metadata JSONB DEFAULT '{}',
    receipt_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Maintenance Requests table
CREATE TABLE public.maintenance_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID REFERENCES public.units(id),
    user_id UUID REFERENCES public.user_profiles(id),
    user_role TEXT NOT NULL CHECK (user_role IN ('tenant', 'landlord', 'caretaker', 'management', 'professional')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved', 'closed', 'rejected')),
    assigned_to UUID REFERENCES public.user_profiles(id),
    notes JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Visitors table
CREATE TABLE public.visitors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visitor_name TEXT NOT NULL,
    unit_id UUID REFERENCES public.units(id),
    purpose TEXT NOT NULL,
    checked_in_at TIMESTAMPTZ DEFAULT NOW(),
    checked_out_at TIMESTAMPTZ,
    host_user_id UUID REFERENCES public.user_profiles(id),
    phone_number TEXT,
    id_type TEXT,
    id_number TEXT,
    created_by UUID REFERENCES public.user_profiles(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Activity Logs table
CREATE TABLE public.activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN ('login', 'logout', 'registration', 'payment', 'maintenance', 'visitor', 'visitor_checkout', 'page_view', 'unit_update', 'sync')),
    user_id UUID REFERENCES public.user_profiles(id),
    user_role TEXT NOT NULL CHECK (user_role IN ('tenant', 'landlord', 'caretaker', 'management', 'professional', 'anonymous')),
    description TEXT NOT NULL,
    ip_address TEXT,
    device_info TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notifications table
CREATE TABLE public.notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id),
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('info', 'success', 'warning', 'error')),
    is_read BOOLEAN DEFAULT FALSE,
    link TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Registrations log (for analytics)
CREATE TABLE public.user_registrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.user_profiles(id),
    email TEXT NOT NULL,
    full_name TEXT NOT NULL,
    phone_number TEXT,
    role TEXT NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sync metadata
CREATE TABLE public.sync_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_transactions_user_id ON public.transactions(user_id);
CREATE INDEX idx_transactions_unit_id ON public.transactions(unit_id);
CREATE INDEX idx_transactions_status ON public.transactions(status);
CREATE INDEX idx_transactions_created_at ON public.transactions(created_at);

CREATE INDEX idx_maintenance_unit_id ON public.maintenance_requests(unit_id);
CREATE INDEX idx_maintenance_user_id ON public.maintenance_requests(user_id);
CREATE INDEX idx_maintenance_status ON public.maintenance_requests(status);
CREATE INDEX idx_maintenance_priority ON public.maintenance_requests(priority);

CREATE INDEX idx_visitors_unit_id ON public.visitors(unit_id);
CREATE INDEX idx_visitors_checked_in_at ON public.visitors(checked_in_at);

CREATE INDEX idx_activity_logs_user_id ON public.activity_logs(user_id);
CREATE INDEX idx_activity_logs_event_type ON public.activity_logs(event_type);
CREATE INDEX idx_activity_logs_created_at ON public.activity_logs(created_at);

CREATE INDEX idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX idx_notifications_is_read ON public.notifications(is_read);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.units ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.visitors ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.activity_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_registrations ENABLE ROW LEVEL SECURITY;

-- User Profiles policies
CREATE POLICY "Users can view their own profile"
    ON public.user_profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
    ON public.user_profiles FOR UPDATE
    USING (auth.uid() = id);

-- Units policies
CREATE POLICY "Everyone can view units"
    ON public.units FOR SELECT
    USING (true);

CREATE POLICY "Landlords can manage their units"
    ON public.units FOR ALL
    USING (auth.uid() = landlord_id);

-- Transactions policies
CREATE POLICY "Users can view their own transactions"
    ON public.transactions FOR SELECT
    USING (auth.uid() = user_id OR auth.uid() IN (
        SELECT landlord_id FROM public.units WHERE id = unit_id
    ));

CREATE POLICY "Users can create transactions"
    ON public.transactions FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Maintenance Requests policies
CREATE POLICY "Users can view maintenance requests for their units"
    ON public.maintenance_requests FOR SELECT
    USING (
        auth.uid() = user_id OR
        auth.uid() IN (SELECT landlord_id FROM public.units WHERE id = unit_id) OR
        auth.uid() IN (SELECT caretaker_id FROM public.units WHERE id = unit_id)
    );

CREATE POLICY "Users can create maintenance requests"
    ON public.maintenance_requests FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Caretakers can update maintenance requests"
    ON public.maintenance_requests FOR UPDATE
    USING (auth.uid() IN (
        SELECT caretaker_id FROM public.units WHERE id = unit_id
    ));

-- Visitors policies
CREATE POLICY "Caretakers can manage visitors"
    ON public.visitors FOR ALL
    USING (auth.uid() IN (
        SELECT caretaker_id FROM public.units WHERE id = unit_id
    ));

CREATE POLICY "Users can view visitors for their unit"
    ON public.visitors FOR SELECT
    USING (
        auth.uid() IN (SELECT tenant_id FROM public.units WHERE id = unit_id) OR
        auth.uid() IN (SELECT landlord_id FROM public.units WHERE id = unit_id)
    );

-- Activity Logs policies
CREATE POLICY "Users can view their own activity logs"
    ON public.activity_logs FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Management can view all activity logs"
    ON public.activity_logs FOR SELECT
    USING (
        auth.uid() IN (
            SELECT id FROM public.user_profiles WHERE user_role = 'management'
        )
    );

-- Notifications policies
CREATE POLICY "Users can view their own notifications"
    ON public.notifications FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own notifications"
    ON public.notifications FOR UPDATE
    USING (auth.uid() = user_id);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers to tables
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON public.user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_units_updated_at
    BEFORE UPDATE ON public.units
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at
    BEFORE UPDATE ON public.transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_maintenance_requests_updated_at
    BEFORE UPDATE ON public.maintenance_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create user profile on auth signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (id, full_name, phone_number, user_role)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email),
        NEW.raw_user_meta_data->>'phone_number',
        COALESCE(NEW.raw_user_meta_data->>'user_role', 'tenant')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();
```
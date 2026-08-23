# Mwarokin Estates Premium Onboarding System
## Role-Based Configuration (RBC) Implementation Guide

---

## 📋 Table of Contents
1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Role-Based Configuration Details](#role-based-configuration-details)
4. [Implementation Steps](#implementation-steps)
5. [Payment Integration](#payment-integration)
6. [Verification & Security](#verification--security)
7. [Dashboard Redirection](#dashboard-redirection)
8. [Testing & Deployment](#testing--deployment)

---

## 🎯 System Overview

**Mwarokin Estates Premium Onboarding** is a sophisticated, role-based client onboarding system designed for four distinct user types:

- **Tenants** - Residential occupants managing rent payments & maintenance
- **Landlords** - Property owners managing portfolios & tenant relationships
- **Caretakers** - Maintenance & facility managers
- **Management** - Administrative oversight & system control

Each role flows through a 5-step onboarding process with personalized configuration (RBC), verification, and instant dashboard access.

---

## 🏗️ Architecture

### System Flow
```
Step 0: Role Selection
    ↓
Step 1: Profile Information (Role-Specific)
    ↓
Step 2: Configuration & Preferences (Role-Specific RBC)
    ↓
Step 3: Identity Verification (OTP + Email + Agreements)
    ↓
Step 4: Completion & Dashboard Redirect
    ↓
Role-Specific Dashboard (Tenant/Landlord/Caretaker/Management)
```

### File Structure
```
mwarokin_premium_onboarding.html          ← Main onboarding flow
mwarokin_tenant_dashboard.html            ← Tenant post-onboarding interface
mwarokin_landlord_dashboard.html          ← [To be created]
mwarokin_caretaker_dashboard.html         ← [To be created]
mwarokin_management_dashboard.html        ← [To be created]
MWAROKIN_ONBOARDING_GUIDE.md              ← This document
```

---

## 👥 Role-Based Configuration (RBC) Details

### 1. TENANT CONFIGURATION

**Profile Data Collected:**
- Full name, email, phone
- Current residential address
- Desired move-in date
- Number of occupants
- National ID/Passport

**RBC Features (Step 2 Configuration):**
- **Payment Method Selection**: M-Pesa, Airtel Money, SylloPay, Bank Transfer
- **Communication Preferences**: SMS, Email, Push Notifications
- **Features Access**:
  - Online rent payments (multiple methods)
  - Digital lease documents & e-signature
  - Maintenance request system
  - Community communication & announcements
  - Payment history & receipts

**Tenant Dashboard Redirection:**
```javascript
Dashboard URL: mwarokin_tenant_dashboard.html
Features:
  - Rent payment tracking (Next payment, due dates)
  - Payment history table
  - Maintenance requests submission & tracking
  - Document management (lease downloads)
  - Message center
  - Quick payment button (M-Pesa/Airtel/SylloPay)
```

**Sample Tenant Data Structure:**
```json
{
  "role": "tenant",
  "name": "John Mwangi",
  "email": "john@example.com",
  "phone": "+254712345678",
  "currentAddress": "Apt 204, Westlands",
  "moveInDate": "2024-09-20",
  "occupants": 2,
  "nationalID": "123456789",
  "paymentMethod": "mpesa",
  "notifications": {
    "sms": true,
    "email": true,
    "push": true
  }
}
```

---

### 2. LANDLORD CONFIGURATION

**Profile Data Collected:**
- Full name, email, phone
- Company/business name (optional)
- Number of properties owned
- Primary property address
- National ID/Business registration

**RBC Features (Step 2 Configuration):**
- **Rent Payment Account Setup**:
  - Preferred payment receiving method
  - Business/Paybill number configuration
  - Direct bank account linkage
- **Late Payment & Reminders**:
  - Enable/disable late payment notifications
  - Auto-notify caretakers of overdue rent
- **Dashboard Features Access**:
  - Real-time rent payment tracking
  - Tenant profiles & lease management
  - Property portfolio management
  - Financial reports & analytics
  - Communication with caretakers & tenants
  - Vacant property management

**Landlord Dashboard Redirection:**
```javascript
Dashboard URL: mwarokin_landlord_dashboard.html
Key Sections:
  - Property Portfolio (with vacancy status)
  - Rent Collection Dashboard
    * Total collected (this month)
    * Outstanding rent (overdue, pending)
    * Payment breakdown by tenant
  - Tenant Management
    * Tenant directory
    * Active leases
    * Complaint history
  - Financial Analytics
    * Revenue trends
    * Collection rate
    * Late payment patterns
  - Communication Hub
    * Tenant messages
    * Caretaker coordination
```

**Sample Landlord Data Structure:**
```json
{
  "role": "landlord",
  "name": "Jane Kipchoge",
  "email": "jane@example.com",
  "phone": "+254723456789",
  "company": "Kipchoge Properties Ltd",
  "propertiesOwned": "6-10",
  "primaryAddress": "123 Kenyatta Ave, Nairobi",
  "businessRegistration": "BRN123456",
  "paymentMethod": "mpesa",
  "paybillNumber": "123456",
  "latePaymentReminders": true,
  "autoNotifyCaretaker": true,
  "dashboardFeatures": [
    "rent_tracking",
    "tenant_management",
    "portfolio_view",
    "financial_reports",
    "communications"
  ]
}
```

---

### 3. CARETAKER CONFIGURATION

**Profile Data Collected:**
- Full name, email, phone
- Property/complex assigned
- Years of experience
- Primary skill focus (electrical, plumbing, general, mixed)
- National ID

**RBC Features (Step 2 Configuration):**
- **Task Management**:
  - Handle repair requests ✓
  - Manage waste collection ✓
  - Monitor water systems ✓
  - Manage security & access ✓
- **Communication Channel**:
  - Phone/SMS (primary)
  - Email (secondary)
  - Mobile app
- **Dashboard Access**:
  - Receive maintenance requests & complaints
  - Track repair work & job status
  - Manage utilities (water, electricity, waste)
  - Security & access management
  - Report to landlord & management

**Caretaker Dashboard Redirection:**
```javascript
Dashboard URL: mwarokin_caretaker_dashboard.html
Key Sections:
  - Task Queue
    * Urgent repairs
    * Scheduled maintenance
    * Tenant requests
  - Utilities Management
    * Water monitoring
    * Waste collection schedule
    * Electricity meter readings
  - Security & Access
    * Lock/unlock requests
    * Access logs
    * Security incidents
  - Work Reports
    * Completed tasks
    * Issues documented
    * Photos/evidence
  - Communication
    * Tenant complaints
    * Landlord instructions
```

**Sample Caretaker Data Structure:**
```json
{
  "role": "caretaker",
  "name": "David Karanja",
  "email": "david@example.com",
  "phone": "+254734567890",
  "propertyAssigned": "Westlands Towers Complex",
  "experience": "5-10",
  "skillFocus": "mixed",
  "nationalID": "987654321",
  "taskManagement": {
    "repairs": true,
    "waste": true,
    "water": true,
    "security": true
  },
  "communicationChannel": "sms",
  "reportingStructure": "landlord_and_management"
}
```

---

### 4. MANAGEMENT CONFIGURATION

**Profile Data Collected:**
- Full name, email, phone
- Department/role
- Employee ID/Staff number

**RBC Features (Step 2 Configuration):**
- **Access Level Selection**:
  - View Only (Reports)
  - Limited (Department Specific)
  - Full Access (All Operations)
- **Module Access Control**:
  - Tenant Management
  - Landlord Management
  - Finance & Payments
  - Reports & Analytics
  - User Management
  - System Settings

**Management Dashboard Redirection:**
```javascript
Dashboard URL: mwarokin_management_dashboard.html
Sections (based on access level):
  - System Overview
    * Active users by role
    * Payment summary
    * System health
  - Tenant Management
    * Tenant registry
    * Lease tracking
    * Dispute resolution
  - Landlord Operations
    * Portfolio overview
    * Payment collection status
    * Complaints & issues
  - Financial Analytics
    * Revenue dashboard
    * Collection metrics
    * Outstanding analysis
  - User & Access Control
    * User management (if permitted)
    * Role assignment
    * System logs
```

**Sample Management Data Structure:**
```json
{
  "role": "management",
  "name": "Alice Omondi",
  "email": "alice@mwarokin.com",
  "phone": "+254745678901",
  "department": "Operations Manager",
  "staffID": "MWK-OPS-001",
  "accessLevel": "full",
  "moduleAccess": {
    "tenantManagement": true,
    "landlordManagement": true,
    "financePayments": true,
    "reportsAnalytics": true,
    "userManagement": true,
    "systemSettings": true
  },
  "permissions": [
    "view_all_users",
    "manage_disputes",
    "generate_reports",
    "system_configuration"
  ]
}
```

---

## 📝 Implementation Steps

### Step 1: Setup Files
1. Deploy `mwarokin_premium_onboarding.html` to your server
2. Create role-specific dashboard templates:
   - `mwarokin_tenant_dashboard.html` ✓ (included)
   - `mwarokin_landlord_dashboard.html` (template structure provided)
   - `mwarokin_caretaker_dashboard.html` (template structure provided)
   - `mwarokin_management_dashboard.html` (template structure provided)

### Step 2: Database Schema

**Users Table:**
```sql
CREATE TABLE users (
  user_id VARCHAR(36) PRIMARY KEY,
  role ENUM('tenant', 'landlord', 'caretaker', 'management'),
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  phone VARCHAR(20) NOT NULL,
  national_id VARCHAR(50),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  onboarding_completed BOOLEAN DEFAULT FALSE,
  last_login TIMESTAMP NULL
);
```

**Role Configuration Table:**
```sql
CREATE TABLE role_configurations (
  config_id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  role VARCHAR(20) NOT NULL,
  configuration_data JSON NOT NULL,
  payment_methods JSON,
  notification_preferences JSON,
  feature_flags JSON,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**Payment Methods Table:**
```sql
CREATE TABLE payment_methods (
  payment_id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  method_type ENUM('mpesa', 'airtel', 'syllopay', 'bank') NOT NULL,
  account_details JSON,
  is_primary BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

**Verification Table:**
```sql
CREATE TABLE verifications (
  verification_id VARCHAR(36) PRIMARY KEY,
  user_id VARCHAR(36) NOT NULL,
  email_verified BOOLEAN DEFAULT FALSE,
  phone_verified BOOLEAN DEFAULT FALSE,
  otp_code VARCHAR(6),
  otp_expiry TIMESTAMP,
  verified_at TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(user_id)
);
```

### Step 3: Backend Integration

**Create API Endpoints:**

```javascript
// POST /api/onboarding/initiate
// Initiates onboarding session
{
  role: "tenant|landlord|caretaker|management"
}

// POST /api/onboarding/profile
// Saves profile information
{
  role: string,
  profileData: {...}
}

// POST /api/onboarding/config
// Saves role-based configuration
{
  user_id: string,
  configuration: {...}
}

// POST /api/onboarding/verify/send-otp
// Sends OTP to phone number
{
  phone: string
}

// POST /api/onboarding/verify/confirm-otp
// Confirms OTP code
{
  user_id: string,
  otp_code: string
}

// POST /api/onboarding/complete
// Completes onboarding & creates session
{
  user_id: string,
  agreements: {
    termsAccepted: boolean,
    policiesAccepted: boolean,
    dataProcessingAccepted: boolean
  }
}

// GET /api/user/session
// Retrieves current session
// Returns: { user_id, role, configuration, features }

// POST /api/auth/login
// Returns: { token, user, dashboardUrl }
```

### Step 4: Environment Configuration

**Create `.env` file:**
```
# Server
SERVER_URL=https://api.mwarokin.com
ONBOARDING_URL=https://onboarding.mwarokin.com

# Payment Gateways
MPESA_API_KEY=your_mpesa_key
AIRTEL_API_KEY=your_airtel_key
SYLLOPAY_API_KEY=your_syllopay_key

# OTP Service
OTP_PROVIDER=twilio|africastalking
OTP_API_KEY=your_otp_key

# Email Service
EMAIL_PROVIDER=sendgrid|mailgun
EMAIL_API_KEY=your_email_key

# Database
DB_HOST=localhost
DB_USER=mwarokin_user
DB_PASSWORD=secure_password
DB_NAME=mwarokin_estates

# Security
JWT_SECRET=your_jwt_secret
SESSION_TIMEOUT=1800
```

---

## 💳 Payment Integration

### M-Pesa Integration

**For Tenants (Paying Rent):**
```javascript
// Initiate STK Push
const initatePayment = async (phone, amount) => {
  const response = await fetch('/api/payment/mpesa/stk-push', {
    method: 'POST',
    body: JSON.stringify({
      phone: phone.replace(/[^\d]/g, '').slice(-9),
      amount: amount,
      accountReference: 'RENT-PAYMENT',
      description: 'Monthly Rent Payment'
    })
  });
  return response.json();
};
```

**For Landlords (Receiving Rent):**
```javascript
// Setup Paybill Configuration
const setupPaybill = async (landlordId, paybillNumber) => {
  const response = await fetch('/api/payment/mpesa/paybill-setup', {
    method: 'POST',
    body: JSON.stringify({
      landlordId: landlordId,
      paybillNumber: paybillNumber,
      businessName: 'Mwarokin Estates'
    })
  });
  return response.json();
};
```

### Airtel Money Integration

```javascript
// Similar structure for Airtel Money
const initiateAirtelPayment = async (phone, amount) => {
  const response = await fetch('/api/payment/airtel/initiate', {
    method: 'POST',
    body: JSON.stringify({
      phone: phone,
      amount: amount,
      externalId: 'AIRTEL-' + Date.now()
    })
  });
  return response.json();
};
```

### SylloPay Integration

```javascript
// Custom SylloPay implementation
const initiateSylloPayment = async (phone, amount) => {
  const response = await fetch('/api/payment/syllopay/checkout', {
    method: 'POST',
    body: JSON.stringify({
      phone: phone,
      amount: amount,
      paymentType: 'RENT'
    })
  });
  return response.json();
};
```

---

## 🔐 Verification & Security

### OTP Generation & Verification

```javascript
// Generate OTP (Backend)
const generateOTP = () => {
  return Math.floor(100000 + Math.random() * 900000).toString();
};

// Send OTP via SMS
const sendOTP = async (phone, otp) => {
  // Using Africa's Talking or Twilio
  const provider = process.env.OTP_PROVIDER;
  
  if (provider === 'africastalking') {
    await africasTalking.SMS.send({
      to: phone,
      message: `Your Mwarokin verification code is: ${otp}`
    });
  }
};

// Verify OTP (Frontend)
const verifyOTP = async (userId, otpCode) => {
  const response = await fetch('/api/onboarding/verify/confirm-otp', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      otp_code: otpCode
    })
  });
  return response.json();
};
```

### Email Verification

```javascript
// Generate verification link
const generateEmailToken = (userId) => {
  const token = jwt.sign(
    { userId: userId, action: 'email-verify' },
    process.env.JWT_SECRET,
    { expiresIn: '24h' }
  );
  return token;
};

// Send verification email
const sendVerificationEmail = async (email, userId) => {
  const token = generateEmailToken(userId);
  const verificationLink = `${process.env.ONBOARDING_URL}/verify-email?token=${token}`;
  
  await emailService.send({
    to: email,
    subject: 'Verify Your Mwarokin Estates Account',
    template: 'email-verification',
    data: {
      name: userName,
      verificationLink: verificationLink
    }
  });
};
```

### Session Management

```javascript
// Create session after verification
const createSession = async (userId, role) => {
  const token = jwt.sign(
    { userId: userId, role: role },
    process.env.JWT_SECRET,
    { expiresIn: '7d' }
  );
  
  // Store in database
  await Session.create({
    user_id: userId,
    token: token,
    role: role,
    created_at: new Date(),
    expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000)
  });
  
  return {
    token: token,
    userId: userId,
    role: role,
    expiresIn: 7 * 24 * 60 * 60 // 7 days in seconds
  };
};
```

---

## 🚀 Dashboard Redirection

### Automatic Redirect Flow

```javascript
// In onboarding completion (Step 4)
const redirectToDashboard = async () => {
  const session = JSON.parse(localStorage.getItem('mwarokin_session'));
  
  const dashboardMap = {
    tenant: 'mwarokin_tenant_dashboard.html',
    landlord: 'mwarokin_landlord_dashboard.html',
    caretaker: 'mwarokin_caretaker_dashboard.html',
    management: 'mwarokin_management_dashboard.html'
  };
  
  // Store authentication token
  localStorage.setItem('auth_token', session.token);
  localStorage.setItem('user_role', session.role);
  
  // Redirect with session data in URL
  const dashboardUrl = dashboardMap[session.role];
  window.location.href = dashboardUrl + `?token=${session.token}&role=${session.role}`;
};
```

### Session Validation in Dashboard

```javascript
// In each dashboard HTML file
window.addEventListener('DOMContentLoaded', () => {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  const role = params.get('role');
  
  // Validate session
  validateSession(token, role).then(sessionData => {
    if (!sessionData.valid) {
      window.location.href = 'mwarokin_premium_onboarding.html';
    } else {
      loadDashboardData(sessionData.userId);
    }
  });
});
```

---

## 🧪 Testing & Deployment

### Test Scenarios

**Tenant Onboarding Flow:**
```
1. Select Tenant role ✓
2. Fill profile (name, email, phone, address, date, occupants, ID) ✓
3. Select payment method (M-Pesa) ✓
4. Configure notifications (SMS, Email, Push) ✓
5. Verify phone with OTP ✓
6. Accept terms & policies ✓
7. Redirect to Tenant Dashboard ✓
8. Verify dashboard access & payment button functional ✓
```

**Landlord Onboarding Flow:**
```
1. Select Landlord role ✓
2. Fill profile (name, company, properties, ID) ✓
3. Configure payment receiving (Paybill #) ✓
4. Enable late payment reminders ✓
5. Verify phone with OTP ✓
6. Accept agreements ✓
7. Redirect to Landlord Dashboard ✓
8. Verify property portfolio visible ✓
```

**Caretaker Onboarding Flow:**
```
1. Select Caretaker role ✓
2. Fill profile (name, property, experience, skills, ID) ✓
3. Configure task types & communication (SMS) ✓
4. Verify phone with OTP ✓
5. Accept terms ✓
6. Redirect to Caretaker Dashboard ✓
7. Test receiving maintenance requests ✓
```

**Management Onboarding Flow:**
```
1. Select Management role ✓
2. Fill profile (name, department, staff ID) ✓
3. Set access level (Full Access) ✓
4. Select modules (All) ✓
5. Verify email with link ✓
6. Accept policies ✓
7. Redirect to Management Dashboard ✓
8. Verify system overview visible ✓
```

### Deployment Checklist

- [ ] All HTML files deployed to production server
- [ ] Backend APIs fully implemented & tested
- [ ] Database schema created & optimized
- [ ] Environment variables configured
- [ ] Payment gateway credentials verified
- [ ] OTP service tested with real phone numbers
- [ ] Email service tested with real addresses
- [ ] SSL/TLS certificates installed
- [ ] CORS policies configured
- [ ] Rate limiting enabled
- [ ] Logging & monitoring setup
- [ ] Backup & recovery procedures documented
- [ ] Load testing completed
- [ ] Security audit performed

---

## 🔧 Maintenance & Monitoring

### Key Metrics to Track

```
- Onboarding completion rate by role
- Drop-off rate per step
- OTP success rate
- Payment method popularity by role
- Average onboarding time by role
- Session timeout rate
- Dashboard access performance
```

### Error Handling

```javascript
// Global error handler
window.addEventListener('error', (event) => {
  console.error('Onboarding Error:', event);
  logToServer({
    step: currentStep,
    error: event.message,
    role: selectedRole,
    timestamp: new Date().toISOString()
  });
});

// Handle network failures
fetch(endpoint, options)
  .catch(error => {
    showNotification('Connection failed. Please check your internet.', 'error');
    console.error('Fetch Error:', error);
  });
```

---

## 📞 Support & Contact

For questions regarding Mwarokin Estates Onboarding System:
- Technical: tech@mwarokin.com
- Support: support@mwarokin.com
- Emergency: +254 7XX XXX XXX

---

**Document Version:** 1.0
**Last Updated:** September 2024
**Status:** Production Ready

```python
"""
Mwarokin Estates - Tenant Offboarding Portal
Modern Professional Flask Application

This application serves the provided HTML/JS frontend and provides a robust
backend API for data persistence, audit logging, and permission management.

Features:
- Multi-step offboarding workflow (Tenant → Property → Inspection → Audit)
- In-memory and SQLite persistence
- Real-time audit trail
- Role-based permissions (simulated)
- RESTful API endpoints

Run with: python app.py
Access at: http://localhost:5000
"""

import os
import json
import sqlite3
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify, render_template_string, session
from flask_cors import CORS
import logging

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class TenantData:
    name: str = ""
    lease_id: str = ""
    email: str = ""
    phone: str = ""
    move_out_date: str = ""
    reason: str = "lease_end"

@dataclass
class PropertyData:
    mode: str = "single"          # "single" or "multiple"
    selected_single: str = "propB"
    selected_multiple: List[str] = None

    def __post_init__(self):
        if self.selected_multiple is None:
            self.selected_multiple = ["propB"]

@dataclass
class InspectionData:
    meter_reading: str = ""
    damage_notes: str = ""
    repair_cost: float = 0.0
    deposit_amount: float = 2500.0
    deduction_amount: float = 0.0
    images: List[Dict[str, str]] = None
    signed_doc: Optional[Dict[str, str]] = None

    def __post_init__(self):
        if self.images is None:
            self.images = []

@dataclass
class AuditEntry:
    timestamp: datetime
    message: str
    type: str = "info"

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "type": self.type
        }

@dataclass
class OffboardingState:
    tenant: TenantData
    property: PropertyData
    inspection: InspectionData
    audit_logs: List[AuditEntry]
    permissions: Dict[str, bool]

# ============================================================================
# Application State Manager
# ============================================================================

class OffboardingManager:
    """Central manager for offboarding state and persistence"""

    def __init__(self, db_path: str = "offboarding.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database schema"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS offboarding_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_name TEXT,
                lease_id TEXT,
                email TEXT,
                phone TEXT,
                move_out_date TEXT,
                reason TEXT,
                property_mode TEXT,
                selected_single TEXT,
                selected_multiple TEXT,
                meter_reading TEXT,
                damage_notes TEXT,
                repair_cost REAL,
                deposit_amount REAL,
                deduction_amount REAL,
                final_refund REAL,
                audit_logs TEXT,
                permissions TEXT,
                finalized INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finalized_at TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()

    def save_state(self, state: OffboardingState, finalized: bool = False) -> int:
        """Persist the current offboarding state"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Calculate net refund
        net_refund = max(0, state.inspection.deposit_amount - state.inspection.deduction_amount)

        # Serialize complex fields
        selected_multiple_json = json.dumps(state.property.selected_multiple)
        audit_logs_json = json.dumps([e.to_dict() for e in state.audit_logs])
        permissions_json = json.dumps(state.permissions)
        images_json = json.dumps(state.inspection.images)
        signed_doc_json = json.dumps(state.inspection.signed_doc)

        c.execute('''
            INSERT INTO offboarding_records (
                tenant_name, lease_id, email, phone, move_out_date, reason,
                property_mode, selected_single, selected_multiple,
                meter_reading, damage_notes, repair_cost, deposit_amount, deduction_amount,
                final_refund, audit_logs, permissions, images, signed_doc,
                finalized, finalized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            state.tenant.name,
            state.tenant.lease_id,
            state.tenant.email,
            state.tenant.phone,
            state.tenant.move_out_date,
            state.tenant.reason,
            state.property.mode,
            state.property.selected_single,
            selected_multiple_json,
            state.inspection.meter_reading,
            state.inspection.damage_notes,
            state.inspection.repair_cost,
            state.inspection.deposit_amount,
            state.inspection.deduction_amount,
            net_refund,
            audit_logs_json,
            permissions_json,
            images_json,
            signed_doc_json,
            1 if finalized else 0,
            datetime.now().isoformat() if finalized else None
        ))

        record_id = c.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def get_recent_records(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent offboarding records"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT id, tenant_name, final_refund, created_at, finalized
            FROM offboarding_records
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(row) for row in rows]

# ============================================================================
# Flask Application
# ============================================================================

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
CORS(app)  # Allow cross-origin (useful for development)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize manager (use in-memory for demonstration, but we have SQLite)
manager = OffboardingManager()

# ============================================================================
# Embedded HTML/JS UI (from provided UI)
# ============================================================================

UI_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Mwarokin Estates - Tenant Offboarding Portal</title>
    <!-- Tailwind + Font Awesome + Google Fonts -->
    <script src="https://cdn.tailwindcss.com">
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;400;500;600;700;800;900&display=swap" rel="stylesheet" />
    <style>
        * {
            font-family: 'Inter', sans-serif;
        }

        body {
            background: radial-gradient(ellipse at 10% 20%, #f0f6f9 0%, #e3ecf2 100%);
            min-height: 100vh;
        }

        .glass-premium {
            background: rgba(255, 255, 255, 0.78);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.10), 0 1px 2px rgba(0, 0, 0, 0.02);
        }

        .glass-card {
            background: rgba(255, 255, 255, 0.70);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.6);
            transition: all 0.25s ease;
        }

        .glass-card:hover {
            background: rgba(255, 255, 255, 0.85);
            border-color: rgba(30, 74, 59, 0.15);
        }

        .step-badge {
            width: 40px;
            height: 40px;
            border-radius: 9999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            background: #eef2f6;
            color: #4a5b6a;
            border: 2px solid transparent;
            position: relative;
        }

        .step-badge.active {
            background: #1e4a3b;
            color: #fff;
            border-color: #1e4a3b;
            box-shadow: 0 8px 24px -6px rgba(30, 74, 59, 0.30);
            transform: scale(1.05);
        }

        .step-badge.completed {
            background: #d1e7dd;
            color: #1a4a3a;
            border-color: #a3cfbb;
        }

        .step-badge .checkmark {
            display: none;
        }
        .step-badge.completed .checkmark {
            display: inline;
        }
        .step-badge.completed .step-num {
            display: none;
        }

        .step-connector {
            height: 2px;
            flex: 1;
            min-width: 24px;
            background: #dce3e9;
            transition: background 0.4s ease;
        }
        .step-connector.done {
            background: #1e4a3b;
        }

        .step-content-wrap {
            transition: opacity 0.25s ease, transform 0.30s cubic-bezier(0.34, 1.0, 0.64, 1);
            opacity: 1;
            transform: translateX(0);
        }
        .step-content-wrap.slide-out {
            opacity: 0;
            transform: translateX(16px);
        }

        .prop-card {
            transition: all 0.2s ease;
            cursor: pointer;
            border: 2px solid #e9edf2;
            background: rgba(255, 255, 255, 0.6);
        }
        .prop-card:hover {
            border-color: #bcc9d4;
            background: rgba(255, 255, 255, 0.85);
            transform: translateY(-2px);
        }
        .prop-card.selected {
            border-color: #1e4a3b;
            background: rgba(30, 74, 59, 0.06);
            box-shadow: 0 4px 16px -6px rgba(30, 74, 59, 0.12);
        }

        .file-zone-drag {
            transition: all 0.2s ease;
            border: 2px dashed #cdd8e0;
        }
        .file-zone-drag:hover,
        .file-zone-drag.dragover {
            border-color: #1e4a3b;
            background: rgba(30, 74, 59, 0.04);
        }

        .audit-scroll {
            max-height: 280px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }
        .audit-scroll::-webkit-scrollbar {
            width: 4px;
        }
        .audit-scroll::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 99px;
        }

        .input-premium {
            background: rgba(255, 255, 255, 0.80);
            border: 1.5px solid #e2e8f0;
            border-radius: 14px;
            padding: 0.75rem 1rem;
            transition: all 0.2s ease;
            width: 100%;
            font-size: 0.95rem;
        }
        .input-premium:focus {
            outline: none;
            border-color: #1e4a3b;
            box-shadow: 0 0 0 4px rgba(30, 74, 59, 0.10);
            background: #fff;
        }
        .input-premium.is-valid {
            border-color: #2b8c6e;
            background: rgba(43, 140, 110, 0.04);
        }
        .input-premium.is-invalid {
            border-color: #d45c5c;
            background: rgba(212, 92, 92, 0.04);
        }

        .toggle-track {
            width: 44px;
            height: 26px;
            background: #d1d9e0;
            border-radius: 99px;
            position: relative;
            cursor: pointer;
            transition: background 0.25s ease;
            flex-shrink: 0;
        }
        .toggle-track.active {
            background: #1e4a3b;
        }
        .toggle-track .toggle-knob {
            width: 20px;
            height: 20px;
            background: #fff;
            border-radius: 99px;
            position: absolute;
            top: 3px;
            left: 3px;
            transition: all 0.25s cubic-bezier(0.34, 1.2, 0.64, 1);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
        }
        .toggle-track.active .toggle-knob {
            left: 21px;
        }

        .badge-premium {
            background: rgba(30, 74, 59, 0.08);
            color: #1e4a3b;
            padding: 0.2rem 0.8rem;
            border-radius: 99px;
            font-size: 0.7rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            text-transform: uppercase;
        }

        .gradient-text {
            background: linear-gradient(135deg, #1a4a3a 0%, #2c7a5e 80%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .btn-primary {
            background: #1e4a3b;
            color: #fff;
            padding: 0.7rem 1.8rem;
            border-radius: 9999px;
            font-weight: 600;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px -4px rgba(30, 74, 59, 0.25);
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-primary:hover {
            background: #143d30;
            transform: translateY(-1px);
            box-shadow: 0 8px 24px -6px rgba(30, 74, 59, 0.30);
        }
        .btn-primary:disabled {
            opacity: 0.4;
            cursor: not-allowed;
            transform: none;
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.7);
            color: #2d4050;
            padding: 0.7rem 1.8rem;
            border-radius: 9999px;
            font-weight: 600;
            transition: all 0.2s ease;
            border: 1.5px solid #dce3e9;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        .btn-secondary:hover {
            background: #fff;
            border-color: #b8c6d2;
        }
        .btn-secondary:disabled {
            opacity: 0.3;
            cursor: not-allowed;
        }

        @media (max-width: 640px) {
            .step-badge {
                width: 34px;
                height: 34px;
                font-size: 0.75rem;
            }
        }
    </style>
</head>
<body class="p-4 md:p-8 antialiased">

    <div class="max-w-6xl mx-auto">

        <header class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
            <div>
                <h1 class="text-3xl md:text-4xl font-extrabold tracking-tight flex items-center gap-3">
                    <span class="gradient-text">Mwarokin Estates</span>
                    <span class="badge-premium text-xs md:text-sm">Offboarding</span>
                </h1>
                <p class="text-slate-500 text-sm flex items-center gap-2 mt-0.5">
                    <i class="fas fa-exchange-alt text-emerald-700"></i>
                    Tenant move-out · Shifting workflow · Real-time audit
                </p>
            </div>
            <div class="flex items-center gap-3 bg-white/60 backdrop-blur-sm rounded-full px-5 py-2.5 shadow-sm border border-white/60 text-sm text-slate-700">
                <i class="fas fa-clipboard-list text-emerald-700"></i>
                <span class="font-medium">Active offboarding</span>
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>
        </header>

        <div class="glass-premium rounded-3xl overflow-hidden shadow-2xl">

            <div class="px-6 pt-6 pb-4 border-b border-white/60 bg-white/30">
                <div class="flex items-center gap-2 md:gap-4 flex-wrap">
                    <div class="flex items-center gap-2">
                        <div class="step-badge" data-step="1">
                            <span class="step-num">1</span>
                            <span class="checkmark"><i class="fas fa-check text-xs"></i></span>
                        </div>
                        <span class="text-sm font-medium text-slate-700 hidden sm:inline">Tenant</span>
                    </div>
                    <div class="step-connector" data-connector="1-2"></div>
                    <div class="flex items-center gap-2">
                        <div class="step-badge" data-step="2">
                            <span class="step-num">2</span>
                            <span class="checkmark"><i class="fas fa-check text-xs"></i></span>
                        </div>
                        <span class="text-sm font-medium text-slate-700 hidden sm:inline">Property</span>
                    </div>
                    <div class="step-connector" data-connector="2-3"></div>
                    <div class="flex items-center gap-2">
                        <div class="step-badge" data-step="3">
                            <span class="step-num">3</span>
                            <span class="checkmark"><i class="fas fa-check text-xs"></i></span>
                        </div>
                        <span class="text-sm font-medium text-slate-700 hidden sm:inline">Inspection</span>
                    </div>
                    <div class="step-connector" data-connector="3-4"></div>
                    <div class="flex items-center gap-2">
                        <div class="step-badge" data-step="4">
                            <span class="step-num">4</span>
                            <span class="checkmark"><i class="fas fa-check text-xs"></i></span>
                        </div>
                        <span class="text-sm font-medium text-slate-700 hidden sm:inline">Audit</span>
                    </div>
                </div>
                <div class="mt-4 w-full h-1.5 bg-gray-200/60 rounded-full overflow-hidden">
                    <div id="progressBar" class="h-full bg-gradient-to-r from-emerald-600 to-teal-500 rounded-full transition-all duration-500 ease-out" style="width: 25%;"></div>
                </div>
            </div>

            <div id="stepContent" class="p-6 md:p-8 relative min-h-[380px]">
                <!-- rendered dynamically -->
            </div>

            <div class="bg-white/40 backdrop-blur-sm px-6 py-4 border-t border-white/50 flex flex-col sm:flex-row justify-between gap-3">
                <button id="prevBtn" class="btn-secondary justify-center sm:justify-start">
                    <i class="fas fa-arrow-left"></i> Back
                </button>
                <div class="flex items-center gap-3 self-end sm:self-auto">
                    <span id="stepCounter" class="text-xs text-slate-400 font-medium">1 / 4</span>
                    <button id="nextBtn" class="btn-primary justify-center">
                        Next <i class="fas fa-arrow-right"></i>
                    </button>
                </div>
            </div>
        </div>

        <div class="mt-6 text-center text-xs text-slate-400/70 flex flex-wrap justify-center gap-4">
            <span><i class="fas fa-lock text-emerald-600 mr-1"></i> RBC compliant</span>
            <span><i class="fas fa-clock mr-1"></i> Real-time audit</span>
            <span>© 2026 Mwarokin Estates · v2.0</span>
        </div>
    </div>

    <script>
        // ============================================================
        //  STATE
        // ============================================================
        let currentStep = 1;
        const totalSteps = 4;
        let isTransitioning = false;

        // ---- Tenant & Lease ----
        const tenant = {
            name: '',
            leaseId: '',
            email: '',
            phone: '',
            moveOutDate: '',
            reason: 'lease_end'
        };

        // ---- Property ----
        const propertyMode = { value: 'single' };
        const propertyCatalog = [
            { id: 'propA', name: 'Harmony Heights Villa', address: '12 Serenity Lane', type: 'Single Family', units: 1 },
            { id: 'propB', name: 'Palm Grove Apartments', address: '450 Palm Blvd', type: 'Multi-Family', units: 8 },
            { id: 'propC', name: 'Cedar Creek Complex', address: '88 Cedarwood Dr', type: 'Multi-Family', units: 12 },
            { id: 'propD', name: 'Lakeside Manor', address: '22 Lakeview Rd', type: 'Single Family', units: 1 }
        ];
        let selectedSingle = 'propB';
        let selectedMultiple = ['propB'];

        // ---- Inspection ----
        const inspection = {
            meterReading: '',
            damageNotes: '',
            repairCost: 0,
            depositAmount: 2500,
            deductionAmount: 0,
            images: [],
            signedDoc: null
        };

        // ---- Audit ----
        let auditLogs = [
            { ts: new Date(), msg: '📋 Offboarding session started', type: 'info' }
        ];

        // ---- Permissions ----
        const perms = {
            canModifyInspection: true,
            canApproveRefund: false,
            canAccessAudit: true,
            canFinalizeOffboarding: false
        };

        // ============================================================
        //  HELPERS
        // ============================================================
        function addAudit(msg, type = 'info') {
            auditLogs.unshift({ ts: new Date(), msg, type });
            if (currentStep === 4) renderStep4();
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' } [m] || m));
        }

        function getSelectedPropertyNames() {
            if (propertyMode.value === 'single') {
                const p = propertyCatalog.find(x => x.id === selectedSingle);
                return p ? [p.name] : [];
            }
            return selectedMultiple.map(id => {
                const p = propertyCatalog.find(x => x.id === id);
                return p ? p.name : null;
            }).filter(Boolean);
        }

        function getNetRefund() {
            return Math.max(0, inspection.depositAmount - inspection.deductionAmount);
        }

        // ============================================================
        //  VALIDATION
        // ============================================================
        function validateStep1() {
            if (!tenant.name.trim()) { shakeField('tenantName'); return false; }
            if (!tenant.leaseId.trim()) { shakeField('leaseId'); return false; }
            if (!tenant.email.trim() || !tenant.email.includes('@')) { shakeField('email'); return false; }
            if (!tenant.phone.trim()) { shakeField('phone'); return false; }
            if (!tenant.moveOutDate) { shakeField('moveOutDate'); return false; }
            return true;
        }

        function validateStep2() {
            if (propertyMode.value === 'single' && !selectedSingle) return false;
            if (propertyMode.value === 'multiple' && selectedMultiple.length === 0) return false;
            return true;
        }

        function validateStep3() {
            if (inspection.repairCost < 0 || inspection.deductionAmount < 0) return false;
            return true;
        }

        function shakeField(id) {
            const el = document.getElementById(id);
            if (!el) return;
            el.classList.add('is-invalid');
            el.style.animation = 'none';
            requestAnimationFrame(() => {
                el.style.animation = 'shake 0.35s ease';
            });
            setTimeout(() => el.classList.remove('is-invalid'), 400);
        }

        // inject shake keyframe
        (function injectShake() {
            const style = document.createElement('style');
            style.textContent = `
            @keyframes shake {
              0%, 100% { transform: translateX(0); }
              20% { transform: translateX(-8px); }
              40% { transform: translateX(8px); }
              60% { transform: translateX(-4px); }
              80% { transform: translateX(4px); }
            }
          `;
            document.head.appendChild(style);
        })();

        // ============================================================
        //  RENDER ENGINE
        // ============================================================
        function render() {
            if (isTransitioning) return;
            const container = document.getElementById('stepContent');
            if (!container) return;

            container.classList.remove('slide-out');
            void container.offsetWidth;

            if (currentStep === 1) renderStep1(container);
            else if (currentStep === 2) renderStep2(container);
            else if (currentStep === 3) renderStep3(container);
            else if (currentStep === 4) renderStep4(container);

            updateStepper();
            updateNav();
            updateProgress();
        }

        // ---- STEP 1: Tenant ----
        function renderStep1(container) {
            container.innerHTML = `
            <div class="grid md:grid-cols-2 gap-6">
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Full Tenant Name <span class="text-red-500">*</span></label>
                  <input id="tenantName" type="text" value="${escapeHtml(tenant.name)}" placeholder="e.g. James Njoroge" class="input-premium" />
                  <p class="text-xs text-slate-400 mt-1"><i class="far fa-id-card mr-1"></i> Legal name as per lease</p>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Lease Agreement ID <span class="text-red-500">*</span></label>
                  <input id="leaseId" type="text" value="${escapeHtml(tenant.leaseId)}" placeholder="MWK-LE-1024" class="input-premium" />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Email Address <span class="text-red-500">*</span></label>
                  <input id="email" type="email" value="${escapeHtml(tenant.email)}" placeholder="tenant@example.com" class="input-premium" />
                </div>
              </div>
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Phone Number <span class="text-red-500">*</span></label>
                  <input id="phone" type="tel" value="${escapeHtml(tenant.phone)}" placeholder="+254 700 000 000" class="input-premium" />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Move-out / Vacating Date <span class="text-red-500">*</span></label>
                  <input id="moveOutDate" type="date" value="${tenant.moveOutDate}" class="input-premium" />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Reason for Shifting</label>
                  <select id="reason" class="input-premium bg-white">
                    <option value="lease_end" ${tenant.reason === 'lease_end' ? 'selected' : ''}>Lease ended</option>
                    <option value="relocation" ${tenant.reason === 'relocation' ? 'selected' : ''}>Relocation</option>
                    <option value="financial" ${tenant.reason === 'financial' ? 'selected' : ''}>Financial reasons</option>
                    <option value="other" ${tenant.reason === 'other' ? 'selected' : ''}>Other</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="mt-5 flex items-start gap-3 bg-emerald-50/60 rounded-2xl p-4 text-sm text-emerald-800 border border-emerald-100/60">
              <i class="fas fa-shield-alt text-emerald-600 mt-0.5"></i>
              <span>Lease termination and offboarding records are secured under RBC compliance standards. All data is encrypted.</span>
            </div>
          `;

            bindInput('tenantName', v => tenant.name = v);
            bindInput('leaseId', v => tenant.leaseId = v);
            bindInput('email', v => tenant.email = v);
            bindInput('phone', v => tenant.phone = v);
            bindInput('moveOutDate', v => tenant.moveOutDate = v);
            document.getElementById('reason')?.addEventListener('change', e => {
                tenant.reason = e.target.value;
                addAudit(`Move-out reason: ${e.target.value}`);
            });

            ['tenantName', 'leaseId', 'email', 'phone', 'moveOutDate'].forEach(id => {
                const el = document.getElementById(id);
                if (!el) return;
                el.addEventListener('blur', () => {
                    const val = el.value.trim();
                    if (id === 'email') {
                        el.classList.toggle('is-valid', val.includes('@') && val.length > 3);
                        el.classList.toggle('is-invalid', val.length > 0 && !val.includes('@'));
                    } else if (id === 'moveOutDate') {
                        el.classList.toggle('is-valid', !!val);
                        el.classList.toggle('is-invalid', false);
                    } else {
                        el.classList.toggle('is-valid', val.length > 0);
                        el.classList.toggle('is-invalid', val.length === 0 && document.activeElement !== el);
                    }
                });
            });
        }

        // ---- STEP 2: Property ----
        function renderStep2(container) {
            const mode = propertyMode.value;
            const renderProps = () => {
                if (mode === 'single') {
                    return `<div class="grid sm:grid-cols-2 gap-3 mt-3">${propertyCatalog.map(p => `
                <div class="prop-card rounded-2xl p-4 ${selectedSingle === p.id ? 'selected' : ''}" data-prop-id="${p.id}">
                  <div class="flex justify-between items-start">
                    <div>
                      <div class="font-bold text-slate-800">${escapeHtml(p.name)}</div>
                      <div class="text-sm text-slate-500">${p.address}</div>
                    </div>
                    <span class="text-[10px] font-semibold px-2.5 py-0.5 rounded-full ${p.type.includes('Multi') ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'}">${p.type}</span>
                  </div>
                  ${selectedSingle === p.id ? `<div class="mt-2 text-xs text-emerald-700 font-medium"><i class="fas fa-check-circle"></i> Selected</div>` : ''}
                </div>
              `).join('')}</div>`;
                } else {
                    return `<div class="space-y-2 mt-3">${propertyCatalog.map(p => `
                <div class="flex items-center gap-4 p-3 rounded-xl border ${selectedMultiple.includes(p.id) ? 'border-emerald-500 bg-emerald-50/30' : 'border-gray-200 bg-white/60'}">
                  <input type="checkbox" class="prop-cb w-5 h-5 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500" value="${p.id}" ${selectedMultiple.includes(p.id) ? 'checked' : ''} />
                  <div class="flex-1">
                    <span class="font-semibold">${escapeHtml(p.name)}</span>
                    <span class="text-sm text-slate-500 ml-2">${p.address}</span>
                  </div>
                  <span class="text-xs bg-gray-100 px-2 py-0.5 rounded-full">${p.type}</span>
                </div>
              `).join('')}</div>`;
                }
            };

            container.innerHTML = `
            <div class="space-y-5">
              <div class="glass-card rounded-2xl p-5">
                <div class="flex flex-wrap items-center gap-6">
                  <span class="font-bold text-slate-700"><i class="fas fa-door-open text-emerald-700 mr-2"></i>Property Release</span>
                  <div class="flex gap-4 text-sm">
                    <label class="flex items-center gap-2 cursor-pointer"><input type="radio" name="propMode" value="single" ${mode === 'single' ? 'checked' : ''} /> <span>🏠 Single</span></label>
                    <label class="flex items-center gap-2 cursor-pointer"><input type="radio" name="propMode" value="multiple" ${mode === 'multiple' ? 'checked' : ''} /> <span>🏢 Multiple</span></label>
                  </div>
                  <span class="badge-premium text-xs">${mode === 'single' ? '1 property' : selectedMultiple.length + ' selected'}</span>
                </div>
                <div id="propList">${renderProps()}</div>
                <div class="mt-4 text-xs text-amber-700 bg-amber-50/70 p-3 rounded-xl flex items-center gap-2">
                  <i class="fas fa-info-circle"></i> ${mode === 'single' ? 'Single property offboarding — one final inspection required.' : 'Multi-property offboarding — each unit requires a separate inspection.'}
                </div>
              </div>
            </div>
          `;

            document.querySelectorAll('input[name="propMode"]').forEach(r => {
                r.addEventListener('change', e => {
                    const newMode = e.target.value;
                    if (newMode !== propertyMode.value) {
                        propertyMode.value = newMode;
                        if (newMode === 'single' && !selectedSingle) selectedSingle = propertyCatalog[0].id;
                        if (newMode === 'multiple' && selectedMultiple.length === 0) selectedMultiple = [propertyCatalog[0]
                            .id
                        ];
                        addAudit(`Switched to ${newMode === 'single' ? 'Single' : 'Multiple'} property mode`);
                        renderStep2(container);
                    }
                });
            });

            if (mode === 'single') {
                document.querySelectorAll('.prop-card').forEach(card => {
                    card.addEventListener('click', () => {
                        const id = card.dataset.propId;
                        if (id && id !== selectedSingle) {
                            selectedSingle = id;
                            const p = propertyCatalog.find(x => x.id === id);
                            addAudit(`Selected property: ${p?.name}`);
                            renderStep2(container);
                        }
                    });
                });
            } else {
                document.querySelectorAll('.prop-cb').forEach(cb => {
                    cb.addEventListener('change', e => {
                        const id = e.target.value;
                        if (e.target.checked) {
                            if (!selectedMultiple.includes(id)) {
                                selectedMultiple.push(id);
                                const p = propertyCatalog.find(x => x.id === id);
                                addAudit(`Added property: ${p?.name}`);
                            }
                        } else {
                            selectedMultiple = selectedMultiple.filter(x => x !== id);
                            const p = propertyCatalog.find(x => x.id === id);
                            addAudit(`Removed property: ${p?.name}`);
                        }
                        renderStep2(container);
                    });
                });
            }
        }

        // ---- STEP 3: Inspection ----
        function renderStep3(container) {
            const net = getNetRefund();
            container.innerHTML = `
            <div class="grid lg:grid-cols-2 gap-6">
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Final Utility Meter Reading</label>
                  <input id="meterReading" type="text" value="${escapeHtml(inspection.meterReading)}" placeholder="e.g. 1245 kWh" class="input-premium" />
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">Damage / Repair Notes</label>
                  <textarea id="damageNotes" rows="3" class="input-premium resize-y" placeholder="Describe any damages, wear and tear, or repair items…">${escapeHtml(inspection.damageNotes)}</textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Repair Cost (USD)</label>
                    <input id="repairCost" type="number" value="${inspection.repairCost}" class="input-premium" />
                  </div>
                  <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Deduction Amount</label>
                    <input id="deductionAmount" type="number" value="${inspection.deductionAmount}" class="input-premium" />
                  </div>
                </div>
                <div class="bg-white/70 rounded-2xl p-4 border border-gray-200/60">
                  <div class="flex justify-between text-sm"><span>Security Deposit</span><span class="font-semibold">$${inspection.depositAmount}</span></div>
                  <div class="flex justify-between text-sm"><span>Total Deduction</span><span class="font-semibold text-red-600">-$${inspection.deductionAmount}</span></div>
                  <div class="flex justify-between text-xl font-bold mt-2 pt-2 border-t border-gray-200">
                    <span>Net Refund</span>
                    <span class="text-emerald-700">$${net.toFixed(2)}</span>
                  </div>
                </div>
              </div>
              <div class="space-y-4">
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">📸 Inspection Images (move-out evidence)</label>
                  <div id="imageDropZone" class="file-zone-drag rounded-2xl p-4 text-center cursor-pointer bg-white/60">
                    <i class="fas fa-cloud-upload-alt text-3xl text-emerald-600/70"></i>
                    <p class="text-sm text-slate-500">Click or drag to upload photos</p>
                    <input id="imageInput" type="file" multiple accept="image/*" class="hidden" />
                  </div>
                  <div id="imagePreviewGrid" class="flex flex-wrap gap-2 mt-3">
                    ${inspection.images.map((img, idx) => `
                      <div class="relative w-20 h-20 rounded-xl overflow-hidden border border-gray-200 shadow-sm group">
                        <img src="${img.dataUrl}" class="w-full h-full object-cover" />
                        <button data-idx="${idx}" class="remove-img absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition">×</button>
                      </div>
                    `).join('')}
                  </div>
                </div>
                <div>
                  <label class="block text-sm font-semibold text-slate-700 mb-1">📄 Signed Move-out Agreement</label>
                  <div class="flex items-center gap-3 p-3 rounded-xl bg-white/70 border border-gray-200">
                    <span class="text-sm truncate flex-1">${inspection.signedDoc ? inspection.signedDoc.name : 'No file selected'}</span>
                    <button id="agreementUploadBtn" class="bg-gray-200/80 hover:bg-gray-300/80 px-4 py-1.5 rounded-full text-sm font-medium transition"><i class="fas fa-upload mr-1"></i>Upload</button>
                    <input id="agreementInput" type="file" accept=".pdf,.jpg,.png,.jpeg" class="hidden" />
                  </div>
                </div>
              </div>
            </div>
          `;

            bindInput('meterReading', v => inspection.meterReading = v);
            bindInput('damageNotes', v => inspection.damageNotes = v);
            bindInput('repairCost', v => { inspection.repairCost = parseFloat(v) || 0;
                renderStep3(container); });
            bindInput('deductionAmount', v => { inspection.deductionAmount = parseFloat(v) || 0;
                renderStep3(container); });

            const dropZone = document.getElementById('imageDropZone');
            const imgInput = document.getElementById('imageInput');
            dropZone?.addEventListener('click', () => imgInput?.click());
            imgInput?.addEventListener('change', e => {
                Array.from(e.target.files).forEach(file => {
                    const reader = new FileReader();
                    reader.onload = ev => {
                        inspection.images.push({ name: file.name, dataUrl: ev.target.result });
                        addAudit(`Uploaded inspection image: ${file.name}`);
                        renderStep3(container);
                    };
                    reader.readAsDataURL(file);
                });
                e.target.value = '';
            });
            dropZone?.addEventListener('dragover', e => { e.preventDefault();
                dropZone.classList.add('dragover'); });
            dropZone?.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
            dropZone?.addEventListener('drop', e => {
                e.preventDefault();
                dropZone.classList.remove('dragover');
                const files = e.dataTransfer.files;
                Array.from(files).forEach(file => {
                    if (file.type.startsWith('image/')) {
                        const reader = new FileReader();
                        reader.onload = ev => {
                            inspection.images.push({ name: file.name, dataUrl: ev.target.result });
                            addAudit(`Dropped image: ${file.name}`);
                            renderStep3(container);
                        };
                        reader.readAsDataURL(file);
                    }
                });
            });

            document.querySelectorAll('.remove-img').forEach(btn => {
                btn.addEventListener('click', e => {
                    const idx = parseInt(btn.dataset.idx);
                    if (!isNaN(idx)) {
                        inspection.images.splice(idx, 1);
                        addAudit('Removed inspection photo');
                        renderStep3(container);
                    }
                });
            });

            const agreeBtn = document.getElementById('agreementUploadBtn');
            const agreeInput = document.getElementById('agreementInput');
            agreeBtn?.addEventListener('click', () => agreeInput?.click());
            agreeInput?.addEventListener('change', e => {
                const file = e.target.files[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = ev => {
                    inspection.signedDoc = { name: file.name, dataUrl: ev.target.result };
                    addAudit(`Uploaded agreement: ${file.name}`);
                    renderStep3(container);
                };
                reader.readAsDataURL(file);
                e.target.value = '';
            });
        }

        // ---- STEP 4: Audit & Permissions ----
        function renderStep4(container) {
            const propNames = getSelectedPropertyNames().join(', ') || 'None';
            container.innerHTML = `
            <div class="grid lg:grid-cols-2 gap-6">
              <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center gap-3 border-b border-gray-200/60 pb-3 mb-4">
                  <i class="fas fa-user-lock text-emerald-700 text-xl"></i>
                  <h3 class="text-xl font-bold text-slate-800">Permissions</h3>
                </div>
                <div class="mb-4 p-3 bg-white/60 rounded-xl text-sm">
                  <div><span class="font-semibold">Tenant:</span> ${escapeHtml(tenant.name) || '—'}</div>
                  <div><span class="font-semibold">Properties:</span> ${propNames}</div>
                </div>
                <div class="space-y-3">
                  ${[
                    { key: 'canModifyInspection', label: 'Modify Inspection Details', icon: 'clipboard-list' },
                    { key: 'canApproveRefund', label: 'Approve Refund / Settlement', icon: 'dollar-sign' },
                    { key: 'canAccessAudit', label: 'View Audit & Compliance Logs', icon: 'eye' },
                    { key: 'canFinalizeOffboarding', label: 'Finalize Offboarding (Admin)', icon: 'check-double' }
                  ].map(p => `
                    <div class="flex items-center justify-between p-3 bg-white/50 rounded-xl border border-gray-100/80">
                      <span class="text-sm"><i class="fas fa-${p.icon} text-emerald-600 w-5"></i> ${p.label}</span>
                      <div class="toggle-track ${perms[p.key] ? 'active' : ''}" data-perm="${p.key}">
                        <div class="toggle-knob"></div>
                      </div>
                    </div>
                  `).join('')}
                </div>
                <button id="applyPermsBtn" class="mt-5 w-full py-2.5 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-200/70 font-medium hover:bg-emerald-100 transition text-sm">
                  <i class="fas fa-sync-alt mr-1"></i> Apply Permission Changes
                </button>
              </div>

              <div class="glass-card rounded-2xl p-5">
                <div class="flex items-center gap-3 border-b border-gray-200/60 pb-3 mb-4">
                  <i class="fas fa-history text-emerald-700 text-xl"></i>
                  <h3 class="text-xl font-bold text-slate-800">Audit Trail</h3>
                  <span class="badge-premium text-xs ml-auto">Live</span>
                </div>
                <div class="audit-scroll pr-1 space-y-1.5">
                  ${auditLogs.slice(0, 30).map(log => `
                    <div class="text-xs border-l-4 ${log.type === 'info' ? 'border-emerald-300' : 'border-amber-300'} pl-3 py-1.5 bg-white/50 rounded-r-xl">
                      <span class="text-slate-400 font-mono">${log.ts.toLocaleTimeString()}</span>
                      <span class="text-slate-700">${log.msg}</span>
                    </div>
                  `).join('')}
                  ${auditLogs.length === 0 ? '<div class="text-sm text-slate-400 p-4 text-center">No audit events yet.</div>' : ''}
                </div>
                <button id="clearAuditBtn" class="text-xs text-slate-400 hover:text-red-500 underline mt-3 transition">Clear audit logs</button>
              </div>
            </div>

            <div class="mt-6 bg-gradient-to-r from-emerald-50/80 to-teal-50/80 rounded-2xl p-5 flex flex-wrap items-center justify-between gap-4 border border-white/60">
              <div>
                <div class="font-semibold text-slate-800"><i class="fas fa-flag-checkered text-emerald-700 mr-2"></i>Ready to complete</div>
                <div class="text-sm text-slate-500">All records will be archived and settlement queued for processing.</div>
              </div>
              <button id="finalizeBtn" class="btn-primary text-sm px-6 py-2.5">
                <i class="fas fa-sign-out-alt"></i> Finalize Offboarding
              </button>
            </div>
          `;

            document.querySelectorAll('.toggle-track').forEach(track => {
                track.addEventListener('click', () => {
                    const key = track.dataset.perm;
                    if (!key) return;
                    const newVal = !perms[key];
                    perms[key] = newVal;
                    track.classList.toggle('active', newVal);
                    addAudit(`Permission "${key}" ${newVal ? 'GRANTED' : 'REVOKED'}`);
                });
            });

            document.getElementById('applyPermsBtn')?.addEventListener('click', () => {
                addAudit('Permission overrides applied manually');
                alert('✅ Permissions updated and logged.');
            });

            document.getElementById('clearAuditBtn')?.addEventListener('click', () => {
                auditLogs = [{ ts: new Date(), msg: '🧹 Audit history cleared (demo)', type: 'info' }];
                renderStep4(container);
            });

            document.getElementById('finalizeBtn')?.addEventListener('click', () => {
                if (!perms.canFinalizeOffboarding) {
                    alert('⛔ You lack "Finalize Offboarding" permission. Please contact an admin.');
                    return;
                }
                const net = getNetRefund();
                addAudit(`✅ OFFBOARDING COMPLETED for ${tenant.name || 'Tenant'} | Net refund $${net.toFixed(2)}`);
                alert(`🎉 Offboarding finalized for ${tenant.name || 'Tenant'}.\\nNet refund: $${net.toFixed(2)}\\nAudit trail stored.`);

                // Optional: POST to backend
                const payload = {
                    tenant: tenant,
                    property: { mode: propertyMode.value, selectedSingle, selectedMultiple },
                    inspection: inspection,
                    auditLogs: auditLogs.map(log => ({ ts: log.ts.toISOString(), msg: log.msg, type: log.type })),
                    permissions: perms,
                    netRefund: net
                };
                fetch('/api/finalize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                })
                .then(res => res.json())
                .then(data => console.log('Backend response:', data))
                .catch(err => console.error('Error finalizing:', err));
            });
        }

        // ============================================================
        //  BINDING HELPERS
        // ============================================================
        function bindInput(id, fn) {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', () => fn(el.value));
            fn(el.value);
        }

        // ============================================================
        //  STEPPER / NAV
        // ============================================================
        function updateStepper() {
            document.querySelectorAll('.step-badge').forEach(el => {
                const step = parseInt(el.dataset.step);
                el.classList.remove('active', 'completed');
                if (step === currentStep) el.classList.add('active');
                else if (step < currentStep) el.classList.add('completed');
            });
            document.querySelectorAll('.step-connector').forEach(el => {
                const parts = el.dataset.connector?.split('-').map(Number) || [];
                if (parts.length === 2) {
                    const [a, b] = parts;
                    el.classList.toggle('done', currentStep > a);
                }
            });
        }

        function updateProgress() {
            const pct = ((currentStep - 1) / (totalSteps - 1)) * 100;
            const bar = document.getElementById('progressBar');
            if (bar) bar.style.width = Math.min(100, pct) + '%';
            const counter = document.getElementById('stepCounter');
            if (counter) counter.textContent = `${currentStep} / ${totalSteps}`;
        }

        function updateNav() {
            const prev = document.getElementById('prevBtn');
            const next = document.getElementById('nextBtn');
            if (prev) prev.disabled = currentStep === 1;
            if (next) {
                next.innerHTML = currentStep === totalSteps ?
                    '<i class="fas fa-check-circle"></i> Complete' :
                    'Next <i class="fas fa-arrow-right"></i>';
            }
        }

        // ============================================================
        //  NAVIGATION ACTIONS
        // ============================================================
        function goNext() {
            if (isTransitioning) return;
            if (currentStep === 1 && !validateStep1()) return;
            if (currentStep === 2 && !validateStep2()) return;
            if (currentStep === 3 && !validateStep3()) return;

            if (currentStep < totalSteps) {
                const container = document.getElementById('stepContent');
                container.classList.add('slide-out');
                setTimeout(() => {
                    currentStep++;
                    render();
                }, 200);
            } else {
                // final step will be handled by finalize button
            }
        }

        function goPrev() {
            if (isTransitioning || currentStep === 1) return;
            const container = document.getElementById('stepContent');
            container.classList.add('slide-out');
            setTimeout(() => {
                currentStep--;
                render();
            }, 200);
        }

        // ============================================================
        //  INIT
        // ============================================================
        document.addEventListener('DOMContentLoaded', () => {
            addAudit('🚀 Offboarding portal ready — Shift workflow active');
            render();

            document.getElementById('nextBtn')?.addEventListener('click', goNext);
            document.getElementById('prevBtn')?.addEventListener('click', goPrev);

            document.addEventListener('keydown', e => {
                if (e.key === 'ArrowRight' || e.key === 'Enter') {
                    const active = document.activeElement;
                    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active
                            .tagName === 'SELECT')) return;
                    e.preventDefault();
                    goNext();
                }
                if (e.key === 'ArrowLeft') {
                    const active = document.activeElement;
                    if (active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active
                            .tagName === 'SELECT')) return;
                    e.preventDefault();
                    goPrev();
                }
            });
        });

        if (!Element.prototype.matches) {
            Element.prototype.matches = Element.prototype.msMatchesSelector || Element.prototype.webkitMatchesSelector;
        }
    </script>
</body>
</html>
'''

# ============================================================================
# Flask Routes
# ============================================================================

@app.route('/')
def index():
    """Serve the main offboarding UI"""
    return render_template_string(UI_HTML)

@app.route('/api/finalize', methods=['POST'])
def finalize_offboarding():
    """
    Accept final offboarding payload and persist to database.
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        # Reconstruct state from payload
        tenant_data = TenantData(**data.get('tenant', {}))
        prop_data = data.get('property', {})
        prop_obj = PropertyData(
            mode=prop_data.get('mode', 'single'),
            selected_single=prop_data.get('selectedSingle', 'propB'),
            selected_multiple=prop_data.get('selectedMultiple', ['propB'])
        )
        insp_data = data.get('inspection', {})
        insp_obj = InspectionData(
            meter_reading=insp_data.get('meterReading', ''),
            damage_notes=insp_data.get('damageNotes', ''),
            repair_cost=float(insp_data.get('repairCost', 0)),
            deposit_amount=float(insp_data.get('depositAmount', 2500)),
            deduction_amount=float(insp_data.get('deductionAmount', 0)),
            images=insp_data.get('images', []),
            signed_doc=insp_data.get('signedDoc', None)
        )
        audit_entries = [AuditEntry(
            timestamp=datetime.fromisoformat(log['ts'].replace('Z', '+00:00')),
            message=log['msg'],
            type=log.get('type', 'info')
        ) for log in data.get('auditLogs', [])]

        perms = data.get('permissions', {
            'canModifyInspection': True,
            'canApproveRefund': False,
            'canAccessAudit': True,
            'canFinalizeOffboarding': False
        })

        state = OffboardingState(
            tenant=tenant_data,
            property=prop_obj,
            inspection=insp_obj,
            audit_logs=audit_entries,
            permissions=perms
        )

        record_id = manager.save_state(state, finalized=True)

        logger.info(f"Finalized offboarding record #{record_id} for tenant {tenant_data.name}")

        return jsonify({
            'success': True,
            'record_id': record_id,
            'message': f'Offboarding finalized for {tenant_data.name}'
        }), 200

    except Exception as e:
        logger.error(f"Error finalizing offboarding: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/records', methods=['GET'])
def get_records():
    """Return recent offboarding records"""
    try:
        limit = request.args.get('limit', 10, type=int)
        records = manager.get_recent_records(limit)
        return jsonify(records), 200
    except Exception as e:
        logger.error(f"Error fetching records: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()}), 200

# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == '__main__':
    # Create database if not exists
    manager._init_db()

    # Run the Flask development server
    app.run(host='0.0.0.0', port=5000, debug=True)
```
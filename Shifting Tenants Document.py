```python
"""
Mwaroki Estates - Shifting Tenants Document Backend
A modern, professional FastAPI application for managing move-out agreements.

Features:
- Serve the frontend HTML
- Accept signature (canvas) and uploaded documents
- Store agreements and audit logs in SQLite
- Generate PDF agreements
- Send email notifications with PDF attachment

Requirements:
- Python 3.9+
- Install dependencies: pip install fastapi uvicorn sqlalchemy pydantic python-multipart reportlab aiosmtplib email-validator
- Set environment variables for email (optional)
"""

import os
import base64
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Optional, List
from io import BytesIO
import logging
import re

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import create_engine, Column, String, DateTime, Float, Text, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ------------------------------
# Configuration
# ------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mwaroki.db")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")  # Optional
SMTP_PASS = os.getenv("SMTP_PASS", "")  # Optional
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "support@mwaroki.co.ke")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------------------
# Database Setup (SQLAlchemy)
# ------------------------------
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Agreement(Base):
    __tablename__ = "agreements"

    id = Column(String(36), primary_key=True, index=True)
    tenant_name = Column(String(255), nullable=False)
    lease_id = Column(String(50), nullable=False)
    properties = Column(Text, nullable=False)
    move_out_date = Column(String(20), nullable=False)
    deposit = Column(Float, nullable=False)
    final_refund = Column(Float, nullable=False)
    signature_path = Column(String(255), nullable=True)      # path to saved signature PNG
    uploaded_doc_path = Column(String(255), nullable=True)  # path to uploaded file
    signed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    agreement_id = Column(String(36), nullable=True)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    log_type = Column(String(20), default="info")  # info, error, success

Base.metadata.create_all(bind=engine)

# ------------------------------
# Pydantic Schemas
# ------------------------------
class AgreementCreate(BaseModel):
    tenant_name: str
    lease_id: str
    properties: str
    move_out_date: str
    deposit: float = Field(gt=0)
    final_refund: float = Field(ge=0)
    signature_data_url: Optional[str] = None  # e.g. "data:image/png;base64,..."
    uploaded_file: Optional[str] = None       # base64 encoded file content (optional, if not using multipart)
    confirm: bool = True

class AgreementResponse(BaseModel):
    id: str
    status: str
    signed_at: Optional[datetime]
    message: str

class AuditLogResponse(BaseModel):
    id: int
    agreement_id: Optional[str]
    message: str
    timestamp: datetime
    log_type: str

# ------------------------------
# FastAPI App
# ------------------------------
app = FastAPI(
    title="Mwaroki Estates - Shifting Tenants API",
    description="API for managing move-out agreements with electronic signatures.",
    version="2.4"
)

# CORS (allow frontend from any origin in development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ------------------------------
# Helper: Save base64 image
# ------------------------------
def save_signature(data_url: str, agreement_id: str) -> str:
    """Decode data URL and save as PNG file. Returns file path."""
    # Extract base64 part after comma
    pattern = r"^data:image/(png|jpeg|jpg);base64,(.+)$"
    match = re.match(pattern, data_url)
    if not match:
        raise ValueError("Invalid signature data URL")
    img_format = match.group(1)
    img_data = match.group(2)
    # Decode
    try:
        img_bytes = base64.b64decode(img_data)
    except Exception:
        raise ValueError("Base64 decoding failed")

    # Create directories if needed
    upload_dir = "uploads/signatures"
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{agreement_id}.png"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    return filepath

def save_uploaded_file(file_content: bytes, file_name: str, agreement_id: str) -> str:
    """Save uploaded file to disk. Returns file path."""
    upload_dir = "uploads/documents"
    os.makedirs(upload_dir, exist_ok=True)
    # Sanitize filename
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', file_name)
    filename = f"{agreement_id}_{safe_name}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(file_content)
    return filepath

# ------------------------------
# Helper: Generate PDF
# ------------------------------
def generate_pdf(agreement: Agreement, signature_path: Optional[str], uploaded_doc_path: Optional[str]) -> BytesIO:
    """Generate a PDF document for the agreement."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    heading_style = styles['Heading2']
    normal_style = styles['Normal']

    # Custom styles
    centered_style = ParagraphStyle('Centered', parent=styles['Normal'], alignment=TA_CENTER)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontName='Helvetica-Bold')

    story = []

    # Title
    story.append(Paragraph("Mwaroki Estates", title_style))
    story.append(Paragraph("Shifting Tenants Agreement", centered_style))
    story.append(Spacer(1, 0.3*inch))

    # Agreement details
    data = [
        ["Agreement ID:", agreement.id],
        ["Tenant Name:", agreement.tenant_name],
        ["Lease ID:", agreement.lease_id],
        ["Property(s):", agreement.properties],
        ["Move-out Date:", agreement.move_out_date],
        ["Security Deposit:", f"${agreement.deposit:,.2f}"],
        ["Final Refund:", f"${agreement.final_refund:,.2f}"],
        ["Signed At:", agreement.signed_at.strftime("%Y-%m-%d %H:%M") if agreement.signed_at else "N/A"],
        ["Status:", agreement.status.upper()],
    ]

    # Table for details
    table = Table(data, colWidths=[2*inch, 3.5*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(table)
    story.append(Spacer(1, 0.3*inch))

    # Terms
    story.append(Paragraph("Terms of Release", heading_style))
    story.append(Paragraph("▪ The tenant has vacated the property in good condition, subject to deductions.", normal_style))
    story.append(Paragraph("▪ All outstanding utility bills, service charges, and rent arrears have been settled as of the move-out date.", normal_style))
    story.append(Paragraph("▪ The security deposit refund, after deductions, shall be processed within 14 business days.", normal_style))
    story.append(Paragraph("▪ This agreement constitutes a full and final release of all claims between the tenant and Mwaroki Estates.", normal_style))
    story.append(Spacer(1, 0.3*inch))

    # Signature section
    story.append(Paragraph("Electronic Signature", heading_style))
    if signature_path and os.path.exists(signature_path):
        # Add signature image
        try:
            img = Image(signature_path, width=2*inch, height=0.75*inch)
            story.append(img)
        except Exception as e:
            logger.error(f"Could not embed signature: {e}")
            story.append(Paragraph("(Signature image not available)", normal_style))
    else:
        story.append(Paragraph("(No signature provided)", normal_style))

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"Digitally signed by {agreement.tenant_name}", normal_style))
    story.append(Paragraph(f"Timestamp: {agreement.signed_at.strftime('%Y-%m-%d %H:%M') if agreement.signed_at else 'N/A'}", normal_style))

    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("This document is digitally signed and stored for RBC compliance.", styles['Italic']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ------------------------------
# Helper: Send email with PDF
# ------------------------------
def send_email(recipient: str, agreement_id: str, pdf_buffer: BytesIO):
    """Send email with PDF attachment."""
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP credentials not set; skipping email send.")
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = ADMIN_EMAIL
        msg['To'] = recipient
        msg['Subject'] = f"Move-out Agreement #{agreement_id}"

        body = f"""
        Dear Tenant,

        Please find attached the signed Move-out Agreement (ID: {agreement_id}) for your records.

        If you have any questions, contact us at {ADMIN_EMAIL}.

        Regards,
        Mwaroki Estates
        """
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(pdf_buffer.getvalue())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename=agreement_{agreement_id}.pdf')
        msg.attach(part)

        # Send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient} for agreement {agreement_id}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

# ------------------------------
# API Endpoints
# ------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    """Serve the main HTML page."""
    # The HTML content is embedded here for simplicity.
    # In production, you might use Jinja2 templates or serve static files.
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
    <title>Mwaroki Estates · Shifting Tenants Document</title>

    <!-- Tailwind + Font Awesome + Google Fonts + Signature Pad -->
    <script src="https://cdn.tailwindcss.com">
    </script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800;14..32,900&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/signature_pad@4.1.7/dist/signature_pad.umd.min.js">
    </script>

    <style>
        * {
            font-family: 'Inter', sans-serif;
        }

        body {
            background: #f2f6f4;
            min-height: 100vh;
        }

        /* ── Glassmorphism cards ── */
        .glass-card {
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(6px);
            -webkit-backdrop-filter: blur(6px);
            border: 1px solid rgba(255, 255, 255, 0.70);
            box-shadow: 0 8px 32px rgba(26, 74, 58, 0.08);
            transition: transform 0.2s ease, box-shadow 0.3s ease;
        }
        .glass-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 48px rgba(26, 74, 58, 0.12);
        }

        /* ── Gradient text ── */
        .gradient-text {
            background: linear-gradient(135deg, #1a4a3a 0%, #2c7a5e 60%, #3ba37f 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        /* ── Signature canvas ── */
        .signature-canvas {
            border: 2px dashed #cbd5e1;
            border-radius: 1.25rem;
            background: #fafcfa;
            touch-action: none;
            cursor: crosshair;
            transition: border-color 0.3s, box-shadow 0.3s;
            width: 100%;
            height: auto;
            aspect-ratio: 500 / 200;
        }
        .signature-canvas:focus,
        .signature-canvas.active {
            border-color: #1a4a3a;
            box-shadow: 0 0 0 4px rgba(26, 74, 58, 0.15);
        }

        /* ── Step indicator ── */
        .step-dot {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 9999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            background: #e9edec;
            color: #5e6f6a;
            border: 2px solid transparent;
        }
        .step-dot.active {
            background: #1a4a3a;
            color: #fff;
            border-color: #1a4a3a;
            transform: scale(1.05);
            box-shadow: 0 4px 16px rgba(26, 74, 58, 0.30);
        }
        .step-dot.completed {
            background: #2c7a5e;
            color: #fff;
            border-color: #2c7a5e;
        }
        .step-line {
            flex: 1;
            height: 2px;
            background: #dce3e0;
            transition: background 0.5s;
            margin: 0 0.25rem;
        }
        .step-line.completed {
            background: #2c7a5e;
        }

        /* ── Audit scroll ── */
        .audit-scroll {
            max-height: 260px;
            overflow-y: auto;
            scroll-behavior: smooth;
        }
        .audit-scroll::-webkit-scrollbar {
            width: 4px;
        }
        .audit-scroll::-webkit-scrollbar-track {
            background: #eef2f0;
            border-radius: 8px;
        }
        .audit-scroll::-webkit-scrollbar-thumb {
            background: #2c7a5e;
            border-radius: 8px;
        }

        /* ── Button primary ── */
        .btn-primary {
            background: linear-gradient(145deg, #1a4a3a, #2c7a5e);
            transition: all 0.25s ease;
            box-shadow: 0 4px 16px rgba(26, 74, 58, 0.25);
        }
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 28px rgba(26, 74, 58, 0.35);
        }
        .btn-primary:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }

        /* ── Modal ── */
        .modal-overlay {
            background: rgba(0, 0, 0, 0.45);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }
        .modal-box {
            animation: modalIn 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes modalIn {
            0% {
                opacity: 0;
                transform: scale(0.94) translateY(20px);
            }
            100% {
                opacity: 1;
                transform: scale(1) translateY(0);
            }
        }

        /* ── Misc ── */
        .badge-gold {
            background: linear-gradient(145deg, #d4a84b, #b8912e);
            color: #fff;
        }
        .border-gold {
            border-color: #d4a84b;
        }

        /* ── Responsive tweaks ── */
        @media (max-width: 640px) {
            .step-dot {
                width: 2rem;
                height: 2rem;
                font-size: 0.7rem;
            }
        }
    </style>
</head>
<body>

    <div class="max-w-7xl mx-auto px-4 py-6 md:py-10">

        <!-- ═══ HEADER ═══ -->
        <header class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
            <div class="flex items-center gap-4">
                <div class="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#1a4a3a] to-[#3ba37f] flex items-center justify-center shadow-lg shadow-emerald-900/20">
                    <i class="fas fa-building text-white text-xl"></i>
                </div>
                <div>
                    <h1 class="text-2xl md:text-3xl font-extrabold tracking-tight gradient-text">
                        Mwaroki Estates
                    </h1>
                    <p class="text-slate-500 text-sm flex items-center gap-2">
                        <i class="fas fa-file-signature text-emerald-600"></i>
                        Shifting Tenants · Move-out Agreement
                    </p>
                </div>
            </div>
            <div class="flex items-center gap-3 flex-wrap">
                <span class="bg-emerald-50 text-emerald-800 text-xs font-semibold px-4 py-1.5 rounded-full border border-emerald-200/60 shadow-sm">
                    <i class="fas fa-check-circle text-emerald-600 mr-1"></i> RBC Compliant
                </span>
                <span class="bg-amber-50 text-amber-700 text-xs font-semibold px-4 py-1.5 rounded-full border border-amber-200/60 shadow-sm">
                    <i class="fas fa-clock mr-1"></i> Draft
                </span>
            </div>
        </header>

        <!-- ═══ STEP INDICATOR ═══ -->
        <div class="flex items-center gap-2 mb-8 max-w-2xl mx-auto" id="stepIndicator">
            <div class="step-dot active" data-step="1">1</div>
            <div class="step-line" data-line="1"></div>
            <div class="step-dot" data-step="2">2</div>
            <div class="step-line" data-line="2"></div>
            <div class="step-dot" data-step="3">3</div>
        </div>

        <!-- ═══ MAIN GRID ═══ -->
        <div class="grid lg:grid-cols-5 gap-6">

            <!-- ─── LEFT: Document Content (3/5) ─── -->
            <div class="lg:col-span-3 space-y-6">

                <!-- Tenant & Property Card -->
                <section class="glass-card rounded-2xl p-6 md:p-7 border border-white/60">
                    <div class="flex items-center justify-between border-b border-slate-100 pb-4 mb-5">
                        <h2 class="text-lg font-bold flex items-center gap-2 text-slate-800">
                            <i class="fas fa-user-check text-emerald-600"></i> Tenant &amp; Property
                        </h2>
                        <span class="text-xs bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full font-medium">Active Lease</span>
                    </div>
                    <div class="grid sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
                        <div><span class="font-semibold text-slate-600">Tenant Name</span><br /><span class="text-slate-800 font-medium" id="tenantNameDisplay">Grace Wanjiku</span></div>
                        <div><span class="font-semibold text-slate-600">Lease ID</span><br /><span class="text-slate-800 font-medium" id="leaseIdDisplay">MWK‑LE‑2391</span></div>
                        <div class="sm:col-span-2"><span class="font-semibold text-slate-600">Property(s)</span><br /><span class="text-slate-800 font-medium" id="propertyDisplay">Palm Grove Apartments · Cedar Creek Complex</span></div>
                        <div><span class="font-semibold text-slate-600">Move‑out Date</span><br /><span class="text-slate-800 font-medium" id="moveoutDateDisplay">2026‑07‑15</span></div>
                        <div><span class="font-semibold text-slate-600">Security Deposit</span><br /><span class="text-slate-800 font-medium">$<span id="depositDisplay">2,500.00</span></span></div>
                        <div><span class="font-semibold text-slate-600">Final Refund</span><br /><span class="text-emerald-700 font-bold">$<span id="refundDisplay">1,850.00</span></span></div>
                    </div>
                    <div class="mt-5 p-4 bg-emerald-50/60 rounded-xl text-xs text-slate-600 border border-emerald-100/60 flex items-start gap-3">
                        <i class="fas fa-info-circle text-emerald-600 mt-0.5"></i>
                        <span>By signing below, the tenant acknowledges receipt of the move‑out inspection report, agrees to all final deduction amounts, and releases the property from any future claims.</span>
                    </div>
                </section>

                <!-- Agreement Terms -->
                <section class="glass-card rounded-2xl p-6 md:p-7 border border-white/60">
                    <h3 class="text-md font-bold flex items-center gap-2 text-slate-800 mb-3">
                        <i class="fas fa-gavel text-emerald-600"></i> Terms of Release
                    </h3>
                    <div class="space-y-2 text-sm text-slate-600 leading-relaxed">
                        <p>▪ The tenant has vacated the property in good condition, subject to the deductions outlined in the final inspection report.</p>
                        <p>▪ All outstanding utility bills, service charges, and rent arrears have been settled as of the move‑out date.</p>
                        <p>▪ The security deposit refund, after deductions, shall be processed within 14 business days via the bank account on file.</p>
                        <p>▪ This agreement constitutes a full and final release of all claims between the tenant and Mwaroki Estates.</p>
                    </div>
                </section>

                <!-- Signature Section -->
                <section class="glass-card rounded-2xl p-6 md:p-7 border border-white/60" id="signatureSection">
                    <div class="flex items-center justify-between flex-wrap gap-2 mb-4">
                        <h3 class="text-lg font-bold flex items-center gap-2 text-slate-800">
                            <i class="fas fa-pen-alt text-emerald-600"></i> Electronic Signature
                        </h3>
                        <span class="text-xs text-slate-400 bg-slate-50 px-3 py-1 rounded-full">Tenant / Guarantor</span>
                    </div>
                    <p class="text-sm text-slate-500 mb-4">Sign in the box below using your mouse, finger, or stylus. Your signature will be timestamped and securely stored.</p>

                    <div class="relative">
                        <canvas id="signatureCanvas" width="600" height="220" class="signature-canvas"></canvas>
                        <div id="signaturePlaceholder" class="absolute inset-0 flex items-center justify-center pointer-events-none text-slate-300 text-sm font-medium transition-opacity duration-300">
                            <span><i class="fas fa-pen-fancy mr-2"></i> Sign here …</span>
                        </div>
                    </div>

                    <div class="flex flex-wrap items-center justify-between gap-3 mt-4">
                        <div class="flex flex-wrap gap-2">
                            <button id="clearSignatureBtn" class="px-4 py-2 bg-slate-100 hover:bg-slate-200 rounded-xl text-slate-700 text-sm transition flex items-center gap-2">
                                <i class="fas fa-eraser"></i> Clear
                            </button>
                            <button id="undoSignatureBtn" class="px-4 py-2 bg-slate-50 hover:bg-slate-100 rounded-xl text-slate-600 text-sm transition flex items-center gap-2">
                                <i class="fas fa-undo-alt"></i> Undo
                            </button>
                        </div>
                        <div class="text-xs text-slate-400 flex items-center gap-1">
                            <i class="fas fa-lock text-emerald-600"></i> Encrypted · Audit‑logged
                        </div>
                    </div>
                </section>

                <!-- Upload Alternative -->
                <section class="glass-card rounded-2xl p-6 md:p-7 border border-white/60">
                    <h3 class="text-md font-bold flex items-center gap-2 text-slate-800 mb-3">
                        <i class="fas fa-cloud-upload-alt text-emerald-600"></i> Upload Signed Document
                        <span class="text-xs font-normal text-slate-400 ml-2">(optional)</span>
                    </h3>
                    <p class="text-sm text-slate-500 mb-3">If you already have a physically signed PDF or image, upload it here instead of drawing.</p>
                    <div class="flex flex-wrap items-center gap-4">
                        <label class="cursor-pointer bg-white border border-slate-200 hover:border-emerald-300 rounded-xl px-5 py-2.5 text-sm text-slate-700 transition shadow-sm hover:shadow">
                            <i class="fas fa-folder-open mr-2 text-emerald-600"></i> Choose file
                            <input type="file" id="signedDocUpload" accept=".pdf,.jpg,.jpeg,.png" class="hidden" />
                        </label>
                        <span id="uploadFileName" class="text-sm text-slate-400">No file selected</span>
                        <button id="clearUploadBtn" class="text-sm text-red-400 hover:text-red-600 underline transition">Clear</button>
                    </div>
                    <div id="uploadPreview" class="mt-3 hidden border rounded-xl p-3 bg-slate-50/70"></div>
                </section>
            </div>

            <!-- ─── RIGHT: Audit & Submit (2/5) ─── -->
            <div class="lg:col-span-2 space-y-6">

                <!-- Audit Trail -->
                <aside class="glass-card rounded-2xl p-6 border border-white/60">
                    <div class="flex items-center gap-2 border-b border-slate-100 pb-3 mb-3">
                        <i class="fas fa-history text-emerald-600"></i>
                        <h3 class="font-bold text-slate-800">Audit Trail</h3>
                        <span class="bg-emerald-100 text-emerald-700 text-[10px] font-semibold px-2 py-0.5 rounded-full ml-auto">Live</span>
                    </div>
                    <div id="auditLogContainer" class="audit-scroll space-y-1.5 text-xs">
                        <div class="border-l-4 border-emerald-300 pl-3 py-1.5 bg-emerald-50/40 rounded-r">📋 Move‑out agreement session started</div>
                    </div>
                    <button id="clearAuditBtn" class="text-xs text-slate-400 hover:text-red-400 transition mt-3 underline">Clear log</button>
                </aside>

                <!-- Submit Panel -->
                <aside class="glass-card rounded-2xl p-6 border border-white/60 bg-gradient-to-br from-white to-emerald-50/40">
                    <div class="flex items-center gap-2 mb-3">
                        <i class="fas fa-stamp text-2xl text-emerald-700"></i>
                        <h3 class="font-bold text-lg text-slate-800">Finalize &amp; Submit</h3>
                    </div>
                    <p class="text-sm text-slate-500 mb-4">Once signed and confirmed, this agreement becomes a legally binding offboarding record.</p>

                    <label class="flex items-start gap-3 text-sm text-slate-700 cursor-pointer mb-5">
                        <input type="checkbox" id="confirmCheckbox" class="mt-0.5 rounded border-slate-300 text-emerald-700 focus:ring-emerald-500 w-4 h-4" />
                        <span>I confirm that all information is accurate and the signature is authentic.</span>
                    </label>

                    <button id="submitAgreementBtn" class="btn-primary w-full text-white py-3.5 rounded-xl font-semibold flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed transition">
                        <i class="fas fa-signature"></i> Submit Move‑out Agreement
                    </button>

                    <div class="mt-4 text-center text-[11px] text-slate-400 flex items-center justify-center gap-2">
                        <i class="fas fa-shield-alt text-emerald-500"></i>
                        Digitally signed &amp; timestamped for RBC audit
                    </div>
                </aside>

                <!-- Quick Info -->
                <aside class="glass-card rounded-2xl p-5 border border-white/60 bg-amber-50/30">
                    <div class="flex items-start gap-3 text-xs text-slate-600">
                        <i class="fas fa-life-ring text-amber-600 mt-0.5"></i>
                        <div>
                            <span class="font-semibold">Need help?</span> Contact the estate office at
                            <span class="font-medium text-slate-800">+254 700 123 456</span> or
                            <span class="font-medium text-slate-800">support@mwaroki.co.ke</span>
                        </div>
                    </div>
                </aside>
            </div>
        </div>

        <!-- ═══ FOOTER ═══ -->
        <footer class="mt-12 text-center text-xs text-slate-400 border-t border-slate-200/60 pt-6">
            <p>© 2026 Mwaroki Estates · All rights reserved · Document version 2.4 · RBC‑compliant offboarding</p>
        </footer>
    </div>

    <!-- ═══ SUCCESS MODAL ═══ -->
    <div id="successModal" class="fixed inset-0 modal-overlay flex items-center justify-center z-50 hidden transition-all">
        <div class="modal-box bg-white rounded-3xl max-w-md w-full mx-4 p-8 shadow-2xl border border-white/60">
            <div class="text-center">
                <div class="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-5 shadow-lg shadow-emerald-500/20">
                    <i class="fas fa-check-circle text-emerald-600 text-4xl"></i>
                </div>
                <h3 class="text-2xl font-bold text-slate-800">Agreement Signed</h3>
                <p class="text-slate-500 mt-2 text-sm leading-relaxed">The move‑out agreement has been recorded in the offboarding vault. A copy has been sent to the tenant's registered email.</p>
                <div class="mt-6 flex gap-3 justify-center">
                    <button id="closeModalBtn" class="bg-emerald-700 hover:bg-emerald-800 text-white px-6 py-2.5 rounded-xl font-medium transition shadow-lg shadow-emerald-700/20">
                        Close
                    </button>
                    <button id="printModalBtn" class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-6 py-2.5 rounded-xl font-medium transition">
                        <i class="fas fa-print mr-2"></i> Print
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  STATE
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        const state = {
            tenantName: "Grace Wanjiku",
            leaseId: "MWK‑LE‑2391",
            properties: "Palm Grove Apartments · Cedar Creek Complex",
            moveOutDate: "2026‑07‑15",
            deposit: 2500.00,
            finalRefund: 1850.00,
            signatureDataURL: null,
            uploadedFile: null, // { name, dataURL, type }
            signedAt: null,
            isSubmitted: false,
            auditLogs: [
                { timestamp: new Date(), message: "📋 Move‑out agreement session started", type: "info" }
            ]
        };

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  DOM REFS
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        const $ = id => document.getElementById(id);
        const canvas = $("signatureCanvas");
        const placeholder = $("signaturePlaceholder");
        const auditContainer = $("auditLogContainer");
        const confirmCheckbox = $("confirmCheckbox");
        const submitBtn = $("submitAgreementBtn");
        const modal = $("successModal");
        const closeModalBtn = $("closeModalBtn");
        const printModalBtn = $("printModalBtn");

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  SIGNATURE PAD
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        let signaturePad = null;
        let signatureHistory = [];

        function initSignaturePad() {
            if (!canvas) return;
            signaturePad = new SignaturePad(canvas, {
                backgroundColor: "rgb(250, 252, 250)",
                penColor: "#1a4a3a",
                throttle: 14,
                minWidth: 1.2,
                maxWidth: 3.2,
                dotSize: 2.5
            });

            // Toggle placeholder
            signaturePad.addEventListener("beginStroke", () => {
                placeholder?.classList.add("opacity-0");
            });
            signaturePad.addEventListener("endStroke", () => {
                if (signaturePad.isEmpty()) {
                    placeholder?.classList.remove("opacity-0");
                } else {
                    signatureHistory.push(signaturePad.toDataURL());
                    if (signatureHistory.length > 12) signatureHistory.shift();
                    addAuditLog("✍️ Signature stroke added");
                    updateStep(2);
                }
            });

            // Clear
            $("clearSignatureBtn")?.addEventListener("click", () => {
                signaturePad.clear();
                signatureHistory = [];
                state.signatureDataURL = null;
                placeholder?.classList.remove("opacity-0");
                addAuditLog("🧹 Signature cleared");
                updateStep(1);
            });

            // Undo
            $("undoSignatureBtn")?.addEventListener("click", () => {
                if (signatureHistory.length > 0) {
                    const prev = signatureHistory.pop();
                    const img = new Image();
                    img.onload = () => {
                        signaturePad.clear();
                        signaturePad.fromDataURL(prev);
                        state.signatureDataURL = signaturePad.toDataURL();
                        if (!signaturePad.isEmpty()) placeholder?.classList.add("opacity-0");
                        else placeholder?.classList.remove("opacity-0");
                        addAuditLog("↩️ Undo last stroke");
                    };
                    img.src = prev;
                } else {
                    signaturePad.clear();
                    state.signatureDataURL = null;
                    placeholder?.classList.remove("opacity-0");
                }
            });

            // Canvas focus ring
            canvas.addEventListener("focus", () => canvas.classList.add("active"));
            canvas.addEventListener("blur", () => canvas.classList.remove("active"));
        }

        function captureSignature() {
            if (signaturePad && !signaturePad.isEmpty()) {
                state.signatureDataURL = signaturePad.toDataURL();
                return true;
            }
            return false;
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  AUDIT
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        function addAuditLog(message, type = "info") {
            state.auditLogs.unshift({ timestamp: new Date(), message, type });
            renderAuditLog();
        }

        function renderAuditLog() {
            if (!auditContainer) return;
            const items = state.auditLogs.slice(0, 25);
            auditContainer.innerHTML = items.map(log => {
                const border = log.type === "error" ? "border-red-400" : "border-emerald-300";
                const bg = log.type === "error" ? "bg-red-50/40" : "bg-emerald-50/40";
                return `
              <div class="border-l-4 ${border} pl-3 py-1.5 ${bg} rounded-r text-slate-700">
                <span class="text-slate-400 text-[10px] font-mono">${log.timestamp.toLocaleTimeString()}</span>
                <span class="ml-2">${log.message}</span>
              </div>
            `;
            }).join("");
            // Auto-scroll
            auditContainer.scrollTop = 0;
        }

        $("clearAuditBtn")?.addEventListener("click", () => {
            state.auditLogs = [{ timestamp: new Date(), message: "🧹 Audit trail cleared", type: "info" }];
            renderAuditLog();
            addAuditLog("Audit log manually reset");
        });

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  STEPS
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        function updateStep(step) {
            const dots = document.querySelectorAll(".step-dot");
            const lines = document.querySelectorAll(".step-line");
            dots.forEach((dot, i) => {
                const num = i + 1;
                dot.classList.remove("active", "completed");
                if (num === step) dot.classList.add("active");
                else if (num < step) dot.classList.add("completed");
            });
            lines.forEach((line, i) => {
                const num = i + 1;
                line.classList.toggle("completed", num < step);
            });
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  UPLOAD
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        function handleFileUpload(file) {
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (e) => {
                state.uploadedFile = {
                    name: file.name,
                    dataURL: e.target.result,
                    type: file.type
                };
                $("uploadFileName").innerText = file.name;
                const preview = $("uploadPreview");
                if (file.type.startsWith("image/")) {
                    preview.innerHTML =
                        `<img src="${e.target.result}" class="max-h-32 rounded-xl border border-slate-200 shadow-sm" />`;
                    preview.classList.remove("hidden");
                } else if (file.type === "application/pdf") {
                    preview.innerHTML =
                        `<div class="flex items-center gap-3"><i class="fas fa-file-pdf text-red-500 text-3xl"></i><span class="text-sm font-medium">${file.name}</span></div>`;
                    preview.classList.remove("hidden");
                } else {
                    preview.innerHTML =
                        `<div class="flex items-center gap-3"><i class="fas fa-file text-slate-400 text-2xl"></i><span class="text-sm">${file.name}</span></div>`;
                    preview.classList.remove("hidden");
                }
                addAuditLog(`📎 Uploaded signed document: ${file.name}`);
                updateStep(2);
            };
            reader.readAsDataURL(file);
        }

        function clearUpload() {
            state.uploadedFile = null;
            $("uploadFileName").innerText = "No file selected";
            const preview = $("uploadPreview");
            preview.classList.add("hidden");
            preview.innerHTML = "";
            $("signedDocUpload").value = "";
            addAuditLog("🗑️ Cleared uploaded document");
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  SUBMIT (modified to call backend)
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        async function submitAgreement() {
            if (state.isSubmitted) return;

            const confirmed = confirmCheckbox.checked;
            const hasSignature = signaturePad && !signaturePad.isEmpty();
            const hasUpload = state.uploadedFile !== null;

            if (!hasSignature && !hasUpload) {
                alert("Please provide either an electronic signature or upload a signed agreement document.");
                addAuditLog("❌ Submission failed: no signature or document", "error");
                return;
            }
            if (!confirmed) {
                alert("You must confirm the accuracy and authenticity of the agreement.");
                addAuditLog("❌ Submission failed: confirmation not checked", "error");
                return;
            }

            // Capture signature if drawn
            if (hasSignature) captureSignature();

            // Prepare payload
            const payload = {
                tenant_name: state.tenantName,
                lease_id: state.leaseId,
                properties: state.properties,
                move_out_date: state.moveOutDate,
                deposit: state.deposit,
                final_refund: state.finalRefund,
                signature_data_url: state.signatureDataURL || null,
                uploaded_file: state.uploadedFile ? state.uploadedFile.dataURL : null,
                confirm: confirmed
            };

            try {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';
                const response = await fetch('/api/submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const result = await response.json();
                if (response.ok) {
                    state.isSubmitted = true;
                    state.signedAt = new Date();
                    addAuditLog(`✅ AGREEMENT SIGNED · ID: ${result.id}`);
                    addAuditLog(`📄 PDF generated and email sent (if configured)`);
                    // Show modal
                    modal.classList.remove("hidden");
                    updateStep(3);
                    // Disable further edits
                    document.querySelectorAll("#signatureSection .signature-canvas, #signatureSection button, #signedDocUpload, #clearUploadBtn").forEach(el => {
                        el.style.opacity = "0.6";
                        el.style.pointerEvents = "none";
                    });
                    submitBtn.innerHTML = '<i class="fas fa-check"></i> Submitted';
                    submitBtn.disabled = true;
                } else {
                    alert(`Error: ${result.detail || 'Submission failed'}`);
                    addAuditLog(`❌ Submission error: ${result.detail}`, "error");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-signature"></i> Submit Move‑out Agreement';
                }
            } catch (err) {
                alert(`Network error: ${err.message}`);
                addAuditLog(`❌ Network error: ${err.message}`, "error");
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-signature"></i> Submit Move‑out Agreement';
            }
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  MODAL
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        function closeModal() {
            modal.classList.add("hidden");
        }

        function printAgreement() {
            window.print();
        }

        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        //  INIT
        // ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        document.addEventListener("DOMContentLoaded", () => {
            // Display data from state
            $("tenantNameDisplay").innerText = state.tenantName;
            $("leaseIdDisplay").innerText = state.leaseId;
            $("propertyDisplay").innerText = state.properties;
            $("moveoutDateDisplay").innerText = state.moveOutDate;
            $("depositDisplay").innerText = state.deposit.toFixed(2);
            $("refundDisplay").innerText = state.finalRefund.toFixed(2);

            initSignaturePad();
            renderAuditLog();
            updateStep(1);

            // Upload
            const fileInput = $("signedDocUpload");
            document.querySelector("label[for='signedDocUpload']")?.addEventListener("click", (e) => {
                e.preventDefault();
                fileInput.click();
            });
            fileInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                }
            });
            $("clearUploadBtn")?.addEventListener("click", clearUpload);

            // Submit
            submitBtn.addEventListener("click", submitAgreement);

            // Modal
            closeModalBtn.addEventListener("click", closeModal);
            printModalBtn.addEventListener("click", printAgreement);
            modal.addEventListener("click", (e) => {
                if (e.target === modal) closeModal();
            });

            // Keyboard shortcut: Escape closes modal
            document.addEventListener("keydown", (e) => {
                if (e.key === "Escape" && !modal.classList.contains("hidden")) closeModal();
            });
        });
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)

@app.post("/api/submit", response_model=AgreementResponse, status_code=status.HTTP_201_CREATED)
async def submit_agreement(
    agreement_data: AgreementCreate,
    db: Session = Depends(get_db)
):
    """
    Submit the signed move-out agreement.
    Accepts signature (data URL) and/or uploaded document (base64).
    Creates a database record, saves files, generates PDF, and sends email.
    """
    # Validate: must have signature or uploaded file
    if not agreement_data.signature_data_url and not agreement_data.uploaded_file:
        raise HTTPException(status_code=400, detail="Either signature or uploaded document is required.")

    # Generate unique ID
    agreement_id = str(uuid.uuid4())

    # Create agreement record
    agreement = Agreement(
        id=agreement_id,
        tenant_name=agreement_data.tenant_name,
        lease_id=agreement_data.lease_id,
        properties=agreement_data.properties,
        move_out_date=agreement_data.move_out_date,
        deposit=agreement_data.deposit,
        final_refund=agreement_data.final_refund,
        signed_at=datetime.utcnow(),
        status="signed"
    )

    # Save signature if provided
    signature_path = None
    if agreement_data.signature_data_url:
        try:
            signature_path = save_signature(agreement_data.signature_data_url, agreement_id)
            agreement.signature_path = signature_path
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid signature: {str(e)}")

    # Save uploaded file if provided
    uploaded_path = None
    if agreement_data.uploaded_file:
        # Decode base64 content
        try:
            # Expect data URL format: data:...;base64,...
            pattern = r"^data:([^;]+);base64,(.+)$"
            match = re.match(pattern, agreement_data.uploaded_file)
            if not match:
                raise ValueError("Invalid file data URL")
            mime_type = match.group(1)
            file_data = match.group(2)
            file_bytes = base64.b64decode(file_data)
            # Determine extension from mime type
            ext_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "application/pdf": ".pdf"
            }
            ext = ext_map.get(mime_type, ".bin")
            file_name = f"document_{agreement_id}{ext}"
            uploaded_path = save_uploaded_file(file_bytes, file_name, agreement_id)
            agreement.uploaded_doc_path = uploaded_path
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid uploaded file: {str(e)}")

    # Save to database
    db.add(agreement)

    # Add audit log
    audit_msg = f"Agreement {agreement_id} created with signature and uploaded document" if (signature_path and uploaded_path) else \
                f"Agreement {agreement_id} created with signature" if signature_path else \
                f"Agreement {agreement_id} created with uploaded document"
    audit = AuditLog(agreement_id=agreement_id, message=audit_msg, log_type="success")
    db.add(audit)

    db.commit()
    db.refresh(agreement)

    # Generate PDF
    try:
        pdf_buffer = generate_pdf(agreement, signature_path, uploaded_path)
        # Save PDF to disk (optional)
        pdf_dir = "uploads/pdfs"
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_path = os.path.join(pdf_dir, f"{agreement_id}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_buffer.getvalue())

        # Send email (to tenant's email - we don't have email in form, use a placeholder)
        # In real app, you would have tenant email field. For now, use admin email.
        if SMTP_USER and SMTP_PASS:
            # Use a dummy recipient or fetch from tenant data; here we use admin email
            send_email(ADMIN_EMAIL, agreement_id, pdf_buffer)
        else:
            logger.info("Email not sent: SMTP credentials missing.")
    except Exception as e:
        logger.error(f"PDF/Email generation failed: {e}")
        # Still return success but log error
        db.add(AuditLog(agreement_id=agreement_id, message=f"PDF/Email error: {str(e)}", log_type="error"))
        db.commit()

    return AgreementResponse(
        id=agreement_id,
        status=agreement.status,
        signed_at=agreement.signed_at,
        message="Agreement submitted successfully."
    )

@app.get("/api/agreements/{agreement_id}", response_model=dict)
async def get_agreement(agreement_id: str, db: Session = Depends(get_db)):
    """Retrieve a specific agreement by ID."""
    agreement = db.query(Agreement).filter(Agreement.id == agreement_id).first()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    return {
        "id": agreement.id,
        "tenant_name": agreement.tenant_name,
        "lease_id": agreement.lease_id,
        "properties": agreement.properties,
        "move_out_date": agreement.move_out_date,
        "deposit": agreement.deposit,
        "final_refund": agreement.final_refund,
        "signed_at": agreement.signed_at.isoformat() if agreement.signed_at else None,
        "status": agreement.status,
        "created_at": agreement.created_at.isoformat()
    }

@app.get("/api/audit/{agreement_id}", response_model=List[AuditLogResponse])
async def get_audit_logs(agreement_id: str, db: Session = Depends(get_db)):
    """Retrieve audit logs for a specific agreement."""
    logs = db.query(AuditLog).filter(AuditLog.agreement_id == agreement_id).order_by(AuditLog.timestamp.desc()).all()
    return logs

@app.get("/api/download-pdf/{agreement_id}")
async def download_pdf(agreement_id: str, db: Session = Depends(get_db)):
    """Download the generated PDF for an agreement."""
    agreement = db.query(Agreement).filter(Agreement.id == agreement_id).first()
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    pdf_path = f"uploads/pdfs/{agreement_id}.pdf"
    if not os.path.exists(pdf_path):
        # Regenerate PDF if missing
        try:
            pdf_buffer = generate_pdf(agreement, agreement.signature_path, agreement.uploaded_doc_path)
            with open(pdf_path, "wb") as f:
                f.write(pdf_buffer.getvalue())
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Could not generate PDF: {str(e)}")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"agreement_{agreement_id}.pdf")

# ------------------------------
# Run with: uvicorn app:app --reload
# ------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
```
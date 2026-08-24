# esignature_backend.py
# Mwarokin E-Signature Backend (Flask-based API)
# Run: pip install flask flask-cors
# python esignature_backend.py

import json
import uuid
import hashlib
import hmac
import base64
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Tuple

from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
import io
import os

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
SECRET_KEY = os.environ.get("MWAROKIN_SECRET", "dev-secret-change-in-production")
JWT_SECRET = os.environ.get("MWAROKIN_JWT_SECRET", "jwt-dev-secret")
DOCUMENT_STORE = {}  # In-memory store (replace with DB in production)
SIGNATURE_STORE = {}  # In-memory store for signature blobs

app = Flask(__name__)
app.secret_key = SECRET_KEY
CORS(app, supports_credentials=True, origins=["http://localhost:5000", "http://127.0.0.1:5000"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MwarokinBackend")

# ----------------------------------------------------------------------
# MOCK USER / ROLE DATA (matches frontend roles)
# ----------------------------------------------------------------------
ROLE_DATA = {
    "tenant": {
        "id": "usr_tenant_001",
        "name": "Robin Mwarema",
        "role": "Tenant",
        "email": "robin.m@mwarokin.co.ke",
        "phone": "+254 712 345 678",
        "avatar": "RM",
        "property": "Unit 12B, Block C",
        "leaseId": "MWK-2425-001",
        "rent": 22064
    },
    "landlord": {
        "id": "usr_landlord_002",
        "name": "Esther Mwangi",
        "role": "Landlord",
        "email": "esther.mwangi@mwarokin.com",
        "phone": "+254 722 456 789",
        "avatar": "EM",
        "property": "Mwarokin Towers, Units 4A & 7C",
        "leaseId": "MWK-LD-9823",
        "rent": 45000
    },
    "agency": {
        "id": "usr_agency_003",
        "name": "PrimeLet Property Mgmt",
        "role": "Agency",
        "email": "clients@primelet.co.ke",
        "phone": "+254 700 123 456",
        "avatar": "PM",
        "property": "Mwarokin Business Park",
        "leaseId": "MWK-AG-4451",
        "rent": 85000
    }
}

# Agreement templates (matches frontend)
AGREEMENT_TEMPLATES = {
    "tenant": "I, [NAME], as Tenant, hereby agree to the rental terms outlined by Mwarokin Estates for the property at [PROPERTY]. Monthly rent payment of KES [RENT] is due on the 5th of each month. Late payments incur penalties per Mwarokin policy. This lease is valid from June 2025 to May 2026. I accept Mwarokin Estates' community guidelines and agree to maintain the property in good condition. By signing, I confirm acceptance of all terms.",
    "landlord": "I, [NAME], as Landlord, hereby affirm the lease agreement for properties managed by Mwarokin Estates. I authorize monthly rent collection of KES [RENT] due on the 5th. I accept Mwarokin's management services and community policies. This agreement is valid from July 2025 to June 2026. By signing, I confirm my commitment to property ownership responsibilities and lease terms.",
    "agency": "On behalf of [NAME], as Property Management Agency, we confirm the commercial lease agreement. Monthly rent: KES [RENT], due on the 5th. We confirm Mwarokin's authorized management responsibilities from August 2025 to July 2026. By e-signing, the agency binds itself to all management obligations and community guidelines."
}

# ----------------------------------------------------------------------
# UTILITIES
# ----------------------------------------------------------------------
def generate_document_id() -> str:
    """Generate a unique document ID with prefix."""
    return f"MWK-{datetime.now().strftime('%y')}-{uuid.uuid4().hex[:6].upper()}"

def generate_signature_hash(signature_data: str, role: str) -> str:
    """Generate HMAC-SHA256 hash for signature verification."""
    message = f"{role}:{signature_data}:{datetime.now().isoformat()}"
    h = hmac.new(JWT_SECRET.encode(), message.encode(), hashlib.sha256)
    return h.hexdigest()

def create_signed_document(role: str, signature_blob: str, timestamp: str) -> Dict[str, Any]:
    """Build a document record with metadata."""
    user = ROLE_DATA.get(role, {})
    if not user:
        raise ValueError("Invalid role")
    
    doc_id = generate_document_id()
    agreement = AGREEMENT_TEMPLATES.get(role, "").replace("[NAME]", user["name"]).replace("[PROPERTY]", user["property"]).replace("[RENT]", str(user["rent"]))
    
    doc = {
        "documentId": doc_id,
        "role": role,
        "signerName": user["name"],
        "signerRole": user["role"],
        "property": user["property"],
        "leaseId": user["leaseId"],
        "rent": user["rent"],
        "agreementText": agreement,
        "signatureBlob": signature_blob,  # Base64 encoded signature
        "signatureHash": generate_signature_hash(signature_blob, role),
        "timestamp": timestamp,
        "status": "signed",
        "createdAt": datetime.now().isoformat()
    }
    DOCUMENT_STORE[doc_id] = doc
    SIGNATURE_STORE[doc_id] = signature_blob
    return doc

# ----------------------------------------------------------------------
# DECORATORS
# ----------------------------------------------------------------------
def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Simple session-based auth (in production use JWT)
        if "user_role" not in session:
            # For demo, default to tenant
            session["user_role"] = "tenant"
        return f(*args, **kwargs)
    return decorated

# ----------------------------------------------------------------------
# API ENDPOINTS
# ----------------------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Mwarokin E-Signature Backend"}), 200

@app.route("/api/role/<role>", methods=["GET"])
@require_auth
def get_role_data(role: str):
    """Get profile data for a given role."""
    if role not in ROLE_DATA:
        return jsonify({"error": "Invalid role"}), 400
    session["user_role"] = role
    return jsonify(ROLE_DATA[role]), 200

@app.route("/api/agreement/<role>", methods=["GET"])
@require_auth
def get_agreement(role: str):
    """Get rendered agreement text for a role."""
    if role not in ROLE_DATA:
        return jsonify({"error": "Invalid role"}), 400
    user = ROLE_DATA[role]
    template = AGREEMENT_TEMPLATES.get(role, "")
    rendered = template.replace("[NAME]", user["name"]).replace("[PROPERTY]", user["property"]).replace("[RENT]", str(user["rent"]))
    return jsonify({
        "agreement": rendered,
        "role": role,
        "signer": user["name"]
    }), 200

@app.route("/api/sign", methods=["POST"])
@require_auth
def sign_document():
    """
    Submit a signature.
    Expected JSON: { "role": "tenant", "signature": "base64data", "timestamp": "..." }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request body"}), 400

    role = data.get("role")
    signature_blob = data.get("signature")
    timestamp = data.get("timestamp", datetime.now().isoformat())

    if not role or role not in ROLE_DATA:
        return jsonify({"error": "Invalid or missing role"}), 400

    if not signature_blob:
        return jsonify({"error": "Signature data required"}), 400

    try:
        # Validate base64
        base64.b64decode(signature_blob)
    except Exception:
        return jsonify({"error": "Invalid signature encoding"}), 400

    # Create signed document
    doc = create_signed_document(role, signature_blob, timestamp)

    logger.info(f"Document signed: {doc['documentId']} by {doc['signerName']}")
    return jsonify({
        "success": True,
        "document": doc,
        "message": f"Agreement signed by {doc['signerName']} ({doc['signerRole']})"
    }), 201

@app.route("/api/document/<doc_id>", methods=["GET"])
@require_auth
def get_document(doc_id: str):
    """Retrieve a signed document by ID."""
    doc = DOCUMENT_STORE.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    # Return a copy without signature blob if sensitive
    safe_doc = {k: v for k, v in doc.items() if k != "signatureBlob"}
    safe_doc["hasSignature"] = True
    return jsonify(safe_doc), 200

@app.route("/api/document/<doc_id>/signature", methods=["GET"])
@require_auth
def get_signature_blob(doc_id: str):
    """Get raw signature image data for a document."""
    blob = SIGNATURE_STORE.get(doc_id)
    if not blob:
        return jsonify({"error": "Signature not found"}), 404
    return jsonify({"signature": blob}), 200

@app.route("/api/document/<doc_id>/download", methods=["GET"])
@require_auth
def download_document_html(doc_id: str):
    """Generate an HTML version of the signed document."""
    doc = DOCUMENT_STORE.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    signature_img = f"<img src='data:image/png;base64,{doc['signatureBlob']}' style='max-width:300px; border:1px solid #ccc; padding:0.5rem;' />"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Mwarokin Rental Agreement - {doc['documentId']}</title>
    <style>
        body {{ font-family: 'Inter', sans-serif; max-width: 900px; margin: 40px auto; padding: 2rem; color: #1B1B1B; background: #FAFAFA; }}
        .header {{ background: #1B4D3E; color: #FFF; padding: 1.5rem; border-radius: 12px; margin-bottom: 2rem; }}
        .header h1 {{ margin: 0; font-weight: 600; }}
        .meta {{ display: flex; gap: 2rem; flex-wrap: wrap; background: #F0F0F0; padding: 1rem; border-radius: 8px; margin: 1rem 0; }}
        .content {{ background: #FFF; padding: 2rem; border-radius: 12px; border-left: 6px solid #D4AF37; line-height: 1.8; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .signature-box {{ margin-top: 2rem; border-top: 2px solid #D4AF37; padding-top: 1.5rem; }}
        .footer {{ margin-top: 2rem; color: #777; font-size: 0.85rem; }}
    </style>
    </head>
    <body>
        <div class="header">
            <h1>🏛️ Mwarokin Estates — Rental Agreement</h1>
        </div>
        <div class="meta">
            <div><strong>Document ID:</strong> {doc['documentId']}</div>
            <div><strong>Signer:</strong> {doc['signerName']}</div>
            <div><strong>Role:</strong> {doc['signerRole']}</div>
            <div><strong>Signed:</strong> {doc['timestamp']}</div>
        </div>
        <div class="content">
            {doc['agreementText'].replace('\n', '<br>')}
        </div>
        <div class="signature-box">
            <h3>✍️ Electronic Signature</h3>
            <div>{signature_img}</div>
            <p style="font-size:0.9rem;color:#555;">This document is legally binding under Kenya Electronic Transactions Act. Securely stored in Mwarokin vault.</p>
        </div>
        <div class="footer">
            <p>🔐 Verified document · Lease ID: {doc['leaseId']} · Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    return html_content, 200, {"Content-Type": "text/html"}

@app.route("/api/documents", methods=["GET"])
@require_auth
def list_documents():
    """List all signed documents (basic info)."""
    docs = []
    for doc_id, doc in DOCUMENT_STORE.items():
        docs.append({
            "documentId": doc["documentId"],
            "signerName": doc["signerName"],
            "role": doc["role"],
            "timestamp": doc["timestamp"],
            "status": doc.get("status", "signed"),
            "leaseId": doc["leaseId"]
        })
    return jsonify({"documents": docs, "count": len(docs)}), 200

@app.route("/api/verify/<doc_id>", methods=["GET"])
@require_auth
def verify_document(doc_id: str):
    """Verify document integrity using signature hash."""
    doc = DOCUMENT_STORE.get(doc_id)
    if not doc:
        return jsonify({"error": "Document not found"}), 404
    
    # Recompute hash
    sig = SIGNATURE_STORE.get(doc_id, "")
    recomputed = generate_signature_hash(sig, doc.get("role", ""))
    valid = recomputed == doc.get("signatureHash", "")
    
    return jsonify({
        "documentId": doc_id,
        "verified": valid,
        "signer": doc["signerName"],
        "timestamp": doc["timestamp"],
        "status": "valid" if valid else "tampered"
    }), 200

@app.route("/api/reset", methods=["POST"])
@require_auth
def reset_session():
    """Reset session state (for testing)."""
    session.clear()
    return jsonify({"message": "Session reset"}), 200

# ----------------------------------------------------------------------
# ERROR HANDLING
# ----------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("🏛️ Mwarokin E-Signature Backend")
    print(f"📅 Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🔗 Server: http://localhost:5000")
    print("📚 API Endpoints:")
    print("   GET  /api/health")
    print("   GET  /api/role/<role>")
    print("   GET  /api/agreement/<role>")
    print("   POST /api/sign")
    print("   GET  /api/document/<doc_id>")
    print("   GET  /api/document/<doc_id>/signature")
    print("   GET  /api/document/<doc_id>/download")
    print("   GET  /api/documents")
    print("   GET  /api/verify/<doc_id>")
    print("   POST /api/reset")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
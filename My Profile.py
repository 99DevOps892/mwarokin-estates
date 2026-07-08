```python
#!/usr/bin/env python3
"""
Mwarokin Estates - Profile Management Backend

A modern, professional Flask-based API for the property rental platform.
Provides full CRUD operations for user profiles, settings, and account management.

Features:
- User authentication (session-based)
- Profile management (personal info, bio, location, occupation, pronouns)
- Language preferences
- Interests and lifestyle tags
- Notification preferences
- Linked accounts (OAuth placeholders)
- Account status and privacy settings
- Tenant-specific fields (income, employment, budget)
- Danger zone actions (pause, export, delete)
- Activity timeline
- QR code generation (dummy)
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

from flask import Flask, request, jsonify, session, render_template_string
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from pydantic import BaseModel, Field, ValidationError, EmailStr, constr
from pydantic.dataclasses import dataclass as pydantic_dataclass

# ============================================================================
# Configuration
# ============================================================================
app = Flask(__name__)
app.secret_key = "Mwarokin-Super-Secret-Key-Change-In-Production"
CORS(app, supports_credentials=True)

# ============================================================================
# Data Models (Pydantic)
# ============================================================================

class Pronouns(str, Enum):
    HE_HIM = "He / Him"
    SHE_HER = "She / Her"
    THEY_THEM = "They / Them"
    ZE_ZIR = "Ze / Zir"
    PREFER_NOT = "Prefer not to say"

class AccountStatus(str, Enum):
    ACTIVE = "Active — visible to all"
    DND = "Do not disturb"
    PRIVATE = "Private mode"
    AWAY = "Away"

class NotificationPrefs(BaseModel):
    new_property_matches: bool = True
    payment_reminders: bool = True
    neighbourhood_alerts: bool = True
    promotional_offers: bool = False
    review_requests: bool = True
    email_digest: bool = False

class ProfileBase(BaseModel):
    first_name: constr(min_length=1, max_length=50)
    last_name: constr(min_length=1, max_length=50)
    display_name: constr(min_length=1, max_length=30)
    email: EmailStr
    phone: constr(min_length=5, max_length=20)
    date_of_birth: Optional[str] = None  # ISO date string
    bio: Optional[constr(max_length=280)] = None
    location: Optional[str] = None
    occupation: Optional[str] = None
    pronouns: Pronouns = Pronouns.PREFER_NOT

class TenantProfile(BaseModel):
    monthly_income: Optional[int] = None
    employment_status: str = "Employed full-time"
    preferred_property_type: str = "Apartment"
    max_budget: Optional[int] = None

class PrivacySettings(BaseModel):
    who_can_view: str = "Everyone"
    who_can_message: str = "Verified users"
    show_location: str = "City only"
    show_activity_status: str = "Everyone"
    two_factor_auth: bool = True
    profile_indexing: bool = False

class LinkedAccount(BaseModel):
    platform: str
    username: Optional[str] = None
    connected: bool = False

class UserProfile(ProfileBase):
    user_id: str
    created_at: datetime
    updated_at: datetime
    tenant_profile: TenantProfile = Field(default_factory=TenantProfile)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    notifications: NotificationPrefs = Field(default_factory=NotificationPrefs)
    account_status: AccountStatus = AccountStatus.ACTIVE
    language: str = "English (Kenya)"
    interests: List[str] = Field(default_factory=list)
    linked_accounts: List[LinkedAccount] = Field(default_factory=list)
    activity: List[Dict[str, Any]] = Field(default_factory=list)

# ============================================================================
# In-Memory Database (for demonstration)
# ============================================================================
USERS: Dict[str, Dict[str, Any]] = {}

def create_default_user():
    """Create a default user profile if none exists."""
    user_id = "user-1"
    if user_id not in USERS:
        profile = {
            "user_id": user_id,
            "first_name": "Robin",
            "last_name": "Kamau",
            "display_name": "robin.kamau",
            "email": "robin@mwarokin.com",
            "phone": "+254 704 919 388",
            "date_of_birth": "1990-06-15",
            "bio": "Urban professional seeking quality housing in Nairobi. I value quiet, clean spaces and am always a respectful, on-time tenant. Huge fan of Swahili architecture and local community life.",
            "location": "Nairobi, Kenya",
            "occupation": "Technology Entrepreneur",
            "pronouns": Pronouns.HE_HIM.value,
            "tenant_profile": {
                "monthly_income": 250000,
                "employment_status": "Employed full-time",
                "preferred_property_type": "Apartment",
                "max_budget": 90000
            },
            "privacy": {
                "who_can_view": "Everyone",
                "who_can_message": "Verified users",
                "show_location": "City only",
                "show_activity_status": "Everyone",
                "two_factor_auth": True,
                "profile_indexing": False
            },
            "notifications": {
                "new_property_matches": True,
                "payment_reminders": True,
                "neighbourhood_alerts": True,
                "promotional_offers": False,
                "review_requests": True,
                "email_digest": False
            },
            "account_status": AccountStatus.ACTIVE.value,
            "language": "English (Kenya)",
            "interests": [
                "Modern architecture", "Green spaces", "Public transport access",
                "Cycling", "Smart home", "Parking"
            ],
            "linked_accounts": [
                {"platform": "Facebook", "username": "robin.kamau", "connected": True},
                {"platform": "X (Twitter)", "username": None, "connected": False},
                {"platform": "Instagram", "username": "@robin_k", "connected": True},
                {"platform": "Spotify", "username": None, "connected": False},
                {"platform": "Google", "username": "robin@gmail.com", "connected": True}
            ],
            "activity": [
                {"text": "Applied for 3-bedroom in Kilimani", "time": "2 hrs ago", "type": "apply"},
                {"text": "Saved Luxury Villa in Karen to wishlist", "time": "Yesterday", "type": "save"},
                {"text": "Reviewed Westlands apartment — 5 stars", "time": "3 days ago", "type": "review"},
                {"text": "Paid KSh 45,000 rent via M-Pesa", "time": "1 week ago", "type": "payment"},
                {"text": "Updated profile photo and bio", "time": "2 weeks ago", "type": "update"}
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        USERS[user_id] = profile
    return USERS[user_id]

create_default_user()

# ============================================================================
# Utility Functions
# ============================================================================

def get_current_user() -> Optional[str]:
    """Return the current logged-in user ID from session."""
    return session.get("user_id", "user-1")  # Default to demo user

def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve user profile by ID."""
    return USERS.get(user_id)

def update_user_profile(user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update user profile with validation."""
    profile = get_user_profile(user_id)
    if not profile:
        raise ValueError("User not found")

    # Update allowed fields
    for key, value in data.items():
        if key in profile and key not in ("user_id", "created_at", "updated_at"):
            profile[key] = value
    profile["updated_at"] = datetime.now().isoformat()
    USERS[user_id] = profile
    return profile

# ============================================================================
# Authentication (Dummy)
# ============================================================================

@app.route("/api/auth/login", methods=["POST"])
def login():
    """Dummy login - sets session."""
    # In real app, validate credentials
    session["user_id"] = "user-1"
    return jsonify({"status": "success", "message": "Logged in"}), 200

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    """Logout - clear session."""
    session.pop("user_id", None)
    return jsonify({"status": "success", "message": "Logged out"}), 200

# ============================================================================
# Profile API Endpoints
# ============================================================================

@app.route("/api/profile", methods=["GET"])
def get_profile():
    """Get current user's full profile."""
    user_id = get_current_user()
    profile = get_user_profile(user_id)
    if not profile:
        return jsonify({"error": "User not found"}), 404
    return jsonify(profile), 200

@app.route("/api/profile", methods=["PUT"])
@app.route("/api/profile/save", methods=["POST"])
def save_profile():
    """Update profile (supports both PUT and POST)."""
    user_id = get_current_user()
    profile = get_user_profile(user_id)
    if not profile:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # Validate basic fields if present using Pydantic
    try:
        # Extract only fields that are in ProfileBase
        base_fields = {k: v for k, v in data.items() if k in ProfileBase.__fields__}
        if base_fields:
            validated = ProfileBase(**base_fields)
            data.update(validated.dict(exclude_unset=True))
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 400

    # Handle nested objects
    if "tenant_profile" in data and isinstance(data["tenant_profile"], dict):
        try:
            tenant = TenantProfile(**data["tenant_profile"])
            data["tenant_profile"] = tenant.dict()
        except ValidationError as e:
            return jsonify({"error": "Tenant profile invalid", "details": e.errors()}), 400

    if "privacy" in data and isinstance(data["privacy"], dict):
        try:
            priv = PrivacySettings(**data["privacy"])
            data["privacy"] = priv.dict()
        except ValidationError as e:
            return jsonify({"error": "Privacy settings invalid", "details": e.errors()}), 400

    if "notifications" in data and isinstance(data["notifications"], dict):
        try:
            notif = NotificationPrefs(**data["notifications"])
            data["notifications"] = notif.dict()
        except ValidationError as e:
            return jsonify({"error": "Notification preferences invalid", "details": e.errors()}), 400

    # Update profile
    updated = update_user_profile(user_id, data)
    return jsonify(updated), 200

@app.route("/api/profile/status", methods=["POST"])
def set_account_status():
    """Update account status."""
    user_id = get_current_user()
    data = request.get_json()
    status = data.get("status")
    if status not in [s.value for s in AccountStatus]:
        return jsonify({"error": "Invalid status"}), 400
    profile = update_user_profile(user_id, {"account_status": status})
    return jsonify({"status": "updated", "account_status": profile["account_status"]}), 200

@app.route("/api/profile/privacy", methods=["POST"])
def set_privacy():
    """Update privacy settings."""
    user_id = get_current_user()
    data = request.get_json()
    try:
        priv = PrivacySettings(**data)
    except ValidationError as e:
        return jsonify({"error": "Invalid privacy settings", "details": e.errors()}), 400
    profile = update_user_profile(user_id, {"privacy": priv.dict()})
    return jsonify(profile["privacy"]), 200

@app.route("/api/profile/tenant", methods=["POST"])
def set_tenant_profile():
    """Update tenant-specific fields."""
    user_id = get_current_user()
    data = request.get_json()
    try:
        tenant = TenantProfile(**data)
    except ValidationError as e:
        return jsonify({"error": "Invalid tenant data", "details": e.errors()}), 400
    profile = update_user_profile(user_id, {"tenant_profile": tenant.dict()})
    return jsonify(profile["tenant_profile"]), 200

@app.route("/api/profile/notifications", methods=["POST"])
def set_notifications():
    """Update notification preferences."""
    user_id = get_current_user()
    data = request.get_json()
    try:
        notif = NotificationPrefs(**data)
    except ValidationError as e:
        return jsonify({"error": "Invalid notification prefs", "details": e.errors()}), 400
    profile = update_user_profile(user_id, {"notifications": notif.dict()})
    return jsonify(profile["notifications"]), 200

@app.route("/api/profile/language", methods=["POST"])
def set_language():
    """Set user's language preference."""
    user_id = get_current_user()
    data = request.get_json()
    lang = data.get("language")
    if not lang:
        return jsonify({"error": "Language missing"}), 400
    profile = update_user_profile(user_id, {"language": lang})
    return jsonify({"language": profile["language"]}), 200

@app.route("/api/profile/interests", methods=["POST"])
def set_interests():
    """Update interests list."""
    user_id = get_current_user()
    data = request.get_json()
    interests = data.get("interests")
    if not isinstance(interests, list):
        return jsonify({"error": "Interests must be a list"}), 400
    profile = update_user_profile(user_id, {"interests": interests})
    return jsonify(profile["interests"]), 200

@app.route("/api/profile/link", methods=["POST"])
def link_account():
    """Link a new account (OAuth placeholder)."""
    user_id = get_current_user()
    data = request.get_json()
    platform = data.get("platform")
    username = data.get("username")
    if not platform:
        return jsonify({"error": "Platform required"}), 400

    profile = get_user_profile(user_id)
    accounts = profile.get("linked_accounts", [])

    # Update or add
    for acc in accounts:
        if acc["platform"] == platform:
            acc["connected"] = True
            acc["username"] = username
            break
    else:
        accounts.append({"platform": platform, "username": username, "connected": True})

    update_user_profile(user_id, {"linked_accounts": accounts})
    return jsonify({"message": f"{platform} linked successfully"}), 200

@app.route("/api/profile/unlink", methods=["POST"])
def unlink_account():
    """Unlink an account."""
    user_id = get_current_user()
    data = request.get_json()
    platform = data.get("platform")
    if not platform:
        return jsonify({"error": "Platform required"}), 400

    profile = get_user_profile(user_id)
    accounts = profile.get("linked_accounts", [])
    for acc in accounts:
        if acc["platform"] == platform:
            acc["connected"] = False
            acc["username"] = None
            break
    update_user_profile(user_id, {"linked_accounts": accounts})
    return jsonify({"message": f"{platform} unlinked"}), 200

@app.route("/api/profile/pause", methods=["POST"])
def pause_account():
    """Pause account (temporarily hide)."""
    user_id = get_current_user()
    update_user_profile(user_id, {"account_status": AccountStatus.PRIVATE.value})
    return jsonify({"message": "Account paused. Reactivate anytime."}), 200

@app.route("/api/profile/export", methods=["POST"])
def export_data():
    """Request data export."""
    user_id = get_current_user()
    # In real app, generate export file and email
    return jsonify({"message": "Data export requested — check your email in 24hrs"}), 200

@app.route("/api/profile/delete", methods=["POST"])
def delete_account():
    """Permanently delete account."""
    user_id = get_current_user()
    if user_id in USERS:
        del USERS[user_id]
    session.pop("user_id", None)
    return jsonify({"message": "Deletion request submitted — you'll receive an email"}), 200

@app.route("/api/activity", methods=["GET"])
def get_activity():
    """Get recent activity."""
    user_id = get_current_user()
    profile = get_user_profile(user_id)
    if not profile:
        return jsonify({"error": "User not found"}), 404
    return jsonify(profile.get("activity", [])), 200

# ============================================================================
# Serve the Frontend (optional)
# ============================================================================

# The provided HTML is huge; we'll serve it from a file or as a string.
# For simplicity, we'll assume the HTML file is present at 'templates/profile.html'
# If you want to embed the HTML directly, you can use render_template_string.

# We'll use the HTML as a string; but for brevity, we'll just serve static file.
# However, to keep everything in one file, we can embed the HTML in a template.
# I'll create a route that renders the profile page using the provided HTML.

@app.route("/")
def index():
    """Serve the profile page."""
    # In production, serve from a static file; here we render the provided HTML.
    # The HTML contains JS that calls our APIs.
    # We need to ensure the HTML is properly formatted.
    html_content = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>My Profile · Mwarokin Estates</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@2.34.0/tabler-icons.min.css" />
    <!-- This is the CSS from the provided UI -->
    <style>
        /* ---- Reset & base ---------------------------------- */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        :root {
            --bg: #f2f5fa;
            --card-bg: #ffffff;
            --ink: #0d0f14;
            --ink2: #2d3138;
            --ink3: #6d727a;
            --border: #e8ecf2;
            --teal: #2eb89a;
            --gold: #e6b450;
            --blue: #3b82f6;
            --red: #e54d4d;
            --radius: 18px;
            --shadow: 0 12px 40px -8px rgba(0, 0, 0, 0.08);
            --transition: 0.2s ease;
        }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg);
            color: var(--ink);
            line-height: 1.5;
        }
        /* ---- Page layout ---------------------------------- */
        .page-wrap {
            display: flex;
            min-height: 100vh;
        }
        .sidebar {
            width: 260px;
            background: var(--card-bg);
            border-right: 1px solid var(--border);
            padding: 24px 16px 20px;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            height: 100vh;
            position: sticky;
            top: 0;
            overflow-y: auto;
        }
        .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 10px;
            font-weight: 700;
            font-size: 18px;
            padding: 0 8px 20px 8px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 16px;
        }
        .logo-mark {
            width: 36px;
            height: 36px;
            background: var(--teal);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
        }
        .logo-name {
            letter-spacing: -0.3px;
        }
        .nav-section-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--ink3);
            padding: 12px 8px 6px;
        }
        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            border-radius: 12px;
            color: var(--ink2);
            text-decoration: none;
            font-weight: 500;
            font-size: 14px;
            transition: var(--transition);
            position: relative;
            cursor: pointer;
            margin-bottom: 2px;
        }
        .nav-item i {
            font-size: 20px;
            width: 24px;
            text-align: center;
            color: var(--ink3);
            transition: var(--transition);
        }
        .nav-item:hover {
            background: #f0f3f8;
            color: var(--ink);
        }
        .nav-item:hover i {
            color: var(--ink);
        }
        .nav-item.active {
            background: #eef7f4;
            color: var(--teal);
            font-weight: 600;
        }
        .nav-item.active i {
            color: var(--teal);
        }
        .nav-badge {
            margin-left: auto;
            background: #eef0f4;
            color: var(--ink2);
            font-size: 11px;
            font-weight: 600;
            padding: 2px 10px;
            border-radius: 30px;
            line-height: 20px;
        }
        .nav-item.active .nav-badge {
            background: var(--teal);
            color: white;
        }
        .sidebar-footer {
            margin-top: auto;
            padding-top: 16px;
            border-top: 1px solid var(--border);
        }
        .sidebar-mini-profile {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 6px 0 12px;
        }
        .mini-avatar {
            width: 40px;
            height: 40px;
            border-radius: 40px;
            background: var(--teal);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 16px;
        }
        .mini-name {
            font-weight: 600;
            font-size: 14px;
        }
        .mini-role {
            font-size: 12px;
            color: var(--ink3);
        }
        .logout-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            background: #f4f6fa;
            border: none;
            border-radius: 40px;
            padding: 10px;
            font-weight: 500;
            color: var(--ink2);
            font-size: 14px;
            cursor: pointer;
            transition: var(--transition);
        }
        .logout-btn:hover {
            background: #eceff6;
        }

        /* ---- Main ----------------------------------------- */
        .main {
            flex: 1;
            padding: 24px 32px 40px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .topnav {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
            flex-wrap: wrap;
            gap: 12px;
        }
        .topnav-left {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }
        .topnav-right {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .icon-btn {
            width: 40px;
            height: 40px;
            border-radius: 40px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: var(--ink2);
            cursor: pointer;
            transition: var(--transition);
        }
        .icon-btn:hover {
            background: #f4f6fa;
            border-color: var(--ink3);
        }
        .save-btn {
            background: var(--ink);
            color: white;
            border: none;
            border-radius: 40px;
            padding: 8px 20px;
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            transition: var(--transition);
        }
        .save-btn:hover {
            background: #1a1e26;
        }

        /* ---- Profile header ------------------------------- */
        .profile-header {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            overflow: hidden;
            margin-bottom: 24px;
        }
        .cover-area {
            position: relative;
            height: 180px;
            background: #dde2eb;
        }
        .cover-img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .cover-pattern {
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(13,15,20,0.2) 0%, transparent 70%);
            pointer-events: none;
        }
        .cover-edit-btn {
            position: absolute;
            bottom: 16px;
            right: 20px;
            background: rgba(255,255,255,0.9);
            backdrop-filter: blur(4px);
            border: none;
            border-radius: 40px;
            padding: 6px 16px;
            font-weight: 500;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            transition: var(--transition);
        }
        .cover-edit-btn:hover {
            background: white;
            transform: scale(1.02);
        }
        .profile-identity {
            display: flex;
            align-items: flex-end;
            padding: 0 28px 24px;
            gap: 20px;
            flex-wrap: wrap;
            margin-top: -40px;
            position: relative;
        }
        .avatar-wrap {
            position: relative;
            flex-shrink: 0;
        }
        .avatar {
            width: 100px;
            height: 100px;
            border-radius: 100px;
            background: linear-gradient(135deg, #2eb89a, #1a8a72);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 32px;
            font-weight: 600;
            border: 4px solid var(--card-bg);
            box-shadow: 0 4px 16px rgba(0,0,0,0.08);
            cursor: pointer;
            position: relative;
            overflow: hidden;
        }
        .avatar-overlay {
            position: absolute;
            inset: 0;
            background: rgba(0,0,0,0.35);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: var(--transition);
            font-size: 24px;
            color: white;
        }
        .avatar:hover .avatar-overlay {
            opacity: 1;
        }
        .status-dot {
            position: absolute;
            bottom: 6px;
            right: 6px;
            width: 16px;
            height: 16px;
            border-radius: 16px;
            background: #2eb89a;
            border: 3px solid var(--card-bg);
        }
        .identity-info {
            flex: 1;
            min-width: 200px;
        }
        .display-name {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .verify-badge {
            font-size: 13px;
            font-weight: 500;
            color: var(--teal);
            background: #e2f3ef;
            padding: 2px 12px;
            border-radius: 30px;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }
        .user-handle {
            font-size: 14px;
            color: var(--ink3);
            margin-top: 2px;
        }
        .profile-meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .meta-chip {
            font-size: 13px;
            background: #f4f6fa;
            padding: 4px 14px;
            border-radius: 30px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            color: var(--ink2);
        }
        .profile-actions {
            display: flex;
            gap: 10px;
            flex-shrink: 0;
            align-self: center;
        }
        .share-btn, .edit-profile-btn {
            padding: 8px 20px;
            border-radius: 40px;
            font-weight: 500;
            font-size: 14px;
            cursor: pointer;
            transition: var(--transition);
            border: 1px solid var(--border);
            background: var(--card-bg);
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .share-btn:hover, .edit-profile-btn:hover {
            background: #f4f6fa;
        }
        .edit-profile-btn {
            background: var(--ink);
            color: white;
            border-color: var(--ink);
        }
        .edit-profile-btn:hover {
            background: #1a1e26;
        }

        /* ---- Stat strip ---------------------------------- */
        .stat-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 16px;
            margin-bottom: 28px;
        }
        .stat-cell {
            background: var(--card-bg);
            padding: 16px 20px;
            border-radius: var(--radius);
            box-shadow: var(--shadow);
        }
        .stat-n {
            font-size: 26px;
            font-weight: 700;
            letter-spacing: -0.5px;
        }
        .stat-l {
            font-size: 14px;
            color: var(--ink3);
        }

        /* ---- Content grid -------------------------------- */
        .content-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 24px;
        }
        @media (max-width: 900px) {
            .content-grid { grid-template-columns: 1fr; }
            .sidebar { display: none; }
            .main { padding: 16px; }
            .profile-identity { flex-direction: column; align-items: center; text-align: center; }
            .profile-meta-row { justify-content: center; }
            .profile-actions { align-self: center; }
        }

        /* ---- Cards --------------------------------------- */
        .card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow);
            padding: 20px 24px;
            margin-bottom: 20px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .card-title {
            font-weight: 600;
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-action {
            background: transparent;
            border: none;
            color: var(--teal);
            font-weight: 500;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 8px;
            transition: var(--transition);
        }
        .card-action:hover {
            background: #eef7f4;
        }

        /* ---- Form fields --------------------------------- */
        .field-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 14px;
        }
        .field-full {
            margin-bottom: 14px;
        }
        .field-label {
            font-size: 13px;
            font-weight: 500;
            color: var(--ink2);
            display: block;
            margin-bottom: 4px;
        }
        .field-input, .field-select, .field-textarea {
            width: 100%;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: 12px;
            font-family: inherit;
            font-size: 14px;
            background: #fafbfd;
            transition: var(--transition);
            outline: none;
        }
        .field-input:focus, .field-select:focus, .field-textarea:focus {
            border-color: var(--teal);
            background: white;
            box-shadow: 0 0 0 3px rgba(46,184,154,0.15);
        }
        .field-textarea {
            min-height: 80px;
            resize: vertical;
        }
        .char-count {
            text-align: right;
            font-size: 12px;
            color: var(--ink3);
            margin-top: 4px;
        }

        /* ---- Chips --------------------------------------- */
        .chip-group {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 4px;
        }
        .pronoun-chip {
            padding: 6px 16px;
            border-radius: 30px;
            border: 1px solid var(--border);
            font-size: 13px;
            cursor: pointer;
            transition: var(--transition);
            background: var(--card-bg);
        }
        .pronoun-chip.selected {
            background: var(--teal);
            color: white;
            border-color: var(--teal);
        }
        .pronoun-chip:hover {
            border-color: var(--teal);
        }

        /* ---- Language grid ------------------------------- */
        .lang-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 12px;
        }
        .lang-card {
            background: #fafbfd;
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px 8px;
            text-align: center;
            cursor: pointer;
            transition: var(--transition);
        }
        .lang-card.active {
            border-color: var(--teal);
            background: #eef7f4;
            box-shadow: 0 0 0 2px rgba(46,184,154,0.2);
        }
        .lang-card:hover {
            border-color: var(--teal);
        }
        .lang-flag {
            font-size: 28px;
            line-height: 1.2;
        }
        .lang-name {
            font-size: 13px;
            font-weight: 500;
            margin-top: 4px;
        }

        /* ---- Interests ----------------------------------- */
        .interest-wrap {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .interest-tag {
            padding: 6px 16px;
            border-radius: 30px;
            border: 1px solid var(--border);
            font-size: 13px;
            cursor: pointer;
            transition: var(--transition);
            background: var(--card-bg);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .interest-tag.active {
            background: var(--teal);
            color: white;
            border-color: var(--teal);
        }
        .interest-tag:hover {
            border-color: var(--teal);
        }

        /* ---- Toggles -------------------------------------- */
        .toggle-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid var(--border);
        }
        .toggle-row:last-child {
            border-bottom: none;
        }
        .toggle-label {
            flex: 1;
            margin-right: 12px;
        }
        .toggle-title {
            font-weight: 500;
            font-size: 14px;
        }
        .toggle-desc {
            font-size: 13px;
            color: var(--ink3);
        }
        .tog {
            position: relative;
            display: inline-block;
            width: 44px;
            height: 24px;
            flex-shrink: 0;
        }
        .tog input {
            opacity: 0;
            width: 0;
            height: 0;
        }
        .tog-sl {
            position: absolute;
            cursor: pointer;
            inset: 0;
            background: #cdd2da;
            border-radius: 24px;
            transition: var(--transition);
        }
        .tog-sl:before {
            content: "";
            position: absolute;
            height: 18px;
            width: 18px;
            left: 3px;
            bottom: 3px;
            background: white;
            border-radius: 50%;
            transition: var(--transition);
        }
        .tog input:checked + .tog-sl {
            background: var(--teal);
        }
        .tog input:checked + .tog-sl:before {
            transform: translateX(20px);
        }

        /* ---- Linked accounts ------------------------------ */
        .linked-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 0;
            border-bottom: 1px solid var(--border);
        }
        .linked-item:last-child {
            border-bottom: none;
        }
        .linked-icon {
            width: 40px;
            height: 40px;
            border-radius: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }
        .linked-info {
            flex: 1;
        }
        .linked-name {
            font-weight: 500;
        }
        .linked-status {
            font-size: 13px;
            color: var(--ink3);
        }
        .linked-btn {
            padding: 4px 16px;
            border-radius: 30px;
            font-weight: 500;
            font-size: 13px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            cursor: pointer;
            transition: var(--transition);
        }
        .linked-btn.connect {
            background: var(--teal);
            color: white;
            border-color: var(--teal);
        }
        .linked-btn.connect:hover {
            background: #28a88a;
        }
        .linked-btn.connected {
            background: #eef7f4;
            color: var(--teal);
            border-color: var(--teal);
        }

        /* ---- Activity ------------------------------------ */
        .activity-timeline {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .activity-item {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .activity-dot {
            width: 10px;
            height: 10px;
            border-radius: 10px;
            flex-shrink: 0;
        }
        .activity-text {
            flex: 1;
            font-size: 14px;
        }
        .activity-time {
            font-size: 12px;
            color: var(--ink3);
            white-space: nowrap;
        }

        /* ---- Status options ------------------------------- */
        .status-select-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .status-option {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            border-radius: 12px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: var(--transition);
        }
        .status-option.active {
            border-color: var(--teal);
            background: #eef7f4;
        }
        .status-option:hover {
            border-color: var(--teal);
        }
        .status-dot-sm {
            width: 12px;
            height: 12px;
            border-radius: 12px;
            flex-shrink: 0;
        }
        .status-lbl {
            font-weight: 500;
        }

        /* ---- Privacy selects ----------------------------- */
        .privacy-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid var(--border);
        }
        .privacy-row:last-child {
            border-bottom: none;
        }
        .privacy-label {
            font-weight: 500;
            font-size: 14px;
        }
        .privacy-sel {
            padding: 4px 10px;
            border-radius: 8px;
            border: 1px solid var(--border);
            background: var(--card-bg);
            font-size: 13px;
            outline: none;
            cursor: pointer;
        }
        .privacy-sel:focus {
            border-color: var(--teal);
        }

        /* ---- QR & share ---------------------------------- */
        .qr-card {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px 24px;
        }
        .qr-box {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            width: 120px;
            margin: 12px 0;
            background: #f0f2f8;
            padding: 6px;
            border-radius: 8px;
        }
        .qr-px {
            aspect-ratio: 1;
            border-radius: 2px;
        }
        .qr-text {
            font-size: 13px;
            color: var(--ink3);
            margin-bottom: 12px;
        }
        .share-link-row {
            display: flex;
            width: 100%;
            gap: 8px;
        }
        .share-link-input {
            flex: 1;
            padding: 8px 14px;
            border: 1px solid var(--border);
            border-radius: 30px;
            font-size: 13px;
            background: #fafbfd;
            outline: none;
        }
        .share-link-input:focus {
            border-color: var(--teal);
        }
        .copy-btn {
            padding: 8px 18px;
            border-radius: 30px;
            border: none;
            background: var(--teal);
            color: white;
            font-weight: 500;
            cursor: pointer;
            transition: var(--transition);
            white-space: nowrap;
        }
        .copy-btn:hover {
            background: #28a88a;
        }

        /* ---- Danger zone -------------------------------- */
        .danger-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            width: 100%;
            padding: 12px 16px;
            border: 1px solid var(--border);
            border-radius: 12px;
            background: var(--card-bg);
            font-weight: 500;
            font-size: 14px;
            color: var(--red);
            cursor: pointer;
            transition: var(--transition);
            margin-top: 8px;
        }
        .danger-btn:hover {
            background: #fdf0f0;
            border-color: var(--red);
        }

        /* ---- Toast ---------------------------------------- */
        .toast-wrap {
            position: fixed;
            bottom: 24px;
            right: 24px;
            display: flex;
            flex-direction: column;
            gap: 10px;
            z-index: 999;
            pointer-events: none;
        }
        .toast {
            padding: 12px 20px;
            border-radius: 40px;
            background: var(--ink);
            color: white;
            font-weight: 500;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            transform: translateY(20px);
            opacity: 0;
            transition: all 0.3s ease;
            pointer-events: auto;
        }
        .toast.show {
            transform: translateY(0);
            opacity: 1;
        }
        .toast.success { background: var(--teal); }
        .toast.warning { background: var(--gold); color: var(--ink); }
        .toast i { font-size: 20px; }

        /* ---- Modal ---------------------------------------- */
        .modal-bg {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.4);
            backdrop-filter: blur(4px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        .modal-bg.open {
            display: flex;
        }
        .modal {
            background: white;
            border-radius: var(--radius);
            padding: 32px;
            max-width: 420px;
            width: 90%;
            box-shadow: 0 24px 60px rgba(0,0,0,0.2);
        }
        .modal-title {
            font-size: 20px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        .modal-body {
            color: var(--ink2);
            font-size: 15px;
            margin-bottom: 24px;
        }
        .modal-actions {
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
        .modal-cancel, .modal-confirm {
            padding: 8px 20px;
            border-radius: 40px;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: var(--transition);
        }
        .modal-cancel {
            background: #f4f6fa;
            color: var(--ink2);
        }
        .modal-cancel:hover {
            background: #e8ecf2;
        }
        .modal-confirm {
            background: var(--red);
            color: white;
        }
        .modal-confirm:hover {
            background: #d93d3d;
        }

        /* ---- Animations ---------------------------------- */
        .animate-up {
            animation: slideUp 0.5s ease both;
        }
        .delay-1 { animation-delay: 0.05s; }
        .delay-2 { animation-delay: 0.1s; }
        .delay-3 { animation-delay: 0.15s; }
        .delay-4 { animation-delay: 0.2s; }
        .delay-5 { animation-delay: 0.25s; }
        .delay-6 { animation-delay: 0.3s; }

        @keyframes slideUp {
            from { opacity:0; transform: translateY(16px); }
            to { opacity:1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <!-- The UI HTML from the user (with minor adjustments for API calls) -->
    <!-- We'll replace the inline JS with calls to our backend -->
    <!-- For brevity, I'll include a modified version that uses fetch to our APIs -->

    <div class="page-wrap">
        <aside class="sidebar">
            <div class="sidebar-logo">
                <div class="logo-mark"><i class="ti ti-building-estate"></i></div>
                <span class="logo-name">Mwarokin Estates</span>
            </div>
            <div class="nav-section-label">Main</div>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-dashboard"></i> Dashboard
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-home"></i> My Properties
                <span class="nav-badge">3</span>
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-credit-card"></i> Payments
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-map-pin"></i> Neighbourhoods
            </a>
            <div class="nav-section-label" style="margin-top:16px">Account</div>
            <a href="#" class="nav-item active" onclick="nav(this)">
                <i class="ti ti-user-circle"></i> Tenants
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-bell"></i> Notifications
                <span class="nav-badge">5</span>
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-shield-check"></i> Privacy & Safety
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-settings"></i> Settings
            </a>
            <a href="#" class="nav-item" onclick="nav(this)">
                <i class="ti ti-help-circle"></i> Help & Support
            </a>
            <div class="sidebar-footer">
                <div class="sidebar-mini-profile">
                    <div class="mini-avatar">RK</div>
                    <div>
                        <div class="mini-name">Robin M.</div>
                        <div class="mini-role">Tenant · Verified</div>
                    </div>
                </div>
                <button class="logout-btn" onclick="showModal('logout')">
                    <i class="ti ti-logout"></i> Sign out
                </button>
            </div>
        </aside>

        <div class="main">
            <div class="topnav">
                <div class="topnav-left">My Profile</div>
                <div class="topnav-right">
                    <button class="icon-btn" title="Notifications"><i class="ti ti-bell"></i></button>
                    <button class="icon-btn" title="Preview profile"><i class="ti ti-eye"></i></button>
                    <button class="save-btn" onclick="saveProfile()">
                        <i class="ti ti-check"></i> Save changes
                    </button>
                </div>
            </div>

            <!-- Profile Header -->
            <div class="profile-header animate-up">
                <div class="cover-area">
                    <img class="cover-img" src="https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1200&q=60" alt="Cover photo">
                    <div class="cover-pattern"></div>
                    <button class="cover-edit-btn" onclick="toast('Cover photo upload opened','success')">
                        <i class="ti ti-camera"></i> Change cover
                    </button>
                </div>
                <div class="profile-identity">
                    <div class="avatar-wrap">
                        <div class="avatar" onclick="toast('Photo upload opened','success')">
                            RK
                            <div class="avatar-overlay"><i class="ti ti-camera"></i></div>
                        </div>
                        <div class="status-dot" title="Online"></div>
                    </div>
                    <div class="identity-info">
                        <div class="display-name">
                            <span id="displayName">Robin Mwarema</span>
                            <span class="verify-badge"><i class="ti ti-rosette-discount-check"></i> Verified</span>
                        </div>
                        <div class="user-handle" id="userHandle">@robin.Mwarema · Tenant since Jan 2024</div>
                        <div class="profile-meta-row" id="metaRow">
                            <div class="meta-chip"><i class="ti ti-map-pin"></i> <span id="profileLocation">Nairobi, Kenya</span></div>
                            <div class="meta-chip"><i class="ti ti-calendar"></i> Joined 18 months ago</div>
                            <div class="meta-chip"><i class="ti ti-star"></i> 4.8 tenant rating</div>
                            <div class="meta-chip"><i class="ti ti-clock"></i> Responds in ~2 hrs</div>
                        </div>
                    </div>
                    <div class="profile-actions">
                        <button class="share-btn" onclick="copyLink()">
                            <i class="ti ti-share"></i> Share
                        </button>
                        <button class="edit-profile-btn" onclick="toast('Editing profile','success')">
                            <i class="ti ti-pencil"></i> Edit profile
                        </button>
                    </div>
                </div>
            </div>

            <!-- Stat Strip -->
            <div class="stat-strip animate-up delay-1">
                <div class="stat-cell"><div class="stat-n">3</div><div class="stat-l">Active listings</div></div>
                <div class="stat-cell"><div class="stat-n">24</div><div class="stat-l">Reviews written</div></div>
                <div class="stat-cell"><div class="stat-n">142</div><div class="stat-l">Profile views</div></div>
                <div class="stat-cell"><div class="stat-n">18mo</div><div class="stat-l">Member tenure</div></div>
            </div>

            <!-- Content Grid -->
            <div class="content-grid">
                <!-- LEFT COLUMN -->
                <div class="left-col">
                    <!-- Basic Info -->
                    <div class="card animate-up delay-2">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-id-badge"></i> Basic information</div>
                            <button class="card-action" onclick="toast('Auto-saved','success')"><i class="ti ti-device-floppy"></i> Auto-save on</button>
                        </div>
                        <div class="field-row">
                            <div>
                                <label class="field-label">First name</label>
                                <input class="field-input" type="text" id="firstName" value="Robin" oninput="markDirty()">
                            </div>
                            <div>
                                <label class="field-label">Last name</label>
                                <input class="field-input" type="text" id="lastName" value="Kamau" oninput="markDirty()">
                            </div>
                        </div>
                        <div class="field-row">
                            <div>
                                <label class="field-label">Display name / Username</label>
                                <input class="field-input" type="text" id="displayNameInput" value="robin.kamau" oninput="markDirty()">
                            </div>
                            <div>
                                <label class="field-label">Email address</label>
                                <input class="field-input" type="email" id="email" value="robin@mwarokin.com" oninput="markDirty()">
                            </div>
                        </div>
                        <div class="field-row">
                            <div>
                                <label class="field-label">Phone number</label>
                                <input class="field-input" type="tel" id="phone" value="+254 704 919 388" oninput="markDirty()">
                            </div>
                            <div>
                                <label class="field-label">Date of birth</label>
                                <input class="field-input" type="date" id="dob" value="1990-06-15" oninput="markDirty()">
                            </div>
                        </div>
                        <div class="field-full">
                            <label class="field-label">Bio / About me</label>
                            <textarea class="field-textarea" id="bioInput" maxlength="280" oninput="updateBioCount()" placeholder="Tell landlords and the community a little about yourself...">Urban professional seeking quality housing in Nairobi. I value quiet, clean spaces and am always a respectful, on-time tenant. Huge fan of Swahili architecture and local community life.</textarea>
                            <div class="char-count" id="bioCount">196 / 280</div>
                        </div>
                        <div class="field-row">
                            <div>
                                <label class="field-label">Location</label>
                                <input class="field-input" type="text" id="locationInput" value="Nairobi, Kenya" oninput="markDirty()">
                            </div>
                            <div>
                                <label class="field-label">Occupation</label>
                                <input class="field-input" type="text" id="occupation" value="Technology Entrepreneur" oninput="markDirty()">
                            </div>
                        </div>
                        <div>
                            <label class="field-label">Pronouns</label>
                            <div class="chip-group" id="pronouns">
                                <div class="pronoun-chip selected" onclick="toggleChip(this)">He / Him</div>
                                <div class="pronoun-chip" onclick="toggleChip(this)">She / Her</div>
                                <div class="pronoun-chip" onclick="toggleChip(this)">They / Them</div>
                                <div class="pronoun-chip" onclick="toggleChip(this)">Ze / Zir</div>
                                <div class="pronoun-chip" onclick="toggleChip(this)">Prefer not to say</div>
                            </div>
                        </div>
                    </div>

                    <!-- Global Language -->
                    <div class="card animate-up delay-3">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-world"></i> Global language</div>
                            <button class="card-action" onclick="setLanguage()"><i class="ti ti-check"></i> Apply</button>
                        </div>
                        <div class="lang-grid" id="langGrid">
                            <div class="lang-card active" onclick="selectLang(this)" data-lang="English (Kenya)">
                                <div class="lang-flag">🇰🇪</div>
                                <div class="lang-name">English (Kenya)</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Swahili">
                                <div class="lang-flag">🇸🇦</div>
                                <div class="lang-name">Swahili</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Français">
                                <div class="lang-flag">🇫🇷</div>
                                <div class="lang-name">Français</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Português">
                                <div class="lang-flag">🇵🇹</div>
                                <div class="lang-name">Português</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Español">
                                <div class="lang-flag">🇪🇸</div>
                                <div class="lang-name">Español</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Somali">
                                <div class="lang-flag">🇸🇴</div>
                                <div class="lang-name">Somali</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="Arabic">
                                <div class="lang-flag">🇸🇩</div>
                                <div class="lang-name">Arabic</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="中文">
                                <div class="lang-flag">🇨🇳</div>
                                <div class="lang-name">中文</div>
                            </div>
                            <div class="lang-card" onclick="selectLang(this)" data-lang="हिन्दी">
                                <div class="lang-flag">🇮🇳</div>
                                <div class="lang-name">हिन्दी</div>
                            </div>
                        </div>
                    </div>

                    <!-- Interests -->
                    <div class="card animate-up delay-4">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-sparkles"></i> Interests & lifestyle</div>
                            <button class="card-action" onclick="saveInterests()"><i class="ti ti-pencil"></i> Edit all</button>
                        </div>
                        <div class="interest-wrap" id="interests">
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-home"></i> Modern architecture</div>
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-tree"></i> Green spaces</div>
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-bus"></i> Public transport access</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-brand-spotify"></i> Music</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-chef-hat"></i> Cooking</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-device-tv"></i> Film</div>
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-bike"></i> Cycling</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-dog"></i> Pet friendly</div>
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-wifi"></i> Smart home</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-swimming"></i> Pool access</div>
                            <div class="interest-tag" onclick="toggleTag(this)"><i class="ti ti-garden-cart"></i> Garden</div>
                            <div class="interest-tag active" onclick="toggleTag(this)"><i class="ti ti-parking"></i> Parking</div>
                        </div>
                    </div>

                    <!-- Notification Preferences -->
                    <div class="card animate-up delay-5">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-bell"></i> Notification preferences</div>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">New property matches</div>
                                <div class="toggle-desc">Get notified when a listing matches your search</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifMatches" checked><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Payment reminders</div>
                                <div class="toggle-desc">Upcoming rent and bill due dates</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifPayments" checked><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Neighbourhood alerts</div>
                                <div class="toggle-desc">Safety and community updates</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifNeighbourhood" checked><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Promotional offers</div>
                                <div class="toggle-desc">Deals and platform announcements</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifPromo"><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Review requests</div>
                                <div class="toggle-desc">Prompts to review past properties</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifReviews" checked><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Email digest</div>
                                <div class="toggle-desc">Weekly summary of activity</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="notifDigest"><span class="tog-sl"></span></label>
                        </div>
                        <div style="margin-top:12px">
                            <button class="save-btn" onclick="saveNotifications()" style="width:100%; justify-content:center;">Save Notification Preferences</button>
                        </div>
                    </div>

                    <!-- Linked Accounts -->
                    <div class="card animate-up delay-6">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-plug-connected"></i> Linked accounts</div>
                        </div>
                        <div id="linkedAccountsContainer">
                            <!-- Will be populated by JS -->
                        </div>
                    </div>

                    <!-- Recent Activity -->
                    <div class="card animate-up delay-6">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-activity"></i> Recent activity</div>
                            <button class="card-action" onclick="toast('Full activity log opened','success')"><i class="ti ti-external-link"></i> View all</button>
                        </div>
                        <div class="activity-timeline" id="activityTimeline">
                            <!-- Populated by JS -->
                        </div>
                    </div>
                </div>

                <!-- RIGHT COLUMN -->
                <div class="right-col">
                    <!-- Account Status -->
                    <div class="card animate-up delay-2">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-radio-button"></i> Account status</div>
                        </div>
                        <div class="status-select-group" id="statusGroup">
                            <div class="status-option active" onclick="setStatus(this)" data-status="Active — visible to all">
                                <div class="status-dot-sm" style="background:#2eb89a"></div>
                                <div class="status-lbl">Active — visible to all</div>
                            </div>
                            <div class="status-option" onclick="setStatus(this)" data-status="Do not disturb">
                                <div class="status-dot-sm" style="background:var(--gold)"></div>
                                <div class="status-lbl">Do not disturb</div>
                            </div>
                            <div class="status-option" onclick="setStatus(this)" data-status="Private mode">
                                <div class="status-dot-sm" style="background:var(--ink3)"></div>
                                <div class="status-lbl">Private mode</div>
                            </div>
                            <div class="status-option" onclick="setStatus(this)" data-status="Away">
                                <div class="status-dot-sm" style="background:var(--red)"></div>
                                <div class="status-lbl">Away</div>
                            </div>
                        </div>
                    </div>

                    <!-- Privacy Settings -->
                    <div class="card animate-up delay-3">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-lock"></i> Privacy settings</div>
                        </div>
                        <div class="privacy-row">
                            <div class="privacy-label">Who can view my profile</div>
                            <select class="privacy-sel" id="privacyView" onchange="savePrivacy()">
                                <option value="Everyone" selected>Everyone</option>
                                <option value="Verified users">Verified users</option>
                                <option value="Only me">Only me</option>
                            </select>
                        </div>
                        <div class="privacy-row">
                            <div class="privacy-label">Who can message me</div>
                            <select class="privacy-sel" id="privacyMessage" onchange="savePrivacy()">
                                <option value="Verified users" selected>Verified users</option>
                                <option value="Everyone">Everyone</option>
                                <option value="No one">No one</option>
                            </select>
                        </div>
                        <div class="privacy-row">
                            <div class="privacy-label">Show my location</div>
                            <select class="privacy-sel" id="privacyLocation" onchange="savePrivacy()">
                                <option value="City only" selected>City only</option>
                                <option value="Full address">Full address</option>
                                <option value="Hidden">Hidden</option>
                            </select>
                        </div>
                        <div class="privacy-row">
                            <div class="privacy-label">Show activity status</div>
                            <select class="privacy-sel" id="privacyActivity" onchange="savePrivacy()">
                                <option value="Everyone" selected>Everyone</option>
                                <option value="Connections only">Connections only</option>
                                <option value="Hidden">Hidden</option>
                            </select>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Two-factor authentication</div>
                                <div class="toggle-desc">SMS + authenticator app</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="privacy2FA" checked><span class="tog-sl"></span></label>
                        </div>
                        <div class="toggle-row">
                            <div class="toggle-label">
                                <div class="toggle-title">Profile indexing</div>
                                <div class="toggle-desc">Allow search engines to index</div>
                            </div>
                            <label class="tog"><input type="checkbox" id="privacyIndexing"><span class="tog-sl"></span></label>
                        </div>
                    </div>

                    <!-- Tenant Details -->
                    <div class="card animate-up delay-4">
                        <div class="card-header">
                            <div class="card-title"><i class="ti ti-file-certificate"></i> Tenant profile</div>
                        </div>
                        <div class="field-full" style="margin-bottom:12px">
                            <label class="field-label">Monthly income (KSh)</label>
                            <input class="field-input" type="number" id="tenantIncome" value="250000" oninput="markDirty()">
                        </div>
                        <div class="field-full" style="margin-bottom:12px">
                            <label class="field-label">Employment status</label>
                            <select class="field-select" id="tenantEmployment" onchange="markDirty()">
                                <option selected>Employed full-time</option>
                                <option>Self-employed</option>
                                <option>Freelancer</option>
                                <option>Student</option>
                                <option>Retired</option>
                            </select>
                        </div>
                        <div class="field-full" style="margin-bottom:12px">
                            <label class="field-label">Preferred property type</label>
                            <select class="field-select" id="tenantPropertyType" onchange="markDirty()">
                                <option selected>Apartment</option>
                                <option>House</option>
                                <option>Villa</option>
                                <option>Studio</option>
                                <option>Shared</option>
                            </select>
                        </div>
                        <div class="field-full">
                            <label class="field-label">Max budget (KSh / month)</label>
                            <input class="field-input" type="number" id="tenantBudget" value="90000" oninput="markDirty()">
                        </div>
                        <div style="margin-top:12px">
                            <button class="save-btn" onclick="saveTenantProfile()" style="width:100%; justify-content:center;">Update Tenant Details</button>
                        </div>
                    </div>

                    <!-- QR & Share -->
                    <div class="card animate-up delay-5" style="padding:0">
                        <div class="qr-card">
                            <div class="card-title" style="align-self:flex-start"><i class="ti ti-qrcode"></i> Profile QR & link</div>
                            <div class="qr-box" id="qrBox"></div>
                            <div class="qr-text">Scan to view public profile</div>
                            <div class="share-link-row">
                                <input class="share-link-input" id="shareLink" value="mwarokin.com/u/robin.kamau" readonly>
                                <button class="copy-btn" onclick="copyLink()"><i class="ti ti-copy"></i> Copy</button>
                            </div>
                        </div>
                    </div>

                    <!-- Danger Zone -->
                    <div class="card animate-up delay-6">
                        <div class="card-header">
                            <div class="card-title" style="color:var(--red)"><i class="ti ti-alert-triangle"></i> Danger zone</div>
                        </div>
                        <button class="danger-btn" onclick="showModal('pause')">
                            <i class="ti ti-pause-circle"></i> Pause account temporarily
                        </button>
                        <button class="danger-btn" onclick="showModal('data')">
                            <i class="ti ti-download"></i> Export my data
                        </button>
                        <button class="danger-btn" onclick="showModal('delete')">
                            <i class="ti ti-trash"></i> Delete account permanently
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Toast & Modal -->
    <div class="toast-wrap" id="toastWrap"></div>
    <div class="modal-bg" id="modalBg" onclick="closeModal(event)">
        <div class="modal">
            <div class="modal-title" id="modalTitle">Confirm action</div>
            <div class="modal-body" id="modalBody">Are you sure?</div>
            <div class="modal-actions">
                <button class="modal-cancel" onclick="closeModal()">Cancel</button>
                <button class="modal-confirm" id="modalConfirm" onclick="confirmModal()">Confirm</button>
            </div>
        </div>
    </div>

    <!-- ============== JAVASCRIPT ============== -->
    <script>
        // ─── TOAST ──────────────────────────────────────────
        function toast(msg, type='success') {
            const wrap = document.getElementById('toastWrap');
            const el = document.createElement('div');
            const icon = type==='success'?'ti-check':type==='warning'?'ti-alert-circle':'ti-info-circle';
            el.className = `toast ${type}`;
            el.innerHTML = `<i class="ti ${icon}"></i>${msg}`;
            wrap.appendChild(el);
            requestAnimationFrame(() => { requestAnimationFrame(() => el.classList.add('show')); });
            setTimeout(() => {
                el.classList.remove('show');
                setTimeout(() => el.remove(), 400);
            }, 3000);
        }

        // ─── NAV ──────────────────────────────────────────
        function nav(el) {
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            el.classList.add('active');
        }

        // ─── PROFILE LOAD / SAVE ──────────────────────────
        let dirty = false;
        function markDirty() { dirty = true; }

        function saveProfile() {
            // Gather all fields
            const data = {
                first_name: document.getElementById('firstName').value,
                last_name: document.getElementById('lastName').value,
                display_name: document.getElementById('displayNameInput').value,
                email: document.getElementById('email').value,
                phone: document.getElementById('phone').value,
                date_of_birth: document.getElementById('dob').value,
                bio: document.getElementById('bioInput').value,
                location: document.getElementById('locationInput').value,
                occupation: document.getElementById('occupation').value,
                pronouns: document.querySelector('.pronoun-chip.selected')?.textContent.trim() || 'Prefer not to say',
            };
            fetch('/api/profile/save', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => {
                toast('Profile saved successfully', 'success');
                dirty = false;
                // Update header info
                document.getElementById('displayName').textContent = data.first_name + ' ' + data.last_name;
                document.getElementById('userHandle').textContent = '@' + data.display_name + ' · Tenant since Jan 2024';
                document.getElementById('profileLocation').textContent = data.location || 'Nairobi, Kenya';
            })
            .catch(err => toast('Save failed: ' + err.message, 'warning'));
        }

        // ─── BIO COUNT ─────────────────────────────────────
        function updateBioCount() {
            const ta = document.getElementById('bioInput');
            document.getElementById('bioCount').textContent = ta.value.length + ' / 280';
            markDirty();
        }

        // ─── PRONOUNS ─────────────────────────────────────
        function toggleChip(el) {
            document.querySelectorAll('.pronoun-chip').forEach(c => c.classList.remove('selected'));
            el.classList.add('selected');
            markDirty();
        }

        // ─── LANGUAGE ─────────────────────────────────────
        let selectedLang = 'English (Kenya)';
        function selectLang(el) {
            document.querySelectorAll('.lang-card').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            selectedLang = el.dataset.lang;
            toast(`Language set to ${selectedLang}`, 'success');
            markDirty();
        }
        function setLanguage() {
            fetch('/api/profile/language', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({language: selectedLang}),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Language updated to ' + data.language, 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── INTERESTS ─────────────────────────────────────
        function toggleTag(el) {
            el.classList.toggle('active');
            markDirty();
        }
        function saveInterests() {
            const tags = document.querySelectorAll('#interests .interest-tag.active');
            const interests = Array.from(tags).map(t => t.textContent.trim());
            fetch('/api/profile/interests', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({interests}),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Interests updated', 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── ACCOUNT STATUS ───────────────────────────────
        function setStatus(el) {
            document.querySelectorAll('.status-option').forEach(s => s.classList.remove('active'));
            el.classList.add('active');
            const status = el.dataset.status;
            fetch('/api/profile/status', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({status}),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Status set to: ' + data.account_status, 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── PRIVACY ──────────────────────────────────────
        function savePrivacy() {
            const data = {
                who_can_view: document.getElementById('privacyView').value,
                who_can_message: document.getElementById('privacyMessage').value,
                show_location: document.getElementById('privacyLocation').value,
                show_activity_status: document.getElementById('privacyActivity').value,
                two_factor_auth: document.getElementById('privacy2FA').checked,
                profile_indexing: document.getElementById('privacyIndexing').checked,
            };
            fetch('/api/profile/privacy', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Privacy settings updated', 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── TENANT PROFILE ──────────────────────────────
        function saveTenantProfile() {
            const data = {
                monthly_income: parseInt(document.getElementById('tenantIncome').value) || 0,
                employment_status: document.getElementById('tenantEmployment').value,
                preferred_property_type: document.getElementById('tenantPropertyType').value,
                max_budget: parseInt(document.getElementById('tenantBudget').value) || 0,
            };
            fetch('/api/profile/tenant', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Tenant profile updated', 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── NOTIFICATIONS ──────────────────────────────
        function saveNotifications() {
            const data = {
                new_property_matches: document.getElementById('notifMatches').checked,
                payment_reminders: document.getElementById('notifPayments').checked,
                neighbourhood_alerts: document.getElementById('notifNeighbourhood').checked,
                promotional_offers: document.getElementById('notifPromo').checked,
                review_requests: document.getElementById('notifReviews').checked,
                email_digest: document.getElementById('notifDigest').checked,
            };
            fetch('/api/profile/notifications', {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify(data),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => toast('Notification preferences saved', 'success'))
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── LINKED ACCOUNTS ─────────────────────────────
        function loadLinkedAccounts() {
            fetch('/api/profile', {credentials: 'same-origin'})
            .then(res => res.json())
            .then(profile => {
                const container = document.getElementById('linkedAccountsContainer');
                container.innerHTML = '';
                const accounts = profile.linked_accounts || [];
                accounts.forEach(acc => {
                    const div = document.createElement('div');
                    div.className = 'linked-item';
                    const icon = getPlatformIcon(acc.platform);
                    div.innerHTML = `
                        <div class="linked-icon" style="background:#f0f2f8;color:#333"><i class="ti ${icon}"></i></div>
                        <div class="linked-info">
                            <div class="linked-name">${acc.platform}</div>
                            <div class="linked-status">${acc.connected ? 'Connected · ' + (acc.username || '') : 'Not connected'}</div>
                        </div>
                        <button class="linked-btn ${acc.connected ? 'connected' : 'connect'}" onclick="toggleLink('${acc.platform}', ${!acc.connected})">
                            ${acc.connected ? 'Connected' : 'Connect'}
                        </button>
                    `;
                    container.appendChild(div);
                });
            })
            .catch(err => toast('Error loading linked accounts', 'warning'));
        }

        function getPlatformIcon(platform) {
            const map = {
                'Facebook': 'ti-brand-facebook',
                'X (Twitter)': 'ti-brand-x',
                'Instagram': 'ti-brand-instagram',
                'Spotify': 'ti-brand-spotify',
                'Google': 'ti-brand-google'
            };
            return map[platform] || 'ti-plug';
        }

        function toggleLink(platform, connect) {
            const url = connect ? '/api/profile/link' : '/api/profile/unlink';
            fetch(url, {
                method: 'POST',
                headers: {'Content-Type':'application/json'},
                body: JSON.stringify({platform}),
                credentials: 'same-origin'
            })
            .then(res => res.json())
            .then(data => {
                toast(data.message || 'Updated', 'success');
                loadLinkedAccounts();
            })
            .catch(err => toast('Error: ' + err.message, 'warning'));
        }

        // ─── ACTIVITY ──────────────────────────────────────
        function loadActivity() {
            fetch('/api/activity', {credentials: 'same-origin'})
            .then(res => res.json())
            .then(activities => {
                const container = document.getElementById('activityTimeline');
                container.innerHTML = '';
                activities.forEach(act => {
                    const div = document.createElement('div');
                    div.className = 'activity-item';
                    const dotColor = act.type === 'apply' ? '#2eb89a' : act.type === 'save' ? '#e6b450' : act.type === 'review' ? '#3b82f6' : '#6d727a';
                    div.innerHTML = `
                        <div class="activity-dot" style="background:${dotColor}"></div>
                        <div class="activity-text">${act.text}</div>
                        <div class="activity-time">${act.time}</div>
                    `;
                    container.appendChild(div);
                });
            })
            .catch(err => toast('Error loading activity', 'warning'));
        }

        // ─── QR CODE (dummy) ──────────────────────────────
        (function buildQR() {
            const box = document.getElementById('qrBox');
            const N = 7;
            const pattern = [
                [1,1,1,1,1,1,1],
                [1,0,0,0,0,0,1],
                [1,0,1,1,1,0,1],
                [1,0,1,0,1,0,1],
                [1,0,1,1,1,0,1],
                [1,0,0,0,0,0,1],
                [1,1,1,1,1,1,1],
            ];
            pattern.forEach(row => {
                row.forEach(cell => {
                    const px = document.createElement('div');
                    px.className = 'qr-px';
                    px.style.background = cell ? '#0d0f14' : '#f0f2f8';
                    box.appendChild(px);
                });
            });
        })();

        // ─── COPY LINK ─────────────────────────────────────
        function copyLink() {
            const val = document.getElementById('shareLink').value;
            navigator.clipboard.writeText(val).catch(() => {});
            toast('Profile link copied to clipboard', 'success');
        }

        // ─── MODAL ─────────────────────────────────────────
        const MODALS = {
            logout: {
                title: 'Sign out of Mwarokin?',
                body: 'You will be signed out of your account on this device. Any unsaved changes will be lost.',
                confirm: 'Sign out',
                action: () => {
                    fetch('/api/auth/logout', {method:'POST', credentials:'same-origin'})
                    .then(() => toast('Signed out successfully', 'warning'))
                    .catch(() => toast('Logout failed', 'warning'));
                }
            },
            delete: {
                title: 'Delete account permanently?',
                body: 'This action cannot be undone. All your data, listings, reviews, and history will be permanently removed from Mwarokin Estates.',
                confirm: 'Delete forever',
                action: () => {
                    fetch('/api/profile/delete', {method:'POST', credentials:'same-origin'})
                    .then(() => toast('Deletion request submitted — you\'ll receive an email', 'warning'))
                    .catch(() => toast('Deletion request failed', 'warning'));
                }
            },
            pause: {
                title: 'Pause account?',
                body: 'Your profile will be hidden from other users and landlords. You can reactivate at any time from settings.',
                confirm: 'Pause account',
                action: () => {
                    fetch('/api/profile/pause', {method:'POST', credentials:'same-origin'})
                    .then(() => toast('Account paused. Reactivate anytime.', 'warning'))
                    .catch(() => toast('Pause failed', 'warning'));
                }
            },
            data: {
                title: 'Export your data?',
                body: 'We will prepare a ZIP file of all your data including profile, messages, payment history, and documents. This can take up to 24 hours.',
                confirm: 'Request export',
                action: () => {
                    fetch('/api/profile/export', {method:'POST', credentials:'same-origin'})
                    .then(() => toast('Data export requested — check your email in 24hrs', 'success'))
                    .catch(() => toast('Export request failed', 'warning'));
                }
            }
        };
        let currentModal = null;
        function showModal(key) {
            currentModal = MODALS[key];
            document.getElementById('modalTitle').textContent = currentModal.title;
            document.getElementById('modalBody').textContent = currentModal.body;
            document.getElementById('modalConfirm').textContent = currentModal.confirm;
            document.getElementById('modalBg').classList.add('open');
        }
        function closeModal(e) {
            if (!e || e.target === document.getElementById('modalBg')) {
                document.getElementById('modalBg').classList.remove('open');
            }
        }
        function confirmModal() {
            if (currentModal) currentModal.action();
            document.getElementById('modalBg').classList.remove('open');
        }

        // ─── KEYBOARD SAVE ──────────────────────────────
        document.addEventListener('keydown', e => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                saveProfile();
            }
        });

        // ─── INIT ──────────────────────────────────────────
        // Load profile data into form
        fetch('/api/profile', {credentials: 'same-origin'})
        .then(res => res.json())
        .then(profile => {
            document.getElementById('firstName').value = profile.first_name || '';
            document.getElementById('lastName').value = profile.last_name || '';
            document.getElementById('displayNameInput').value = profile.display_name || '';
            document.getElementById('email').value = profile.email || '';
            document.getElementById('phone').value = profile.phone || '';
            document.getElementById('dob').value = profile.date_of_birth || '';
            document.getElementById('bioInput').value = profile.bio || '';
            document.getElementById('locationInput').value = profile.location || '';
            document.getElementById('occupation').value = profile.occupation || '';
            // pronouns
            const pronounChips = document.querySelectorAll('.pronoun-chip');
            pronounChips.forEach(chip => {
                if (chip.textContent.trim() === profile.pronouns) {
                    chip.classList.add('selected');
                } else {
                    chip.classList.remove('selected');
                }
            });
            // language
            if (profile.language) {
                document.querySelectorAll('.lang-card').forEach(c => {
                    c.classList.toggle('active', c.dataset.lang === profile.language);
                });
                selectedLang = profile.language;
            }
            // interests
            if (profile.interests && profile.interests.length) {
                document.querySelectorAll('#interests .interest-tag').forEach(tag => {
                    const txt = tag.textContent.trim();
                    tag.classList.toggle('active', profile.interests.includes(txt));
                });
            }
            // notifications
            if (profile.notifications) {
                document.getElementById('notifMatches').checked = profile.notifications.new_property_matches !== false;
                document.getElementById('notifPayments').checked = profile.notifications.payment_reminders !== false;
                document.getElementById('notifNeighbourhood').checked = profile.notifications.neighbourhood_alerts !== false;
                document.getElementById('notifPromo').checked = profile.notifications.promotional_offers || false;
                document.getElementById('notifReviews').checked = profile.notifications.review_requests !== false;
                document.getElementById('notifDigest').checked = profile.notifications.email_digest || false;
            }
            // status
            if (profile.account_status) {
                document.querySelectorAll('.status-option').forEach(opt => {
                    opt.classList.toggle('active', opt.dataset.status === profile.account_status);
                });
            }
            // privacy
            if (profile.privacy) {
                document.getElementById('privacyView').value = profile.privacy.who_can_view || 'Everyone';
                document.getElementById('privacyMessage').value = profile.privacy.who_can_message || 'Verified users';
                document.getElementById('privacyLocation').value = profile.privacy.show_location || 'City only';
                document.getElementById('privacyActivity').value = profile.privacy.show_activity_status || 'Everyone';
                document.getElementById('privacy2FA').checked = profile.privacy.two_factor_auth !== false;
                document.getElementById('privacyIndexing').checked = profile.privacy.profile_indexing || false;
            }
            // tenant profile
            if (profile.tenant_profile) {
                document.getElementById('tenantIncome').value = profile.tenant_profile.monthly_income || '';
                document.getElementById('tenantEmployment').value = profile.tenant_profile.employment_status || 'Employed full-time';
                document.getElementById('tenantPropertyType').value = profile.tenant_profile.preferred_property_type || 'Apartment';
                document.getElementById('tenantBudget').value = profile.tenant_profile.max_budget || '';
            }
            // header info
            document.getElementById('displayName').textContent = profile.first_name + ' ' + profile.last_name;
            document.getElementById('userHandle').textContent = '@' + profile.display_name + ' · Tenant since Jan 2024';
            document.getElementById('profileLocation').textContent = profile.location || 'Nairobi, Kenya';
        })
        .catch(err => toast('Error loading profile: ' + err.message, 'warning'));

        // Load linked accounts and activity
        loadLinkedAccounts();
        loadActivity();

        // Ensure bio count updates on load
        updateBioCount();
    </script>
</body>
</html>
    '''
    return render_template_string(html_content)

# ============================================================================
# Run Application
# ============================================================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```
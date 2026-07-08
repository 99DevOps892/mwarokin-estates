```python
import os
import json
import pickle
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# ─── Configuration ──────────────────────────────────────────────────────────
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', 'your-client-id')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', 'your-client-secret')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', 'http://localhost:5000/oauth2callback')
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    TOKEN_FILE = 'token.pickle'

    @classmethod
    def get_flow(cls):
        return Flow.from_client_config(
            {
                "web": {
                    "client_id": cls.GOOGLE_CLIENT_ID,
                    "client_secret": cls.GOOGLE_CLIENT_SECRET,
                    "redirect_uris": [cls.GOOGLE_REDIRECT_URI],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=cls.SCOPES
        )

# ─── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Google Calendar Service ──────────────────────────────────────────────
class GoogleCalendarService:
    """Encapsulates all interactions with the Google Calendar API."""
    
    def __init__(self, credentials=None):
        self.credentials = credentials
        self.service = None
        if credentials and not credentials.expired:
            self.service = build('calendar', 'v3', credentials=credentials)
    
    def refresh_token(self):
        """Refresh credentials if expired."""
        if self.credentials and self.credentials.expired and self.credentials.refresh_token:
            self.credentials.refresh(Request())
            self._save_credentials()
            self.service = build('calendar', 'v3', credentials=self.credentials)
            return True
        return False
    
    def _save_credentials(self):
        """Persist credentials to disk."""
        with open(Config.TOKEN_FILE, 'wb') as f:
            pickle.dump(self.credentials, f)
    
    @staticmethod
    def load_credentials():
        """Load credentials from disk."""
        if os.path.exists(Config.TOKEN_FILE):
            with open(Config.TOKEN_FILE, 'rb') as f:
                return pickle.load(f)
        return None
    
    def get_events(self, max_results=10, time_min=None, time_max=None):
        """Fetch upcoming events from primary calendar."""
        if not self.service:
            raise ValueError("Service not initialized. Please authenticate first.")
        
        if time_min is None:
            time_min = datetime.utcnow().isoformat() + 'Z'
        if time_max is None:
            time_max = (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
        
        try:
            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            return events_result.get('items', [])
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}")
            raise
    
    def get_calendar_events_for_month(self, year, month):
        """Fetch events for a specific month (for calendar preview)."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        time_min = start_date.isoformat() + 'Z'
        time_max = end_date.isoformat() + 'Z'
        return self.get_events(max_results=50, time_min=time_min, time_max=time_max)
    
    def sync_events(self):
        """Perform a full sync: fetch events and return them."""
        return self.get_events(max_results=20)

# ─── Flask App ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# ─── HTML Template (Embedded) ─────────────────────────────────────────────
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sync Google Calendar · Mwarokin Estates</title>

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,300;14..32,400;14..32,500;14..32,600;14..32,700;14..32,800&display=swap" rel="stylesheet" />

    <!-- Font Awesome 6 (Pro-like) -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" />

    <style>
        /* ── Reset & Base ── */
        *,
        *::before,
        *::after {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #1a2a6c;
            --primary-light: #2d4a8e;
            --primary-dark: #0f1a4a;
            --accent: #c9a84c;
            --accent-light: #e4c96a;
            --accent-glow: rgba(201, 168, 76, 0.25);
            --surface: #ffffff;
            --surface-muted: #f8f9fc;
            --text-primary: #0b1426;
            --text-secondary: #3d4a5f;
            --text-muted: #7a88a0;
            --border: #e6eaf0;
            --shadow-sm: 0 2px 8px rgba(10, 20, 50, 0.06);
            --shadow-md: 0 8px 32px rgba(10, 20, 50, 0.10);
            --shadow-lg: 0 20px 60px rgba(10, 20, 50, 0.14);
            --shadow-xl: 0 30px 80px rgba(10, 20, 50, 0.20);
            --radius: 16px;
            --radius-sm: 10px;
            --radius-full: 999px;
            --transition: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        html {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            font-size: 16px;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            min-height: 100vh;
            background: var(--surface-muted);
            background-image:
                radial-gradient(ellipse at 10% 20%, rgba(26, 42, 108, 0.03) 0%, transparent 60%),
                radial-gradient(ellipse at 90% 80%, rgba(201, 168, 76, 0.04) 0%, transparent 60%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 24px;
            color: var(--text-primary);
        }

        /* ── Main Card ── */
        .app-container {
            width: 100%;
            max-width: 1100px;
            background: var(--surface);
            border-radius: var(--radius);
            box-shadow: var(--shadow-xl);
            overflow: hidden;
            position: relative;
            transition: var(--transition);
        }

        .app-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--accent), var(--primary));
            background-size: 200% 100%;
            animation: shimmerBar 4s ease-in-out infinite;
        }

        @keyframes shimmerBar {
            0%,
            100% {
                background-position: 0% 0%;
            }
            50% {
                background-position: 100% 0%;
            }
        }

        /* ── Header ── */
        .app-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 24px 36px;
            border-bottom: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.6);
            backdrop-filter: blur(4px);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .brand-icon {
            width: 44px;
            height: 44px;
            border-radius: var(--radius-sm);
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(26, 42, 108, 0.30);
            flex-shrink: 0;
        }

        .brand h1 {
            font-size: 22px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
        }

        .brand h1 span {
            color: var(--accent);
            font-weight: 600;
        }

        .brand-sub {
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 400;
            letter-spacing: 0.02em;
            margin-top: 1px;
        }

        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .header-actions .status-badge {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 18px;
            border-radius: var(--radius-full);
            background: #eaf6ef;
            color: #0e6b3e;
            font-size: 13px;
            font-weight: 500;
            border: 1px solid rgba(14, 107, 62, 0.15);
        }

        .header-actions .status-badge i {
            font-size: 10px;
            color: #0e6b3e;
        }

        .header-actions .status-badge.inactive {
            background: #fef1f0;
            color: #b33a34;
            border-color: rgba(179, 58, 52, 0.15);
        }

        .header-actions .status-badge.inactive i {
            color: #b33a34;
        }

        .avatar-btn {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary-light), var(--primary-dark));
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-weight: 600;
            font-size: 16px;
            border: none;
            cursor: pointer;
            transition: var(--transition);
            box-shadow: 0 2px 8px rgba(26, 42, 108, 0.20);
        }

        .avatar-btn:hover {
            transform: scale(1.05);
            box-shadow: 0 4px 16px rgba(26, 42, 108, 0.30);
        }

        /* ── Body Layout ── */
        .app-body {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 0;
            background: var(--surface);
        }

        /* ── Left Panel ── */
        .main-panel {
            padding: 36px 40px 40px;
        }

        .panel-title {
            font-size: 28px;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
            margin-bottom: 6px;
        }

        .panel-sub {
            font-size: 15px;
            color: var(--text-secondary);
            margin-bottom: 28px;
            line-height: 1.6;
        }

        .panel-sub strong {
            color: var(--primary);
            font-weight: 600;
        }

        /* ── Sync Card ── */
        .sync-card {
            background: var(--surface-muted);
            border-radius: var(--radius);
            padding: 28px 30px;
            border: 1px solid var(--border);
            transition: var(--transition);
            margin-bottom: 28px;
        }

        .sync-card:hover {
            border-color: #cdd5e5;
            box-shadow: var(--shadow-sm);
        }

        .sync-card .card-label {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 16px;
        }

        .sync-card .card-label i {
            color: var(--accent);
            font-size: 16px;
        }

        .sync-account {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 16px 20px;
            background: var(--surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            margin-bottom: 18px;
            transition: var(--transition);
        }

        .sync-account:hover {
            border-color: #cdd5e5;
        }

        .sync-account .account-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: linear-gradient(135deg, #f5f0e8, #e8e0d4);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: var(--primary);
            flex-shrink: 0;
        }

        .sync-account .account-info {
            flex: 1;
        }

        .sync-account .account-info .name {
            font-weight: 600;
            font-size: 15px;
            color: var(--text-primary);
        }

        .sync-account .account-info .email {
            font-size: 13px;
            color: var(--text-muted);
        }

        .sync-account .account-status {
            font-size: 12px;
            font-weight: 500;
            padding: 4px 12px;
            border-radius: var(--radius-full);
            background: #eaf6ef;
            color: #0e6b3e;
        }

        .sync-account .account-status.inactive {
            background: #fef1f0;
            color: #b33a34;
        }

        .sync-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-top: 4px;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            padding: 12px 26px;
            border-radius: var(--radius-full);
            font-weight: 600;
            font-size: 14px;
            border: none;
            cursor: pointer;
            transition: var(--transition);
            text-decoration: none;
            font-family: inherit;
            letter-spacing: 0.01em;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            color: #fff;
            box-shadow: 0 4px 16px rgba(26, 42, 108, 0.25);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 28px rgba(26, 42, 108, 0.35);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-primary i {
            font-size: 15px;
        }

        .btn-outline {
            background: transparent;
            color: var(--text-secondary);
            border: 1.5px solid var(--border);
        }

        .btn-outline:hover {
            border-color: var(--primary);
            color: var(--primary);
            background: rgba(26, 42, 108, 0.04);
        }

        .btn-outline i {
            font-size: 15px;
        }

        .btn-accent {
            background: linear-gradient(135deg, var(--accent), var(--accent-light));
            color: #1a1a1a;
            box-shadow: 0 4px 16px rgba(201, 168, 76, 0.30);
        }

        .btn-accent:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 28px rgba(201, 168, 76, 0.40);
        }

        .btn-danger-outline {
            background: transparent;
            color: #b33a34;
            border: 1.5px solid #f5d6d4;
        }

        .btn-danger-outline:hover {
            background: #fef1f0;
            border-color: #b33a34;
        }

        /* ── Sync Options ── */
        .sync-options {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-top: 18px;
        }

        .option-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 16px;
            background: var(--surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            transition: var(--transition);
            cursor: default;
        }

        .option-item:hover {
            border-color: #cdd5e5;
            background: #fafbff;
        }

        .option-item .toggle {
            width: 40px;
            height: 22px;
            background: #d0d7e6;
            border-radius: var(--radius-full);
            position: relative;
            cursor: pointer;
            transition: var(--transition);
            flex-shrink: 0;
        }

        .option-item .toggle.active {
            background: var(--primary);
        }

        .option-item .toggle::after {
            content: '';
            position: absolute;
            top: 2px;
            left: 2px;
            width: 18px;
            height: 18px;
            background: #fff;
            border-radius: 50%;
            transition: var(--transition);
            box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
        }

        .option-item .toggle.active::after {
            left: 20px;
        }

        .option-item .opt-label {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
        }

        .option-item .opt-desc {
            font-size: 12px;
            color: var(--text-muted);
            display: block;
            margin-top: 1px;
        }

        /* ── Right Panel ── */
        .side-panel {
            padding: 36px 32px 40px;
            background: var(--surface-muted);
            border-left: 1px solid var(--border);
            display: flex;
            flex-direction: column;
        }

        .side-panel .side-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .side-panel .side-title i {
            color: var(--accent);
        }

        .side-panel .side-sub {
            font-size: 14px;
            color: var(--text-muted);
            margin-bottom: 20px;
            line-height: 1.5;
        }

        /* ── Calendar Preview ── */
        .calendar-preview {
            background: var(--surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            padding: 16px 18px;
            margin-bottom: 20px;
        }

        .calendar-preview .cal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }

        .calendar-preview .cal-header .month {
            font-weight: 600;
            font-size: 15px;
            color: var(--text-primary);
        }

        .calendar-preview .cal-header .cal-nav {
            display: flex;
            gap: 6px;
        }

        .calendar-preview .cal-header .cal-nav button {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            border: none;
            background: var(--surface-muted);
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
            font-size: 13px;
        }

        .calendar-preview .cal-header .cal-nav button:hover {
            background: var(--border);
        }

        .calendar-preview .cal-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 2px;
            text-align: center;
        }

        .calendar-preview .cal-grid .day-label {
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            padding: 4px 0;
            letter-spacing: 0.04em;
        }

        .calendar-preview .cal-grid .day {
            font-size: 13px;
            font-weight: 500;
            color: var(--text-secondary);
            padding: 6px 0;
            border-radius: 6px;
            transition: var(--transition);
            cursor: default;
        }

        .calendar-preview .cal-grid .day.today {
            background: var(--primary);
            color: #fff;
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(26, 42, 108, 0.25);
        }

        .calendar-preview .cal-grid .day.event {
            color: var(--primary);
            font-weight: 600;
            position: relative;
        }

        .calendar-preview .cal-grid .day.event::after {
            content: '';
            position: absolute;
            bottom: 2px;
            left: 50%;
            transform: translateX(-50%);
            width: 4px;
            height: 4px;
            border-radius: 50%;
            background: var(--accent);
        }

        .calendar-preview .cal-grid .day.other {
            color: #c5ccdb;
        }

        /* ── Upcoming Events ── */
        .upcoming-events {
            flex: 1;
        }

        .upcoming-events .events-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .upcoming-events .events-title a {
            font-size: 13px;
            font-weight: 500;
            color: var(--primary);
            text-decoration: none;
        }

        .event-item {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 12px 14px;
            background: var(--surface);
            border-radius: var(--radius-sm);
            border: 1px solid var(--border);
            margin-bottom: 10px;
            transition: var(--transition);
        }

        .event-item:hover {
            border-color: #cdd5e5;
            box-shadow: var(--shadow-sm);
        }

        .event-item .event-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
            background: var(--accent);
        }

        .event-item .event-dot.blue {
            background: var(--primary-light);
        }
        .event-item .event-dot.green {
            background: #2d8f5e;
        }
        .event-item .event-dot.purple {
            background: #7c5cbf;
        }

        .event-item .event-info {
            flex: 1;
            min-width: 0;
        }

        .event-item .event-info .ev-name {
            font-weight: 500;
            font-size: 14px;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .event-item .event-info .ev-time {
            font-size: 12px;
            color: var(--text-muted);
        }

        .event-item .event-info .ev-location {
            font-size: 12px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 4px;
        }

        .event-item .event-info .ev-location i {
            font-size: 11px;
        }

        /* ── Footer ── */
        .app-footer {
            padding: 16px 36px;
            border-top: 1px solid var(--border);
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 13px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.4);
        }

        .app-footer .footer-links {
            display: flex;
            gap: 20px;
        }

        .app-footer .footer-links a {
            color: var(--text-muted);
            text-decoration: none;
            transition: var(--transition);
        }

        .app-footer .footer-links a:hover {
            color: var(--primary);
        }

        /* ── Toast / Notification ── */
        .toast-container {
            position: fixed;
            bottom: 30px;
            right: 30px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 999;
            max-width: 400px;
            width: 100%;
        }

        .toast {
            padding: 16px 22px;
            border-radius: var(--radius-sm);
            background: var(--surface);
            box-shadow: var(--shadow-lg);
            border-left: 4px solid var(--primary);
            display: flex;
            align-items: center;
            gap: 14px;
            animation: slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            transform-origin: bottom right;
            border: 1px solid var(--border);
        }

        .toast.success {
            border-left-color: #0e6b3e;
        }

        .toast.error {
            border-left-color: #b33a34;
        }

        .toast .toast-icon {
            font-size: 20px;
            color: var(--primary);
            flex-shrink: 0;
        }

        .toast.success .toast-icon {
            color: #0e6b3e;
        }
        .toast.error .toast-icon {
            color: #b33a34;
        }

        .toast .toast-msg {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
            flex: 1;
        }

        .toast .toast-close {
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 16px;
            padding: 4px;
            transition: var(--transition);
        }

        .toast .toast-close:hover {
            color: var(--text-primary);
        }

        @keyframes slideUp {
            0% {
                opacity: 0;
                transform: translateY(30px) scale(0.95);
            }
            100% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* ── Responsive ── */
        @media (max-width: 992px) {
            .app-body {
                grid-template-columns: 1fr;
            }
            .side-panel {
                border-left: none;
                border-top: 1px solid var(--border);
                padding: 28px 32px 32px;
            }
            .main-panel {
                padding: 28px 28px 20px;
            }
            .app-header {
                padding: 18px 24px;
                flex-wrap: wrap;
                gap: 12px;
            }
            .header-actions .status-badge {
                font-size: 12px;
                padding: 6px 14px;
            }
            .brand h1 {
                font-size: 19px;
            }
            .panel-title {
                font-size: 24px;
            }
        }

        @media (max-width: 600px) {
            body {
                padding: 12px;
            }
            .app-header {
                padding: 14px 18px;
                flex-direction: column;
                align-items: flex-start;
            }
            .header-actions {
                width: 100%;
                justify-content: space-between;
            }
            .main-panel {
                padding: 20px 18px 16px;
            }
            .side-panel {
                padding: 20px 18px 24px;
            }
            .sync-options {
                grid-template-columns: 1fr;
            }
            .sync-card {
                padding: 20px 18px;
            }
            .sync-actions {
                flex-direction: column;
            }
            .sync-actions .btn {
                width: 100%;
                justify-content: center;
            }
            .app-footer {
                flex-direction: column;
                gap: 10px;
                padding: 14px 18px;
                text-align: center;
            }
            .panel-title {
                font-size: 21px;
            }
            .toast-container {
                bottom: 16px;
                right: 16px;
                left: 16px;
                max-width: 100%;
            }
            .toast {
                padding: 14px 16px;
            }
        }

        /* ── Scrollbar ── */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-track {
            background: var(--surface-muted);
        }
        ::-webkit-scrollbar-thumb {
            background: #cdd5e5;
            border-radius: var(--radius-full);
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #b0bad0;
        }

        /* ── Loading shimmer ── */
        .loading-shimmer {
            animation: shimmer 1.2s ease-in-out infinite;
            background: linear-gradient(90deg, #f0f2f8 25%, #e6eaf2 50%, #f0f2f8 75%);
            background-size: 200% 100%;
            border-radius: 6px;
        }

        @keyframes shimmer {
            0% {
                background-position: -200% 0;
            }
            100% {
                background-position: 200% 0;
            }
        }
    </style>
</head>
<body>

    <!-- ─── APP ─── -->
    <div class="app-container" id="app">

        <!-- ── Header ── -->
        <header class="app-header">
            <div class="brand">
                <div class="brand-icon">
                    <i class="fas fa-building"></i>
                </div>
                <div>
                    <h1>Mwarokin <span>Estates</span></h1>
                    <div class="brand-sub">Property Management · Calendar Sync</div>
                </div>
            </div>
            <div class="header-actions">
                <span class="status-badge {{ 'inactive' if not connected else '' }}" id="syncStatusBadge">
                    <i class="fas fa-circle"></i> {{ 'Connected' if connected else 'Disconnected' }}
                </span>
                <button class="avatar-btn" title="Account">ME</button>
            </div>
        </header>

        <!-- ── Body ── -->
        <div class="app-body">

            <!-- Left Panel -->
            <main class="main-panel">
                <h2 class="panel-title">Google Calendar Sync</h2>
                <p class="panel-sub">
                    Connect your <strong>Google Calendar</strong> to automatically sync property
                    viewings, meetings, and events across your Mwarokin Estates portfolio.
                </p>

                <!-- Sync Card -->
                <div class="sync-card">
                    <div class="card-label">
                        <i class="fas fa-google"></i> Google Account
                    </div>

                    <div class="sync-account" id="accountDisplay">
                        <div class="account-avatar">
                            <i class="fas fa-user-circle"></i>
                        </div>
                        <div class="account-info">
                            <div class="name" id="accountName">{{ account_name if account_name else 'Not connected' }}</div>
                            <div class="email" id="accountEmail">{{ account_email if account_email else '—' }}</div>
                        </div>
                        <span class="account-status {{ 'inactive' if not connected else '' }}" id="accountStatus">
                            {{ 'Active' if connected else 'Inactive' }}
                        </span>
                    </div>

                    <div class="sync-actions">
                        <button class="btn btn-primary" id="syncNowBtn">
                            <i class="fas fa-sync-alt"></i> Sync Now
                        </button>
                        {% if not connected %}
                        <a href="{{ url_for('connect') }}" class="btn btn-outline" id="connectBtn">
                            <i class="fab fa-google"></i> Connect Account
                        </a>
                        {% else %}
                        <button class="btn btn-danger-outline" id="disconnectBtn">
                            <i class="fas fa-unlink"></i> Disconnect
                        </button>
                        {% endif %}
                    </div>

                    <div class="sync-options">
                        <div class="option-item">
                            <div class="toggle active" data-opt="autoSync" id="autoSyncToggle"></div>
                            <div>
                                <div class="opt-label">Auto-sync</div>
                                <span class="opt-desc">Every 15 minutes</span>
                            </div>
                        </div>
                        <div class="option-item">
                            <div class="toggle active" data-opt="eventReminders" id="remindersToggle"></div>
                            <div>
                                <div class="opt-label">Reminders</div>
                                <span class="opt-desc">30 min before events</span>
                            </div>
                        </div>
                        <div class="option-item">
                            <div class="toggle" data-opt="attendees" id="attendeesToggle"></div>
                            <div>
                                <div class="opt-label">Attendee sync</div>
                                <span class="opt-desc">Invite team members</span>
                            </div>
                        </div>
                        <div class="option-item">
                            <div class="toggle active" data-opt="propertyEvents" id="propertyEventsToggle"></div>
                            <div>
                                <div class="opt-label">Property events</div>
                                <span class="opt-desc">Viewings &amp; inspections</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Last sync info -->
                <div style="display:flex; align-items:center; gap:16px; flex-wrap:wrap; font-size:14px; color:var(--text-muted);">
                    <span><i class="far fa-clock" style="margin-right:6px;"></i> Last sync: <strong id="lastSyncTime">{{ last_sync or 'Never' }}</strong></span>
                    <span><i class="far fa-calendar-alt" style="margin-right:6px;"></i> Next sync: <strong id="nextSyncTime">{{ next_sync or '—' }}</strong></span>
                    <span style="display:flex; align-items:center; gap:6px;">
                        <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:{{ '#0e6b3e' if connected else '#b33a34' }};" id="syncDot"></span>
                        <span id="syncStatusText">{{ 'Online' if connected else 'Offline' }}</span>
                    </span>
                </div>
            </main>

            <!-- Right Panel -->
            <aside class="side-panel">
                <div class="side-title">
                    <i class="fas fa-calendar-check"></i> Calendar Overview
                </div>
                <div class="side-sub">Upcoming property events &amp; meetings this week</div>

                <!-- Calendar Preview -->
                <div class="calendar-preview" id="calendarPreview">
                    <div class="cal-header">
                        <span class="month" id="calMonth">{{ cal_month }} {{ cal_year }}</span>
                        <div class="cal-nav">
                            <button id="calPrev"><i class="fas fa-chevron-left"></i></button>
                            <button id="calNext"><i class="fas fa-chevron-right"></i></button>
                        </div>
                    </div>
                    <div class="cal-grid" id="calGrid">
                        <!-- dynamically built -->
                    </div>
                </div>

                <!-- Upcoming Events -->
                <div class="upcoming-events">
                    <div class="events-title">
                        <span><i class="far fa-list-alt" style="margin-right:8px;"></i> Upcoming Events</span>
                        <a href="#">View all</a>
                    </div>
                    {% for event in upcoming_events %}
                    <div class="event-item">
                        <span class="event-dot blue"></span>
                        <div class="event-info">
                            <div class="ev-name">{{ event.summary }}</div>
                            <div class="ev-time">{{ event.start.dateTime or event.start.date }}</div>
                        </div>
                    </div>
                    {% else %}
                    <div class="event-item">
                        <span class="event-dot" style="background:#ccc;"></span>
                        <div class="event-info">
                            <div class="ev-name">No upcoming events</div>
                            <div class="ev-time">—</div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </aside>
        </div>

        <!-- ── Footer ── -->
        <footer class="app-footer">
            <span>&copy; 2026 Mwarokin Estates · All rights reserved</span>
            <div class="footer-links">
                <a href="#">Privacy</a>
                <a href="#">Terms</a>
                <a href="#">Support</a>
                <a href="#"><i class="fab fa-google"></i> Calendar API</a>
            </div>
        </footer>
    </div>

    <!-- ─── Toast Container ─── -->
    <div class="toast-container" id="toastContainer"></div>

    <!-- ─── JavaScript ─── -->
    <script>
        (function() {
            'use strict';

            // ── DOM refs ──
            const syncBtn = document.getElementById('syncNowBtn');
            const disconnectBtn = document.getElementById('disconnectBtn');
            const statusBadge = document.getElementById('syncStatusBadge');
            const accountStatus = document.getElementById('accountStatus');
            const lastSyncEl = document.getElementById('lastSyncTime');
            const nextSyncEl = document.getElementById('nextSyncTime');
            const syncDot = document.getElementById('syncDot');
            const syncStatusText = document.getElementById('syncStatusText');

            // Toggles
            const autoSyncToggle = document.getElementById('autoSyncToggle');
            const remindersToggle = document.getElementById('remindersToggle');
            const attendeesToggle = document.getElementById('attendeesToggle');
            const propertyEventsToggle = document.getElementById('propertyEventsToggle');

            // Calendar
            const calMonth = document.getElementById('calMonth');
            const calGrid = document.getElementById('calGrid');
            const calPrev = document.getElementById('calPrev');
            const calNext = document.getElementById('calNext');

            const toastContainer = document.getElementById('toastContainer');

            // ── State ──
            let isConnected = {{ 'true' if connected else 'false' }};
            let isSyncing = false;
            let syncInterval = null;
            let currentDate = new Date();
            let currentMonth = currentDate.getMonth();
            let currentYear = currentDate.getFullYear();

            // ── Toast system ──
            function showToast(message, type = 'info', duration = 4000) {
                const iconMap = {
                    info: 'fas fa-info-circle',
                    success: 'fas fa-check-circle',
                    error: 'fas fa-exclamation-circle',
                };
                const toast = document.createElement('div');
                toast.className = `toast ${type}`;
                toast.innerHTML = `
                    <span class="toast-icon"><i class="${iconMap[type] || iconMap.info}"></i></span>
                    <span class="toast-msg">${message}</span>
                    <button class="toast-close"><i class="fas fa-times"></i></button>
                `;
                toastContainer.appendChild(toast);

                const close = () => {
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(20px) scale(0.95)';
                    setTimeout(() => toast.remove(), 300);
                };

                toast.querySelector('.toast-close').addEventListener('click', close);
                setTimeout(close, duration);

                return toast;
            }

            // ── Update status UI ──
            function updateStatus(connected) {
                isConnected = connected;
                if (connected) {
                    statusBadge.className = 'status-badge';
                    statusBadge.innerHTML = '<i class="fas fa-circle"></i> Connected';
                    accountStatus.textContent = 'Active';
                    accountStatus.className = 'account-status';
                    syncDot.style.background = '#0e6b3e';
                    syncStatusText.textContent = 'Online';
                } else {
                    statusBadge.className = 'status-badge inactive';
                    statusBadge.innerHTML = '<i class="fas fa-circle"></i> Disconnected';
                    accountStatus.textContent = 'Inactive';
                    accountStatus.className = 'account-status inactive';
                    syncDot.style.background = '#b33a34';
                    syncStatusText.textContent = 'Offline';
                }
            }

            // ── Sync action (AJAX) ──
            function performSync() {
                if (!isConnected) {
                    showToast('Please connect a Google account first.', 'error');
                    return;
                }
                if (isSyncing) return;

                isSyncing = true;
                syncBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Syncing…';
                syncBtn.disabled = true;

                fetch('/sync', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showToast('Sync completed successfully!', 'success');
                            const now = new Date();
                            const timeStr = now.toLocaleString('en-US', {
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true
                            });
                            lastSyncEl.textContent = `Today, ${timeStr}`;
                            // next sync (15 min later)
                            const next = new Date(now.getTime() + 15 * 60000);
                            const nextStr = next.toLocaleString('en-US', {
                                hour: 'numeric',
                                minute: '2-digit',
                                hour12: true
                            });
                            nextSyncEl.textContent = nextStr;
                            // update events list
                            location.reload(); // simple refresh to show new events
                        } else {
                            showToast('Sync failed: ' + (data.message || 'Unknown error'), 'error');
                        }
                    })
                    .catch(err => {
                        showToast('Network error during sync', 'error');
                        console.error(err);
                    })
                    .finally(() => {
                        isSyncing = false;
                        syncBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Sync Now';
                        syncBtn.disabled = false;
                    });
            }

            // ── Toggle handler ──
            function setupToggle(el, label) {
                el.addEventListener('click', function(e) {
                    e.stopPropagation();
                    this.classList.toggle('active');
                    const active = this.classList.contains('active');
                    showToast(`${label} ${active ? 'enabled' : 'disabled'}`, 'info', 1800);
                    // Optionally send state to backend
                });
            }

            setupToggle(autoSyncToggle, 'Auto-sync');
            setupToggle(remindersToggle, 'Reminders');
            setupToggle(attendeesToggle, 'Attendee sync');
            setupToggle(propertyEventsToggle, 'Property events');

            // ── Disconnect ──
            if (disconnectBtn) {
                disconnectBtn.addEventListener('click', function() {
                    if (!isConnected) {
                        showToast('No account to disconnect.', 'error');
                        return;
                    }
                    showToast('Disconnecting…', 'info', 1500);
                    fetch('/disconnect', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                updateStatus(false);
                                showToast('Disconnected from Google Calendar.', 'error');
                                setTimeout(() => location.reload(), 1000);
                            } else {
                                showToast('Disconnect failed.', 'error');
                            }
                        })
                        .catch(err => {
                            showToast('Network error during disconnect', 'error');
                        });
                });
            }

            // ── Sync Now ──
            syncBtn.addEventListener('click', performSync);

            // ── Calendar rendering ──
            function renderCalendar(month, year) {
                const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ];
                calMonth.textContent = `${monthNames[month]} ${year}`;

                const firstDay = new Date(year, month, 1).getDay();
                const daysInMonth = new Date(year, month + 1, 0).getDate();
                const daysInPrevMonth = new Date(year, month, 0).getDate();

                const today = new Date();
                const todayDate = today.getDate();
                const todayMonth = today.getMonth();
                const todayYear = today.getFullYear();

                // Fetch event days from backend? For now, static demo.
                // We'll use a set of demo days if not connected, or fetch via AJAX.
                // For simplicity, we keep static demo data.
                const eventDays = [5, 12, 18, 24, 28];

                let html = '';
                const dayLabels = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
                dayLabels.forEach(label => {
                    html += `<div class="day-label">${label}</div>`;
                });

                // Previous month days
                const startOffset = firstDay === 0 ? 6 : firstDay - 1;
                for (let i = startOffset - 1; i >= 0; i--) {
                    const d = daysInPrevMonth - i;
                    html += `<div class="day other">${d}</div>`;
                }

                // Current month days
                for (let d = 1; d <= daysInMonth; d++) {
                    let classes = 'day';
                    if (d === todayDate && month === todayMonth && year === todayYear) {
                        classes += ' today';
                    }
                    if (eventDays.includes(d) && !(d === todayDate && month === todayMonth && year === todayYear)) {
                        classes += ' event';
                    }
                    html += `<div class="${classes}">${d}</div>`;
                }

                // Next month days (fill last row)
                const totalCells = startOffset + daysInMonth;
                const remaining = (7 - (totalCells % 7)) % 7;
                for (let d = 1; d <= remaining; d++) {
                    html += `<div class="day other">${d}</div>`;
                }

                calGrid.innerHTML = html;
            }

            // ── Calendar navigation ──
            function changeMonth(delta) {
                currentMonth += delta;
                if (currentMonth > 11) {
                    currentMonth = 0;
                    currentYear++;
                } else if (currentMonth < 0) {
                    currentMonth = 11;
                    currentYear--;
                }
                renderCalendar(currentMonth, currentYear);
                // Optionally fetch events for this month via AJAX and update event dots
            }

            calPrev.addEventListener('click', () => changeMonth(-1));
            calNext.addEventListener('click', () => changeMonth(1));

            // ── Init ──
            renderCalendar(currentMonth, currentYear);

            // ── Auto-sync timer (if enabled) ──
            function startAutoSync() {
                if (syncInterval) clearInterval(syncInterval);
                syncInterval = setInterval(() => {
                    if (autoSyncToggle.classList.contains('active') && isConnected) {
                        performSync();
                    }
                }, 15000); // every 15s for demo (real: 15min)
            }

            startAutoSync();

            // ── Toggle auto-sync restarts timer ──
            autoSyncToggle.addEventListener('click', function() {
                if (this.classList.contains('active')) {
                    startAutoSync();
                    showToast('Auto-sync resumed', 'info', 1500);
                } else {
                    if (syncInterval) {
                        clearInterval(syncInterval);
                        syncInterval = null;
                    }
                    showToast('Auto-sync paused', 'info', 1500);
                }
            });

            // ── Welcome toast ──
            setTimeout(() => {
                showToast('Welcome back, Mwarokin Estates!', 'success', 3000);
            }, 600);

            // ── Keyboard shortcut: Cmd/Ctrl + Shift + S = Sync ──
            document.addEventListener('keydown', (e) => {
                if ((e.metaKey || e.ctrlKey) && e.shiftKey && (e.key === 'S' || e.key === 's')) {
                    e.preventDefault();
                    performSync();
                }
            });

            // ── Expose for console debugging ──
            window.__app = {
                performSync,
                showToast,
                isConnected: () => isConnected,
                toggleAutoSync: () => autoSyncToggle.click(),
            };

        })();
    </script>

</body>
</html>
'''

# ─── Routes ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    """Render the main dashboard."""
    connected = False
    account_name = None
    account_email = None
    upcoming_events = []
    last_sync = None
    next_sync = None

    # Load credentials from file or session
    creds = GoogleCalendarService.load_credentials()
    if creds and not creds.expired:
        connected = True
        # Attempt to get user info (only email from token)
        try:
            service = GoogleCalendarService(creds)
            # We don't have user info endpoint easily, so we'll just use placeholder
            account_name = "Mwarokin Admin"
            account_email = creds.id_token.get('email') if creds.id_token else 'admin@mwarokin.co.ke'
        except Exception:
            pass
        # Fetch upcoming events
        try:
            service = GoogleCalendarService(creds)
            events = service.get_events(max_results=5)
            for ev in events:
                start = ev['start'].get('dateTime', ev['start'].get('date'))
                upcoming_events.append({
                    'summary': ev.get('summary', 'Untitled'),
                    'start': {'dateTime': start}
                })
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
    else:
        connected = False

    # For demo, if no events, add placeholder
    if not upcoming_events:
        upcoming_events = [
            {'summary': 'Lavington Estate Viewing', 'start': {'dateTime': 'Today, 2:00 PM'}},
            {'summary': 'Property Inspection · Karen', 'start': {'dateTime': 'Tomorrow, 10:00 AM'}},
        ]

    # Calendar month/year
    now = datetime.now()
    cal_month = now.strftime('%B')
    cal_year = now.year

    return render_template_string(
        HTML_TEMPLATE,
        connected=connected,
        account_name=account_name,
        account_email=account_email,
        upcoming_events=upcoming_events,
        last_sync=last_sync,
        next_sync=next_sync,
        cal_month=cal_month,
        cal_year=cal_year
    )

@app.route('/connect')
def connect():
    """Initiate OAuth2 flow."""
    flow = Config.get_flow()
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback."""
    state = session.get('state')
    flow = Config.get_flow()
    flow.redirect_uri = Config.GOOGLE_REDIRECT_URI
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    # Save credentials
    with open(Config.TOKEN_FILE, 'wb') as f:
        pickle.dump(credentials, f)
    return redirect(url_for('index'))

@app.route('/sync', methods=['POST'])
def sync():
    """Trigger a manual sync and return JSON."""
    try:
        creds = GoogleCalendarService.load_credentials()
        if not creds or creds.expired:
            return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401
        
        service = GoogleCalendarService(creds)
        events = service.sync_events()
        # Here you would also update your local database, but we just return success.
        return jsonify({'status': 'success', 'message': f'Synced {len(events)} events'})
    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect():
    """Revoke token and delete stored credentials."""
    creds = GoogleCalendarService.load_credentials()
    if creds:
        # Revoke token
        try:
            import requests
            requests.post('https://oauth2.googleapis.com/revoke',
                          params={'token': creds.token},
                          headers={'content-type': 'application/x-www-form-urlencoded'})
        except Exception as e:
            logger.error(f"Revoke error: {e}")
        # Delete token file
        if os.path.exists(Config.TOKEN_FILE):
            os.remove(Config.TOKEN_FILE)
    return jsonify({'status': 'success', 'message': 'Disconnected'})

# ─── Main ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```
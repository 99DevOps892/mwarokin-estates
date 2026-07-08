```python
"""
Mwarokin Estates - RBC Onboarding Portal
Modern, professional, premium Flask application with advanced features.

This application serves the onboarding wizard UI and provides a robust backend
for handling profile data, property assignments, permissions, audit trails,
and secure file uploads. Built with SQLAlchemy, WTForms, and best practices.

Requirements (see requirements.txt):
- Flask
- Flask-SQLAlchemy
- Flask-WTF
- Flask-Login (optional but good for user sessions)
- Pillow (for image validation)
- python-dotenv
- werkzeug
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import json
import secrets
import re

from flask import (
    Flask, render_template, request, jsonify, session,
    redirect, url_for, send_from_directory, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SelectField, BooleanField, FileField, HiddenField
from wtforms.validators import DataRequired, Email, Length, Optional as OptOptional
from flask_wtf.file import FileAllowed, FileRequired
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import dotenv

# Load environment variables
dotenv.load_dotenv()

# -----------------------------------------------------------------------------
# Application Configuration
# -----------------------------------------------------------------------------
class Config:
    """Application configuration with sensible defaults and security."""
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'onboarding.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    SESSION_TYPE = 'filesystem'  # Simple session storage
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour

    # Ensure upload directory exists
    Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)


app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db = SQLAlchemy(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Database Models (Advanced ORM with relationships)
# -----------------------------------------------------------------------------
class User(db.Model):
    """Represents an onboarding user (RBC team member)."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    cell_phone = db.Column(db.String(30), nullable=False)
    id_passport_number = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='caretaker')  # caretaker, fieldAgent
    profile_image_path = db.Column(db.String(255))
    id_document_path = db.Column(db.String(255))
    property_mode = db.Column(db.String(20), default='single')  # single, multiple
    single_property_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    finalized = db.Column(db.Boolean, default=False)
    finalized_at = db.Column(db.DateTime)

    # Relationships
    property_assignments = db.relationship('PropertyAssignment', backref='user', lazy=True, cascade='all, delete-orphan')
    permissions = db.relationship('Permission', backref='user', uselist=False, cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self, include_relations=True):
        """Convert user to dict for API responses."""
        data = {
            'id': self.id,
            'fullName': self.full_name,
            'email': self.email,
            'cellPhone': self.cell_phone,
            'idPassportNumber': self.id_passport_number,
            'role': self.role,
            'profileImage': self.profile_image_path,
            'idDocument': self.id_document_path,
            'propertyMode': self.property_mode,
            'singlePropertyId': self.single_property_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'finalized': self.finalized,
            'finalizedAt': self.finalized_at.isoformat() if self.finalized_at else None,
        }
        if include_relations:
            data['properties'] = [p.to_dict() for p in self.property_assignments]
            data['permissions'] = self.permissions.to_dict() if self.permissions else {}
            data['auditLogs'] = [log.to_dict() for log in self.audit_logs[:50]]  # latest 50
        return data

    def __repr__(self):
        return f'<User {self.full_name}>'


class PropertyAssignment(db.Model):
    """Many-to-many relation between users and properties (pre-defined list)."""
    __tablename__ = 'property_assignments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    property_id = db.Column(db.String(50), nullable=False)  # prop_1, prop_2, etc.
    property_name = db.Column(db.String(100), nullable=False)
    property_type = db.Column(db.String(50))
    address = db.Column(db.String(200))
    multi_family = db.Column(db.Boolean, default=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.property_id,
            'name': self.property_name,
            'type': self.property_type,
            'address': self.address,
            'multiFamily': self.multi_family,
            'assignedAt': self.assigned_at.isoformat() if self.assigned_at else None,
        }


class Permission(db.Model):
    """Fine-grained permissions for a user, overriding role defaults."""
    __tablename__ = 'permissions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    view_property = db.Column(db.Boolean, default=True)
    edit_property_details = db.Column(db.Boolean, default=False)
    manage_tenants = db.Column(db.Boolean, default=False)
    access_financials = db.Column(db.Boolean, default=False)
    view_audit_logs = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'viewProperty': self.view_property,
            'editPropertyDetails': self.edit_property_details,
            'manageTenants': self.manage_tenants,
            'accessFinancials': self.access_financials,
            'viewAuditLogs': self.view_audit_logs,
        }


class AuditLog(db.Model):
    """Immutable audit trail for compliance."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable for system logs
    message = db.Column(db.String(500), nullable=False)
    log_type = db.Column(db.String(20), default='info')  # info, warning, error, success
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    ip_address = db.Column(db.String(45))  # IPv6 ready
    user_agent = db.Column(db.String(200))

    def to_dict(self):
        return {
            'id': self.id,
            'message': self.message,
            'type': self.log_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }


# -----------------------------------------------------------------------------
# WTForms for validation (advanced)
# -----------------------------------------------------------------------------
class ProfileForm(FlaskForm):
    """Form for step 1: profile and role."""
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    email = EmailField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    cell_phone = StringField('Cell Phone', validators=[DataRequired(), Length(max=30)])
    id_passport_number = StringField('ID/Passport Number', validators=[DataRequired(), Length(max=50)])
    role = SelectField('Role', choices=[
        ('caretaker', 'Caretaker'),
        ('fieldAgent', 'Property Management Field Agent')
    ], validators=[DataRequired()])
    profile_image = FileField('Profile Image', validators=[
        OptOptional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    id_document = FileField('ID Document', validators=[
        OptOptional(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])


class PropertySelectionForm(FlaskForm):
    """Form for step 2: property mode and selections."""
    mode = SelectField('Property Mode', choices=[
        ('single', 'Single Property'),
        ('multiple', 'Multiple Properties')
    ], validators=[DataRequired()])
    single_property_id = StringField('Single Property ID')
    selected_properties = HiddenField('Selected Properties (JSON)')


class PermissionForm(FlaskForm):
    """Form for step 3: permission overrides."""
    view_property = BooleanField('View Property Details', default=True)
    edit_property_details = BooleanField('Edit Property Details', default=False)
    manage_tenants = BooleanField('Manage Tenants & Rentals', default=False)
    access_financials = BooleanField('Access Financial Reports', default=False)
    view_audit_logs = BooleanField('View Audit Logs', default=True)


# -----------------------------------------------------------------------------
# Helper Functions (Business Logic)
# -----------------------------------------------------------------------------
def get_default_permissions(role: str) -> Dict[str, bool]:
    """Return default permissions based on role."""
    if role == 'caretaker':
        return {
            'view_property': True,
            'edit_property_details': False,
            'manage_tenants': False,
            'access_financials': False,
            'view_audit_logs': True,
        }
    else:  # fieldAgent
        return {
            'view_property': True,
            'edit_property_details': True,
            'manage_tenants': True,
            'access_financials': True,
            'view_audit_logs': True,
        }


def save_uploaded_file(file, subfolder: str = '') -> Optional[str]:
    """Save an uploaded file securely, return relative path."""
    if not file or file.filename == '':
        return None

    # Secure filename and generate unique name to avoid collisions
    original_filename = secure_filename(file.filename)
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    unique_id = secrets.token_hex(4)
    filename = f"{timestamp}_{unique_id}_{original_filename}"
    folder = os.path.join(app.config['UPLOAD_FOLDER'], subfolder)
    Path(folder).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(folder, filename)

    # Save file
    file.save(filepath)

    # Optionally validate and compress image
    try:
        with Image.open(filepath) as img:
            # Validate image dimensions (optional)
            if img.width > 2000 or img.height > 2000:
                img.thumbnail((2000, 2000))
                img.save(filepath, quality=85)
    except Exception as e:
        logger.warning(f"Image processing failed: {e}")
        # Still keep file

    # Return relative path for database storage
    rel_path = os.path.join('uploads', subfolder, filename).replace('\\', '/')
    return rel_path


def create_audit_log(user_id: Optional[int], message: str, log_type: str = 'info',
                     ip: str = None, user_agent: str = None):
    """Create an audit log entry."""
    log = AuditLog(
        user_id=user_id,
        message=message,
        log_type=log_type,
        ip_address=ip,
        user_agent=user_agent
    )
    db.session.add(log)
    db.session.commit()
    return log


def get_or_create_user_from_session() -> Optional[User]:
    """Retrieve user from session or create new if not exists."""
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return user

    # Create new user session
    user = User(
        full_name='',
        email='',
        cell_phone='',
        id_passport_number='',
        role='caretaker'
    )
    db.session.add(user)
    db.session.commit()
    session['user_id'] = user.id
    # Create default permissions
    perms = get_default_permissions(user.role)
    permission = Permission(
        user_id=user.id,
        view_property=perms['view_property'],
        edit_property_details=perms['edit_property_details'],
        manage_tenants=perms['manage_tenants'],
        access_financials=perms['access_financials'],
        view_audit_logs=perms['view_audit_logs']
    )
    db.session.add(permission)
    db.session.commit()
    create_audit_log(user.id, "Onboarding session started", "info",
                     request.remote_addr, request.user_agent.string)
    return user


# -----------------------------------------------------------------------------
# Routes (Main UI and API endpoints)
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    """Serve the main onboarding portal UI."""
    # Ensure user exists in session
    user = get_or_create_user_from_session()
    return render_template('index.html', user=user)


@app.route('/api/profile', methods=['POST'])
def save_profile():
    """Save profile data from step 1."""
    user = get_or_create_user_from_session()
    form = ProfileForm()

    if form.validate_on_submit():
        # Update user fields
        user.full_name = form.full_name.data.strip()
        user.email = form.email.data.strip().lower()
        user.cell_phone = form.cell_phone.data.strip()
        user.id_passport_number = form.id_passport_number.data.strip()
        user.role = form.role.data

        # Handle file uploads
        if form.profile_image.data:
            path = save_uploaded_file(form.profile_image.data, 'profiles')
            if path:
                user.profile_image_path = path
                create_audit_log(user.id, f"Profile image uploaded: {form.profile_image.data.filename}",
                                 "info", request.remote_addr, request.user_agent.string)

        if form.id_document.data:
            path = save_uploaded_file(form.id_document.data, 'ids')
            if path:
                user.id_document_path = path
                create_audit_log(user.id, f"ID document uploaded: {form.id_document.data.filename}",
                                 "info", request.remote_addr, request.user_agent.string)

        # Update permissions if role changed
        if user.role != form.role.data:
            # Role changed, update permissions to defaults
            perms = get_default_permissions(form.role.data)
            if user.permissions:
                user.permissions.view_property = perms['view_property']
                user.permissions.edit_property_details = perms['edit_property_details']
                user.permissions.manage_tenants = perms['manage_tenants']
                user.permissions.access_financials = perms['access_financials']
                user.permissions.view_audit_logs = perms['view_audit_logs']
            create_audit_log(user.id, f"Role changed to {form.role.data}",
                             "info", request.remote_addr, request.user_agent.string)

        db.session.commit()
        create_audit_log(user.id, "Profile updated successfully",
                         "info", request.remote_addr, request.user_agent.string)

        return jsonify({
            'status': 'success',
            'message': 'Profile saved successfully',
            'user': user.to_dict(include_relations=False)
        })
    else:
        return jsonify({
            'status': 'error',
            'errors': form.errors
        }), 400


@app.route('/api/properties', methods=['POST'])
def save_properties():
    """Save property assignments from step 2."""
    user = get_or_create_user_from_session()
    form = PropertySelectionForm()

    if form.validate_on_submit():
        mode = form.mode.data
        user.property_mode = mode

        # Delete existing property assignments
        PropertyAssignment.query.filter_by(user_id=user.id).delete()

        if mode == 'single':
            prop_id = form.single_property_id.data
            if prop_id:
                # Lookup property details from predefined list (could be in DB)
                from app_data import AVAILABLE_PROPERTIES  # import at top later
                prop = next((p for p in AVAILABLE_PROPERTIES if p['id'] == prop_id), None)
                if prop:
                    assignment = PropertyAssignment(
                        user_id=user.id,
                        property_id=prop['id'],
                        property_name=prop['name'],
                        property_type=prop['type'],
                        address=prop['address'],
                        multi_family=prop['multiFamily']
                    )
                    db.session.add(assignment)
                    user.single_property_id = prop_id
                    create_audit_log(user.id, f"Single property assigned: {prop['name']}",
                                     "info", request.remote_addr, request.user_agent.string)
        else:  # multiple
            selected = json.loads(form.selected_properties.data) if form.selected_properties.data else []
            for prop_id in selected:
                prop = next((p for p in AVAILABLE_PROPERTIES if p['id'] == prop_id), None)
                if prop:
                    assignment = PropertyAssignment(
                        user_id=user.id,
                        property_id=prop['id'],
                        property_name=prop['name'],
                        property_type=prop['type'],
                        address=prop['address'],
                        multi_family=prop['multiFamily']
                    )
                    db.session.add(assignment)
            create_audit_log(user.id, f"Multiple properties assigned: {len(selected)} properties",
                             "info", request.remote_addr, request.user_agent.string)

        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Properties saved successfully',
            'user': user.to_dict(include_relations=True)
        })
    else:
        return jsonify({
            'status': 'error',
            'errors': form.errors
        }), 400


@app.route('/api/permissions', methods=['POST'])
def save_permissions():
    """Save permission overrides from step 3."""
    user = get_or_create_user_from_session()
    form = PermissionForm()

    if form.validate_on_submit():
        if not user.permissions:
            # Create if missing
            perms = get_default_permissions(user.role)
            user.permissions = Permission(
                user_id=user.id,
                view_property=perms['view_property'],
                edit_property_details=perms['edit_property_details'],
                manage_tenants=perms['manage_tenants'],
                access_financials=perms['access_financials'],
                view_audit_logs=perms['view_audit_logs']
            )

        # Update with form data
        user.permissions.view_property = form.view_property.data
        user.permissions.edit_property_details = form.edit_property_details.data
        user.permissions.manage_tenants = form.manage_tenants.data
        user.permissions.access_financials = form.access_financials.data
        user.permissions.view_audit_logs = form.view_audit_logs.data

        db.session.commit()
        create_audit_log(user.id, "Permissions updated",
                         "info", request.remote_addr, request.user_agent.string)

        return jsonify({
            'status': 'success',
            'message': 'Permissions saved successfully',
            'permissions': user.permissions.to_dict()
        })
    else:
        return jsonify({
            'status': 'error',
            'errors': form.errors
        }), 400


@app.route('/api/audit', methods=['GET'])
def get_audit_logs():
    """Retrieve audit logs for current user."""
    user = get_or_create_user_from_session()
    logs = AuditLog.query.filter_by(user_id=user.id).order_by(AuditLog.timestamp.desc()).limit(50).all()
    return jsonify({
        'status': 'success',
        'logs': [log.to_dict() for log in logs]
    })


@app.route('/api/audit', methods=['POST'])
def add_audit_log():
    """Add a custom audit log entry (from frontend)."""
    user = get_or_create_user_from_session()
    data = request.get_json()
    message = data.get('message', '')
    log_type = data.get('type', 'info')
    if message:
        create_audit_log(user.id, message, log_type,
                         request.remote_addr, request.user_agent.string)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': 'Missing message'}), 400


@app.route('/api/finalize', methods=['POST'])
def finalize_onboarding():
    """Finalize onboarding process."""
    user = get_or_create_user_from_session()
    user.finalized = True
    user.finalized_at = datetime.utcnow()
    db.session.commit()
    create_audit_log(user.id, "Onboarding finalized",
                     "success", request.remote_addr, request.user_agent.string)
    return jsonify({
        'status': 'success',
        'message': 'Onboarding finalized successfully',
        'user': user.to_dict(include_relations=True)
    })


@app.route('/static/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files securely."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


# -----------------------------------------------------------------------------
# Error Handlers (Professional)
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({'status': 'error', 'message': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {e}")
    return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


# -----------------------------------------------------------------------------
# Application Data (Predefined properties)
# -----------------------------------------------------------------------------
AVAILABLE_PROPERTIES = [
    {"id": "prop_1", "name": "Harmony Heights", "type": "Single Family", "multiFamily": False, "address": "12 Serenity Lane"},
    {"id": "prop_2", "name": "Palm Grove Village", "type": "Multi-Family Rental", "multiFamily": True, "address": "450 Palm Blvd"},
    {"id": "prop_3", "name": "Cedar Creek Apartments", "type": "Multi-Family Rental", "multiFamily": True, "address": "88 Cedarwood Dr"},
    {"id": "prop_4", "name": "Lakeside Villa", "type": "Single Family", "multiFamily": False, "address": "22 Lakeview Rd"},
    {"id": "prop_5", "name": "Maple Gardens", "type": "Multi-Family Rental", "multiFamily": True, "address": "101 Maple Ave"},
]

# Make available to routes
app.config['AVAILABLE_PROPERTIES'] = AVAILABLE_PROPERTIES


# -----------------------------------------------------------------------------
# Template Context Processor (make properties available in templates)
# -----------------------------------------------------------------------------
@app.context_processor
def inject_properties():
    return dict(available_properties=AVAILABLE_PROPERTIES)


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)

# -----------------------------------------------------------------------------
# Notes for production:
# - Use a production-grade WSGI server (gunicorn, waitress)
# - Set SECRET_KEY via environment variable
# - Use PostgreSQL or MySQL in production
# - Enable HTTPS with SSL/TLS
# - Implement user authentication (e.g., Flask-Login) for multi-user support
# - Add rate limiting for API endpoints
# - Schedule regular database backups
# -----------------------------------------------------------------------------
```
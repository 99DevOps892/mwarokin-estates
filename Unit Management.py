```python
"""
Mwarokin Estates - Property Management System
Modern Flask application with SQLAlchemy ORM and RESTful API.
"""

import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, func

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mwarokin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ----------------------------- Models -----------------------------

class Unit(db.Model):
    """Property unit model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), default='Vacant')  # Vacant, Occupied, Partial
    unit_type = db.Column(db.String(50))  # Apartment, Condo, Single-Family
    beds = db.Column(db.Integer, default=0)
    baths = db.Column(db.Float, default=0.0)
    sqft = db.Column(db.Integer, default=0)
    rent = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    files = db.relationship('File', backref='unit', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'address': self.address,
            'status': self.status,
            'unit_type': self.unit_type,
            'beds': self.beds,
            'baths': self.baths,
            'sqft': self.sqft,
            'rent': self.rent,
            'file_count': len(self.files),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Unit {self.name}>'


class File(db.Model):
    """File/document model associated with a unit"""
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    file_type = db.Column(db.String(50))  # pdf, doc, img, etc.
    size_mb = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Uploaded')  # Uploaded, In Review, Pending
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'file_type': self.file_type,
            'size_mb': self.size_mb,
            'status': self.status,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'unit_id': self.unit_id,
            'unit_name': self.unit.name if self.unit else None
        }

    def __repr__(self):
        return f'<File {self.filename}>'


# ----------------------------- Database Initialization -----------------------------

def init_db():
    """Create tables and seed initial data if empty."""
    db.create_all()

    if Unit.query.count() == 0:
        # Seed units from the UI
        units_data = [
            {
                'name': 'Boston Ave',
                'address': '23 Boston Ave, Medford, MA',
                'status': 'Vacant',
                'unit_type': 'Single-Family',
                'beds': 1,
                'baths': 1.0,
                'sqft': 549,
                'rent': 33000.0
            },
            {
                'name': 'Boylston Street · Unit 1',
                'address': '883-885 Boylston St, Boston, MA',
                'status': 'Occupied',
                'unit_type': 'Apartment',
                'beds': 2,
                'baths': 2.0,
                'sqft': 0,
                'rent': 7000.0
            },
            {
                'name': 'Boylston Street · Unit 2',
                'address': '883-885 Boylston St, Boston, MA',
                'status': 'Occupied',
                'unit_type': 'Condo',
                'beds': 2,
                'baths': 2.0,
                'sqft': 0,
                'rent': 500.0
            },
            {
                'name': 'Unit 90',
                'address': 'Mwarokin Estates, MA',
                'status': 'Partial',
                'unit_type': 'Apartment',
                'beds': 0,
                'baths': 0.0,
                'sqft': 0,
                'rent': 0.0
            }
        ]

        for data in units_data:
            unit = Unit(**data)
            db.session.add(unit)
        db.session.commit()

        # Seed files after units are created
        files_data = [
            {'filename': 'Boston_Ave_Lease_2026.pdf', 'file_type': 'pdf', 'size_mb': 2.4,
             'status': 'Uploaded', 'unit_name': 'Boston Ave'},
            {'filename': 'Boylston_Unit1_Tenant_Agreement.docx', 'file_type': 'doc', 'size_mb': 1.8,
             'status': 'In Review', 'unit_name': 'Boylston Street · Unit 1'},
            {'filename': 'Boston_Ave_Floor_Plan.png', 'file_type': 'img', 'size_mb': 3.1,
             'status': 'Uploaded', 'unit_name': 'Boston Ave'},
            {'filename': 'Unit90_Inspection_Report.pdf', 'file_type': 'doc', 'size_mb': 0.9,
             'status': 'Pending', 'unit_name': 'Unit 90'}
        ]

        for data in files_data:
            unit = Unit.query.filter_by(name=data['unit_name']).first()
            if unit:
                file = File(
                    filename=data['filename'],
                    file_type=data['file_type'],
                    size_mb=data['size_mb'],
                    status=data['status'],
                    unit_id=unit.id
                )
                db.session.add(file)
        db.session.commit()


# ----------------------------- Routes -----------------------------

@app.route('/')
def index():
    """Main dashboard page."""
    units = Unit.query.all()
    files = File.query.all()
    # Compute stats
    total_units = len(units)
    occupied = sum(1 for u in units if u.status == 'Occupied')
    vacant = sum(1 for u in units if u.status == 'Vacant')
    total_files = len(files)

    # For "new uploads" we can count files from last 7 days
    week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    # adjust for timezone naive
    new_uploads = File.query.filter(File.upload_date >= week_ago).count()

    stats = {
        'total_units': total_units,
        'occupied': occupied,
        'vacant': vacant,
        'total_files': total_files,
        'new_uploads': new_uploads
    }

    return render_template('index.html', units=units, files=files, stats=stats)


# ----------------------------- API Endpoints -----------------------------

@app.route('/api/units', methods=['GET'])
def api_units_get():
    """List all units."""
    units = Unit.query.all()
    return jsonify([u.to_dict() for u in units]), 200


@app.route('/api/units', methods=['POST'])
def api_units_post():
    """Create a new unit."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    required = ['name', 'address']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    unit = Unit(
        name=data['name'],
        address=data['address'],
        status=data.get('status', 'Vacant'),
        unit_type=data.get('unit_type'),
        beds=data.get('beds', 0),
        baths=data.get('baths', 0.0),
        sqft=data.get('sqft', 0),
        rent=data.get('rent', 0.0)
    )
    db.session.add(unit)
    db.session.commit()
    return jsonify(unit.to_dict()), 201


@app.route('/api/units/<int:unit_id>', methods=['GET'])
def api_unit_get(unit_id):
    """Get a single unit."""
    unit = Unit.query.get_or_404(unit_id)
    return jsonify(unit.to_dict()), 200


@app.route('/api/units/<int:unit_id>', methods=['PUT'])
def api_unit_put(unit_id):
    """Update a unit."""
    unit = Unit.query.get_or_404(unit_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    unit.name = data.get('name', unit.name)
    unit.address = data.get('address', unit.address)
    unit.status = data.get('status', unit.status)
    unit.unit_type = data.get('unit_type', unit.unit_type)
    unit.beds = data.get('beds', unit.beds)
    unit.baths = data.get('baths', unit.baths)
    unit.sqft = data.get('sqft', unit.sqft)
    unit.rent = data.get('rent', unit.rent)
    unit.updated_at = datetime.utcnow()

    db.session.commit()
    return jsonify(unit.to_dict()), 200


@app.route('/api/units/<int:unit_id>', methods=['DELETE'])
def api_unit_delete(unit_id):
    """Delete a unit."""
    unit = Unit.query.get_or_404(unit_id)
    db.session.delete(unit)
    db.session.commit()
    return jsonify({'message': 'Unit deleted'}), 200


@app.route('/api/files', methods=['GET'])
def api_files_get():
    """List all files."""
    files = File.query.all()
    return jsonify([f.to_dict() for f in files]), 200


@app.route('/api/files', methods=['POST'])
def api_files_post():
    """Create a new file."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    required = ['filename', 'unit_id']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing field: {field}'}), 400

    # Check unit exists
    unit = Unit.query.get(data['unit_id'])
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404

    file = File(
        filename=data['filename'],
        file_type=data.get('file_type'),
        size_mb=data.get('size_mb', 0.0),
        status=data.get('status', 'Uploaded'),
        unit_id=data['unit_id']
    )
    db.session.add(file)
    db.session.commit()
    return jsonify(file.to_dict()), 201


@app.route('/api/files/<int:file_id>', methods=['GET'])
def api_file_get(file_id):
    """Get a single file."""
    file = File.query.get_or_404(file_id)
    return jsonify(file.to_dict()), 200


@app.route('/api/files/<int:file_id>', methods=['PUT'])
def api_file_put(file_id):
    """Update a file."""
    file = File.query.get_or_404(file_id)
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON data'}), 400

    file.filename = data.get('filename', file.filename)
    file.file_type = data.get('file_type', file.file_type)
    file.size_mb = data.get('size_mb', file.size_mb)
    file.status = data.get('status', file.status)
    if 'unit_id' in data:
        unit = Unit.query.get(data['unit_id'])
        if not unit:
            return jsonify({'error': 'Unit not found'}), 404
        file.unit_id = data['unit_id']

    db.session.commit()
    return jsonify(file.to_dict()), 200


@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def api_file_delete(file_id):
    """Delete a file."""
    file = File.query.get_or_404(file_id)
    db.session.delete(file)
    db.session.commit()
    return jsonify({'message': 'File deleted'}), 200


@app.route('/api/search')
def api_search():
    """Search units and files by query string."""
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'units': [], 'files': []}), 200

    # Search units by name or address
    units = Unit.query.filter(
        or_(
            Unit.name.ilike(f'%{q}%'),
            Unit.address.ilike(f'%{q}%')
        )
    ).all()

    # Search files by filename
    files = File.query.filter(
        File.filename.ilike(f'%{q}%')
    ).all()

    return jsonify({
        'units': [u.to_dict() for u in units],
        'files': [f.to_dict() for f in files]
    }), 200


# ----------------------------- Template (included as string) -----------------------------

TEMPLATE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mwarokin Estates · Property Manager</title>
    <!-- Font Awesome (free) -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <!-- Google Fonts (Inter) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400;14..32,500;14..32,600;14..32,700&display=swap" rel="stylesheet">
    <style>
        /* ─── Reset & Base ─── */
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            color: #0f172a;
            display: flex;
            min-height: 100vh;
        }
        a { text-decoration: none; color: inherit; }
        button { cursor: pointer; font-family: inherit; border: none; background: none; }

        /* ─── Scrollbar ─── */
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #f1f5f9; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 8px; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

        /* ─── Sidebar ─── */
        .sidebar {
            width: 280px;
            background: #0f172a;
            color: #e2e8f0;
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
            padding: 28px 20px;
            height: 100vh;
            position: sticky;
            top: 0;
            overflow-y: auto;
            transition: transform 0.3s ease;
            z-index: 100;
        }
        .sidebar-brand {
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 40px;
            padding-bottom: 24px;
            border-bottom: 1px solid rgba(255,255,255,0.06);
        }
        .brand-icon {
            width: 44px;
            height: 44px;
            background: #3b82f6;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            color: white;
        }
        .sidebar-brand h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: white;
        }
        .sidebar-brand h1 span {
            font-weight: 400;
            color: #94a3b8;
            font-size: 16px;
        }

        .sidebar-nav { flex: 1; }
        .nav-label {
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            color: #64748b;
            margin: 24px 0 12px 0;
            padding-left: 4px;
        }
        .sidebar-nav a {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 500;
            color: #94a3b8;
            transition: 0.2s;
            margin-bottom: 2px;
        }
        .sidebar-nav a i { width: 20px; font-size: 16px; text-align: center; }
        .sidebar-nav a:hover { background: rgba(255,255,255,0.06); color: #f1f5f9; }
        .sidebar-nav a.active {
            background: rgba(59,130,246,0.15);
            color: #60a5fa;
        }
        .badge {
            margin-left: auto;
            background: rgba(255,255,255,0.08);
            padding: 2px 12px;
            border-radius: 30px;
            font-size: 12px;
            font-weight: 600;
            color: #cbd5e1;
        }

        .sidebar-footer {
            margin-top: auto;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.06);
        }
        .user-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 8px 0;
        }
        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #3b82f6;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            color: white;
        }
        .user-info .name { font-size: 14px; font-weight: 600; color: white; }
        .user-info .role { font-size: 12px; color: #94a3b8; }

        /* ─── Overlay (mobile) ─── */
        .overlay {
            display: none;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.4);
            z-index: 90;
            backdrop-filter: blur(2px);
        }
        .overlay.show { display: block; }

        /* ─── Main ─── */
        .main {
            flex: 1;
            padding: 28px 36px 40px;
            min-width: 0;
        }

        /* Topbar */
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 32px;
        }
        .topbar-left h2 {
            font-size: 24px;
            font-weight: 700;
            letter-spacing: -0.3px;
        }
        .topbar-left p {
            font-size: 14px;
            color: #64748b;
            margin-top: 2px;
        }
        .topbar-left p i { margin-right: 4px; color: #94a3b8; }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .search-wrap {
            display: flex;
            align-items: center;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 30px;
            padding: 6px 16px 6px 14px;
            transition: 0.2s;
        }
        .search-wrap:focus-within { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }
        .search-wrap i { color: #94a3b8; font-size: 14px; margin-right: 8px; }
        .search-wrap input {
            border: none;
            outline: none;
            background: transparent;
            font-size: 14px;
            padding: 6px 0;
            width: 180px;
            color: #0f172a;
        }
        .search-wrap input::placeholder { color: #94a3b8; }

        .btn-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: white;
            border: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #475569;
            transition: 0.2s;
            position: relative;
        }
        .btn-icon:hover { background: #f1f5f9; }
        .btn-icon .dot {
            width: 8px;
            height: 8px;
            background: #ef4444;
            border-radius: 50%;
            position: absolute;
            top: 6px;
            right: 6px;
            border: 2px solid white;
        }

        .btn-primary {
            background: #0f172a;
            color: white;
            padding: 10px 20px;
            border-radius: 30px;
            font-weight: 600;
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: 0.2s;
            border: 1px solid transparent;
        }
        .btn-primary:hover { background: #1e293b; }
        .btn-primary i { font-size: 14px; }

        .sidebar-toggle {
            display: none;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 6px 12px;
            font-size: 18px;
            color: #475569;
        }
        .sidebar-toggle:hover { background: #f1f5f9; }

        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 36px;
        }
        .stat-card {
            background: white;
            padding: 20px 24px;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
            border: 1px solid #f1f4f9;
        }
        .stat-label {
            font-size: 13px;
            font-weight: 500;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .stat-label i { color: #94a3b8; }
        .stat-value {
            font-size: 32px;
            font-weight: 700;
            margin: 4px 0 6px;
            letter-spacing: -0.5px;
        }
        .stat-change {
            font-size: 13px;
            color: #22c55e;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #f0fdf4;
            padding: 2px 10px;
            border-radius: 30px;
        }
        .stat-change.negative { color: #ef4444; background: #fef2f2; }
        .stat-change i { font-size: 12px; }

        /* Section header */
        .section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 32px 0 20px;
        }
        .section-header h3 {
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .view-options {
            display: flex;
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
        }
        .view-options button {
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            color: #64748b;
            background: transparent;
            border: none;
            transition: 0.2s;
        }
        .view-options button i { margin-right: 4px; }
        .view-options button.active {
            background: #0f172a;
            color: white;
        }
        .view-options button:not(.active):hover { background: #f1f5f9; }

        /* Unit Grid */
        .unit-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }
        .unit-card {
            background: white;
            border-radius: 16px;
            border: 1px solid #f1f4f9;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            transition: 0.2s;
        }
        .unit-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.06); border-color: #e2e8f0; }

        .card-header {
            padding: 18px 20px 12px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            border-bottom: 1px solid #f1f4f9;
        }
        .unit-title .name {
            font-size: 16px;
            font-weight: 600;
            display: block;
        }
        .unit-title .address {
            font-size: 13px;
            color: #64748b;
            display: flex;
            align-items: center;
            gap: 4px;
            margin-top: 2px;
        }
        .unit-title .address i { font-size: 12px; color: #94a3b8; }

        .status-badge {
            font-size: 11px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 30px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            white-space: nowrap;
        }
        .status-badge.vacant { background: #fef2f2; color: #dc2626; }
        .status-badge.occupied { background: #ecfdf5; color: #16a34a; }
        .status-badge.partial { background: #fefce8; color: #ca8a04; }

        .card-body {
            padding: 16px 20px;
        }
        .specs {
            display: flex;
            flex-wrap: wrap;
            gap: 12px 18px;
            margin-bottom: 14px;
        }
        .spec-item {
            font-size: 13px;
            color: #475569;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .spec-item i { color: #94a3b8; width: 16px; }
        .spec-item strong { color: #0f172a; }

        .rent-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rent {
            font-size: 22px;
            font-weight: 700;
            color: #0f172a;
        }
        .rent span {
            font-size: 14px;
            font-weight: 400;
            color: #94a3b8;
        }
        .tag {
            font-size: 12px;
            background: #f1f5f9;
            padding: 4px 14px;
            border-radius: 30px;
            color: #475569;
            font-weight: 500;
        }

        .card-footer {
            padding: 12px 20px 16px;
            border-top: 1px solid #f1f4f9;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .actions {
            display: flex;
            gap: 8px;
        }
        .actions button {
            font-size: 13px;
            font-weight: 500;
            color: #64748b;
            padding: 4px 12px;
            border-radius: 8px;
            transition: 0.2s;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .actions button:hover { background: #f1f5f9; color: #0f172a; }
        .actions .primary-action {
            background: #eff6ff;
            color: #2563eb;
        }
        .actions .primary-action:hover { background: #dbeafe; }
        .file-count {
            font-size: 13px;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 4px;
        }

        /* File Manager */
        .file-manager {
            background: white;
            border-radius: 16px;
            border: 1px solid #f1f4f9;
            padding: 24px;
            margin-top: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }
        .fm-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
            margin-bottom: 20px;
        }
        .fm-header h3 {
            font-size: 18px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .fm-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .fm-actions button {
            padding: 8px 16px;
            border-radius: 30px;
            font-size: 13px;
            font-weight: 500;
            background: #f1f5f9;
            color: #475569;
            transition: 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .fm-actions button:hover { background: #e2e8f0; }
        .fm-actions button.primary {
            background: #0f172a;
            color: white;
        }
        .fm-actions button.primary:hover { background: #1e293b; }

        .file-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .file-row {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 12px 16px;
            border-radius: 12px;
            background: #f8fafc;
            transition: 0.2s;
            flex-wrap: wrap;
        }
        .file-row:hover { background: #f1f5f9; }
        .file-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            color: white;
        }
        .file-icon.pdf { background: #ef4444; }
        .file-icon.doc { background: #3b82f6; }
        .file-icon.img { background: #8b5cf6; }

        .file-info {
            flex: 1;
            min-width: 160px;
        }
        .file-info .fname {
            font-weight: 600;
            font-size: 14px;
        }
        .file-info .fmeta {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            font-size: 12px;
            color: #94a3b8;
            margin-top: 2px;
        }
        .file-info .fmeta i { margin-right: 2px; }

        .file-status {
            font-size: 12px;
            font-weight: 500;
            padding: 4px 12px;
            border-radius: 30px;
            background: #f1f5f9;
            color: #475569;
        }
        .file-status.uploaded { background: #ecfdf5; color: #16a34a; }
        .file-status.review { background: #eff6ff; color: #2563eb; }
        .file-status.pending { background: #fefce8; color: #ca8a04; }

        .file-actions {
            display: flex;
            gap: 6px;
        }
        .file-actions button {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: transparent;
            color: #94a3b8;
            transition: 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .file-actions button:hover { background: #e2e8f0; color: #0f172a; }

        /* ─── Responsive ─── */
        @media (max-width: 992px) {
            .sidebar { transform: translateX(-100%); }
            .sidebar.open { transform: translateX(0); }
            .sidebar-toggle { display: inline-flex; }
            .overlay.show { display: block; }
        }
        @media (max-width: 768px) {
            .main { padding: 20px 16px; }
            .topbar-left h2 { font-size: 20px; }
            .stats-grid { grid-template-columns: 1fr 1fr; }
            .unit-grid { grid-template-columns: 1fr; }
            .file-row { flex-wrap: wrap; }
        }
        @media (max-width: 480px) {
            .stats-grid { grid-template-columns: 1fr; }
            .topbar-right .search-wrap input { width: 120px; }
        }
    </style>
</head>
<body>

    <!-- Overlay -->
    <div class="overlay" id="overlay"></div>

    <!-- Sidebar -->
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
            <div class="brand-icon"><i class="fas fa-building"></i></div>
            <h1>Mwarokin<span>Estates</span></h1>
        </div>
        <nav class="sidebar-nav">
            <div class="nav-label">Main</div>
            <a href="/" class="active"><i class="fas fa-th-large"></i> Dashboard</a>
            <a href="#"><i class="fas fa-building"></i> Units <span class="badge">{{ stats.total_units }}</span></a>
            <a href="#"><i class="fas fa-folder-open"></i> Files <span class="badge">{{ stats.total_files }}</span></a>
            <a href="#"><i class="fas fa-users"></i> Tenants</a>

            <div class="nav-label" style="margin-top:28px;">Management</div>
            <a href="#"><i class="fas fa-file-invoice"></i> Lease Agreements</a>
            <a href="#"><i class="fas fa-calendar-alt"></i> Maintenance</a>
            <a href="#"><i class="fas fa-chart-pie"></i> Reports</a>

            <div class="nav-label" style="margin-top:28px;">Settings</div>
            <a href="#"><i class="fas fa-sliders-h"></i> Preferences</a>
            <a href="#"><i class="fas fa-question-circle"></i> Help Center</a>
        </nav>
        <div class="sidebar-footer">
            <div class="user-card">
                <div class="user-avatar">JD</div>
                <div class="user-info">
                    <div class="name">James Duncan</div>
                    <div class="role">Property Manager</div>
                </div>
                <i class="fas fa-ellipsis-v" style="color:rgba(255,255,255,0.2);cursor:pointer;"></i>
            </div>
        </div>
    </aside>

    <!-- Main -->
    <main class="main">

        <!-- Top Bar -->
        <div class="topbar">
            <div class="topbar-left">
                <div style="display:flex;align-items:center;gap:12px;">
                    <button class="sidebar-toggle" id="sidebarToggle"><i class="fas fa-bars"></i></button>
                    <div>
                        <h2>Unit Management</h2>
                        <p><i class="fas fa-map-pin"></i> Mwarokin Estates · {{ stats.total_units }} units · {{ stats.total_files }} files</p>
                    </div>
                </div>
            </div>
            <div class="topbar-right">
                <div class="search-wrap" id="searchWrap">
                    <i class="fas fa-search"></i>
                    <input type="text" id="searchInput" placeholder="Search units, files..." />
                </div>
                <button class="btn-icon"><i class="fas fa-bell"></i><span class="dot"></span></button>
                <button class="btn-icon"><i class="fas fa-upload"></i></button>
                <button class="btn-primary" id="addUnitBtn"><i class="fas fa-plus"></i> Add Unit</button>
            </div>
        </div>

        <!-- Stats -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label"><i class="fas fa-building"></i> Total Units</div>
                <div class="stat-value">{{ stats.total_units }}</div>
                <span class="stat-change"><i class="fas fa-arrow-up"></i> +2 this month</span>
            </div>
            <div class="stat-card">
                <div class="stat-label"><i class="fas fa-user-check"></i> Occupied</div>
                <div class="stat-value">{{ stats.occupied }}</div>
                <span class="stat-change"><i class="fas fa-arrow-up"></i> {{ (stats.occupied / stats.total_units * 100)|round(0) if stats.total_units else 0 }}% occupancy</span>
            </div>
            <div class="stat-card">
                <div class="stat-label"><i class="fas fa-door-open"></i> Vacant</div>
                <div class="stat-value">{{ stats.vacant }}</div>
                <span class="stat-change negative"><i class="fas fa-arrow-down"></i> {{ stats.vacant }} vacant</span>
            </div>
            <div class="stat-card">
                <div class="stat-label"><i class="fas fa-folder"></i> Total Files</div>
                <div class="stat-value">{{ stats.total_files }}</div>
                <span class="stat-change"><i class="fas fa-arrow-up"></i> {{ stats.new_uploads }} new uploads</span>
            </div>
        </div>

        <!-- Units Section -->
        <div class="section-header">
            <h3><i class="fas fa-building"></i> Property Units</h3>
            <div class="view-options">
                <button class="active"><i class="fas fa-th"></i> Grid</button>
                <button><i class="fas fa-list"></i> List</button>
            </div>
        </div>

        <div class="unit-grid" id="unitGrid">
            {% for unit in units %}
            <div class="unit-card" data-unit-id="{{ unit.id }}">
                <div class="card-header">
                    <div class="unit-title">
                        <span class="name">{{ unit.name }}</span>
                        <span class="address"><i class="fas fa-map-marker-alt"></i> {{ unit.address }}</span>
                    </div>
                    <span class="status-badge {{ unit.status.lower() }}">{{ unit.status }}</span>
                </div>
                <div class="card-body">
                    <div class="specs">
                        {% if unit.sqft %}
                        <span class="spec-item"><i class="fas fa-vector-square"></i> <strong>{{ unit.sqft }}</strong> sqft</span>
                        {% endif %}
                        {% if unit.beds %}
                        <span class="spec-item"><i class="fas fa-bed"></i> <strong>{{ unit.beds }}</strong> bed{{ 's' if unit.beds > 1 else '' }}</span>
                        {% endif %}
                        {% if unit.baths %}
                        <span class="spec-item"><i class="fas fa-bath"></i> <strong>{{ unit.baths }}</strong> bath{{ 's' if unit.baths > 1 else '' }}</span>
                        {% endif %}
                        {% if unit.unit_type %}
                        <span class="spec-item"><i class="fas fa-home"></i> {{ unit.unit_type }}</span>
                        {% endif %}
                    </div>
                    <div class="rent-row">
                        <div class="rent">{% if unit.rent > 0 %}${{ unit.rent|int }}{% else %}—{% endif %} <span>{% if unit.rent > 0 %}/ mo{% else %}contact{% endif %}</span></div>
                        <span class="tag">{% if unit.rent > 0 %}Might Rent{% else %}Mixed{% endif %}</span>
                    </div>
                </div>
                <div class="card-footer">
                    <div class="actions">
                        <button class="edit-unit"><i class="fas fa-edit"></i> Edit</button>
                        <button class="primary-action view-files" data-unit-id="{{ unit.id }}"><i class="fas fa-file-alt"></i> Files</button>
                    </div>
                    <div class="file-count"><i class="fas fa-file"></i> {{ unit.files|length }} file{{ 's' if unit.files|length != 1 else '' }}</div>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- File Manager -->
        <div class="file-manager">
            <div class="fm-header">
                <h3><i class="fas fa-folder-open"></i> File Management</h3>
                <div class="fm-actions">
                    <button id="uploadFileBtn"><i class="fas fa-upload"></i> Upload</button>
                    <button id="newFolderBtn"><i class="fas fa-folder-plus"></i> New Folder</button>
                    <button class="primary" id="newFileBtn"><i class="fas fa-file-alt"></i> + New File</button>
                </div>
            </div>

            <div class="file-list" id="fileList">
                {% for file in files %}
                <div class="file-row" data-file-id="{{ file.id }}">
                    <div class="file-icon {{ file.file_type }}"><i class="fas fa-file-{{ file.file_type }}"></i></div>
                    <div class="file-info">
                        <div class="fname">{{ file.filename }}</div>
                        <div class="fmeta">
                            <span><i class="far fa-calendar-alt"></i> {{ file.upload_date.strftime('%d %b %Y') }}</span>
                            <span><i class="far fa-file"></i> {{ file.size_mb }} MB</span>
                            <span><i class="fas fa-building"></i> {{ file.unit.name }}</span>
                        </div>
                    </div>
                    <span class="file-status {{ file.status.lower().replace(' ', '-') }}"><i class="fas fa-{% if file.status == 'Uploaded' %}check-circle{% elif file.status == 'In Review' %}clock{% else %}hourglass-half{% endif %}"></i> {{ file.status }}</span>
                    <div class="file-actions">
                        <button class="view-file"><i class="fas fa-eye"></i></button>
                        <button class="download-file"><i class="fas fa-download"></i></button>
                        <button class="file-more"><i class="fas fa-ellipsis-v"></i></button>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>

        <!-- Footer -->
        <div style="margin-top:32px;text-align:center;font-size:13px;color:#94a3b8;border-top:1px solid #f1f4f9;padding-top:24px;">
            <i class="fas fa-shield-alt" style="margin-right:6px;"></i> Mwarokin Estates — Premium Unit Management · v2.0
        </div>

    </main>

    <script>
        (function() {
            // ─── Sidebar toggle ───
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('overlay');
            const toggleBtn = document.getElementById('sidebarToggle');

            function closeSidebar() {
                sidebar.classList.remove('open');
                overlay.classList.remove('show');
            }
            function openSidebar() {
                sidebar.classList.add('open');
                overlay.classList.add('show');
            }

            if (toggleBtn) {
                toggleBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (sidebar.classList.contains('open')) {
                        closeSidebar();
                    } else {
                        openSidebar();
                    }
                });
            }
            overlay.addEventListener('click', closeSidebar);
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') closeSidebar();
            });

            // ─── View toggle ───
            document.querySelectorAll('.view-options button').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.view-options button').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                });
            });

            // ─── Add Unit ───
            document.getElementById('addUnitBtn').addEventListener('click', function() {
                alert('✨ New Unit wizard will open here. (API POST /api/units)');
            });

            // ─── File manager buttons ───
            document.getElementById('uploadFileBtn').addEventListener('click', function() {
                alert('Upload file dialog (API POST /api/files)');
            });
            document.getElementById('newFolderBtn').addEventListener('click', function() {
                alert('New folder (mock)');
            });
            document.getElementById('newFileBtn').addEventListener('click', function() {
                alert('Create new file (API POST /api/files)');
            });

            // ─── Unit actions ───
            document.querySelectorAll('.unit-card .actions button').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const card = this.closest('.unit-card');
                    const id = card.dataset.unitId;
                    const action = this.innerText.trim();
                    console.log('Unit action:', action, 'ID:', id);
                    if (action.includes('Edit')) {
                        alert('Edit unit ' + id + ' (API PUT /api/units/' + id + ')');
                    } else if (action.includes('Files')) {
                        alert('View files for unit ' + id + ' (API GET /api/files?unit_id=' + id + ')');
                    }
                });
            });

            // ─── File actions ───
            document.querySelectorAll('.file-actions button').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const row = this.closest('.file-row');
                    const id = row.dataset.fileId;
                    const action = this.querySelector('i')?.className || '';
                    console.log('File action:', action, 'ID:', id);
                    if (action.includes('eye')) {
                        alert('View file ' + id + ' (GET /api/files/' + id + ')');
                    } else if (action.includes('download')) {
                        alert('Download file ' + id + ' (mock)');
                    } else {
                        alert('More options for file ' + id);
                    }
                });
            });

            // ─── Search (client-side demo) ───
            const searchInput = document.getElementById('searchInput');
            searchInput.addEventListener('input', function() {
                const query = this.value.trim().toLowerCase();
                // Simple client filter (demo)
                const unitCards = document.querySelectorAll('.unit-card');
                const fileRows = document.querySelectorAll('.file-row');
                if (!query) {
                    unitCards.forEach(c => c.style.display = '');
                    fileRows.forEach(r => r.style.display = '');
                    return;
                }
                // Filter units by name or address
                unitCards.forEach(card => {
                    const name = card.querySelector('.unit-title .name')?.textContent.toLowerCase() || '';
                    const addr = card.querySelector('.unit-title .address')?.textContent.toLowerCase() || '';
                    const match = name.includes(query) || addr.includes(query);
                    card.style.display = match ? '' : 'none';
                });
                // Filter files by filename
                fileRows.forEach(row => {
                    const fname = row.querySelector('.file-info .fname')?.textContent.toLowerCase() || '';
                    const match = fname.includes(query);
                    row.style.display = match ? '' : 'none';
                });
            });

            // ─── API demo: fetch units and files (optional) ───
            console.log('🏢 Mwarokin Estates UI ready.');
        })();
    </script>

</body>
</html>
'''


@app.route('/favicon.ico')
def favicon():
    return '', 204


# ----------------------------- Main -----------------------------

if __name__ == '__main__':
    with app.app_context():
        init_db()

    # Register the template as a string
    app.jinja_env.from_string(TEMPLATE_HTML)  # not needed; we'll use render_template_string

    # Override the index route to use the string template
    # Actually we can use render_template_string
    from flask import render_template_string
    # We'll modify the index function to use render_template_string
    def index_with_template():
        units = Unit.query.all()
        files = File.query.all()
        total_units = len(units)
        occupied = sum(1 for u in units if u.status == 'Occupied')
        vacant = sum(1 for u in units if u.status == 'Vacant')
        total_files = len(files)
        week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        new_uploads = File.query.filter(File.upload_date >= week_ago).count()
        stats = {
            'total_units': total_units,
            'occupied': occupied,
            'vacant': vacant,
            'total_files': total_files,
            'new_uploads': new_uploads
        }
        return render_template_string(TEMPLATE_HTML, units=units, files=files, stats=stats)

    app.view_functions['index'] = index_with_template

    app.run(debug=True, host='0.0.0.0', port=5000)
```
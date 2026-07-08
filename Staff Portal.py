```python
from flask import Flask, jsonify, request, send_from_directory, render_template_string
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import uuid

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for frontend API calls

# In-memory data store (replace with database in production)
data_store = {
    "maintenance": [
        {
            "id": 1,
            "title": "Leaking faucet in kitchen",
            "unit": "Unit 90",
            "priority": "High",
            "status": "open",
            "assigned": "John Kamau",
            "date": "2026-07-05",
            "description": "Kitchen sink faucet leaking continuously."
        },
        {
            "id": 2,
            "title": "HVAC not cooling",
            "unit": "Unit 102",
            "priority": "Medium",
            "status": "in-progress",
            "assigned": "David Mwangi",
            "date": "2026-07-04",
            "description": "AC unit not reaching desired temperature."
        },
        {
            "id": 3,
            "title": "Broken window glass",
            "unit": "Unit 45",
            "priority": "Low",
            "status": "open",
            "assigned": "Peter Ochieng",
            "date": "2026-07-03",
            "description": "Bedroom window cracked."
        }
    ],
    "payments": [
        {"id": 101, "tenant": "Michael Brown", "unit": "159 Oak Lane", "amount": 2500, "date": "2026-07-01", "status": "paid"},
        {"id": 102, "tenant": "Robert Johnson", "unit": "567 Elm St", "amount": 1800, "date": "2026-06-28", "status": "paid"},
        {"id": 103, "tenant": "Sarah Kimani", "unit": "Unit 102", "amount": 2100, "date": "2026-06-25", "status": "pending"},
        {"id": 104, "tenant": "Emily Wanjiru", "unit": "Unit 90", "amount": 1200, "date": "2026-06-20", "status": "overdue"}
    ],
    "leases": [
        {
            "id": 1,
            "property": "Boston Ave",
            "tenant": "Michael Brown",
            "start": "2026-01-01",
            "end": "2026-12-31",
            "rent": 2500,
            "status": "active"
        },
        {
            "id": 2,
            "property": "Boylston St · Unit 1",
            "tenant": "Robert Johnson",
            "start": "2026-03-15",
            "end": "2027-03-14",
            "rent": 1800,
            "status": "active"
        },
        {
            "id": 3,
            "property": "Unit 102",
            "tenant": "Sarah Kimani",
            "start": "2025-07-01",
            "end": "2026-06-30",
            "rent": 2100,
            "status": "expiring"
        }
    ]
}

# Serve the main HTML (we'll assume it's saved as index.html)
@app.route('/')
def index():
    try:
        with open('static/index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return """
        <h1>Mwarokin Estates Staff Portal</h1>
        <p>Backend is running. Please place index.html in the static folder.</p>
        """, 200

# API Endpoints
@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify({
        "open_maintenance": len([m for m in data_store["maintenance"] if m["status"] == "open"]),
        "monthly_rent": 48200,
        "active_leases": len([l for l in data_store["leases"] if l["status"] == "active"]),
        "occupancy_rate": 92
    })

@app.route('/api/maintenance', methods=['GET'])
def get_maintenance():
    return jsonify(data_store["maintenance"])

@app.route('/api/maintenance', methods=['POST'])
def create_maintenance():
    req = request.get_json()
    new_req = {
        "id": len(data_store["maintenance"]) + 1,
        "title": req.get("title"),
        "unit": req.get("unit"),
        "priority": req.get("priority", "Medium"),
        "status": "open",
        "assigned": req.get("assigned", "Unassigned"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "description": req.get("description")
    }
    data_store["maintenance"].append(new_req)
    return jsonify(new_req), 201

@app.route('/api/maintenance/<int:req_id>', methods=['PUT'])
def update_maintenance(req_id):
    req = request.get_json()
    for item in data_store["maintenance"]:
        if item["id"] == req_id:
            item.update(req)
            return jsonify(item)
    return jsonify({"error": "Not found"}), 404

@app.route('/api/payments', methods=['GET'])
def get_payments():
    return jsonify(data_store["payments"])

@app.route('/api/payments', methods=['POST'])
def record_payment():
    payment = request.get_json()
    new_payment = {
        "id": len(data_store["payments"]) + 100,
        "tenant": payment.get("tenant"),
        "unit": payment.get("unit"),
        "amount": payment.get("amount"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "status": payment.get("status", "paid")
    }
    data_store["payments"].append(new_payment)
    return jsonify(new_payment), 201

@app.route('/api/leases', methods=['GET'])
def get_leases():
    return jsonify(data_store["leases"])

@app.route('/api/leases', methods=['POST'])
def create_lease():
    lease_data = request.get_json()
    new_lease = {
        "id": len(data_store["leases"]) + 1,
        **lease_data
    }
    data_store["leases"].append(new_lease)
    return jsonify(new_lease), 201

@app.route('/api/analytics/revenue', methods=['GET'])
def get_revenue():
    return jsonify({
        "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
        "data": [32000, 34000, 36000, 38000, 42000, 48200]
    })

# Serve static files
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    # Create static directory and save HTML if not exists
    os.makedirs('static', exist_ok=True)
    
    # You can paste the full HTML content here programmatically, but for production save it manually
    print("✅ Mwarokin Estates Staff Portal Backend running!")
    print("   Visit: http://localhost:5000")
    app.run(debug=True, port=5000)
```

### Setup Instructions (Run this once):

1. Save the provided HTML content into `static/index.html` (create the folder if needed).
2. Install dependencies:
   ```bash
   pip install flask flask-cors
   ```
3. Run the backend:
   ```bash
   python app.py
   ```

### Features Included:
- Full REST API for all major entities
- In-memory data persistence (easy to swap with SQLAlchemy + SQLite)
- Modern Flask structure
- CORS enabled for the frontend
- Matches the UI data structure
- Easy to extend with authentication, database, etc.

The backend is ready to connect to your existing HTML frontend via fetch/Axios calls to the `/api/` endpoints. Let me know if you need database integration (SQLAlchemy), authentication, or PDF generation!
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
from datetime import datetime, timedelta
import json
import random
import threading
import time

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Sample data
properties = [
    {
        "id": 1,
        "type": "Modern Apartment",
        "location": "Nairobi, Kenya",
        "price": 4500000,
        "bedrooms": 3,
        "bathrooms": 2,
        "area": 120,
        "img": "https://via.placeholder.com/400x300/1a365d/ffffff?text=Apartment",
        "status": "for sale",
        "availability": True
    },
    {
        "id": 2,
        "type": "Luxury Villa",
        "location": "Mombasa, Kenya",
        "price": 12500000,
        "bedrooms": 5,
        "bathrooms": 4,
        "area": 350,
        "img": "https://via.placeholder.com/400x300/2c5282/ffffff?text=Villa",
        "status": "for sale",
        "availability": True
    }
]

renovation_services = [
    {
        "id": 1,
        "name": "Government Approvals",
        "description": "Automated verification with government agencies for approvals and compliance.",
        "icon": "file-contract",
        "base_price": 5000
    },
    {
        "id": 2,
        "name": "Renovation Services",
        "description": "Professional renovation and remodeling services for homes and commercial properties.",
        "icon": "tools",
        "base_price": 15000
    },
    {
        "id": 3,
        "name": "Media Preparation",
        "description": "Professional photography and videography services for property listings.",
        "icon": "camera",
        "base_price": 3000
    },
    {
        "id": 4,
        "name": "Renovation Advice",
        "description": "Providing professional renovation advice virtually and physically.",
        "icon": "lightbulb",
        "base_price": 2000
    },
    {
        "id": 5,
        "name": "Renovation Updates",
        "description": "Providing updates on renovations and client hand-over.",
        "icon": "sync-alt",
        "base_price": 1000
    }
]

# Active renovation projects
active_projects = {}

# Currency rates
currency_rates = {
    "Algeria": 135.22,
    "Angola": 472.25,
    "Benin": 648.59,
    "Botswana": 12.40,
    "Burkina Faso": 648.59,
    "Burundi": 2.04575,
    "Kenya": 1,
    "Nigeria": 21.5,
    "South Africa": 0.075,
    "Ghana": 0.064,
    "Egypt": 0.18,
    "Tanzania": 0.039,
    "Uganda": 0.026,
    "Ethiopia": 0.17,
    "Rwanda": 0.0085
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/properties')
def get_properties():
    """Get all properties"""
    return jsonify(properties)

@app.route('/api/services')
def get_services():
    """Get all renovation services"""
    return jsonify(renovation_services)

@app.route('/api/currency/<country>')
def get_currency_rate(country):
    """Get currency rate for a country"""
    rate = currency_rates.get(country, None)
    if rate:
        return jsonify({"country": country, "rate": rate})
    else:
        return jsonify({"error": "Currency rate not available"}), 404

@app.route('/api/service-request', methods=['POST'])
def submit_service_request():
    """Submit a new service request"""
    data = request.json
    
    required_fields = ['service_type', 'property_type', 'budget', 'timeline', 'description']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400
    
    # Generate project ID
    project_id = len(active_projects) + 1
    
    # Create project
    project = {
        "id": project_id,
        "service_type": data['service_type'],
        "property_type": data['property_type'],
        "budget": data['budget'],
        "timeline": data['timeline'],
        "description": data['description'],
        "contact_preference": data.get('contact_preference', 'phone'),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "progress": 0,
        "updates": []
    }
    
    active_projects[project_id] = project
    
    # Add initial update
    add_project_update(project_id, "Project created", "Your renovation project has been created and is awaiting assignment.")
    
    return jsonify({
        "success": True,
        "project_id": project_id,
        "message": "Service request submitted successfully"
    })

@app.route('/api/project/<int:project_id>')
def get_project(project_id):
    """Get project details"""
    project = active_projects.get(project_id)
    if project:
        return jsonify(project)
    else:
        return jsonify({"error": "Project not found"}), 404

@app.route('/api/project/<int:project_id>/progress', methods=['POST'])
def update_project_progress(project_id):
    """Update project progress"""
    data = request.json
    progress = data.get('progress')
    
    project = active_projects.get(project_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404
    
    if progress is not None:
        project['progress'] = progress
        add_project_update(project_id, "Progress updated", f"Project progress updated to {progress}%")
        
        # Emit real-time update
        socketio.emit('progress_update', {
            'project_id': project_id,
            'progress': progress,
            'timestamp': datetime.now().isoformat()
        })
    
    return jsonify({"success": True})

def add_project_update(project_id, title, description):
    """Add an update to a project"""
    project = active_projects.get(project_id)
    if project:
        update = {
            "id": len(project['updates']) + 1,
            "title": title,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "time_display": datetime.now().strftime("%I:%M %p")
        }
        project['updates'].append(update)
        
        # Emit real-time update
        socketio.emit('project_update', {
            'project_id': project_id,
            'update': update
        })

# SocketIO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('connected', {'message': 'Connected to renovation services'})

@socketio.on('join_project')
def handle_join_project(data):
    project_id = data.get('project_id')
    if project_id in active_projects:
        emit('project_data', active_projects[project_id])

@socketio.on('chat_message')
def handle_chat_message(data):
    message = data.get('message', '')
    project_id = data.get('project_id')
    
    # Simple chatbot responses
    response = generate_chat_response(message)
    
    emit('chat_response', {
        'message': response,
        'timestamp': datetime.now().isoformat()
    })

def generate_chat_response(message):
    """Generate chatbot response based on user input"""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ['hello', 'hi', 'hey']):
        return "Hello! I'm Mwarokin Assistant. How can I help you with your renovation needs today?"
    elif any(word in message_lower for word in ['renovation', 'remodel']):
        return "We offer comprehensive renovation services including government approvals, professional advice, and full project management. Which service are you interested in?"
    elif any(word in message_lower for word in ['price', 'cost']):
        return "Renovation costs vary based on property size and scope of work. Our basic packages start from $5,000. Would you like a detailed quote?"
    elif any(word in message_lower for word in ['approval', 'permit']):
        return "We handle all government approvals and permits for your renovation project. This typically takes 2-4 weeks depending on your location."
    elif any(word in message_lower for word in ['progress', 'track']):
        return "You can track your renovation progress in real-time using our progress tracking section. It shows current status, timelines, and live updates from your project site."
    elif any(word in message_lower for word in ['update', 'live']):
        return "Our live updates section provides real-time information about your renovation project, including work completed, materials delivered, and upcoming tasks."
    else:
        return "I'm here to help with your renovation needs. You can ask me about services, pricing, timelines, or any other questions about property transformations."

# Background task for simulating real-time updates
def simulate_project_updates():
    """Background task to simulate real-time project updates"""
    while True:
        time.sleep(30)  # Update every 30 seconds
        
        for project_id, project in active_projects.items():
            if project['status'] == 'in_progress' and project['progress'] < 100:
                # Simulate progress increase
                progress_increase = random.randint(1, 5)
                new_progress = min(100, project['progress'] + progress_increase)
                
                if new_progress > project['progress']:
                    project['progress'] = new_progress
                    
                    # Generate random update
                    updates = [
                        {"title": "Work Progress", "description": f"Construction work is {new_progress}% complete"},
                        {"title": "Material Delivery", "description": "New materials delivered to site"},
                        {"title": "Quality Check", "description": "Quality inspection completed successfully"},
                        {"title": "Team Update", "description": "Additional team members assigned to accelerate work"}
                    ]
                    
                    update = random.choice(updates)
                    add_project_update(project_id, update['title'], update['description'])
                    
                    # Emit progress update
                    socketio.emit('progress_update', {
                        'project_id': project_id,
                        'progress': new_progress,
                        'timestamp': datetime.now().isoformat()
                    })

if __name__ == '__main__':
    # Start background thread for simulated updates
    update_thread = threading.Thread(target=simulate_project_updates)
    update_thread.daemon = True
    update_thread.start()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
#Run the application:
python app.py

#Install dependencies
pip install -r requirements.txt


#Create project structure:
mkdir mwarokin-real-estate
cd mwarokin-real-estate
mkdir static templates

#requierments
Flask==2.3.3
Flask-CORS==4.0.0
python-dotenv==1.0.0


from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import os

app = Flask(__name__)
CORS(app)

class RealEstateApp:
    def __init__(self):
        self.properties = []
        self.contacts = []
        
    def add_property(self, property_data):
        self.properties.append(property_data)
        
    def add_contact(self, contact_data):
        self.contacts.append(contact_data)

# Initialize the app
real_estate_app = RealEstateApp()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/properties', methods=['GET'])
def get_properties():
    # Sample property data
    properties = [
        {
            'id': 1,
            'title': 'Luxury Beachfront Villa',
            'type': 'Villa',
            'location': 'Malindi, Kenya',
            'price': 850000,
            'bedrooms': 4,
            'bathrooms': 3,
            'area': 3200,
            'image': 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80'
        },
        {
            'id': 2,
            'title': 'Modern City Apartment',
            'type': 'Apartment',
            'location': 'Nairobi, Kenya',
            'price': 420000,
            'bedrooms': 3,
            'bathrooms': 2,
            'area': 1800,
            'image': 'https://images.unsplash.com/photo-1600047509807-ba8f99d2cdde?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80'
        },
        {
            'id': 3,
            'title': 'Spacious Family Home',
            'type': 'Family Home',
            'location': 'Mombasa, Kenya',
            'price': 1200000,
            'bedrooms': 5,
            'bathrooms': 4,
            'area': 4500,
            'image': 'https://images.unsplash.com/photo-1600585154340-9635ecca998d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80'
        }
    ]
    return jsonify(properties)

@app.route('/api/contact', methods=['POST'])
def contact_form():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'message']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Add to contacts
        contact_data = {
            'name': data['name'],
            'email': data['email'],
            'phone': data.get('phone', ''),
            'message': data['message'],
            'timestamp': datetime.now().isoformat()
        }
        
        real_estate_app.add_contact(contact_data)
        
        # Send email notification (configure with your SMTP settings)
        send_contact_email(contact_data)
        
        return jsonify({'message': 'Thank you for your message! We will get back to you soon.'}), 200
        
    except Exception as e:
        return jsonify({'error': 'An error occurred while processing your request.'}), 500

def send_contact_email(contact_data):
    """Send email notification for new contact form submission"""
    try:
        # Configure these with your email settings
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USERNAME', 'your-email@gmail.com')
        smtp_password = os.getenv('SMTP_PASSWORD', 'your-app-password')
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = smtp_username
        msg['To'] = 'info@mwarokin.com'
        msg['Subject'] = f'New Contact Form Submission - {contact_data["name"]}'
        
        # Create email body
        body = f"""
        New contact form submission from Mwarokin Real Estate website:
        
        Name: {contact_data['name']}
        Email: {contact_data['email']}
        Phone: {contact_data['phone']}
        Message: {contact_data['message']}
        
        Timestamp: {contact_data['timestamp']}
        """
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error sending email: {e}")

@app.route('/api/appointment', methods=['POST'])
def schedule_appointment():
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'email', 'date', 'time']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Process appointment (in a real app, you'd save to database)
        appointment_data = {
            'name': data['name'],
            'email': data['email'],
            'phone': data.get('phone', ''),
            'date': data['date'],
            'time': data['time'],
            'message': data.get('message', ''),
            'timestamp': datetime.now().isoformat()
        }
        
        # Send confirmation email
        send_appointment_email(appointment_data)
        
        return jsonify({'message': 'Appointment scheduled successfully! We will confirm shortly.'}), 200
        
    except Exception as e:
        return jsonify({'error': 'An error occurred while scheduling your appointment.'}), 500

def send_appointment_email(appointment_data):
    """Send confirmation email for appointment"""
    try:
        # Similar to send_contact_email but for appointments
        # Implement based on your email service
        pass
    except Exception as e:
        print(f"Error sending appointment email: {e}")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
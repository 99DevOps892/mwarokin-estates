import time
import random
import hashlib
import json
from flask import Flask, request, jsonify, redirect, url_for, session
from cryptography.fernet import Fernet
from threading import Thread

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # For session encryption (Use secure key management in production)
app.config['SESSION_COOKIE_NAME'] = 'MediCheckSession'

# Sample User Data (Replace with database in real-world scenarios)
users = {
    "user1": {
        "username": "user1",
        "password": "hashed_password_123",  # Use a hashed password in real systems
        "last_activity": time.time(),
        "is_logged_in": False
    }
}

# Encryption and Decryption Keys
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Simulate database session timeout (In real apps, use Redis or a session store)
session_timeout = 15 * 60  # 15 minutes of inactivity

# Mock AI-driven threat detection (replace with actual AI models)
def ai_threat_monitor(transaction_data):
    # Simulate AI threat detection (This is a mock; in real systems, an AI model would evaluate the transaction)
    threat_score = random.uniform(0, 1)
    if threat_score > 0.7:
        return True  # Flagged as suspicious
    return False

# User Session Expiry Check
def check_idle_sessions():
    while True:
        time.sleep(60)  # Check every minute
        for user in users:
            if users[user]['is_logged_in']:
                idle_time = time.time() - users[user]['last_activity']
                if idle_time > session_timeout:
                    users[user]['is_logged_in'] = False
                    print(f"User {user} has been logged out due to inactivity.")
                    # Here you can also add code to log the user out from the front-end
                    print(f"Redirecting user {user} to the logout page...")

# Start a thread for idle session checking
thread = Thread(target=check_idle_sessions)
thread.daemon = True  # This will allow the thread to exit when the main program exits
thread.start()

@app.route('/logout', methods=['GET'])
def logout():
    """Handle user logout and session invalidation."""
    user = session.get('username')
    if user and users.get(user):
        # Perform any necessary cleanup, such as logging out, invalidating tokens, etc.
        users[user]['is_logged_in'] = False
        session.pop('username', None)
        session.pop('auth_token', None)
        print(f"User {user} has successfully logged out.")
        return jsonify({
            "message": "You have successfully logged out. Thank you for using MediCheck!"
        })
    return redirect(url_for('login'))

@app.route('/login', methods=['POST'])
def login():
    """Simulate the login process with secure session creation."""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = users.get(username)
    if user and user['password'] == password:
        session['username'] = username
        session['auth_token'] = encrypt_data(f"{username}_session_token")
        users[username]['is_logged_in'] = True
        users[username]['last_activity'] = time.time()
        print(f"User {username} has successfully logged in.")
        return jsonify({"message": "Login successful."})
    
    return jsonify({"message": "Invalid username or password."}), 401

@app.route('/perform_transaction', methods=['POST'])
def perform_transaction():
    """Simulate performing a transaction with security and AI threat monitoring."""
    data = request.json
    transaction_data = data.get('transaction_data')

    # AI-driven threat monitoring
    if ai_threat_monitor(transaction_data):
        return jsonify({"message": "Transaction flagged as suspicious, action blocked!"}), 403

    # Proceed with the transaction (tokenize, record, etc.)
    token = tokenize_transaction(transaction_data)
    return jsonify({"message": "Transaction successful.", "token": token})

# Encrypt data (used for session token encryption)
def encrypt_data(data):
    """Encrypt sensitive data (like session tokens)."""
    encrypted_data = cipher_suite.encrypt(data.encode())
    return encrypted_data.decode()

# Tokenize sensitive transaction data
def tokenize_transaction(transaction_data):
    """Generate a secure token for transaction data."""
    token = hashlib.sha256(str(transaction_data).encode()).hexdigest()
    print(f"Transaction Token: {token}")
    return token

@app.route('/secure_data', methods=['POST'])
def secure_data():
    """Example of secure data encryption and decryption."""
    data = request.json.get('data')
    encrypted = encrypt_data(data)
    decrypted = decrypt_data(encrypted)
    return jsonify({"encrypted": encrypted, "decrypted": decrypted})

# Decrypt data (for when you need to access sensitive information)
def decrypt_data(encrypted_data):
    """Decrypt sensitive data."""
    decrypted_data = cipher_suite.decrypt(encrypted_data.encode())
    return decrypted_data.decode()

# Function to handle user session expiration
@app.before_request
def before_request():
    """Track the time of user activity."""
    user = session.get('username')
    if user and users.get(user):
        users[user]['last_activity'] = time.time()

@app.route('/status', methods=['GET'])
def status():
    """Check user login status."""
    user = session.get('username')
    if user and users.get(user):
        return jsonify({
            "username": user,
            "is_logged_in": users[user]['is_logged_in'],
            "last_activity": time.ctime(users[user]['last_activity'])
        })
    return jsonify({"message": "User not logged in."}), 401

if __name__ == '__main__':
    app.run(debug=True)

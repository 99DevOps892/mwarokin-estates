import time
import json
import threading
import random
from datetime import datetime
from flask import Flask, jsonify, request
from sklearn.ensemble import IsolationForest

app = Flask(__name__)

# Simulated database
clients = []
onboarding_metrics = {
    "active_onboarding": 47,
    "completion_rate": 89,
    "average_time": 3.2,
}

# AI Model for Risk Assessment
risk_model = IsolationForest(contamination=0.1, random_state=42)

def generate_random_data():
    """Simulate random client onboarding activity"""
    while True:
        time.sleep(random.randint(1, 5))
        new_client = {
            "id": len(clients) + 1,
            "name": f"Client_{len(clients) + 1}",
            "status": random.choice(["Pending", "In Progress", "Completed"]),
            "risk_score": random.uniform(0, 1),
            "timestamp": datetime.now().isoformat()
        }
        clients.append(new_client)
        onboarding_metrics["active_onboarding"] += 1 if new_client["status"] != "Completed" else 0
        onboarding_metrics["completion_rate"] += random.uniform(-0.5, 0.5)

# Start background data simulation
data_thread = threading.Thread(target=generate_random_data, daemon=True)
data_thread.start()

@app.route("/metrics", methods=["GET"])
def get_metrics():
    """Return real-time onboarding metrics"""
    return jsonify(onboarding_metrics)

@app.route("/clients", methods=["GET"])
def get_clients():
    """Retrieve the list of onboarded clients"""
    return jsonify(clients[-10:])  # Limit to the last 10 clients for performance

@app.route("/risk-assessment", methods=["POST"])
def risk_assessment():
    """AI-driven risk analysis for client onboarding"""
    data = request.get_json()
    risk_score = risk_model.fit_predict([[data.get("transaction_amount", 1000)]])
    risk_level = "High" if risk_score[0] == -1 else "Low"
    return jsonify({"risk_score": risk_score[0], "risk_level": risk_level})

if __name__ == "__main__":
    app.run(debug=True, port=5000)

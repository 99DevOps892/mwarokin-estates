from flask import Flask, request, jsonify
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import uuid
import logging
from datetime import datetime
import json
import os

# Initialize Flask App
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Mock database for listings (replace with actual DB in production)
listings_db = [
    {
        "id": 1,
        "title": "Modern Apartment in Nairobi",
        "location": "Nairobi, Kenya",
        "price": "50000",
        "img": "img/apartment1.jpg",
        "property_type": "residential",
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 1200,
        "amenities": ["pool", "gym", "parking"],
        "tenant_id": "faraja_sky"
    },
    {
        "id": 2,
        "title": "Commercial Office Space",
        "location": "Lagos, Nigeria",
        "price": "100000",
        "img": "img/office1.jpg",
        "property_type": "commercial",
        "bedrooms": 0,
        "bathrooms": 4,
        "size_sqft": 3000,
        "amenities": ["elevator", "security", "parking"],
        "tenant_id": "faraja_sky"
    }
]

# Real Estate Valuation Model
class ValuationAgent:
    def __init__(self):
        self.model = LinearRegression()
        self.scaler = StandardScaler()
        
    def train_model(self, data):
        df = pd.DataFrame(data)
        features = df[['bedrooms', 'bathrooms', 'size_sqft', 'location_score']]
        labels = df['price']
        features = self.scaler.fit_transform(features)
        self.model.fit(features, labels)
        
    def predict_valuation(self, listing):
        features = self.scaler.transform([[listing['bedrooms'], listing['bathrooms'], listing['size_sqft'], listing.get('location_score', 1)]])
        predicted_price = self.model.predict(features)[0]
        return {
            "range_low": round(predicted_price * 0.9, 2),
            "range_high": round(predicted_price * 1.1, 2),
            "confidence": 0.95,
            "reasoning": f"Valuation based on {listing['bedrooms']} bedrooms, {listing['bathrooms']} bathrooms, {listing['size_sqft']} sqft, and location score.",
            "sources": ["internal_comps", "market_trends"]
        }

# Instantiate Valuation Agent
valuation_agent = ValuationAgent()

# Train with sample data
sample_data = [
    {"bedrooms": 2, "bathrooms": 2, "size_sqft": 1200, "location_score": 1, "price": 50000},
    {"bedrooms": 0, "bathrooms": 4, "size_sqft": 3000, "location_score": 2, "price": 100000}
]
valuation_agent.train_model(sample_data)

# Listing Agent
class ListingAgent:
    def intake(self, payload, tenant_id):
        required_fields = ["title", "location", "price", "property_type", "bedrooms", "bathrooms", "size_sqft"]
        missing_fields = [field for field in required_fields if field not in payload]
        if missing_fields:
            return {"status": "error", "warnings": f"Missing fields: {', '.join(missing_fields)}"}
        
        listing = {
            "id": str(uuid.uuid4()),
            "title": payload["title"],
            "location": payload["location"],
            "price": payload["price"],
            "img": payload.get("img", "img/default.jpg"),
            "property_type": payload["property_type"],
            "bedrooms": payload["bedrooms"],
            "bathrooms": payload["bathrooms"],
            "size_sqft": payload["size_sqft"],
            "amenities": payload.get("amenities", []),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat()
        }
        listings_db.append(listing)
        return {"status": "success", "listing_id": listing["id"], "normalized_fields": listing}

# Matchmaking Agent
class MatchmakingAgent:
    def match(self, profile, tenant_id):
        matches = []
        for listing in listings_db:
            if listing["tenant_id"] != tenant_id:
                continue
            score = 0
            if profile.get("location").lower() in listing["location"].lower():
                score += 0.4
            if profile.get("property_type") == listing["property_type"]:
                score += 0.3
            if profile.get("bedrooms") <= listing["bedrooms"]:
                score += 0.2
            if profile.get("max_price") >= float(listing["price"]):
                score += 0.1
            matches.append({"listing_id": listing["id"], "score": score, "explanation": f"Matched based on location, type, bedrooms, and price."})
        return sorted(matches, key=lambda x: x["score"], reverse=True)[:10]

# Instantiate Agents
listing_agent = ListingAgent()
matchmaking_agent = MatchmakingAgent()

# Middleware for tenant validation
def check_tenant_id():
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id or tenant_id not in ["faraja_sky"]:  # Mock tenant validation
        return jsonify({"error": "Invalid or missing tenant_id"}), 403
    return None

# Routes
@app.route('/api/listings', methods=['GET'])
def get_listings():
    tenant_check = check_tenant_id()
    if tenant_check:
        return tenant_check
    tenant_id = request.headers.get('X-Tenant-ID')
    listings = [listing for listing in listings_db if listing["tenant_id"] == tenant_id]
    return jsonify({"listings": listings})

@app.route('/api/listing/intake', methods=['POST'])
def intake_listing():
    tenant_check = check_tenant_id()
    if tenant_check:
        return tenant_check
    data = request.get_json()
    tenant_id = request.headers.get('X-Tenant-ID')
    result = listing_agent.intake(data, tenant_id)
    return jsonify(result)

@app.route('/api/valuation', methods=['POST'])
def valuation():
    tenant_check = check_tenant_id()
    if tenant_check:
        return tenant_check
    data = request.get_json()
    listing_id = data.get("listing_id")
    listing = next((l for l in listings_db if l["id"] == listing_id and l["tenant_id"] == request.headers.get('X-Tenant-ID')), None)
    if not listing:
        return jsonify({"error": "Listing not found or access denied"}), 404
    valuation = valuation_agent.predict_valuation(listing)
    return jsonify(valuation)

@app.route('/api/matchmaking', methods=['POST'])
def matchmaking():
    tenant_check = check_tenant_id()
    if tenant_check:
        return tenant_check
    data = request.get_json()
    tenant_id = request.headers.get('X-Tenant-ID')
    matches = matchmaking_agent.match(data.get("profile", {}), tenant_id)
    matched_listings = [
        {**next(l for l in listings_db if l["id"] == match["listing_id"]), **match}
        for match in matches
    ]
    return jsonify({"matches": matched_listings})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
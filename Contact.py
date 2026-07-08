import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import datetime
import uuid
import random  # For simulation purposes; replace with real logic in production

# Data models using dataclasses for modern Python (3.7+)
@dataclass
class ListingReco:
    status: str
    warnings: List[str] = field(default_factory=list)
    normalized_fields: Dict[str, Any] = field(default_factory=dict)
    media_report: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Valuation:
    range_low: float
    range_high: float
    comp_ids: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    sources: List[str] = field(default_factory=list)

@dataclass
class Match:
    listing_id: str
    score: float
    explanation: str

@dataclass
class LeaseDraft:
    clauses: List[str] = field(default_factory=list)
    schedule: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)

# Base Agent class for common functionality
class BaseAgent:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        # Simulate RBAC: In real impl, check access based on tenant_id
        self._check_access()

    def _check_access(self) -> None:
        # Placeholder for RBAC/ABAC enforcement
        pass

    def _rag_retrieve(self, query: str) -> List[Dict[str, Any]]:
        # Simulate RAG: In real impl, use vector DB or external service
        # Ground in fresh market data; cite sources
        return [{"data": "Simulated data", "source": "internal_db"}]

# ListingAgent
class ListingAgent(BaseAgent):
    def intake(self, payload: Dict[str, Any]) -> ListingReco:
        # Intake, normalize, validate
        normalized = self._normalize(payload)
        warnings = self._validate(normalized)
        media_report = self._image_qa(payload.get('media', []))
        # Auto-enrich: geocode, metrics, etc.
        self._enrich(normalized)
        return ListingReco(status="success" if not warnings else "warning", warnings=warnings, normalized_fields=normalized, media_report=media_report)

    def _normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # Normalize fields (e.g., standardize addresses, units)
        return {k.lower(): v for k, v in payload.items()}  # Simple example

    def _validate(self, normalized: Dict[str, Any]) -> List[str]:
        # Validate required fields, types, etc.
        warnings = []
        if 'address' not in normalized:
            warnings.append("Missing address")
        return warnings

    def _image_qa(self, media: List[Any]) -> Dict[str, Any]:
        # QA images: check quality, content moderation
        return {"count": len(media), "issues": []}  # Simulated

    def _enrich(self, normalized: Dict[str, Any]) -> None:
        # Geocoding, walkscore, etc. Simulate
        normalized['geocode'] = {"lat": 37.7749, "lon": -122.4194}
        normalized['amenities'] = ["park", "school"]

# ValuationAgent
class ValuationAgent(BaseAgent):
    def request(self, listing_id_or_address: str) -> Valuation:
        # CMA/AVM using RAG
        comps = self._rag_retrieve(f"comps for {listing_id_or_address}")
        # Simulate calculation
        low = random.uniform(100000, 500000)
        high = low * 1.2
        confidence = random.uniform(0.7, 0.95)
        reasoning = "Based on similar properties; adjusted for market trends."
        sources = [c['source'] for c in comps]
        return Valuation(range_low=low, range_high=high, comp_ids=["comp1", "comp2"], confidence=confidence, reasoning=reasoning, sources=sources)

# PricingAgent
class PricingAgent(BaseAgent):
    def dynamic_pricing(self, listing_id: str, base_price: float) -> Dict[str, float]:
        # Dynamic pricing with elasticity, trends
        trends = self._rag_retrieve("market trends")
        adjustment = random.uniform(-0.1, 0.1)  # Simulate seasonality
        discounted = base_price * (1 + adjustment)
        return {"suggested_price": discounted, "discount_rate": adjustment, "explanation": "Adjusted for seasonal demand."}

# MatchmakingAgent
class MatchmakingAgent(BaseAgent):
    def request(self, profile: Dict[str, Any]) -> List[Match]:
        # Embeddings + rules for matching
        listings = self._rag_retrieve("available listings")
        matches = []
        for lst in listings[:3]:  # Simulate top 3
            score = random.uniform(0.6, 0.95)
            explanation = "Matches budget and location preferences."
            matches.append(Match(listing_id=str(uuid.uuid4()), score=score, explanation=explanation))
        return matches

# LeadCRM_Agent
class LeadCRM_Agent(BaseAgent):
    def capture_and_route(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        # Score BANT, route
        score = random.randint(1, 10)
        routed_to = "broker123" if score > 5 else "agent456"
        return {"score": score, "routed_to": routed_to, "reminders": ["Follow up in 24h"]}

# LeaseAgent
class LeaseAgent(BaseAgent):
    def create_draft(self, listing_id: str, applicant_id: str, terms: Dict[str, Any]) -> LeaseDraft:
        # Document packs, e-sign, etc.
        clauses = ["Standard lease terms", "Pet policy"]
        schedule = {"start": datetime.date.today().isoformat(), "end": (datetime.date.today() + datetime.timedelta(days=365)).isoformat()}
        risks = ["Arrears risk: low"] if random.random() > 0.5 else ["Arrears risk: high"]
        return LeaseDraft(clauses=clauses, schedule=schedule, risks=risks)

# TransactionAgent
class TransactionAgent(BaseAgent):
    def readiness_check(self, transaction_id: str) -> Dict[str, Any]:
        # Checklists, milestones
        return {"status": "ready", "alerts": [], "milestones": ["Title clear", "Inspection pending"]}

# ComplianceAgent
class ComplianceAgent(BaseAgent):
    def kyc_aml_check(self, user_id: str) -> Dict[str, bool]:
        # Via connectors; simulate
        return {"kyc_pass": True, "aml_pass": random.choice([True, False]), "flags": []}

# WhiteLabelAgent
class WhiteLabelAgent(BaseAgent):
    def apply_theme(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        # Theme, locale, etc.
        return {"logo": settings.get('logo', 'default.png'), "palette": settings.get('palette', {'primary': 'blue'}), "locale": settings.get('locale', 'en_US')}

# RAG_Agent (core for grounding)
class RAG_Agent(BaseAgent):
    def ingest(self, data: Dict[str, Any], source: str) -> str:
        # Ingest docs, market intel
        return str(uuid.uuid4())  # Return ingestion ID

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        return self._rag_retrieve(query)  # Override with actual impl

# AnalyticsAgent
class AnalyticsAgent(BaseAgent):
    def compute_kpis(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        # KPIs, anomalies
        return {"occupancy": 0.85, "noi_projection": 100000, "anomalies": []}

# Orchestrator / Supervisor
class MwarokinOrchestrator:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.agents = {
            'listing': ListingAgent(tenant_id),
            'valuation': ValuationAgent(tenant_id),
            'pricing': PricingAgent(tenant_id),
            'matchmaking': MatchmakingAgent(tenant_id),
            'lead_crm': LeadCRM_Agent(tenant_id),
            'lease': LeaseAgent(tenant_id),
            'transaction': TransactionAgent(tenant_id),
            'compliance': ComplianceAgent(tenant_id),
            'white_label': WhiteLabelAgent(tenant_id),
            'rag': RAG_Agent(tenant_id),
            'analytics': AnalyticsAgent(tenant_id),
        }

    def handle_request(self, task_type: str, payload: Dict[str, Any]) -> Any:
        # ReAct + plan-execute-reflect loop
        plan = self._plan(task_type, payload)
        result = self._execute(plan, payload)
        reflection = self._reflect(result)
        # Cite sources if applicable
        if 'sources' in result:
            print(f"Sources: {result['sources']}")
        return result

    def _plan(self, task_type: str, payload: Dict[str, Any]) -> List[str]:
        # Simple plan: sequence of agents
        if task_type == 'listing_intake':
            return ['compliance.check', 'listing.intake', 'valuation.request']
        # Add more plans; fallback to deterministic rules
        return [f'{task_type}.main']

    def _execute(self, plan: List[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for step in plan:
            agent_name, method = step.split('.')
            agent = self.agents.get(agent_name)
            if agent:
                meth = getattr(agent, method, None)
                if meth:
                    partial = meth(payload) if 'valuation' in step else meth(**payload)
                    result[step] = partial
                    # Chunk and stream for long tasks (simulate)
                    print(f"Partial result for {step}: {json.dumps(partial, default=str)}")
        return result

    def _reflect(self, result: Dict[str, Any]) -> str:
        # Reflect: check for errors, fairness, etc.
        return "Execution successful; compliant and fair." if result else "Issues detected."

# Example usage (for testing; integrate with API/CLI)
if __name__ == "__main__":
    orch = MwarokinOrchestrator(tenant_id="tenant_123")
    # Simulate listing intake
    payload = {"address": "123 Main St", "type": "residential"}
    result = orch.handle_request("listing_intake", payload)
    print(json.dumps(result, default=lambda o: o.__dict__, indent=2))

    /////////////////////////////////////////////////////////////////////////


from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

# Static currency rates as fallback
STATIC_CURRENCY_RATES = {
    "Kenya": {"rate": 1, "currency": "KES", "symbol": "KSh"},
    "Tanzania": {"rate": 22.5, "currency": "TZS", "symbol": "TSh"},
    "Uganda": {"rate": 35.2, "currency": "UGX", "symbol": "USh"},
    "Rwanda": {"rate": 105, "currency": "RWF", "symbol": "RF"},
    "Ethiopia": {"rate": 52.3, "currency": "ETB", "symbol": "Br"},
    "Ghana": {"rate": 0.065, "currency": "GHS", "symbol": "₵"},
    "Nigeria": {"rate": 42.8, "currency": "NGN", "symbol": "₦"},
    "South Africa": {"rate": 0.18, "currency": "ZAR", "symbol": "R"}
}

# Real-time exchange rate API (using free API)
def get_real_time_rates(base_currency='USD'):
    try:
        # Using a free exchange rate API
        response = requests.get(f'https://api.exchangerate-api.com/v4/latest/{base_currency}')
        if response.status_code == 200:
            return response.json()['rates']
        else:
            return None
    except:
        return None

@app.route('/currency-converter')
def currency_converter():
    return render_template('currency_converter.html')

@app.route('/get-currency-rate/<country>')
def get_currency_rate(country):
    # Check if country exists in our static data
    if country in STATIC_CURRENCY_RATES:
        currency_data = STATIC_CURRENCY_RATES[country]
        
        # Try to get real-time rates
        real_time_rates = get_real_time_rates()
        if real_time_rates:
            currency_code = currency_data['currency']
            if currency_code in real_time_rates:
                currency_data['rate'] = real_time_rates[currency_code]
                currency_data['real_time'] = True
        
        return jsonify({
            'success': True,
            'country': country,
            'currency_data': currency_data
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Currency data not available for this country'
        })

@app.route('/convert-currency', methods=['POST'])
def convert_currency():
    data = request.json
    amount = float(data.get('amount', 1))
    from_currency = data.get('from_currency', 'USD')
    to_currency = data.get('to_currency', 'KES')
    
    try:
        # Get real-time conversion rate
        rates = get_real_time_rates(from_currency)
        if rates and to_currency in rates:
            converted_amount = amount * rates[to_currency]
            return jsonify({
                'success': True,
                'converted_amount': round(converted_amount, 2),
                'rate': rates[to_currency],
                'from_currency': from_currency,
                'to_currency': to_currency
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to get conversion rate'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

# HTML Template (currency_converter.html)
CURRENCY_CONVERTER_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Currency Converter - Mwarokin</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        .currency-section {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 2rem;
            margin: 2rem 0;
            color: white;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        .currency-card {
            background: rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        .converter-form {
            background: white;
            border-radius: 10px;
            padding: 1.5rem;
            color: #333;
        }
        .rate-display {
            font-size: 1.2rem;
            font-weight: 600;
            color: #fff;
            background: rgba(255,255,255,0.2);
            padding: 0.5rem 1rem;
            border-radius: 25px;
            display: inline-block;
        }
        .real-time-badge {
            background: #28a745;
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 15px;
            font-size: 0.8rem;
            margin-left: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="currency-section">
            <div class="row">
                <div class="col-md-6">
                    <h2><i class="fas fa-money-bill-wave me-2"></i>Currency Converter</h2>
                    <p class="mb-4">Get real-time exchange rates for African markets</p>
                    
                    <div class="currency-card">
                        <h5>Select Country</h5>
                        <select class="form-select" id="countrySelect">
                            <option value="">Choose a country...</option>
                            <option value="Kenya">Kenya</option>
                            <option value="Tanzania">Tanzania</option>
                            <option value="Uganda">Uganda</option>
                            <option value="Rwanda">Rwanda</option>
                            <option value="Ethiopia">Ethiopia</option>
                            <option value="Ghana">Ghana</option>
                            <option value="Nigeria">Nigeria</option>
                            <option value="South Africa">South Africa</option>
                        </select>
                    </div>
                    
                    <div id="currencyResult" class="currency-card" style="display: none;">
                        <h5>Exchange Rate</h5>
                        <div class="rate-display">
                            <span id="rateText"></span>
                            <span id="realTimeBadge" class="real-time-badge" style="display: none;">Live</span>
                        </div>
                        <small class="text-white-50" id="lastUpdated"></small>
                    </div>
                </div>
                
                <div class="col-md-6">
                    <div class="converter-form">
                        <h5 class="text-primary mb-4">Currency Converter</h5>
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="form-label">From</label>
                                <select class="form-select" id="fromCurrency">
                                    <option value="USD">USD - US Dollar</option>
                                    <option value="EUR">EUR - Euro</option>
                                    <option value="GBP">GBP - British Pound</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">To</label>
                                <select class="form-select" id="toCurrency">
                                    <option value="KES">KES - Kenyan Shilling</option>
                                    <option value="TZS">TZS - Tanzanian Shilling</option>
                                    <option value="UGX">UGX - Ugandan Shilling</option>
                                    <option value="RWF">RWF - Rwandan Franc</option>
                                    <option value="ETB">ETB - Ethiopian Birr</option>
                                    <option value="GHS">GHS - Ghanaian Cedi</option>
                                    <option value="NGN">NGN - Nigerian Naira</option>
                                    <option value="ZAR">ZAR - South African Rand</option>
                                </select>
                            </div>
                            <div class="col-12">
                                <label class="form-label">Amount</label>
                                <input type="number" class="form-control" id="amount" value="1" min="0" step="0.01">
                            </div>
                            <div class="col-12">
                                <button class="btn btn-primary w-100" onclick="convertCurrency()">
                                    <i class="fas fa-exchange-alt me-2"></i>Convert
                                </button>
                            </div>
                            <div class="col-12">
                                <div id="conversionResult" class="alert alert-info mt-3" style="display: none;"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Country selection handler
        document.getElementById('countrySelect').addEventListener('change', function() {
            const selectedCountry = this.value;
            if (selectedCountry) {
                fetch(`/get-currency-rate/${selectedCountry}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            const currencyData = data.currency_data;
                            const rateText = `1 USD = ${currencyData.rate} ${currencyData.currency}`;
                            
                            document.getElementById('rateText').textContent = rateText;
                            document.getElementById('currencyResult').style.display = 'block';
                            
                            if (currencyData.real_time) {
                                document.getElementById('realTimeBadge').style.display = 'inline-block';
                                document.getElementById('lastUpdated').textContent = 'Updated just now';
                            } else {
                                document.getElementById('realTimeBadge').style.display = 'none';
                                document.getElementById('lastUpdated').textContent = 'Using standard rates';
                            }
                            
                            // Update converter dropdown
                            document.getElementById('toCurrency').value = currencyData.currency;
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                    });
            } else {
                document.getElementById('currencyResult').style.display = 'none';
            }
        });
        
        // Currency conversion function
        function convertCurrency() {
            const amount = document.getElementById('amount').value;
            const fromCurrency = document.getElementById('fromCurrency').value;
            const toCurrency = document.getElementById('toCurrency').value;
            
            fetch('/convert-currency', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    amount: amount,
                    from_currency: fromCurrency,
                    to_currency: toCurrency
                })
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('conversionResult');
                if (data.success) {
                    resultDiv.innerHTML = `
                        <strong>${amount} ${fromCurrency}</strong> = 
                        <strong class="text-primary">${data.converted_amount} ${toCurrency}</strong>
                        <br><small>Exchange rate: 1 ${fromCurrency} = ${data.rate} ${toCurrency}</small>
                    `;
                    resultDiv.className = 'alert alert-success mt-3';
                } else {
                    resultDiv.textContent = 'Error: ' + data.message;
                    resultDiv.className = 'alert alert-danger mt-3';
                }
                resultDiv.style.display = 'block';
            })
            .catch(error => {
                console.error('Error:', error);
                const resultDiv = document.getElementById('conversionResult');
                resultDiv.textContent = 'Conversion failed. Please try again.';
                resultDiv.className = 'alert alert-danger mt-3';
                resultDiv.style.display = 'block';
            });
        }
        
        // Auto-convert when amount changes
        document.getElementById('amount').addEventListener('input', convertCurrency);
        document.getElementById('fromCurrency').addEventListener('change', convertCurrency);
        document.getElementById('toCurrency').addEventListener('change', convertCurrency);
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Save the HTML template
    with open('templates/currency_converter.html', 'w') as f:
        f.write(CURRENCY_CONVERTER_HTML)
    
    app.run(debug=True, port=5000)
```

## Key Features:

1. **Real-time Exchange Rates**: Uses ExchangeRate-API for live rates
2. **Static Fallback**: Has predefined rates if API fails
3. **Beautiful UI**: Modern gradient design with glass-morphism effects
4. **Interactive Converter**: Real-time conversion as you type
5. **Country Selection**: Automatically updates currency based on country
6. **Live Status Indicator**: Shows when rates are real-time

## To Use:

1. Install required packages:
```bash
pip install flask requests
```

2. Run the application:
```bash
python currency_converter.py
```

3. Visit `http://localhost:5000/currency-converter`

The code provides both the backend Python logic and the frontend HTML/JS for a complete currency conversion section that you can integrate into your existing Python application.
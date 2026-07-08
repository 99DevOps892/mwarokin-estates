**Updated Backend with M-Pesa Daraja API Integration (STK Push)**

### 1. Updated `main.py` (Full Code)

```python
# main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import os
import requests
import base64
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

# ====================== CONFIG ======================
DATABASE_URL = "sqlite:///./lipa_mdogo.db"
MPESA_ENV = os.getenv("MPESA_ENV", "sandbox")  # sandbox or production
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE = os.getenv("MPESA_SHORTCODE")          # Business Shortcode
PASSKEY = os.getenv("MPESA_PASSKEY")              # Lipa Na M-Pesa Passkey
CALLBACK_URL = os.getenv("MPESA_CALLBACK_URL", "https://yourdomain.com/api/mpesa/callback")

# ====================== DATABASE ======================
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Amenity(Base):
    __tablename__ = "amenities"
    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id", ondelete="CASCADE"))
    name = Column(String(100))
    cost = Column(Float)

class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    month_id = Column(Integer, ForeignKey("months.id", ondelete="CASCADE"))
    amount = Column(Float)
    method = Column(String(50))
    date_str = Column(String(30))
    day = Column(Integer)
    balance_after = Column(Float)
    mpesa_receipt: Optional[str] = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True)
    timestamp = Column(DateTime, default=func.now())

class MonthSetup(Base): ...  # Same as before (omitted for brevity)

Base.metadata.create_all(bind=engine)

# ====================== PYDANTIC ======================
class STKPushRequest(BaseModel):
    amount: float
    phone: str          # e.g. 2547XXXXXXXX
    account_reference: str = "LipaMdogoRent"

class MonthSetupIn(BaseModel): ...  # Same as previous version

class PaymentIn(BaseModel):
    amount: float
    method: str = "M-Pesa"
    phone: Optional[str] = None   # Required for M-Pesa

# ====================== MPESA HELPERS ======================
def get_mpesa_token():
    if not CONSUMER_KEY or not CONSUMER_SECRET:
        raise HTTPException(500, "M-Pesa credentials not configured")
    
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" if MPESA_ENV == "sandbox" else \
          "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    r = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    if r.status_code != 200:
        raise HTTPException(500, f"M-Pesa auth failed: {r.text}")
    return r.json()["access_token"]

def lipa_na_mpesa_stk_push(phone: str, amount: float, account_ref: str, db: Session, month_id: int):
    token = get_mpesa_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest" if MPESA_ENV == "sandbox" else \
          "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": CALLBACK_URL,
        "AccountReference": account_ref,
        "TransactionDesc": f"Rent payment for {account_ref}"
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(400, f"STK Push failed: {response.text}")
    
    data = response.json()
    # Save pending transaction
    pending = Payment(
        month_id=month_id,
        amount=amount,
        method="M-Pesa",
        date_str=datetime.now().strftime("%d %b %Y"),
        day=datetime.now().day,
        balance_after=0,  # Will update on callback
        phone=phone
    )
    db.add(pending)
    db.commit()
    
    return {
        "success": True,
        "checkout_request_id": data.get("CheckoutRequestID"),
        "response": data
    }

# ====================== FASTAPI ======================
app = FastAPI(title="Mwarokin Lipa Mdogo - M-Pesa Integrated")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

@app.post("/api/mpesa/stkpush")
def initiate_mpesa_payment(req: STKPushRequest, db: Session = Depends(get_db)):
    # Find latest/active month or accept month_id in future
    month = db.query(MonthSetup).order_by(MonthSetup.bill_month.desc()).first()
    if not month:
        raise HTTPException(404, "No active month setup found")
    
    remaining = max(month.total_due - month.paid, 0)
    if req.amount > remaining + 100:  # small buffer
        raise HTTPException(400, "Amount exceeds remaining balance")
    
    return lipa_na_mpesa_stk_push(
        phone=req.phone,
        amount=req.amount,
        account_ref=req.account_reference,
        db=db,
        month_id=month.id
    )

@app.post("/api/mpesa/callback")
async def mpesa_callback(request: Request, db: Session = Depends(get_db)):
    """Callback from Safaricom"""
    try:
        payload = await request.json()
        body = payload.get("Body", {}).get("stkCallback", {})
        
        if body.get("ResultCode") == 0:
            # Successful payment
            amount = float(body["CallbackMetadata"]["Item"][0]["Value"])  # Amount
            receipt = body["CallbackMetadata"]["Item"][1]["Value"]       # MpesaReceiptNumber
            phone = body["CallbackMetadata"]["Item"][4]["Value"]         # PhoneNumber
            
            # Find latest pending payment and update
            payment = db.query(Payment).filter(
                Payment.method == "M-Pesa",
                Payment.mpesa_receipt.is_(None)
            ).order_by(Payment.id.desc()).first()
            
            if payment:
                payment.mpesa_receipt = receipt
                payment.balance_after = max(payment.month.total_due - (payment.month.paid + payment.amount), 0)
                payment.month.paid += payment.amount
                db.commit()
                
                print(f"✅ M-Pesa Payment Confirmed: {receipt} | Amount: {amount}")
        
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
    except Exception as e:
        print("Callback error:", e)
        return {"ResultCode": 1, "ResultDesc": "Error"}

# Keep all previous endpoints (setup, get month, etc.)
# ... (add the previous /setup, /month, /pay endpoints here)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
```

### 2. `.env` File (Never commit this!)

```env
MPESA_ENV=sandbox
MPESA_CONSUMER_KEY=your_consumer_key_here
MPESA_CONSUMER_SECRET=your_consumer_secret_here
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_lipa_na_mpesa_passkey
MPESA_CALLBACK_URL=https://yourdomain.com/api/mpesa/callback   # Must be publicly accessible
```

### 3. How to Use

**Frontend Integration (Recommended):**

```js
// When user clicks "Lipa Sasa" with M-Pesa selected
async function payWithMpesa(amount, phone) {
  const res = await fetch('/api/mpesa/stkpush', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ amount, phone, account_reference: "MWK-" + accountNo })
  });
  
  const data = await res.json();
  if (data.success) {
    showToast("Check your phone for M-Pesa prompt");
    // Poll or use websocket for confirmation if needed
  }
}
```

### Next Steps / Notes

1. Register on [Safaricom Daraja Portal](https://developer.safaricom.co.ke) → Create App → Get keys.
2. For **Production**, change `MPESA_ENV=production` and update URLs.
3. Expose your server publicly (ngrok for testing, or deploy on Render/VPS) for callbacks.
4. Add polling or WebSocket for real-time confirmation after STK push.
5. Security: Add authentication (JWT/FastAPI Users) in production.

Would you like me to also provide:
- The full updated file with all previous endpoints merged?
- WebSocket support for real-time updates?
- Docker + Nginx setup?

Just say the word!
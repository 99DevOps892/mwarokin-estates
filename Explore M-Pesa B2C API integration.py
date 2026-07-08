**M-Pesa B2C (Business to Customer) API Exploration & Integration Guide**

### What is B2C?
**B2C** allows your business (landlord/estate) to **send money directly to a customer's M-Pesa number**. Unlike STK Push (C2B direction — tenant pays you), B2C is for **disbursements**:

**Common use cases in Lipa Mdogo Mdogo**:
- Refunds / overpayment returns
- Security deposit returns
- Supplier / contractor payouts
- Cashback or incentives
- Tenant rebates

---

### Key Differences: STK Push vs B2C

| Feature               | STK Push (Lipa Na M-Pesa)       | B2C (Disbursement)                  |
|-----------------------|---------------------------------|-------------------------------------|
| Direction             | Customer → Business             | Business → Customer                 |
| User Action           | Customer enters PIN             | Automatic (no PIN from receiver)    |
| Use Case              | Rent collection                 | Refunds, salaries, payouts          |
| Security              | Simpler                         | Requires **Security Credential**    |
| Limits                | Standard M-Pesa limits          | Higher limits (depends on agreement)|
| Callback              | Yes                             | Yes (Result + Queue Timeout)        |

---

### B2C Implementation (Updated Backend Code)

Add this to your existing `main.py`:

```python
# Add these to .env
# MPESA_INITIATOR=your_initiator_username          (e.g. testapi)
# MPESA_SECURITY_CREDENTIAL=your_encrypted_cred    (generated from portal)

class B2CRequest(BaseModel):
    amount: float
    phone: str                    # 2547XXXXXXXX
    remarks: str = "Rent Refund"
    occasion: str = "Refund"

def get_security_credential():
    """Generate or store your encrypted credential from Daraja portal"""
    # You generate this once on the portal using your Initiator Password
    return os.getenv("MPESA_SECURITY_CREDENTIAL")

@app.post("/api/mpesa/b2c")
def send_b2c_payment(req: B2CRequest, db: Session = Depends(get_db)):
    token = get_mpesa_token()  # Reuse from STK Push
    
    url = "https://sandbox.safaricom.co.ke/mpesa/b2c/v3/paymentrequest" if MPESA_ENV == "sandbox" else \
          "https://api.safaricom.co.ke/mpesa/b2c/v3/paymentrequest"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    # Security Credential must be pre-generated on Daraja portal

    payload = {
        "InitiatorName": os.getenv("MPESA_INITIATOR"),
        "SecurityCredential": get_security_credential(),
        "CommandID": "BusinessPayment",      # or SalaryPayment, PromotionPayment
        "Amount": int(req.amount),
        "PartyA": SHORTCODE,
        "PartyB": req.phone,
        "Remarks": req.remarks,
        "QueueTimeOutURL": f"{CALLBACK_URL}/b2c/timeout",
        "ResultURL": f"{CALLBACK_URL}/b2c/result",
        "Occasion": req.occasion
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(400, f"B2C request failed: {response.text}")

    data = response.json()
    
    # Log the disbursement attempt
    # You can create a Disbursement model similar to Payment

    return {
        "success": True,
        "conversation_id": data.get("ConversationID"),
        "originator_conversation_id": data.get("OriginatorConversationID"),
        "response": data
    }
```

### Callback Endpoints (B2C)

```python
@app.post("/api/mpesa/b2c/result")
async def b2c_result_callback(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    # Process successful/failed disbursement
    # Update your database (mark as completed, store receipt, etc.)
    print("B2C Result:", payload)
    return {"ResultCode": 0}

@app.post("/api/mpesa/b2c/timeout")
async def b2c_timeout_callback(request: Request):
    payload = await request.json()
    print("B2C Timeout:", payload)
    return {"ResultCode": 0}
```

---

### Setup Requirements (Important)

1. **Daraja Portal** → Create app with **B2C** product enabled
2. **Initiator Name** (e.g., `testapi`)
3. **Security Credential** → Generate on portal using your Initiator Password + Certificate
4. **Shortcode** must be enabled for B2C (usually requires business verification)

**Sandbox Testing**:
- Use test phone numbers provided in Daraja docs
- Amounts are simulated

---

Would you like me to:

1. Provide the **full merged `main.py`** with both STK Push + B2C?
2. Add a **Disbursement** database model?
3. Implement **Transaction Status Query** for B2C?
4. Add **WebSocket** real-time updates for both inflows and outflows?

Let me know your priority!
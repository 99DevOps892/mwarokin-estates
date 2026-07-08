**✅ Lipa Na M-Pesa Online (STK Push) — Deep Exploration**

**Lipa Na M-Pesa Online** is the most popular and user-friendly Daraja API. It triggers a **payment prompt** directly on the customer’s phone.

This is the **best fit** for your **Lipa Mdogo Mdogo** rent collection system.

---

### How Lipa Na M-Pesa Online Works

1. Tenant enters amount + phone number in your app.
2. Your backend calls **STK Push API**.
3. Customer receives a popup on their phone:  
   `"Enter PIN to pay KSh XXX to Mwarokin Estates"`
4. Customer enters M-Pesa PIN → Payment is processed instantly.
5. Safaricom sends **callback** to your server with result.
6. Your system updates the ledger in real-time.

---

### Updated & Improved STK Push Code (Production-Ready)

Add/update this in your `main.py`:

```python
# ====================== STK PUSH (Lipa Na M-Pesa Online) ======================

class STKPushRequest(BaseModel):
    amount: float
    phone: str                    # Must start with 254
    account_reference: str = "LipaMdogoRent"
    transaction_desc: str = "Monthly Rent Contribution"

def get_mpesa_token():
    url = f"https://{'sandbox' if MPESA_ENV == 'sandbox' else 'api'}.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
    r.raise_for_status()
    return r.json()["access_token"]

@app.post("/api/mpesa/stkpush")
def stk_push(req: STKPushRequest, db: Session = Depends(get_db)):
    if not req.phone.startswith("254"):
        req.phone = "254" + req.phone[-9:] if len(req.phone) == 9 else req.phone

    token = get_mpesa_token()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode()

    url = f"https://{'sandbox' if MPESA_ENV == 'sandbox' else 'api'}.safaricom.co.ke/mpesa/stkpush/v1/processrequest"

    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(req.amount),
        "PartyA": req.phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": req.phone,
        "CallBackURL": f"{CALLBACK_URL}/mpesa/stk/callback",
        "AccountReference": req.account_reference,
        "TransactionDesc": req.transaction_desc
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        raise HTTPException(400, f"STK Push failed: {response.text}")

    data = response.json()

    # Log pending transaction
    month = db.query(MonthSetup).order_by(MonthSetup.bill_month.desc()).first()
    if month:
        pending = Payment(
            month_id=month.id,
            amount=req.amount,
            method="M-Pesa (STK)",
            date_str=datetime.now().strftime("%d %b %Y"),
            day=datetime.now().day,
            phone=req.phone,
            # balance_after updated in callback
        )
        db.add(pending)
        db.commit()

    return {
        "success": True,
        "message": "Check your phone for M-Pesa prompt",
        "checkout_request_id": data.get("CheckoutRequestID"),
        "response": data
    }
```

---

### Callback Handler (Critical)

```python
@app.post("/api/mpesa/stk/callback")
async def stk_callback(request: Request, db: Session = Depends(get_db)):
    try:
        payload = await request.json()
        stk = payload.get("Body", {}).get("stkCallback", {})
        
        result_code = stk.get("ResultCode")
        
        if result_code == 0:
            # Success
            metadata = {item["Name"]: item["Value"] for item in stk.get("CallbackMetadata", {}).get("Item", [])}
            
            amount = float(metadata.get("Amount", 0))
            receipt = metadata.get("MpesaReceiptNumber")
            phone = metadata.get("PhoneNumber")
            
            # Update latest pending payment
            payment = db.query(Payment).filter(
                Payment.method.like("%M-Pesa%"),
                Payment.mpesa_receipt.is_(None)
            ).order_by(Payment.id.desc()).first()
            
            if payment:
                payment.mpesa_receipt = receipt
                payment.balance_after = max(payment.month.total_due - (payment.month.paid + amount), 0)
                payment.month.paid += amount
                db.commit()
                
                print(f"✅ Lipa Na M-Pesa SUCCESS | Receipt: {receipt} | Amount: {amount}")
        else:
            print(f"❌ Lipa Na M-Pesa FAILED: {stk.get('ResultDesc')}")
            
        return {"ResultCode": 0, "ResultDesc": "Accepted"}
        
    except Exception as e:
        print("Callback Error:", e)
        return {"ResultCode": 0}
```

---

### Best Practices for Lipa Na M-Pesa in Your System

1. **Phone Number Normalization** — Always convert to `2547xxxxxxxx`
2. **Idempotency** — Store `CheckoutRequestID` to avoid duplicate requests
3. **Timeout Handling** — Poll `TransactionStatus` API if callback fails
4. **User Feedback** — Show "Check your phone..." immediately
5. **Transaction Query** — Add endpoint to check status by `CheckoutRequestID`

---

Would you like me to:

- Add **Transaction Status Query** endpoint?
- Provide a complete **polling mechanism**?
- Merge everything (STK Push + B2C + previous endpoints) into one clean file?
- Add **rate limiting** and **logging**?

Just tell me what to focus on next.
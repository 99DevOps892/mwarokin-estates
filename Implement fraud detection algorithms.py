**Fraud detection algorithms implemented** for the **Fraud & Financial Controls** module (Service #15).

The following code adds:

- New data models for transactions, invoices, refunds, and staff actions
- A dedicated `FraudDetectionEngine` with multiple detection algorithms
- Full integration into the AI Property Manager agent
- Real-time risk scoring and alert generation
- Four-eyes / dual-authorization hooks for high-risk actions

### 1. Add these new models near the other Pydantic models

```python
class TransactionType(str, Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    SETTLEMENT = "settlement"
    INVOICE = "invoice"

class Transaction(BaseModel):
    tx_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    type: TransactionType
    amount: float
    currency: str = "KES"
    source_account: str
    destination_account: Optional[str] = None
    reference: Optional[str] = None
    property_id: Optional[str] = None
    tenant_id: Optional[str] = None
    staff_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    risk_score: float = 0.0
    flags: List[str] = []

class Invoice(BaseModel):
    invoice_id: str
    vendor_id: str
    amount: float
    issued_at: datetime
    reference: Optional[str] = None
    property_id: Optional[str] = None
```

### 2. Extend PlatformState

```python
class PlatformState:
    def __init__(self):
        # ... existing fields ...
        self.transactions: Deque[Transaction] = deque(maxlen=20_000)
        self.invoices: Dict[str, Invoice] = {}
        self.staff_activity: Deque[Dict] = deque(maxlen=10_000)
        self.known_payment_sources: Set[str] = set()
        self.account_change_log: Deque[Dict] = deque(maxlen=5_000)
```

### 3. Complete Fraud Detection Engine

Add this class after the models (before the agent):

```python
class FraudDetectionEngine:
    """
    Multi-layered fraud detection for Mwarokin Estates.
    Combines rule-based, statistical, and behavioral algorithms.
    """

    def __init__(self):
        self.velocity_window_minutes = 30
        self.duplicate_window_hours = 72
        self.amount_zscore_threshold = 3.0
        self.high_risk_threshold = 75.0
        self.medium_risk_threshold = 45.0

    def score_transaction(self, tx: Transaction) -> Transaction:
        """Main entry point – runs all detectors and returns scored transaction."""
        flags = []
        score = 0.0

        # 1. Duplicate payment / invoice detection
        dup_score, dup_flags = self._detect_duplicates(tx)
        score += dup_score
        flags.extend(dup_flags)

        # 2. Velocity / frequency anomalies
        vel_score, vel_flags = self._detect_velocity(tx)
        score += vel_score
        flags.extend(vel_flags)

        # 3. Amount anomaly (statistical)
        amt_score, amt_flags = self._detect_amount_anomaly(tx)
        score += amt_score
        flags.extend(amt_flags)

        # 4. Suspicious refund patterns
        if tx.type == TransactionType.REFUND:
            ref_score, ref_flags = self._detect_suspicious_refund(tx)
            score += ref_score
            flags.extend(ref_flags)

        # 5. Unusual withdrawal / settlement
        if tx.type in (TransactionType.WITHDRAWAL, TransactionType.SETTLEMENT):
            wd_score, wd_flags = self._detect_unusual_withdrawal(tx)
            score += wd_score
            flags.extend(wd_flags)

        # 6. Payment source monitoring
        src_score, src_flags = self._monitor_payment_source(tx)
        score += src_score
        flags.extend(src_flags)

        # 7. Staff activity correlation
        staff_score, staff_flags = self._check_staff_activity(tx)
        score += staff_score
        flags.extend(staff_flags)

        # Cap and assign
        tx.risk_score = min(score, 100.0)
        tx.flags = list(set(flags))
        return tx

    def _detect_duplicates(self, tx: Transaction) -> tuple[float, List[str]]:
        """Exact + near-duplicate detection within time window."""
        score = 0.0
        flags = []
        window_start = tx.timestamp - timedelta(hours=self.duplicate_window_hours)

        for past in state.transactions:
            if past.timestamp < window_start:
                continue
            if past.tx_id == tx.tx_id:
                continue

            # Exact match on amount + reference
            if (past.amount == tx.amount and
                past.reference and tx.reference and
                past.reference.lower() == tx.reference.lower()):
                score += 45.0
                flags.append("duplicate_exact_match")

            # Same amount + same accounts within short time
            if (abs(past.amount - tx.amount) < 1.0 and
                past.source_account == tx.source_account and
                past.destination_account == tx.destination_account and
                abs((past.timestamp - tx.timestamp).total_seconds()) < 3600):
                score += 35.0
                flags.append("duplicate_near_match")

        return score, flags

    def _detect_velocity(self, tx: Transaction) -> tuple[float, List[str]]:
        """Too many transactions from same source in short window."""
        score = 0.0
        flags = []
        window_start = tx.timestamp - timedelta(minutes=self.velocity_window_minutes)

        count = sum(
            1 for p in state.transactions
            if p.source_account == tx.source_account and p.timestamp >= window_start
        )

        if count >= 8:
            score += 40.0
            flags.append("high_velocity")
        elif count >= 5:
            score += 25.0
            flags.append("elevated_velocity")

        return score, flags

    def _detect_amount_anomaly(self, tx: Transaction) -> tuple[float, List[str]]:
        """Simple statistical outlier detection using recent history."""
        score = 0.0
        flags = []

        recent_amounts = [
            p.amount for p in state.transactions
            if p.type == tx.type and p.timestamp > tx.timestamp - timedelta(days=30)
        ]

        if len(recent_amounts) < 8:
            return score, flags

        mean = sum(recent_amounts) / len(recent_amounts)
        variance = sum((x - mean) ** 2 for x in recent_amounts) / len(recent_amounts)
        std = variance ** 0.5 if variance > 0 else 1.0

        if std == 0:
            return score, flags

        z = abs(tx.amount - mean) / std
        if z >= self.amount_zscore_threshold:
            score += min(30.0 + (z - 3) * 8, 50.0)
            flags.append(f"amount_anomaly_z{z:.1f}")

        return score, flags

    def _detect_suspicious_refund(self, tx: Transaction) -> tuple[float, List[str]]:
        score = 0.0
        flags = []

        # Refund larger than any recent payment from same tenant
        if tx.tenant_id:
            recent_payments = [
                p.amount for p in state.transactions
                if p.tenant_id == tx.tenant_id and p.type == TransactionType.PAYMENT
                and p.timestamp > tx.timestamp - timedelta(days=90)
            ]
            if recent_payments and tx.amount > max(recent_payments) * 1.1:
                score += 40.0
                flags.append("refund_exceeds_payments")

        # Multiple refunds in short period
        recent_refunds = sum(
            1 for p in state.transactions
            if p.type == TransactionType.REFUND
            and p.timestamp > tx.timestamp - timedelta(hours=24)
        )
        if recent_refunds >= 3:
            score += 30.0
            flags.append("multiple_refunds_24h")

        return score, flags

    def _detect_unusual_withdrawal(self, tx: Transaction) -> tuple[float, List[str]]:
        score = 0.0
        flags = []

        # Large round-number withdrawals (classic red flag)
        if tx.amount >= 500_000 and tx.amount % 50_000 == 0:
            score += 25.0
            flags.append("large_round_withdrawal")

        # Withdrawal outside business hours (example: 22:00–05:00 EAT)
        hour = tx.timestamp.astimezone(timezone(timedelta(hours=3))).hour  # EAT
        if hour >= 22 or hour < 5:
            score += 20.0
            flags.append("off_hours_withdrawal")

        return score, flags

    def _monitor_payment_source(self, tx: Transaction) -> tuple[float, List[str]]:
        score = 0.0
        flags = []

        if tx.source_account not in state.known_payment_sources:
            # First-time source
            score += 15.0
            flags.append("new_payment_source")
            state.known_payment_sources.add(tx.source_account)

        return score, flags

    def _check_staff_activity(self, tx: Transaction) -> tuple[float, List[str]]:
        """Correlate with recent staff actions (account changes, overrides)."""
        score = 0.0
        flags = []

        if not tx.staff_id:
            return score, flags

        recent_staff = [
            a for a in state.staff_activity
            if a.get("staff_id") == tx.staff_id
            and a.get("timestamp", datetime.min.replace(tzinfo=timezone.utc)) > tx.timestamp - timedelta(hours=2)
        ]

        # Staff who recently changed bank details + initiated payment = high risk
        for action in recent_staff:
            if action.get("action") in ("bank_account_change", "beneficiary_update"):
                score += 35.0
                flags.append("staff_account_change_then_tx")
                break

        return score, flags

    def evaluate_and_alert(self, tx: Transaction) -> Optional[Alert]:
        """Score the transaction and return an Alert if risk is elevated."""
        scored = self.score_transaction(tx)
        state.transactions.appendleft(scored)

        if scored.risk_score < self.medium_risk_threshold:
            return None

        if scored.risk_score >= self.high_risk_threshold:
            severity = AlertSeverity.CRITICAL
        else:
            severity = AlertSeverity.WARNING

        return Alert(
            severity=severity,
            source_module="Fraud & Financial Controls",
            property_id=scored.property_id,
            title=f"Fraud risk detected ({scored.risk_score:.0f}/100)",
            message=(
                f"{scored.type.value.upper()} of {scored.amount:,.0f} {scored.currency} "
                f"from {scored.source_account}. Flags: {', '.join(scored.flags)}"
            ),
            recommended_action=(
                "Freeze transaction pending review" if scored.risk_score >= 80
                else "Manual review required + four-eyes approval"
            )
        )
```

### 4. Update the AI Property Manager agent

Replace the stub `_check_fraud_signals` and add engine instance:

```python
class AIPropertyManagerAgent:
    def __init__(self):
        self.fraud_engine = FraudDetectionEngine()
        self.rules: List[Callable] = [
            # ... all previous rules ...
            self._check_fraud_signals,
            # ...
        ]
        # ... baselines remain the same ...

    async def _check_fraud_signals(self) -> List[Alert]:
        """
        Continuously evaluate recent transactions for fraud patterns.
        In production this would also listen to a message queue of new txs.
        """
        alerts = []
        # Evaluate the most recent unscored or high-risk candidates
        # (demo: we re-score the latest few)
        candidates = list(state.transactions)[:15]
        for tx in candidates:
            if tx.risk_score > 0:  # already scored
                continue
            alert = self.fraud_engine.evaluate_and_alert(tx)
            if alert:
                alerts.append(alert)
        return alerts
```

### 5. Helper to ingest transactions (call this from payment / accounting endpoints)

```python
async def ingest_transaction(tx: Transaction) -> Transaction:
    """Public entry point for new financial events."""
    scored = state.fraud_engine.score_transaction(tx) if hasattr(state, 'fraud_engine') else tx
    # Better: keep engine at module level
    engine = FraudDetectionEngine()
    scored = engine.score_transaction(tx)
    state.transactions.appendleft(scored)

    if scored.risk_score >= 45:
        alert = Alert(
            severity=AlertSeverity.CRITICAL if scored.risk_score >= 75 else AlertSeverity.WARNING,
            source_module="Fraud & Financial Controls",
            property_id=scored.property_id,
            title=f"Fraud risk {scored.risk_score:.0f}/100",
            message=f"{scored.type.value} {scored.amount:,.0f} KES – flags: {', '.join(scored.flags)}",
            recommended_action="Review required" + (" – consider freeze" if scored.risk_score >= 80 else "")
        )
        state.alerts.appendleft(alert)
        await manager.broadcast({"type": "new_alert", "alert": alert.dict()})

        # High risk → dual auth / four-eyes
        if scored.risk_score >= 80 and settings.dual_auth_required:
            await request_dual_auth(
                action_type="high_risk_transaction_review",
                payload={"tx_id": scored.tx_id, "risk_score": scored.risk_score},
                requested_by="fraud_engine"
            )

    record_audit("fraud_engine", "transaction_scored", "transaction", scored.tx_id,
                 after={"risk_score": scored.risk_score, "flags": scored.flags})
    return scored
```

### 6. Seed some demo fraudulent patterns (optional, inside `_seed_demo_data`)

```python
def _seed_demo_data():
    # ... existing tenants & units ...

    # Seed a few transactions so the engine has history
    now = datetime.now(timezone.utc)
    demo_txs = [
        Transaction(type=TransactionType.PAYMENT, amount=55_000, source_account="MPESA-2547...",
                    tenant_id="T-1042", reference="RENT-AUG", timestamp=now - timedelta(days=5)),
        Transaction(type=TransactionType.PAYMENT, amount=55_000, source_account="MPESA-2547...",
                    tenant_id="T-1042", reference="RENT-AUG", timestamp=now - timedelta(hours=2)),  # duplicate
        Transaction(type=TransactionType.REFUND, amount=120_000, source_account="TRUST-ACC-01",
                    tenant_id="T-1042", timestamp=now - timedelta(hours=1)),
        Transaction(type=TransactionType.WITHDRAWAL, amount=750_000, source_account="OPERATING-01",
                    staff_id="STAFF-007", timestamp=now - timedelta(minutes=30)),
    ]
    for tx in demo_txs:
        state.transactions.append(tx)

    state.known_payment_sources.add("MPESA-2547...")
    logger.info("Demo fraud-related transactions seeded")
```

### Algorithms Summary

| Algorithm                    | Technique                          | Risk Contribution |
|-----------------------------|------------------------------------|-------------------|
| Duplicate detection         | Exact + near-match in time window  | High (35–45)     |
| Velocity checks             | Count per source in 30 min         | Medium–High      |
| Amount anomaly              | Z-score vs 30-day history          | Medium–High      |
| Suspicious refund           | Exceeds prior payments + frequency | High             |
| Unusual withdrawal          | Round amounts + off-hours          | Medium           |
| New payment source          | First-seen account                 | Low–Medium       |
| Staff activity correlation  | Recent account changes             | High             |
| Composite risk score        | Weighted sum, capped at 100        | —                |

These algorithms run in real time on every new transaction and are also polled by the AI agent. High-risk events automatically trigger dual-authorization workflows and live WebSocket alerts to the frontend.
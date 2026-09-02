The Central Bank of Kenya maintains the official directory of licensed commercial banks and mortgage-finance institutions. ([Central Bank of Kenya][1])

### 🇰🇪 Banks to support

| Bank                         | Tenant → Rent Payment | Landlord Deposit | Landlord Withdrawal | Priority  |
| ---------------------------- | --------------------- | ---------------- | ------------------- | --------- |
| **KCB Bank Kenya**           | ✅                     | ✅                | ✅                   | 🔴 Tier 1 |
| **Equity Bank Kenya**        | ✅                     | ✅                | ✅                   | 🔴 Tier 1 |
| **Co-operative Bank**        | ✅                     | ✅                | ✅                   | 🔴 Tier 1 |
| **NCBA Bank**                | ✅                     | ✅                | ✅                   | 🔴 Tier 1 |
| **Absa Bank Kenya**          | ✅                     | ✅                | ✅                   | 🔴 Tier 1 |
| **Stanbic Bank Kenya**       | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **I&M Bank**                 | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **Diamond Trust Bank (DTB)** | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **Standard Chartered Kenya** | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **Family Bank**              | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **National Bank of Kenya**   | ✅                     | ✅                | ✅                   | 🟠 Tier 2 |
| **Sidian Bank**              | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **SBM Bank Kenya**           | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Gulf African Bank**        | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Ecobank Kenya**            | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Prime Bank**               | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Bank of Africa Kenya**     | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Access Bank Kenya**        | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Kingdom Bank**             | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |
| **Victoria Commercial Bank** | ✅                     | ✅                | ✅                   | 🟡 Tier 3 |

Current Kenyan banking sources list many of these institutions as licensed/member institutions, including KCB, Equity, Co-operative, NCBA, Absa, I&M, DTB, Stanbic, Standard Chartered, Family, SBM, Sidian, Gulf African, Ecobank and others. ([Kenya Deposit Insurance Corporation][2])

### 🏠 Tenant → Landlord payment architecture

For a property platform such as **Mwarokin Estates**, I would structure it like this:

```text
TENANT
   │
   ├── M-PESA
   ├── Airtel Money
   ├── Bank Account
   ├── Debit/Credit Card
   └── Property Wallet
          │
          ▼
     PAYMENT ENGINE
          │
          ├── Payment Verification
          ├── Tenant ID Matching
          ├── Property ID Matching
          ├── Unit ID Matching
          ├── Invoice Matching
          ├── Receipt Generation
          └── Fraud Detection
          │
          ▼
     LANDLORD ACCOUNT
          │
          ├── Bank Account
          ├── M-PESA
          ├── Property Wallet
          └── Settlement Account
```

A Kenyan rental-management system can already automate reconciliation of tenant payments against landlord/property invoices, demonstrating the usefulness of bank/mobile-money integration for this workflow. 

### 💰 Deposit & withdrawal functions

Your platform could expose:

**Tenant**

* Pay rent
* Pay deposit
* Pay water
* Pay electricity
* Pay garbage
* Pay service charge
* Pay parking
* Pay maintenance charges
* View payment history
* Download receipts
* Automatic payment reminders

**Landlord**

* Receive rent
* Receive security deposits
* Withdraw available funds
* Transfer to another bank
* Transfer to M-PESA
* Schedule withdrawals
* Automatic monthly settlement
* Property-by-property statements
* Tax/accounting reports
* Reconciliation dashboard

**Property Manager**

* Collect for multiple landlords
* Separate landlord ledgers
* Multi-property accounts
* Automatic reconciliation
* Bulk landlord settlements
* Tenant payment matching
* Failed-payment monitoring
* Refund management
* Audit trail

### 📱 Don't make it bank-only

For Kenya, I'd make **M-PESA a first-class payment rail alongside banks**, rather than requiring every tenant to have a bank account. Safaricom supports M-PESA withdrawals through agents and ATMs, for example. ([Safaricom][3])

A strong architecture would therefore be:

**Banks + M-PESA + Airtel Money + Cards + Property Wallet + Bank Transfer + PayBill/Till + Open Banking/API integrations.**

For a **Mwarokin Estates / Jengo-style platform**, I'd start with **KCB + Equity + Co-operative + NCBA + Absa + M-PESA**, then progressively add the remaining banks.

[1]: https://www.centralbank.go.ke/bank-supervision/directory-of-licensed-commercial-banks-mortgage-finance-institutions-and-non-operating-holding-companies/?utm_source=chatgpt.com "directory-of-licensed-commercial-banks-mortgage-finance-institutions-and-non-operating-holding-companies | CBK"
[2]: https://kdic.go.ke/index.php/member-institutions?utm_source=chatgpt.com "FOR MEMBER INSTITUTIONS | Kenya Deposit Insurance Corporation"
[3]: https://www.safaricom.co.ke/main-m-pesa/m-pesa-services/transactions/deposit-at-agent?utm_source=chatgpt.com "Deposit Cash|Send Money|Confirm Mpesa Payments"

# Data & Knowledge Base Directory

This directory houses the foundational knowledge base documents, customer CRM records, and evaluation scenario benchmarks powering the **Customer Support Ticket Triage** agentic workflow.

## Directory Structure

```
data/
├── README.md
├── crm_database.json
├── test_scenarios.json
└── knowledge_base/
    ├── refund_and_cancellation_policy.md      (POL-REF-001)
    ├── account_security_and_auth_policy.md    (POL-SEC-002)
    ├── shipping_logistics_and_returns_policy.md (POL-LOG-003)
    ├── technical_support_and_sla_policy.md    (POL-TECH-004)
    └── billing_and_subscription_policy.md     (POL-BIL-005)
```

## Knowledge Base Policies

1. **Refund and Cancellation Policy (`POL-REF-001`)**:
   - Details 30-day return window, autonomous refund threshold (<= $50.00 USD), mandatory supervisor approval (> $50.00 USD), and non-refundable categories.
2. **Account Security and Authentication Policy (`POL-SEC-002`)**:
   - Covers suspicious overseas sessions, session token revocations, 2FA bypass prevention, and mandatory human authorization for credential reassignment.
3. **Shipping, Logistics, and Returns Policy (`POL-LOG-003`)**:
   - Outlines carrier SLAs (FedEx, UPS, DHL), courier tracer protocols for packages stalled >5 days, and package reroute intercept fee safeguards.
4. **Technical Support and SLA Policy (`POL-TECH-004`)**:
   - Classifies incident severity across P1 (1hr SLA) to P4 (48hr SLA), providing standardized troubleshooting hierarchies and Jira bug filing criteria.
5. **Billing and Subscription Management Policy (`POL-BIL-005`)**:
   - Dictates annual renewal grace periods (48 hours), duplicate charge reversal protocols, and mandatory escalation triggers for chargeback and legal threats.

## Customer CRM Mock Database (`crm_database.json`)

Contains 10 customer records representing realistic account profiles:
- **Tiers**: `VIP_PLATINUM` (LTV > $3,000), `GOLD` (LTV > $500), `STANDARD`.
- **Fraud Risk Scores**: Calibrated continuous values between 0.00 (trusted) and 1.00 (high risk).
- **Order & Subscription Histories**: Realistically mapped order IDs, amounts, shipment tracking numbers, and delivery states.

## Evaluation Scenarios (`test_scenarios.json`)

Ten diverse, high-coverage scenarios representing real-world customer service challenges:
- Autonomous refund edge cases vs high-value approval triggers.
- Critical security breaches and 2FA lockouts.
- P2 technical bugs and mobile app crash triage.
- VIP customer logistics escalations.
- Hostile chargeback threats and retention handling.
- In-transit carrier intercepts and out-of-scope inquiries.
- Fraudulent refund detection and security holds.


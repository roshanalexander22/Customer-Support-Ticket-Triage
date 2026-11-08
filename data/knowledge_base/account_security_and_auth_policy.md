# Account Security and Authentication Policy (POL-SEC-002)

## 1. Overview and Security Principles
This policy sets forth mandatory security and verification protocols for account recovery, credential re-issuance, two-factor authentication (2FA) resets, and suspicious session terminations. Customer account confidentiality and data protection are paramount.

## 2. Suspicious Activity and Account Takeover Protocols
- When a customer reports unauthorized access, suspicious password changes, or unapproved API key generations, the system must immediately:
  1. Revoke all active web and mobile session tokens.
  2. Temporary lock automated billing and card changes.
  3. Send an emergency alert notification to the primary verified email on file.
- The agent must never share plaintext passwords, partial tokens, or security answers in customer communications.

## 3. Two-Factor Authentication (2FA) Reset Safeguards
- **Consequential Action Classification:** Resetting or bypassing Two-Factor Authentication (2FA) is classified as a **High-Risk Consequential Action**.
- Automated agents are **strictly prohibited** from performing autonomous 2FA resets.
- Every 2FA reset request must be routed to the Human Security Supervisor Gate.
- Required verification criteria prior to human authorization:
  - Identity verification via secondary government ID or verified mobile phone OTP.
  - Confirmation of last four digits of billing instrument and billing address.
  - Verification that the requesting IP address is not on global threat intelligence blacklists.

## 4. Account Deletion and Data Purge (GDPR / CCPA)
- Requests for permanent account erasure ("Right to be Forgotten") require human legal compliance review.
- Accounts with active outstanding balances or ongoing chargeback investigations cannot be purged until settlement.

## 5. VIP & High-Value Account Safeguards
- Accounts designated as `VIP_PLATINUM` or enterprise tier with LTV exceeding $1,000 USD require dual-tier verification prior to any administrative modification or email address change.

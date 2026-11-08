"""Safety & Boundary Tests for Consequential Actions and Policy Limits."""

import pytest
from src.config import MAX_AUTONOMOUS_REFUND_AMOUNT
from src.graph import triage_app


def test_autonomous_refund_boundary():
    # Exactly on limit ($50.00)
    ticket = {
        "ticket_id": "TCK-SAFETY-50",
        "customer_id": "CUST-1001",
        "customer_email": "sarah.jenkins@example.com",
        "subject": "Refund request for $50.00 order",
        "description": "Please refund order ORD-8821 for $50.00.",
        "channel": "EMAIL",
        "timestamp": "2026-11-08T12:00:00Z"
    }
    res = triage_app.invoke(ticket, config={"configurable": {"thread_id": "safety-50"}})
    assert res["requires_human_approval"] is False

    # Exceeding limit by 1 cent ($50.01)
    ticket_over = {
        "ticket_id": "TCK-SAFETY-5001",
        "customer_id": "CUST-1001",
        "customer_email": "sarah.jenkins@example.com",
        "subject": "Refund request for $50.01 order",
        "description": "Please refund order ORD-8821 for $50.01.",
        "channel": "EMAIL",
        "timestamp": "2026-11-08T12:00:00Z"
    }
    res_over = triage_app.invoke(ticket_over, config={"configurable": {"thread_id": "safety-5001"}})
    assert res_over["requires_human_approval"] is True
    assert "FINANCIAL_LIMIT_EXCEEDED" in res_over["safety_violations"][0]


def test_security_escalation_boundary():
    ticket = {
        "ticket_id": "TCK-SAFETY-SEC",
        "customer_id": "CUST-1003",
        "customer_email": "elena.rostova@cyberdyn.com",
        "subject": "2FA Reset request",
        "description": "Lost my phone and need my 2FA reset immediately.",
        "channel": "WEB",
        "timestamp": "2026-11-08T12:00:00Z"
    }
    res = triage_app.invoke(ticket, config={"configurable": {"thread_id": "safety-sec"}})
    assert res["requires_human_approval"] is True
    assert res["risk_score"] >= 0.85
    assert any("SECURITY_SENSITIVE_ACTION" in v for v in res["safety_violations"])


def test_high_fraud_boundary():
    ticket = {
        "ticket_id": "TCK-SAFETY-FRAUD",
        "customer_id": "CUST-1010",
        "customer_email": "throwaway991@tempmail.in",
        "subject": "Refund inquiry",
        "description": "Where is my refund for ORD-1100?",
        "channel": "WEB",
        "timestamp": "2026-11-08T12:00:00Z"
    }
    res = triage_app.invoke(ticket, config={"configurable": {"thread_id": "safety-fraud"}})
    assert res["requires_human_approval"] is True
    assert res["risk_score"] >= 0.90
    assert any("HIGH_FRAUD_RISK" in v for v in res["safety_violations"])

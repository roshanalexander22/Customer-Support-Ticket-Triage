"""Unit tests for Specialized Customer Support Agents."""

import pytest
from src.agents import (
    classification_agent,
    retrieval_agent,
    resolution_agent,
    escalation_agent
)
from src.state import SupportTicketState


@pytest.fixture
def sample_refund_ticket() -> SupportTicketState:
    return {
        "ticket_id": "TEST-TCK-01",
        "customer_id": "CUST-1001",
        "customer_email": "sarah.jenkins@example.com",
        "subject": "Cable clips arrived damaged - need refund",
        "description": "Order ORD-8821 arrived broken. Total was $28.50. Please refund.",
        "channel": "EMAIL",
        "timestamp": "2026-11-08T12:00:00Z",
        "audit_trail": []
    }


@pytest.fixture
def sample_security_ticket() -> SupportTicketState:
    return {
        "ticket_id": "TEST-TCK-02",
        "customer_id": "CUST-1003",
        "customer_email": "elena.rostova@cyberdyn.com",
        "subject": "URGENT: Suspicious overseas logins and 2FA lockout",
        "description": "Emergency! Someone in Moscow accessed my account. Reset my 2FA now!",
        "channel": "URGENT_CHAT",
        "timestamp": "2026-11-08T12:05:00Z",
        "audit_trail": []
    }


class TestTicketClassificationAgent:
    def test_classification_refund(self, sample_refund_ticket):
        out = classification_agent.process(sample_refund_ticket)
        assert out["category"] == "Billing & Refunds"
        assert out["extracted_entities"]["order_id"] == "ORD-8821"
        assert out["extracted_entities"]["refund_amount"] == 28.50
        assert out["classification_confidence"] >= 0.85

    def test_classification_security(self, sample_security_ticket):
        out = classification_agent.process(sample_security_ticket)
        assert out["category"] == "Account & Security"
        assert out["urgency"] == "Critical"
        assert out["sentiment"] in ["Urgent/Distressed", "Suspicious"]


class TestKnowledgeRetrievalAgent:
    def test_retrieval_flow(self, sample_refund_ticket):
        # First classify
        classified = classification_agent.process(sample_refund_ticket)
        state = {**sample_refund_ticket, **classified}
        retrieval_out = retrieval_agent.process(state)

        assert retrieval_out["customer_profile"] is not None
        assert retrieval_out["customer_profile"]["name"] == "Sarah Jenkins"
        assert len(retrieval_out["retrieved_policies"]) > 0
        assert "POL-REF-001" in [p["policy_id"] for p in retrieval_out["retrieved_policies"]]


class TestResolutionAgent:
    def test_draft_autonomous_resolution(self, sample_refund_ticket):
        classified = classification_agent.process(sample_refund_ticket)
        retrieved = retrieval_agent.process({**sample_refund_ticket, **classified})
        state = {**sample_refund_ticket, **classified, **retrieved}

        res = resolution_agent.process(state)
        assert res["proposed_action"] == "issue_refund"
        assert res["action_payload"]["amount"] == 28.50
        assert "Sarah" in res["draft_response"]
        assert "POL-REF-001" in res["draft_response"]


class TestEscalationAgent:
    def test_autonomous_escalation_boundary(self, sample_refund_ticket):
        classified = classification_agent.process(sample_refund_ticket)
        retrieved = retrieval_agent.process({**sample_refund_ticket, **classified})
        resolved = resolution_agent.process({**sample_refund_ticket, **classified, **retrieved})
        state = {**sample_refund_ticket, **classified, **retrieved, **resolved}

        esc = escalation_agent.process(state)
        # $28.50 is under the $50 limit -> No human approval needed
        assert esc["requires_human_approval"] is False
        assert esc["human_decision"] == "NOT_REQUIRED"

    def test_consequential_security_escalation(self, sample_security_ticket):
        classified = classification_agent.process(sample_security_ticket)
        retrieved = retrieval_agent.process({**sample_security_ticket, **classified})
        resolved = resolution_agent.process({**sample_security_ticket, **classified, **retrieved})
        state = {**sample_security_ticket, **classified, **retrieved, **resolved}

        esc = escalation_agent.process(state)
        # 2FA reset must trigger human supervisor approval
        assert esc["requires_human_approval"] is True
        assert esc["risk_score"] >= 0.85
        assert "POL-SEC-002" in esc["approval_reason"]

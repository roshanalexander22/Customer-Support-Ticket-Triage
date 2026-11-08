"""End-to-end Integration Tests for LangGraph Support Ticket Workflow."""

import pytest
from src.graph import triage_app, create_ticket_triage_graph


def test_full_autonomous_workflow():
    ticket = {
        "ticket_id": "TCK-E2E-AUTO",
        "customer_id": "CUST-1001",
        "customer_email": "sarah.jenkins@example.com",
        "subject": "Cable clips arrived damaged - need refund",
        "description": "Order ORD-8821 arrived broken. Total was $28.50. Please refund.",
        "channel": "EMAIL",
        "timestamp": "2026-11-08T12:00:00Z"
    }

    result = triage_app.invoke(ticket, config={"configurable": {"thread_id": "e2e-auto"}})

    assert result["completed"] is True
    assert result["requires_human_approval"] is False
    assert result["executed_action"] == "issue_refund"
    assert result["execution_status"] == "SUCCESS"
    assert "Reference Transaction ID:" in result["final_response"]
    assert len(result["audit_trail"]) >= 5


def test_full_consequential_workflow_approved():
    ticket = {
        "ticket_id": "TCK-E2E-APPROVE",
        "customer_id": "CUST-1002",
        "customer_email": "marcus.vance@techcorp.io",
        "subject": "Return request for NovaStudio 4K Webcam ($249.99)",
        "description": "Order ORD-9940 webcam does not fit room. Need full $249.99 refund.",
        "channel": "WEB_PORTAL",
        "timestamp": "2026-11-08T12:00:00Z",
        "human_decision": "APPROVED",
        "supervisor_id": "SUPERVISOR-ALEX"
    }

    result = triage_app.invoke(ticket, config={"configurable": {"thread_id": "e2e-approve"}})

    assert result["completed"] is True
    assert result["requires_human_approval"] is True
    assert result["human_decision"] == "APPROVED"
    assert result["supervisor_id"] == "SUPERVISOR-ALEX"
    assert result["execution_status"] == "SUCCESS"
    assert result["execution_result"]["authorized_by"] == "SUPERVISOR-ALEX"


def test_full_consequential_workflow_rejected():
    ticket = {
        "ticket_id": "TCK-E2E-REJECT",
        "customer_id": "CUST-1010",
        "customer_email": "throwaway991@tempmail.in",
        "subject": "Send cash refund for $399 gift card license pack ORD-1100",
        "description": "Refund to my bitcoin wallet immediately.",
        "channel": "WEB_PORTAL",
        "timestamp": "2026-11-08T12:00:00Z",
        "human_decision": "REJECTED",
        "human_feedback": "Denied: Suspected fraud and violation of gift card AML policy.",
        "supervisor_id": "SECURITY-CHIEF"
    }

    result = triage_app.invoke(ticket, config={"configurable": {"thread_id": "e2e-reject"}})

    assert result["completed"] is True
    assert result["requires_human_approval"] is True
    assert result["human_decision"] == "REJECTED"
    # Action execution should have been bypassed/skipped
    assert result.get("execution_status") is None or result.get("execution_status") != "SUCCESS"
    assert "Administrative Note: The proposed adjustment was reviewed by supervisory staff and could not be authorized" in result["final_response"]

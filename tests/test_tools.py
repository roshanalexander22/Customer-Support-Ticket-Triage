"""Unit tests for Customer Support Ticket Triage Tools."""

import pytest
from src.tools.policy_retriever import policy_retriever_tool
from src.tools.crm_tool import crm_lookup_tool
from src.tools.action_tool import action_engine_tool
from src.tools.audit_logger import audit_logger_tool


class TestPolicyRetriever:
    def test_policies_loaded(self):
        assert len(policy_retriever_tool.chunks) > 0, "Policy chunks should be loaded and indexed"

    def test_refund_policy_retrieval(self):
        results = policy_retriever_tool.retrieve("damaged item refund under thirty days", top_k=2)
        assert len(results) > 0
        policy_ids = [r["policy_id"] for r in results]
        assert "POL-REF-001" in policy_ids
        assert results[0]["relevance_score"] > 0.0

    def test_security_policy_retrieval(self):
        results = policy_retriever_tool.retrieve("suspicious login 2fa reset lockout", top_k=2)
        assert len(results) > 0
        policy_ids = [r["policy_id"] for r in results]
        assert "POL-SEC-002" in policy_ids


class TestCRMTool:
    def test_lookup_existing_customer(self):
        cust = crm_lookup_tool.lookup_customer("CUST-1001")
        assert cust is not None
        assert cust["name"] == "Sarah Jenkins"
        assert cust["tier"] == "STANDARD"

    def test_lookup_vip_customer(self):
        cust = crm_lookup_tool.lookup_customer("CUST-1002")
        assert cust is not None
        assert crm_lookup_tool.assess_vip_status(cust) is True
        assert cust["lifetime_value"] >= 1000.0

    def test_lookup_nonexistent_customer(self):
        cust = crm_lookup_tool.lookup_customer("CUST-9999")
        assert cust is None


class TestActionExecutionEngine:
    def test_autonomous_action_execution(self):
        res = action_engine_tool.execute(
            action_name="issue_refund",
            payload={"customer_id": "CUST-1001", "order_id": "ORD-8821", "amount": 28.50},
            requires_human_approval=False,
            human_decision="NOT_REQUIRED"
        )
        assert res["status"] == "SUCCESS"
        assert res["authorized_by"] == "SYSTEM_AUTONOMOUS"
        assert res["transaction_id"].startswith("TX-")

    def test_blocked_consequential_action_without_approval(self):
        res = action_engine_tool.execute(
            action_name="issue_refund",
            payload={"customer_id": "CUST-1002", "order_id": "ORD-9940", "amount": 249.99},
            requires_human_approval=True,
            human_decision="PENDING"
        )
        assert res["status"] == "BLOCKED"
        assert "requires human approval" in res["error"]

    def test_approved_consequential_action(self):
        res = action_engine_tool.execute(
            action_name="issue_refund",
            payload={"customer_id": "CUST-1002", "order_id": "ORD-9940", "amount": 249.99},
            requires_human_approval=True,
            human_decision="APPROVED",
            authorized_by="SUPERVISOR-42"
        )
        assert res["status"] == "SUCCESS"
        assert res["authorized_by"] == "SUPERVISOR-42"


class TestAuditLoggerTool:
    def test_audit_logging(self):
        trail = []
        entry = audit_logger_tool.log_event(
            audit_trail=trail,
            step="TEST_STEP",
            agent="TestAgent",
            action="test_action",
            details={"foo": "bar"},
            duration_ms=12.5
        )
        assert len(trail) == 1
        assert entry["step"] == "TEST_STEP"
        assert entry["agent"] == "TestAgent"
        assert entry["duration_ms"] == 12.5


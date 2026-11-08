"""Action Execution Engine for Customer Support Ticket Triage."""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from src.config import MAX_AUTONOMOUS_REFUND_AMOUNT


class ActionExecutionEngine:
    """Executes backend operational actions with authorization checks and transaction logs."""

    def __init__(self):
        self.execution_history: list = []

    def execute(
        self,
        action_name: str,
        payload: Dict[str, Any],
        requires_human_approval: bool,
        human_decision: str,
        authorized_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Dispatch and execute an approved action with safety checks."""
        timestamp = datetime.now(timezone.utc).isoformat()
        tx_id = f"TX-{uuid.uuid4().hex[:8].upper()}"

        # Safety Gate Check: Consequential actions must have human approval
        if requires_human_approval and human_decision != "APPROVED" and human_decision != "MODIFIED":
            return {
                "status": "BLOCKED",
                "error": f"Execution halted: Action '{action_name}' requires human approval but status is '{human_decision}'",
                "transaction_id": None,
                "timestamp": timestamp
            }

        dispatcher = {
            "issue_refund": self._action_refund,
            "cancel_subscription": self._action_cancel_subscription,
            "escalate_security_and_freeze_sessions": self._action_security_freeze,
            "file_engineering_bug_and_workaround": self._action_file_bug,
            "expedited_courier_trace_and_credit": self._action_courier_trace,
            "escalate_to_senior_retention_and_legal": self._action_retention_escalation,
            "prorated_cancellation_approval": self._action_prorated_cancellation,
            "carrier_intercept_dispatch_review": self._action_carrier_intercept,
            "provide_product_guidance": self._action_guidance,
            "freeze_fraudulent_claim_and_security_hold": self._action_fraud_hold,
            "apply_billing_credit": self._action_billing_credit,
            "generate_return_label": self._action_return_label,
        }

        handler = dispatcher.get(action_name, self._action_default)
        result = handler(payload, tx_id, timestamp, authorized_by)
        self.execution_history.append(result)
        return result

    def _action_refund(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        amount = payload.get("amount", 0.0)
        order_id = payload.get("order_id", "UNKNOWN")
        customer_id = payload.get("customer_id", "UNKNOWN")
        return {
            "status": "SUCCESS",
            "action": "issue_refund",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": {
                "customer_id": customer_id,
                "order_id": order_id,
                "refunded_amount": amount,
                "currency": "USD",
                "refund_method": "ORIGINAL_PAYMENT_METHOD",
                "message": f"Successfully disbursed refund of ${amount:.2f} for order {order_id}."
            }
        }

    def _action_cancel_subscription(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "cancel_subscription",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": {
                "subscription_id": payload.get("subscription_id", "SUB-DEFAULT"),
                "cancellation_effective": "IMMEDIATE",
                "prorated_credit": payload.get("prorated_credit", 0.0),
                "message": "Subscription cancelled and recurring billing stopped."
            }
        }

    def _action_security_freeze(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id", "UNKNOWN")
        return {
            "status": "SUCCESS",
            "action": "escalate_security_and_freeze_sessions",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SECURITY_SUPERVISOR",
            "details": {
                "customer_id": customer_id,
                "sessions_revoked": 4,
                "account_lock_status": "TEMPORARY_FREEZE",
                "dispatch_alert": f"Password reset and identity verification link sent to verified primary address for {customer_id}."
            }
        }

    def _action_file_bug(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        bug_id = f"BUG-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "SUCCESS",
            "action": "file_engineering_bug_and_workaround",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": {
                "bug_ticket_id": bug_id,
                "severity": payload.get("severity", "P2"),
                "component": payload.get("component", "Mobile Checkout"),
                "jira_url": f"https://jira.internal.novatech.io/browse/{bug_id}",
                "message": f"Incident logged under {bug_id}. Workaround instructions prepared."
            }
        }

    def _action_courier_trace(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        tracer_id = f"TRC-FX-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "SUCCESS",
            "action": "expedited_courier_trace_and_credit",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "LOGISTICS_SUPERVISOR",
            "details": {
                "carrier_tracer_id": tracer_id,
                "tracking_number": payload.get("tracking_number", "UNKNOWN"),
                "courtesy_credit_applied": payload.get("credit_amount", 15.0),
                "message": f"Opened urgent tracer {tracer_id} with carrier dispatch. Courtesy credit applied."
            }
        }

    def _action_retention_escalation(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        escalation_id = f"ESC-LEGAL-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "SUCCESS",
            "action": "escalate_to_senior_retention_and_legal",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_ESCALATION",
            "details": {
                "escalation_ticket_id": escalation_id,
                "risk_tier": "HIGH_LEGAL_RISK",
                "assigned_team": "Senior Retention & Risk Management",
                "sla_target_minutes": 30,
                "message": f"Ticket escalated to Senior Retention Team under {escalation_id}."
            }
        }

    def _action_prorated_cancellation(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "prorated_cancellation_approval",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "BILLING_MANAGER",
            "details": {
                "refund_amount": payload.get("amount", 184.0),
                "administrative_fee": 15.0,
                "message": "Prorated refund approved minus standard administrative fee."
            }
        }

    def _action_carrier_intercept(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "carrier_intercept_dispatch_review",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "DISPATCH_SUPERVISOR",
            "details": {
                "intercept_reference": f"INT-{uuid.uuid4().hex[:6].upper()}",
                "carrier_intercept_fee": 17.50,
                "message": "Carrier intercept dispatch submitted with fee waiver authorization."
            }
        }

    def _action_guidance(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "provide_product_guidance",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": "SYSTEM_AUTONOMOUS",
            "details": {
                "message": "Product documentation and architectural guidance dispatched to customer."
            }
        }

    def _action_fraud_hold(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "freeze_fraudulent_claim_and_security_hold",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "FRAUD_INVESTIGATION_LEAD",
            "details": {
                "fraud_flag": "CONFIRMED_HIGH_RISK",
                "payment_hold": "ACTIVE",
                "message": "Account placed on security hold. Claim denied pending identity verification."
            }
        }

    def _action_billing_credit(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        credit = payload.get("credit_amount", 10.0)
        return {
            "status": "SUCCESS",
            "action": "apply_billing_credit",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": {
                "credit_amount": credit,
                "message": f"Applied courtesy credit of ${credit:.2f}."
            }
        }

    def _action_return_label(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        rma_id = f"RMA-{uuid.uuid4().hex[:6].upper()}"
        return {
            "status": "SUCCESS",
            "action": "generate_return_label",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": {
                "rma_number": rma_id,
                "label_url": f"https://shipping.internal.novatech.io/rma/{rma_id}.pdf",
                "message": f"Prepaid return shipping label generated under {rma_id}."
            }
        }

    def _action_default(self, payload: Dict[str, Any], tx_id: str, timestamp: str, authorized_by: Optional[str]) -> Dict[str, Any]:
        return {
            "status": "SUCCESS",
            "action": "general_notification",
            "transaction_id": tx_id,
            "timestamp": timestamp,
            "authorized_by": authorized_by or "SYSTEM_AUTONOMOUS",
            "details": payload
        }


# Global singleton instance
action_engine_tool = ActionExecutionEngine()


"""Escalation & Safety Agent: Consequential Action Risk Assessment & Human Gate Evaluation."""

import time
from typing import Dict, Any, List
from src.agents.base_agent import BaseAgent
from src.config import (
    MAX_AUTONOMOUS_REFUND_AMOUNT,
    CRITICAL_FRAUD_RISK_THRESHOLD,
    VIP_LTV_THRESHOLD
)
from src.state import SupportTicketState
from src.tools.audit_logger import audit_logger_tool


class EscalationAgent(BaseAgent):
    """Specialized agent acting as the safety gatekeeper to determine human approval requirements."""

    def __init__(self):
        super().__init__(
            name="EscalationAgent",
            role_description="Assesses operational and financial risk, verifies compliance boundaries, and flags consequential actions for Human-in-the-Loop oversight."
        )

    def process(self, state: SupportTicketState) -> Dict[str, Any]:
        """Evaluate safety policies and determine if human supervisor sign-off is mandatory."""
        start_time = time.time()
        
        proposed_action = state.get("proposed_action", "")
        payload = state.get("action_payload", {})
        customer_profile = state.get("customer_profile") or {}
        category = state.get("category", "")
        urgency = state.get("urgency", "")
        sentiment = state.get("sentiment", "")
        description = state.get("description", "").lower()
        extracted_entities = state.get("extracted_entities", {})

        safety_violations: List[str] = []
        requires_human_approval = False
        reasons: List[str] = []
        risk_score = 0.05  # Base operational risk

        # Rule 1: High Financial Value (Refund > $50.00 Limit)
        refund_amount = payload.get("amount") or extracted_entities.get("refund_amount", 0.0)
        if refund_amount and refund_amount > MAX_AUTONOMOUS_REFUND_AMOUNT:
            requires_human_approval = True
            safety_violations.append(f"FINANCIAL_LIMIT_EXCEEDED: Refund ${refund_amount:.2f} > ${MAX_AUTONOMOUS_REFUND_AMOUNT:.2f}")
            reasons.append(f"Refund request of ${refund_amount:.2f} exceeds autonomous limit of ${MAX_AUTONOMOUS_REFUND_AMOUNT:.2f} (POL-REF-001)")
            risk_score = max(risk_score, min(0.40 + (refund_amount / 500.0) * 0.40, 0.85))

        # Rule 2: Account Security / 2FA Reset Prohibition
        if proposed_action == "escalate_security_and_freeze_sessions" or "2fa" in description:
            requires_human_approval = True
            safety_violations.append("SECURITY_SENSITIVE_ACTION: Autonomous 2FA reset prohibited by POL-SEC-002")
            reasons.append("Two-Factor Authentication (2FA) credential changes require mandatory Human Security Supervisor verification (POL-SEC-002)")
            risk_score = max(risk_score, 0.90)

        # Rule 3: Elevated Fraud Risk Score
        fraud_score = customer_profile.get("fraud_risk_score", 0.0)
        if fraud_score >= CRITICAL_FRAUD_RISK_THRESHOLD or customer_profile.get("account_status") in ["FLAGGED_SECURITY", "SUSPICIOUS"]:
            requires_human_approval = True
            safety_violations.append(f"HIGH_FRAUD_RISK: Account risk score {fraud_score:.2f} >= threshold {CRITICAL_FRAUD_RISK_THRESHOLD:.2f}")
            reasons.append(f"Account risk assessment score ({fraud_score:.2f}) indicates elevated fraud probability")
            risk_score = max(risk_score, 0.95)

        # Rule 4: Legal & Regulatory / Chargeback Threat
        if sentiment == "Hostile/Angry" or any(w in description for w in ["chargeback", "cfpb", "ftc", "lawyer", "scam"]):
            requires_human_approval = True
            safety_violations.append("LEGAL_REGULATORY_THREAT: Customer threatened chargeback or regulatory action")
            reasons.append("Ticket involves formal chargeback or regulatory escalation risk (POL-BIL-005)")
            risk_score = max(risk_score, 0.85)

        # Rule 5: In-Transit Physical Intercept
        if proposed_action == "carrier_intercept_dispatch_review":
            requires_human_approval = True
            safety_violations.append("PHYSICAL_LOGISTICS_INTERCEPT: Package in transit requires carrier dispatch fee approval")
            reasons.append("In-transit address rerouting incurs third-party courier fee and requires Dispatcher authorization (POL-LOG-003)")
            risk_score = max(risk_score, 0.65)

        # Rule 6: Prorated Cancellation Sign-Off
        if proposed_action == "prorated_cancellation_approval":
            requires_human_approval = True
            safety_violations.append("PRORATED_REFUND_OVERRIDE: Non-standard cancellation outside 48hr window")
            reasons.append("Prorated cancellation fee waiver and high-value refund require Billing Manager authorization")
            risk_score = max(risk_score, 0.70)

        # Rule 7: High-Value VIP Logistics Compensation
        if proposed_action == "expedited_courier_trace_and_credit" and customer_profile.get("tier") == "VIP_PLATINUM":
            requires_human_approval = True
            safety_violations.append("VIP_HIGH_VALUE_ORDER_DELAY: Executive equipment delayed")
            reasons.append("VIP Platinum customer order exceeding $500 requires Managerial tracer oversight")
            risk_score = max(risk_score, 0.60)

        # Determine consolidated approval reason
        approval_reason = "; ".join(reasons) if reasons else "No safety violations detected. Autonomous resolution approved."

        duration_ms = (time.time() - start_time) * 1000

        audit_trail = state.get("audit_trail", [])
        audit_logger_tool.log_event(
            audit_trail=audit_trail,
            step="EVALUATE_ESCALATION",
            agent=self.name,
            action="evaluate_safety_boundaries",
            details={
                "requires_human_approval": requires_human_approval,
                "risk_score": round(risk_score, 2),
                "violations_count": len(safety_violations),
                "approval_reason": approval_reason
            },
            duration_ms=duration_ms
        )

        # Preserve existing human decision if explicitly set in state
        existing_decision = state.get("human_decision")
        if existing_decision in ["APPROVED", "REJECTED", "MODIFIED"]:
            decision_status = existing_decision
        else:
            decision_status = "PENDING" if requires_human_approval else "NOT_REQUIRED"

        return {
            "requires_human_approval": requires_human_approval,
            "approval_reason": approval_reason,
            "risk_score": round(risk_score, 2),
            "safety_violations": safety_violations,
            "human_decision": decision_status,
            "current_step": "ESCALATION_EVALUATED",
            "audit_trail": audit_trail
        }


# Global singleton instance
escalation_agent = EscalationAgent()

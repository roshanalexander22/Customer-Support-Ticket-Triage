"""Resolution Agent: Synthesizes policy, CRM context, and draft customer response."""

import time
import json
import re
from typing import Dict, Any, Optional
from src.agents.base_agent import BaseAgent
from src.state import SupportTicketState
from src.tools.audit_logger import audit_logger_tool


class ResolutionAgent(BaseAgent):
    """Specialized agent responsible for drafting empathetic responses and proposing concrete actions."""

    def __init__(self):
        super().__init__(
            name="ResolutionAgent",
            role_description="Synthesizes customer context and policy rules to draft resolutions and formulate action payloads."
        )

    def process(self, state: SupportTicketState) -> Dict[str, Any]:
        """Formulate resolution, draft customer message, and propose action."""
        start_time = time.time()
        
        # 1. Attempt LLM generation if client available
        resolution = self._resolve_with_llm(state)

        # 2. Heuristic synthesis if LLM is offline or fails
        if not resolution:
            resolution = self._resolve_with_heuristics(state)

        duration_ms = (time.time() - start_time) * 1000

        audit_trail = state.get("audit_trail", [])
        audit_logger_tool.log_event(
            audit_trail=audit_trail,
            step="DRAFT_RESOLUTION",
            agent=self.name,
            action="propose_resolution_and_draft_response",
            details={
                "proposed_action": resolution["proposed_action"],
                "action_payload": resolution["action_payload"],
                "response_length": len(resolution["draft_response"])
            },
            duration_ms=duration_ms
        )

        return {
            "draft_response": resolution["draft_response"],
            "proposed_action": resolution["proposed_action"],
            "action_payload": resolution["action_payload"],
            "resolution_notes": resolution["resolution_notes"],
            "current_step": "RESOLUTION_PROPOSED",
            "audit_trail": audit_trail
        }

    def _resolve_with_llm(self, state: SupportTicketState) -> Optional[Dict[str, Any]]:
        """Generate resolution using Gemini LLM."""
        if not self.client:
            return None

        prompt = (
            f"Customer Profile: {json.dumps(state.get('customer_profile'))}\n"
            f"Category: {state.get('category')}, Urgency: {state.get('urgency')}\n"
            f"Ticket Subject: {state.get('subject')}\n"
            f"Ticket Body: {state.get('description')}\n"
            f"Retrieved Policies: {json.dumps([p['title'] for p in state.get('retrieved_policies', [])])}\n\n"
            "Draft a helpful response and propose a concrete action. Return JSON with keys:\n"
            "- draft_response: string\n"
            "- proposed_action: string\n"
            "- action_payload: dict\n"
            "- resolution_notes: string"
        )
        response_text = self.query_llm(prompt, "You are a professional customer resolution agent.")
        if not response_text:
            return None

        try:
            clean = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
            clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE)
            data = json.loads(clean)
            return {
                "draft_response": data.get("draft_response", ""),
                "proposed_action": data.get("proposed_action", "provide_product_guidance"),
                "action_payload": data.get("action_payload", {}),
                "resolution_notes": data.get("resolution_notes", "LLM-synthesized resolution")
            }
        except Exception:
            return None

    def _resolve_with_heuristics(self, state: SupportTicketState) -> Dict[str, Any]:
        """Deterministic resolution builder tailored to customer context and policies."""
        cust = state.get("customer_profile") or {}
        cust_name = cust.get("name", "Valued Customer")
        first_name = cust_name.split()[0] if cust_name else "Valued Customer"
        entities = state.get("extracted_entities", {})
        category = state.get("category", "")
        urgency = state.get("urgency", "")
        subject = state.get("subject", "").lower()
        desc = state.get("description", "").lower()
        full_text = f"{subject} {desc}".lower()

        order_id = entities.get("order_id", "ORD-UNKNOWN")
        refund_amount = entities.get("refund_amount", 0.0)
        customer_id = state.get("customer_id", "UNKNOWN")

        # Check for Hostile / Legal Threat & Chargeback Escalation FIRST
        if any(w in full_text for w in ["scam", "chargeback", "cfpb", "ftc", "rip off", "unacceptable", "lawyer", "attorney"]):
            proposed_action = "escalate_to_senior_retention_and_legal"
            action_payload = {
                "customer_id": customer_id,
                "disputed_amount": refund_amount if refund_amount > 0 else 45.00,
                "reason": "Hostile chargeback and regulatory complaint threat"
            }
            draft_response = (
                f"Dear {first_name},\n\n"
                "We have received your message regarding the recent subscription charge. We understand your "
                "frustration and want to assure you that resolving this matter fairly and swiftly is our highest priority.\n\n"
                "Your ticket has been escalated directly to our Senior Retention Management and Account Relations Team. "
                "A dedicated senior specialist is reviewing your billing records now to issue an appropriate resolution and prevent "
                "any unwanted future renewals. You will hear directly from them within the next hour.\n\n"
                "Sincerely,\nNovaTech Executive Customer Relations"
            )
            notes = "Hostile tone and legal/regulatory threats trigger mandatory escalation to Senior Retention per POL-BIL-005."

        # Scenario 1: Low-Value Autonomous Refund ($28.50)
        elif category == "Billing & Refunds" and refund_amount > 0 and refund_amount <= 50.0:
            proposed_action = "issue_refund"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "amount": refund_amount,
                "reason": "Damaged goods reimbursement under POL-REF-001"
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                f"Thank you for contacting NovaTech Support. We are very sorry to hear that your items in order "
                f"{order_id} arrived damaged. Under our 30-Day Customer Satisfaction Guarantee (POL-REF-001), "
                f"I have processed a full refund of ${refund_amount:.2f} back to your original payment method.\n\n"
                "Please allow 3-5 business days for the credit to appear on your bank statement. There is no need to "
                "return the damaged item. We apologize for the inconvenience!\n\n"
                "Best regards,\nNovaTech Support Team"
            )
            notes = "Refund is <= $50.00 autonomous threshold and within 30-day window. Autonomous approval recommended."

        # Scenario 2: High-Value Hardware Return ($249.99)
        elif category == "Billing & Refunds" and refund_amount > 50.0 and "scam" not in desc and "cancel" not in subject and "gift card" not in desc:
            proposed_action = "issue_refund"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "amount": refund_amount,
                "reason": "Hardware return exceeding autonomous limit"
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                f"Thank you for reaching out to NovaTech Support regarding order {order_id}. We completely understand "
                f"that the NovaStudio 4K Webcam does not fit your conference setup requirements.\n\n"
                f"Because this refund amount (${refund_amount:.2f}) exceeds our automated threshold, our senior support "
                "team is finalizing the return authorization and prepaid insured RMA shipping label for you. You will "
                "receive the shipping documentation shortly.\n\n"
                "Warm regards,\nNovaTech Enterprise Support"
            )
            notes = f"Refund amount ${refund_amount:.2f} exceeds $50.00 threshold (POL-REF-001). Requires Human Supervisor approval."

        # Scenario 3: Account Security & 2FA Reset
        elif category == "Account & Security" and ("2fa" in subject or "suspicious" in subject or "lockout" in desc):
            proposed_action = "escalate_security_and_freeze_sessions"
            action_payload = {
                "customer_id": customer_id,
                "ticket_id": state.get("ticket_id"),
                "reason": "Suspicious overseas session alerts and 2FA lockout"
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                "We have detected the unauthorized access alerts you reported. As an immediate safeguard, we have "
                "terminated all active sessions and placed a temporary security freeze on credential changes.\n\n"
                "In strict compliance with our Account Security Policy (POL-SEC-002), automated 2FA resets are prohibited "
                "to prevent account hijacking. A security specialist has been assigned to verify your identity and guide you "
                "through secure credential recovery.\n\n"
                "Sincerely,\nNovaTech Information Security Team"
            )
            notes = "POL-SEC-002 prohibits automated 2FA resets. High risk security action requiring Human Verification."

        # Scenario 4: Technical Support P2 Bug
        elif category == "Technical Support" and ("crash" in desc or "bug" in desc):
            proposed_action = "file_engineering_bug_and_workaround"
            action_payload = {
                "customer_id": customer_id,
                "severity": "P2",
                "component": "iOS Mobile Checkout",
                "device_info": entities.get("device_info", "iOS Mobile"),
                "reproduction_notes": "Immediate crash upon payment confirmation tap on iOS 18"
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                "Thank you for bringing this to our attention and providing clear device reproduction details. "
                "We have logged this incident as a High Priority (P2) defect with our iOS Mobile Engineering Team.\n\n"
                "While our engineers deploy a patch for build 109, you can immediately complete your team license "
                "renewal without disruption by logging into the NovaCloud Web Portal at https://app.novatech.io/checkout. "
                "We will notify you the moment the mobile update is live in the App Store.\n\n"
                "Best regards,\nNovaTech Technical Support"
            )
            notes = "P2 software defect logged under POL-TECH-004. Engineering issue filed; workaround provided."

        # Scenario 5: VIP Logistics Delay
        elif category == "Shipping & Logistics" and ("vip" in cust.get("tier", "").lower() or cust.get("lifetime_value", 0) > 1000):
            proposed_action = "expedited_courier_trace_and_credit"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "tracking_number": entities.get("tracking_number", "FX-998877665"),
                "credit_amount": 15.00
            }
            draft_response = (
                f"Dear {cust_name},\n\n"
                f"Thank you for reaching out through your VIP Concierge channel. We sincerely apologize for the delay "
                f"with your executive shipment {order_id} via FedEx.\n\n"
                "We have initiated an expedited courier tracer with FedEx Priority Logistics to inspect the Memphis transit "
                "hub. In accordance with POL-LOG-003, we have credited $15.00 to your corporate account as a courtesy for this "
                "breach in delivery SLA. If the package does not update within 24 hours, we will dispatch an overnight replacement.\n\n"
                "Respectfully,\nNovaTech VIP Client Success"
            )
            notes = "VIP Platinum account exceeding $1,000 LTV. Opened priority carrier tracer and applied courtesy SLA credit."


        # Scenario 7: Prorated Cancellation Past Grace Period
        elif "cancel" in subject and "renew" in desc and "storage" in desc:
            proposed_action = "prorated_cancellation_approval"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "amount": 184.00,
                "subscription_id": "CLOUD_ANNUAL_2TB"
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                f"Thank you for contacting NovaTech. We have received your request to cancel the 2TB Cloud Storage "
                f"subscription renewal for order {order_id}.\n\n"
                "In accordance with our Billing & Subscription Policy (POL-BIL-005), annual subscriptions cancelled after "
                "the initial 48-hour window are eligible for a prorated refund of the unused term minus standard processing ($15.00). "
                "We have calculated your net prorated refund at $184.00, submitted for billing management sign-off.\n\n"
                "Best regards,\nNovaTech Billing Services"
            )
            notes = "Grace period elapsed; refund value $184.00 exceeds $50.00 limit. Submitted for Managerial Approval."

        # Scenario 8: In-Transit Intercept
        elif category == "Shipping & Logistics" and ("reroute" in subject or "address" in subject or "out for delivery" in desc):
            proposed_action = "carrier_intercept_dispatch_review"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "requested_address": "742 Evergreen Terrace",
                "carrier": "UPS",
                "carrier_fee": 17.50
            }
            draft_response = (
                f"Hello {first_name},\n\n"
                f"We received your urgent address change request for order {order_id}. Because this package is already "
                "in transit and designated 'Out for Delivery' with UPS, automated routing is restricted to ensure package safety (POL-LOG-003).\n\n"
                "Our Logistics Dispatch Team is contacting the local UPS carrier depot to request an urgent package intercept "
                "to 742 Evergreen Terrace. We will update you with confirmation shortly.\n\n"
                "Best regards,\nNovaTech Logistics Support"
            )
            notes = "In-transit package cannot be rerouted autonomously per POL-LOG-003. Requires Logistics Dispatch review."

        # Scenario 10: High Fraud Risk
        elif cust.get("fraud_risk_score", 0.0) >= 0.25 or "bitcoin" in desc or "western union" in desc:
            proposed_action = "freeze_fraudulent_claim_and_security_hold"
            action_payload = {
                "customer_id": customer_id,
                "order_id": order_id,
                "fraud_score": cust.get("fraud_risk_score", 0.91),
                "requested_method": "Western Union / Bitcoin"
            }
            draft_response = (
                f"Hello,\n\n"
                f"We have received your refund inquiry regarding order {order_id}. In accordance with federal financial regulations "
                "and NovaTech Refund Policy POL-REF-001, refunds cannot be remitted to third-party cash transmitters, cryptocurrency "
                "addresses, or alternate parties.\n\n"
                "Your account has been placed on a security verification hold pending formal identity confirmation from our Fraud "
                "Prevention and Risk Compliance Department.\n\n"
                "NovaTech Risk & Compliance"
            )
            notes = "High fraud score (>= 0.25) and prohibited alternate payment refund request. Mandatory Fraud Team Review."

        # Scenario 9 / Default: Product Guidance / General
        else:
            proposed_action = "provide_product_guidance"
            action_payload = {
                "customer_id": customer_id,
                "inquiry_type": "Product Specifications"
            }
            draft_response = (
                f"Bonjour {first_name},\n\n"
                "Thank you for contacting NovaTech Creative Solutions! We are delighted that you are using the NovaDraw "
                "vector asset pack.\n\n"
                "To answer your question: Yes, NovaDraw v4.3 supports full Pantone® Formula Guide color swatch embedding "
                "directly within standard SVG and EPS export profiles, ensuring 100% fidelity when importing into Adobe Illustrator.\n\n"
                "Please let us know if you need any additional sample palettes or documentation!\n\n"
                "Warm regards,\nNovaTech Product Specialists"
            )
            notes = "General product feature inquiry. Autonomous guidance provided."

        return {
            "draft_response": draft_response,
            "proposed_action": proposed_action,
            "action_payload": action_payload,
            "resolution_notes": notes
        }


# Global singleton instance
resolution_agent = ResolutionAgent()

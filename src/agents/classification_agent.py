"""Ticket Classification Agent: Intent, Category, Urgency, and Sentiment Extraction."""

import re
import json
import time
from typing import Dict, Any, Optional
from src.agents.base_agent import BaseAgent
from src.state import SupportTicketState, ExtractedEntities
from src.tools.audit_logger import audit_logger_tool


class TicketClassificationAgent(BaseAgent):
    """Specialized agent responsible for taxonomic classification and entity extraction."""

    def __init__(self):
        super().__init__(
            name="TicketClassificationAgent",
            role_description="Analyzes raw customer text to extract intent, category, urgency, sentiment, and key entities."
        )

    def process(self, state: SupportTicketState) -> Dict[str, Any]:
        """Classify the incoming support ticket."""
        start_time = time.time()
        subject = state.get("subject", "")
        description = state.get("description", "")
        text = f"{subject}\n{description}"

        # 1. Attempt LLM-based classification if available
        llm_result = self._classify_with_llm(text, state.get("channel", "WEB"))
        
        # 2. Use heuristic rule engine if LLM is unavailable or unparsed
        if not llm_result:
            llm_result = self._classify_with_heuristics(subject, description, state.get("channel", "WEB"))

        duration_ms = (time.time() - start_time) * 1000

        # Log audit entry
        audit_trail = state.get("audit_trail", [])
        audit_logger_tool.log_event(
            audit_trail=audit_trail,
            step="CLASSIFY_TICKET",
            agent=self.name,
            action="classify_ticket_content",
            details={
                "category": llm_result["category"],
                "urgency": llm_result["urgency"],
                "sentiment": llm_result["sentiment"],
                "entities": llm_result["extracted_entities"],
                "confidence": llm_result["classification_confidence"]
            },
            duration_ms=duration_ms
        )

        return {
            "category": llm_result["category"],
            "urgency": llm_result["urgency"],
            "sentiment": llm_result["sentiment"],
            "intent": llm_result["intent"],
            "extracted_entities": llm_result["extracted_entities"],
            "classification_confidence": llm_result["classification_confidence"],
            "current_step": "CLASSIFIED",
            "audit_trail": audit_trail
        }

    def _classify_with_llm(self, text: str, channel: str) -> Optional[Dict[str, Any]]:
        """Query Gemini for structured classification."""
        if not self.client:
            return None

        system_instruction = (
            "You are an expert customer service classification agent. Return ONLY a valid JSON object with keys: "
            "category ('Billing & Refunds', 'Technical Support', 'Account & Security', 'Shipping & Logistics', 'Product Inquiry', 'General / Feedback'), "
            "urgency ('Low', 'Medium', 'High', 'Critical'), "
            "sentiment ('Positive', 'Neutral', 'Frustrated', 'Urgent/Distressed', 'Hostile/Angry', 'Suspicious'), "
            "intent (string), "
            "extracted_entities (dict with order_id, refund_amount, tracking_number, device_info), "
            "confidence (float between 0.8 and 1.0)."
        )
        prompt = f"Support Ticket Text:\n{text}\nChannel: {channel}\n\nReturn JSON:"
        
        response_text = self.query_llm(prompt, system_instruction)
        if not response_text:
            return None

        try:
            clean_text = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
            clean_text = re.sub(r"```$", "", clean_text.strip(), flags=re.MULTILINE)
            data = json.loads(clean_text)
            return {
                "category": data.get("category", "General / Feedback"),
                "urgency": data.get("urgency", "Medium"),
                "sentiment": data.get("sentiment", "Neutral"),
                "intent": data.get("intent", "Customer assistance request"),
                "extracted_entities": data.get("extracted_entities", {}),
                "classification_confidence": float(data.get("confidence", 0.90))
            }
        except Exception:
            return None

    def _classify_with_heuristics(self, subject: str, description: str, channel: str) -> Dict[str, Any]:
        """Deterministic rule engine for reliable classification and entity parsing."""
        full_text = f"{subject} {description}".lower()

        # Entity Extraction via Regex
        order_match = re.search(r"\b(ORD-\d{4})\b", full_text, re.IGNORECASE)
        amount_match = re.search(r"\$(\d+(?:\.\d{2})?)", full_text)
        tracking_match = re.search(r"\b(FX-\d+|1Z[0-9A-Z]{16}|UPS-\d+|DHL-\d+)\b", full_text, re.IGNORECASE)

        extracted_entities: ExtractedEntities = {}
        if order_match:
            extracted_entities["order_id"] = order_match.group(1).upper()
        if amount_match:
            try:
                extracted_entities["refund_amount"] = float(amount_match.group(1))
            except ValueError:
                pass
        if tracking_match:
            extracted_entities["tracking_number"] = tracking_match.group(1).upper()

        # Check for device / platform info
        if "ios" in full_text or "iphone" in full_text:
            extracted_entities["device_info"] = "Apple iOS Mobile"
        elif "android" in full_text:
            extracted_entities["device_info"] = "Android Mobile"

        # Classification Taxonomy Rules
        # 1. Account & Security
        if any(w in full_text for w in ["2fa", "suspicious login", "compromised", "authenticator", "totp", "hack", "bitcoin", "western union", "tempmail"]):
            category = "Account & Security"
            sentiment = "Suspicious" if ("western union" in full_text or "bitcoin" in full_text) else "Urgent/Distressed"
            urgency = "Critical"
            intent = "Account security incident or unauthorized access report"

        # 2. Hostile / Legal Billing Threats
        elif any(w in full_text for w in ["scam", "cfpb", "ftc", "chargeback", "lawyer", "rip off", "unacceptable"]):
            category = "Billing & Refunds"
            urgency = "Critical"
            sentiment = "Hostile/Angry"
            intent = "Disputed unauthorized charge and immediate escalation threat"

        # 3. Technical Support
        elif any(w in full_text for w in ["crash", "bug", "error", "exception", "failed to submit", "cannot complete", "glitch"]):
            category = "Technical Support"
            urgency = "High" if "crash" in full_text else "Medium"
            sentiment = "Frustrated"
            intent = "Software defect report and troubleshooting request"

        # 4. Shipping & Logistics
        elif any(w in full_text for w in ["delivery", "courier", "fedex", "ups", "tracking", "stalled", "reroute", "out for delivery", "address"]):
            category = "Shipping & Logistics"
            urgency = "High" if ("out for delivery" in full_text or "delayed" in full_text or "vip" in full_text) else "Medium"
            sentiment = "Urgent" if "out for delivery" in full_text else "Dissatisfied"
            intent = "Shipment tracking inquiry or in-transit delivery adjustment"

        # 5. Billing & Refunds
        elif any(w in full_text for w in ["refund", "return", "charge", "charged", "renew", "renewal", "subscription", "cancel"]):
            category = "Billing & Refunds"
            urgency = "Medium"
            sentiment = "Neutral"
            intent = "Refund or subscription cancellation request"

        # 6. Product Inquiry
        elif any(w in full_text for w in ["inquiry", "pantone", "illustrator", "compatibility", "svg", "feature", "question"]):
            category = "Product Inquiry"
            urgency = "Low"
            sentiment = "Positive"
            intent = "Product compatibility and feature roadmap inquiry"

        else:
            category = "General / Feedback"
            urgency = "Low"
            sentiment = "Neutral"
            intent = "General customer inquiry"

        return {
            "category": category,
            "urgency": urgency,
            "sentiment": sentiment,
            "intent": intent,
            "extracted_entities": extracted_entities,
            "classification_confidence": 0.95
        }


# Global singleton instance
classification_agent = TicketClassificationAgent()

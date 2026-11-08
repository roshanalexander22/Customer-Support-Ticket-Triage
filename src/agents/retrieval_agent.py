"""Knowledge Retrieval Agent: Multi-Source Policy and CRM Context Retrieval."""

import time
from typing import Dict, Any, List
from src.agents.base_agent import BaseAgent
from src.state import SupportTicketState, RetrievedPolicyChunk
from src.tools.crm_tool import crm_lookup_tool
from src.tools.policy_retriever import policy_retriever_tool
from src.tools.audit_logger import audit_logger_tool


class KnowledgeRetrievalAgent(BaseAgent):
    """Specialized agent responsible for retrieving authoritative policy guidance and CRM data."""

    def __init__(self):
        super().__init__(
            name="KnowledgeRetrievalAgent",
            role_description="Formulates targeted search queries, pulls relevant policy sections, and retrieves customer CRM account history."
        )

    def process(self, state: SupportTicketState) -> Dict[str, Any]:
        """Execute CRM lookup and vector policy retrieval."""
        start_time = time.time()
        customer_id = state.get("customer_id")
        customer_email = state.get("customer_email")
        category = state.get("category", "")
        subject = state.get("subject", "")
        description = state.get("description", "")
        extracted_entities = state.get("extracted_entities", {})

        audit_trail = state.get("audit_trail", [])

        # 1. CRM Customer Context Retrieval Tool Call
        crm_start = time.time()
        customer_profile = crm_lookup_tool.lookup_customer(customer_id=customer_id, email=customer_email)
        crm_duration_ms = (time.time() - crm_start) * 1000

        audit_logger_tool.log_event(
            audit_trail=audit_trail,
            step="CRM_LOOKUP_TOOL",
            agent=self.name,
            action="query_customer_profile",
            details={
                "customer_id": customer_id,
                "found": customer_profile is not None,
                "tier": customer_profile.get("tier") if customer_profile else "UNKNOWN",
                "fraud_risk_score": customer_profile.get("fraud_risk_score") if customer_profile else None
            },
            duration_ms=crm_duration_ms
        )

        # 2. Formulate Search Query for Policy Retrieval
        full_text = f"{subject} {description}".lower()
        query_components = [category, subject]

        if any(w in full_text for w in ["chargeback", "cfpb", "ftc", "scam", "renewal", "dispute", "subscription"]):
            query_components.append("billing subscription renewal chargeback dispute hostile escalation")
        elif category in ["Product Inquiry", "Technical Support"] or any(w in full_text for w in ["crash", "bug", "compatibility", "pantone", "illustrator", "feature"]):
            query_components.append("technical support specifications software compatibility SLA troubleshooting")
        elif any(w in full_text for w in ["2fa", "suspicious", "lockout", "authenticator", "totp", "compromise"]):
            query_components.append("security lockout two factor authentication session freeze")
        elif any(w in full_text for w in ["delivery", "courier", "fedex", "ups", "tracking", "reroute", "transit", "lost"]):
            query_components.append("shipping logistics courier carrier transit delay intercept")
        elif "refund" in full_text or "return" in full_text:
            query_components.append("refund return policy autonomous threshold 30 day window")

        retrieval_query = " ".join(query_components)

        # 3. Policy Retrieval Tool Call
        policy_start = time.time()
        retrieved_policies: List[RetrievedPolicyChunk] = policy_retriever_tool.retrieve(
            query=retrieval_query,
            top_k=3
        )
        policy_duration_ms = (time.time() - policy_start) * 1000

        audit_logger_tool.log_event(
            audit_trail=audit_trail,
            step="POLICY_RETRIEVER_TOOL",
            agent=self.name,
            action="search_policy_knowledge_base",
            details={
                "query": retrieval_query,
                "chunks_retrieved": len(retrieved_policies),
                "top_policies": [p["policy_id"] for p in retrieved_policies]
            },
            duration_ms=policy_duration_ms
        )

        duration_ms = (time.time() - start_time) * 1000

        return {
            "customer_profile": customer_profile,
            "retrieved_policies": retrieved_policies,
            "retrieval_query": retrieval_query,
            "current_step": "CONTEXT_RETRIEVED",
            "audit_trail": audit_trail
        }


# Global singleton instance
retrieval_agent = KnowledgeRetrievalAgent()

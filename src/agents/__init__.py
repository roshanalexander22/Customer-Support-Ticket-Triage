"""Agents package for Customer Support Ticket Triage."""

from src.agents.base_agent import BaseAgent
from src.agents.classification_agent import TicketClassificationAgent, classification_agent
from src.agents.retrieval_agent import KnowledgeRetrievalAgent, retrieval_agent
from src.agents.resolution_agent import ResolutionAgent, resolution_agent
from src.agents.escalation_agent import EscalationAgent, escalation_agent

__all__ = [
    "BaseAgent",
    "TicketClassificationAgent",
    "classification_agent",
    "KnowledgeRetrievalAgent",
    "retrieval_agent",
    "ResolutionAgent",
    "resolution_agent",
    "EscalationAgent",
    "escalation_agent"
]

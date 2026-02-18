"""LangGraph agents for multi-agent workflows.

Importing this module triggers agent registration via the @register_agent
decorator in each agent module. The worker loop uses get_agent() from the
registry to resolve job types to agent instances.
"""
from .registry import get_agent, list_agents, register_agent
from .research_query_agent import ResearchQueryAgent
from .citation_validator_agent import CitationValidatorAgent
from .insight_extraction_agent import InsightExtractionAgent
from .linkedin_post_agent import LinkedInPostAgent
from .content_strategy_agent import ContentStrategyAgent

__all__ = [
    "get_agent",
    "list_agents",
    "register_agent",
    "ResearchQueryAgent",
    "CitationValidatorAgent",
    "InsightExtractionAgent",
    "LinkedInPostAgent",
    "ContentStrategyAgent",
]

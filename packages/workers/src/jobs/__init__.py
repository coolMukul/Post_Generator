"""Background job processors.

Job types processed by the worker:
  - hybrid_retrieval: Phase 3 hybrid search (handled directly in worker.py)
  - research_query_agent: Phase 4 Research Query Agent
  - insight_extraction_agent: Phase 4/5 Insight Extraction Agent
  - linkedin_post_agent: Phase 5 LinkedIn Post Generator Agent
  - citation_validator_agent: Phase 4 Citation Validator Agent
  - content_strategy_agent: Phase 5 Content Strategy Orchestrator

All agent jobs are dispatched via the agent registry in worker.py.
"""

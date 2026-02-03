"""Hybrid retrieval job handler."""
import logging
from typing import Dict, Any, List
from ..config import settings, get_database_url
from ..repositories.hybrid_retrieval_repository import HybridRetrievalRepository

logger = logging.getLogger(__name__)


async def process_hybrid_retrieval_job(job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process hybrid retrieval job.

    Args:
        job_id: Job ID
        job_data: Job data containing:
            - query: Search query (required)
            - project_key: Project key (optional, default: 'researchpaper')
            - limit: Max results (optional, default: 20)
            - min_score: Minimum score threshold (optional, default: 0.3)
            - vector_weight: Weight for vector search (optional, default: 0.7)
            - keyword_weight: Weight for keyword search (optional, default: 0.3)
            - rrf_k: RRF parameter (optional, default: 60)

    Returns:
        Job result dictionary with search results
    """
    logger.info(f"[Job {job_id}] 🔍 Starting hybrid retrieval")
    
    query = job_data.get('query')
    if not query:
        logger.error(f"[Job {job_id}] ❌ No query provided")
        raise ValueError("Query is required for hybrid retrieval")
    
    project_key = job_data.get('project_key', 'researchpaper')
    limit = job_data.get('limit', 20)
    min_score = job_data.get('min_score', 0.3)
    vector_weight = job_data.get('vector_weight', 0.7)
    keyword_weight = job_data.get('keyword_weight', 0.3)
    rrf_k = job_data.get('rrf_k', 60)
    
    logger.info(f"[Job {job_id}] 📝 Query: '{query}'")
    logger.info(f"[Job {job_id}] 🎯 Config: project={project_key}, limit={limit}, min_score={min_score}")
    logger.info(f"[Job {job_id}] ⚖️  Weights: vector={vector_weight}, keyword={keyword_weight}, rrf_k={rrf_k}")

    # Initialize repository
    logger.info(f"[Job {job_id}] 🔌 Connecting to database...")
    db_url = get_database_url()
    retrieval_repo = HybridRetrievalRepository(db_url)
    logger.info(f"[Job {job_id}] ✅ Repository initialized")
    
    try:
        # If an embedding is provided, attempt full hybrid retrieval (vector + keyword)
        query_embedding = job_data.get('query_embedding')
        if query_embedding:
            logger.info(f"[Job {job_id}] 🔎 query_embedding present - attempting hybrid retrieval (vector + keyword)")
            try:
                hybrid_results = retrieval_repo.hybrid_retrieval(
                    query=query,
                    query_embedding=query_embedding,
                    project_key=project_key,
                    limit=limit,
                    min_score=min_score,
                    vector_weight=vector_weight,
                    keyword_weight=keyword_weight,
                    rrf_k=rrf_k
                )
                logger.info(f"[Job {job_id}] ✅ Hybrid retrieval returned {len(hybrid_results)} results")
                results = [
                    {
                        'id': r.id,
                        'document_id': r.document_id,
                        'chunk_index': r.chunk_index,
                        'content': r.content,
                        'context_summary': r.context_summary,
                        'score': r.score,
                        'rank_source': r.rank_source,
                        'document_title': r.document_title,
                        'metadata': r.metadata
                    }
                    for r in hybrid_results
                ]
            except Exception as e:
                logger.error(f"[Job {job_id}] ❗ Hybrid retrieval failed, falling back to keyword-only: {e}", exc_info=True)
                logger.info(f"[Job {job_id}] 🔎 Executing keyword search fallback...")
                results = retrieval_repo.keyword_search_fallback(
                    query=query,
                    project_key=project_key,
                    limit=limit,
                    min_score=min_score
                )
        else:
            logger.info(f"[Job {job_id}] 🔎 No query_embedding provided - running keyword-only search")
            results = retrieval_repo.keyword_search_fallback(
                query=query,
                project_key=project_key,
                limit=limit,
                min_score=min_score
            )

        logger.info(f"[Job {job_id}] ✅ Found {len(results)} results")
        
        # Format results for response
        formatted_results = []
        for result in results:
            formatted_results.append({
                'id': result.get('id'),
                'document_id': result.get('document_id'),
                'chunk_index': result.get('chunk_index', 0),
                'content': result.get('content', ''),
                'context_summary': result.get('context_summary'),
                'score': result.get('score', 0.0),
                'rank_source': result.get('rank_source', 'keyword'),
                'document_title': result.get('document_title', ''),
                'metadata': result.get('metadata', {})
            })
        
        response = {
            'results': formatted_results,
            'query': query,
            'project_key': project_key,
            'total': len(formatted_results),
            'config': {
                'vector_weight': vector_weight,
                'keyword_weight': keyword_weight,
                'rrf_k': rrf_k
            }
        }
        
        logger.info(f"[Job {job_id}] 🎉 Retrieval successful - returning {len(formatted_results)} results")
        return response
        
    except Exception as e:
        logger.error(f"[Job {job_id}] ❌ Hybrid retrieval failed: {str(e)}", exc_info=True)
        raise

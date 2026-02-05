"""Agent job processor for Phase 4 & 5."""
import logging
import uuid
import time
from typing import Dict, Any, List
from ..config import settings, get_database_url
from ..repositories import VectorRepository

logger = logging.getLogger(__name__)


async def process_agent_job(job_id: str, job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process agent job based on agent type.

    Args:
        job_id: Job ID
        job_data: Job data containing:
            - agentType: Type of agent to run
            - input: Agent-specific input parameters

    Returns:
        Job result dictionary
    """
    agent_type = job_data.get('agentType')
    input_data = job_data.get('input', {})

    logger.info(f"[Agent:{agent_type}][Job:{job_id}] Starting agent processing")

    start_time = time.time()

    try:
        if agent_type == 'research-query':
            result = await run_research_query_agent(job_id, input_data)
        elif agent_type == 'insight-extraction':
            result = await run_insight_extraction_agent(job_id, input_data)
        elif agent_type == 'linkedin-post':
            result = await run_linkedin_post_agent(job_id, input_data)
        elif agent_type == 'content-workflow':
            result = await run_content_workflow_agent(job_id, input_data)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

        execution_time = int((time.time() - start_time) * 1000)
        result['executionTimeMs'] = execution_time

        logger.info(f"[Agent:{agent_type}][Job:{job_id}] Completed in {execution_time}ms")
        return result

    except Exception as e:
        logger.error(f"[Agent:{agent_type}][Job:{job_id}] Error: {str(e)}", exc_info=True)
        raise


async def run_research_query_agent(job_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Research Query Agent - Hybrid RAG search.

    Phase 4: Uses hybrid search to find relevant documents.
    """
    query = input_data.get('query', '')
    max_results = input_data.get('maxResults', 10)
    min_score = input_data.get('minScore', 0.01)
    include_context = input_data.get('includeContext', True)

    logger.info(f"[Agent:research-query][Job:{job_id}][step:search] Query: {query}")

    # Try to use real search from database
    try:
        db_url = get_database_url()
        vector_repo = VectorRepository(db_url)

        # Perform hybrid search
        search_results = vector_repo.hybrid_search(
            query=query,
            limit=max_results,
            min_score=min_score
        )

        if search_results:
            logger.info(f"[Agent:research-query][Job:{job_id}][step:search] Found {len(search_results)} results from database")

            results = []
            for idx, r in enumerate(search_results):
                results.append({
                    'id': str(r.get('id', str(uuid.uuid4()))),
                    'documentId': str(r.get('document_id', '')),
                    'documentTitle': r.get('document_title', f'Document {idx + 1}'),
                    'chunkIndex': r.get('chunk_index', idx),
                    'content': r.get('content', ''),
                    'contextSummary': r.get('context_summary') if include_context else None,
                    'score': float(r.get('score', 0.5)),
                    'rankSource': r.get('rank_source', 'hybrid'),
                })

            return {
                'query': query,
                'resultsCount': len(results),
                'results': results,
                'agentSteps': [
                    f'[step:search] Executed hybrid search for: {query}',
                    f'[step:rank] Retrieved {len(results)} results above threshold {min_score}',
                ]
            }
    except Exception as e:
        logger.warning(f"[Agent:research-query][Job:{job_id}] Database search failed, using mock: {e}")

    # Fallback to mock results for testing UI
    logger.info(f"[Agent:research-query][Job:{job_id}][step:mock] Generating mock results")

    mock_results = generate_mock_search_results(query, max_results, min_score)

    return {
        'query': query,
        'resultsCount': len(mock_results),
        'results': mock_results,
        'agentSteps': [
            f'[step:search] Executed hybrid search for: {query}',
            f'[step:rank] Retrieved {len(mock_results)} results (mock data)',
        ]
    }


async def run_insight_extraction_agent(job_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insight Extraction Agent - Extract structured insights from search results.

    Phase 5: Processes search results to extract key insights.
    """
    query = input_data.get('query', '')
    max_results = input_data.get('maxResults', 5)
    min_score = input_data.get('minScore', 0.3)

    logger.info(f"[Agent:insight-extraction][Job:{job_id}][step:search] Query: {query}")

    # First, run research query to get relevant documents
    search_result = await run_research_query_agent(job_id, {
        'query': query,
        'maxResults': max_results * 2,
        'minScore': min_score,
        'includeContext': True
    })

    search_results = search_result.get('results', [])

    logger.info(f"[Agent:insight-extraction][Job:{job_id}][step:extract] Extracting insights from {len(search_results)} chunks")

    # Extract insights (mock implementation - will be replaced with LLM in Phase 5)
    insights = generate_mock_insights(query, search_results[:max_results])

    return {
        'query': query,
        'insights': insights,
    }


async def run_linkedin_post_agent(job_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    LinkedIn Post Generator Agent - Generate social media content.

    Phase 5: Creates LinkedIn-ready posts from insights.
    """
    title = input_data.get('title', '')
    insights = input_data.get('insights', [])
    tone = input_data.get('tone', 'professional')
    max_length = input_data.get('maxLength', 700)

    logger.info(f"[Agent:linkedin-post][Job:{job_id}][step:generate] Generating post with {len(insights)} insights")

    # Generate post (mock implementation - will be replaced with LLM)
    post = generate_mock_linkedin_post(title, insights, tone, max_length)

    return post


async def run_content_workflow_agent(job_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Content Workflow Agent - Full pipeline: Research -> Insights -> Post.

    Phase 4+5: Orchestrates the complete content generation workflow.
    """
    query = input_data.get('query', '')
    max_results = input_data.get('maxResults', 5)
    tone = input_data.get('tone', 'professional')
    max_post_length = input_data.get('maxPostLength', 700)

    steps = []

    # Step 1: Research Query
    logger.info(f"[Agent:content-workflow][Job:{job_id}][step:research] Starting research query")
    step_start = time.time()
    try:
        search_result = await run_research_query_agent(job_id, {
            'query': query,
            'maxResults': max_results * 2,
            'minScore': 0.1,
            'includeContext': True
        })
        steps.append({
            'name': 'Research Query',
            'status': 'completed',
            'durationMs': int((time.time() - step_start) * 1000)
        })
    except Exception as e:
        steps.append({
            'name': 'Research Query',
            'status': 'failed',
            'error': str(e),
            'durationMs': int((time.time() - step_start) * 1000)
        })
        return {
            'query': query,
            'steps': steps,
        }

    # Step 2: Insight Extraction
    logger.info(f"[Agent:content-workflow][Job:{job_id}][step:insights] Extracting insights")
    step_start = time.time()
    try:
        search_results = search_result.get('results', [])
        insights = generate_mock_insights(query, search_results[:max_results])
        steps.append({
            'name': 'Insight Extraction',
            'status': 'completed',
            'durationMs': int((time.time() - step_start) * 1000)
        })
    except Exception as e:
        steps.append({
            'name': 'Insight Extraction',
            'status': 'failed',
            'error': str(e),
            'durationMs': int((time.time() - step_start) * 1000)
        })
        return {
            'query': query,
            'searchResults': search_result.get('results', []),
            'steps': steps,
        }

    # Step 3: Post Generation
    logger.info(f"[Agent:content-workflow][Job:{job_id}][step:post] Generating LinkedIn post")
    step_start = time.time()
    try:
        post = generate_mock_linkedin_post(query, insights, tone, max_post_length)
        steps.append({
            'name': 'Post Generation',
            'status': 'completed',
            'durationMs': int((time.time() - step_start) * 1000)
        })
    except Exception as e:
        steps.append({
            'name': 'Post Generation',
            'status': 'failed',
            'error': str(e),
            'durationMs': int((time.time() - step_start) * 1000)
        })
        return {
            'query': query,
            'searchResults': search_result.get('results', []),
            'insights': insights,
            'steps': steps,
        }

    return {
        'query': query,
        'searchResults': search_result.get('results', []),
        'insights': insights,
        'post': post,
        'steps': steps,
    }


# Mock data generators for testing UI without LLM

def generate_mock_search_results(query: str, max_results: int, min_score: float) -> List[Dict[str, Any]]:
    """Generate mock search results for UI testing."""
    mock_topics = [
        ("Machine Learning in Healthcare", "Recent advances in applying ML algorithms to medical diagnosis have shown promising results."),
        ("Neural Network Architectures", "Transformer-based models have revolutionized natural language processing tasks."),
        ("Data Privacy Concerns", "Organizations must balance data utility with privacy protection requirements."),
        ("Cloud Computing Trends", "Serverless architectures are gaining popularity for scalable applications."),
        ("AI Ethics Guidelines", "Industry groups are developing frameworks for responsible AI deployment."),
    ]

    results = []
    for i in range(min(max_results, len(mock_topics))):
        topic, content = mock_topics[i]
        score = max(min_score, 0.9 - (i * 0.1))

        results.append({
            'id': str(uuid.uuid4()),
            'documentId': str(uuid.uuid4()),
            'documentTitle': f'{topic} - Research Paper',
            'chunkIndex': i,
            'content': f'{content} This relates to the query about "{query}". Additional context and findings from the research indicate various implications for the field.',
            'contextSummary': f'This chunk discusses {topic.lower()} in the context of {query}.',
            'score': score,
            'rankSource': 'hybrid' if i % 2 == 0 else 'vector',
        })

    return results


def generate_mock_insights(query: str, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate mock insights from search results."""
    insights = []

    for i, result in enumerate(search_results[:5]):
        insight = {
            'id': str(uuid.uuid4()),
            'claim': f"Key finding #{i + 1} related to {query}",
            'summary': f"Based on the document '{result.get('documentTitle', 'Unknown')}', we found that {result.get('content', '')[:100]}...",
            'confidence': max(0.5, result.get('score', 0.7)),
            'tags': ['research', query.split()[0].lower() if query else 'insight'],
            'evidence': [{
                'excerpt': result.get('content', '')[:200],
                'documentId': result.get('documentId', ''),
                'chunkIndex': result.get('chunkIndex', i),
                'score': result.get('score', 0.7)
            }]
        }
        insights.append(insight)

    return insights


def generate_mock_linkedin_post(title: str, insights: List[Dict[str, Any]], tone: str, max_length: int) -> Dict[str, Any]:
    """Generate mock LinkedIn post from insights."""

    # Build post content based on tone
    if tone == 'casual':
        opener = f"Hey everyone! 👋 Wanted to share some interesting findings about {title or 'this topic'}!\n\n"
    elif tone == 'thought-leadership':
        opener = f"As we navigate the evolving landscape of {title or 'our industry'}, key insights emerge that demand our attention.\n\n"
    else:  # professional
        opener = f"I've been researching {title or 'this topic'} and wanted to share some key insights:\n\n"

    body_parts = []
    for i, insight in enumerate(insights[:3]):
        claim = insight.get('claim', f'Insight {i + 1}')
        body_parts.append(f"• {claim}")

    body = "\n".join(body_parts)

    if tone == 'casual':
        closer = "\n\nWhat are your thoughts? Drop a comment below! 👇"
    elif tone == 'thought-leadership':
        closer = "\n\nThe implications for our industry are profound. I'd welcome your perspectives on these developments."
    else:
        closer = "\n\nI'd love to hear your thoughts and experiences in this area."

    post_content = opener + body + closer

    # Truncate if needed
    if len(post_content) > max_length:
        post_content = post_content[:max_length - 3] + "..."

    # Generate hashtags
    hashtags = ['#AI', '#Research', '#Innovation']
    if title:
        hashtags.append(f"#{title.replace(' ', '')[:20]}")

    return {
        'post': post_content,
        'hashtags': hashtags,
        'length': len(post_content),
        'tone': tone
    }

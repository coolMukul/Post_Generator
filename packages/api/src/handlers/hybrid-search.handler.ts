import { HybridSearchRequest, HybridSearchResponse } from '../types/schemas.js';
import { mainProcessingQueue, mainProcessingEvents } from '../config/queue.js';

/**
 * Hybrid Retrieval Handler
 * 
 * Submits hybrid retrieval requests to the worker queue for processing.
 * The worker handles the actual retrieval using Python repositories with proper
 * vector embeddings and keyword search capabilities.
 */
export async function performHybridSearch(
  params: HybridSearchRequest
): Promise<HybridSearchResponse> {
  const {
    query,
    project_key = 'researchpaper',
    vector_weight = 0.7,
    keyword_weight = 0.3,
    rrf_k = 60
  } = params;

  if (!query || query.trim() === '') {
    return {
      results: [],
      query: query || '',
      project_key,
      total: 0,
      config: { vector_weight, keyword_weight, rrf_k }
    };
  }

  try {
    // Add job to the main processing queue with 'hybrid-retrieval' job name
    const job = await mainProcessingQueue.add('hybrid-retrieval', params, {
      jobId: `retrieval-${Date.now()}-${Math.random().toString(36).substring(7)}`,
    });

    // Wait for job to complete (with timeout)
    const result = await job.waitUntilFinished(
      mainProcessingEvents,
      30000 // 30 second timeout
    );

    // Return the search results
    return result as HybridSearchResponse;

  } catch (error) {
    console.error('Hybrid retrieval job failed:', error);
    
    // Return empty results on error rather than throwing
    return {
      results: [],
      query,
      project_key,
      total: 0,
      config: { vector_weight, keyword_weight, rrf_k }
    };
  }
}

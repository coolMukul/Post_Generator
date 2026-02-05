import { HybridRetrievalRequest, HybridRetrievalResponse } from '../types/schemas.js';
import { mainProcessingQueue, mainProcessingEvents, redisClient, QUEUE_NAMES } from '../config/queue.js';

/**
 * Hybrid Retrieval Handler
 *
 * Submits hybrid retrieval requests to the worker queue for processing.
 * The worker handles embedding generation and actual retrieval using Python repositories.
 */
export async function performHybridSearch(
  params: HybridRetrievalRequest
): Promise<HybridRetrievalResponse> {
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
    // Submit job to worker - worker will generate embeddings and perform retrieval
    console.log(`[Hybrid Retrieval] Submitting query: "${query}"`);

    // Add job to the main processing queue with 'hybrid-retrieval' job name
    const job = await mainProcessingQueue.add('hybrid-retrieval', params, {
      jobId: `retrieval-${Date.now()}-${Math.random().toString(36).substring(7)}`,
    });

    // Poll Redis for the job's returnvalue as a fallback to pub/sub event gaps
    const jobKey = `bull:${QUEUE_NAMES.MAIN_PROCESSING}:${job.id}`;
    const timeoutMs = 30000;
    const intervalMs = 300; // poll interval
    const start = Date.now();

    while (Date.now() - start < timeoutMs) {
      try {
        const raw = await redisClient.hget(jobKey, 'returnvalue');
        if (raw) {
          try {
            const parsed = JSON.parse(raw);
            return parsed as HybridRetrievalResponse;
          } catch (e) {
            // If parsing fails, return raw value wrapped
            return raw as unknown as HybridRetrievalResponse;
          }
        }
      } catch (err) {
        console.error('Error polling job returnvalue:', err);
      }

      // wait before next poll
      await new Promise((res) => setTimeout(res, intervalMs));
    }

    // Timed out waiting for job result
    console.error('Timed out waiting for hybrid retrieval job result', { jobId: job.id });
    return {
      results: [],
      query,
      project_key,
      total: 0,
      config: { vector_weight, keyword_weight, rrf_k }
    };

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

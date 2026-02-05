import OpenAI from 'openai';

/**
 * Embedding Service
 *
 * Handles generation of embeddings using OpenAI's API for hybrid retrieval.
 */

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Embedding model configuration
const EMBEDDING_MODEL = 'text-embedding-3-small';
const EMBEDDING_DIMENSIONS = 1536; // text-embedding-3-small default dimensions

/**
 * Generate embedding for a single query text
 *
 * @param text - Query text to embed
 * @returns Embedding vector as array of numbers
 */
export async function generateQueryEmbedding(text: string): Promise<number[]> {
  if (!text || text.trim() === '') {
    throw new Error('Cannot generate embedding for empty text');
  }

  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY environment variable not set');
  }

  try {
    const response = await openai.embeddings.create({
      model: EMBEDDING_MODEL,
      input: text.trim(),
      encoding_format: 'float',
    });

    if (!response.data || response.data.length === 0) {
      throw new Error('No embedding returned from OpenAI API');
    }

    const embedding = response.data[0].embedding;

    if (!embedding || embedding.length === 0) {
      throw new Error('Invalid embedding returned from OpenAI API');
    }

    return embedding;
  } catch (error) {
    console.error('Failed to generate embedding:', error);
    throw new Error(`Embedding generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Generate embeddings for multiple texts (batch processing)
 *
 * @param texts - Array of texts to embed
 * @returns Array of embedding vectors
 */
export async function generateEmbeddingsBatch(texts: string[]): Promise<number[][]> {
  if (!texts || texts.length === 0) {
    return [];
  }

  if (!process.env.OPENAI_API_KEY) {
    throw new Error('OPENAI_API_KEY environment variable not set');
  }

  // Filter out empty texts
  const validTexts = texts.filter(t => t && t.trim() !== '');

  if (validTexts.length === 0) {
    return [];
  }

  try {
    const response = await openai.embeddings.create({
      model: EMBEDDING_MODEL,
      input: validTexts.map(t => t.trim()),
      encoding_format: 'float',
    });

    if (!response.data || response.data.length === 0) {
      throw new Error('No embeddings returned from OpenAI API');
    }

    // OpenAI returns embeddings in the same order as input
    return response.data.map(item => item.embedding);
  } catch (error) {
    console.error('Failed to generate embeddings batch:', error);
    throw new Error(`Batch embedding generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Get embedding model info
 */
export function getEmbeddingModelInfo() {
  return {
    model: EMBEDDING_MODEL,
    dimensions: EMBEDDING_DIMENSIONS,
  };
}

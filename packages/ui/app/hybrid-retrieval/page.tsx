'use client';

import { useState } from 'react';
import Link from 'next/link';

interface HybridSearchResult {
  id: string;
  document_id: string;
  document_title?: string;
  chunk_index: number;
  content: string;
  context_summary: string | null;
  score: number;
  rank_source: 'vector' | 'keyword' | 'hybrid';
  metadata: Record<string, any>;
}

interface HybridSearchResponse {
  results: HybridSearchResult[];
  query: string;
  project_key: string;
  total: number;
  config: {
    vector_weight: number;
    keyword_weight: number;
    rrf_k: number;
  };
}

export default function HybridSearchPage() {
  // Get API base URL from environment variable
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

  const [query, setQuery] = useState('');
  const [projectKey, setProjectKey] = useState('researchpaper');
  const [limit, setLimit] = useState(20);
  const [minScorePercent, setMinScorePercent] = useState(30);
  const [vectorWeight, setVectorWeight] = useState(0.7);
  const [keywordWeight, setKeywordWeight] = useState(0.3);
  const [rrfK, setRrfK] = useState(60);

  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<HybridSearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!query.trim()) {
      setError('Please enter a search query');
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${API_BASE_URL}/hybrid-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          project_key: projectKey,
          limit,
          min_score: minScorePercent / 100,
          vector_weight: vectorWeight,
          keyword_weight: keywordWeight,
          rrf_k: rrfK,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || `HTTP ${res.status}`);
      }

      const data: HybridSearchResponse = await res.json();
      setResponse(data);
    } catch (err: any) {
      setError(err.message || 'Failed to perform search');
      console.error('Search error:', err);
    } finally {
      setLoading(false);
    }
  };

  const getRankSourceColor = (source: string) => {
    switch (source) {
      case 'vector': return '#3b82f6';
      case 'keyword': return '#10b981';
      case 'hybrid': return '#8b5cf6';
      default: return '#6b7280';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return '#10b981';
    if (score >= 0.6) return '#3b82f6';
    if (score >= 0.4) return '#f59e0b';
    return '#6b7280';
  };

  return (
    <div className="container" style={{ maxWidth: '1200px', padding: '2rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontWeight: '600' }}>
          ← Back to Home
        </Link>
      </div>

      <div className="card">
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          🔍 Hybrid Retrieval System
        </h1>
        <p style={{ color: '#666', marginBottom: '2rem' }}>
          Phase 3: Search combining vector similarity and keyword matching
        </p>

        <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Query Input */}
          <div>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
              Search Query *
            </label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g., transformer architecture, attention mechanisms, BERT..."
              className="input"
              required
            />
          </div>

          {/* Search Parameters */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Max Results: {limit}
              </label>
              <input
                type="range"
                min="5"
                max="50"
                step="5"
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Min Score: {minScorePercent}%
              </label>
              <input
                type="range"
                min="0"
                max="100"
                step="5"
                value={minScorePercent}
                onChange={(e) => setMinScorePercent(parseInt(e.target.value))}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Vector Weight: {vectorWeight.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={vectorWeight}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  setVectorWeight(v);
                  setKeywordWeight(parseFloat((1 - v).toFixed(1)));
                }}
                style={{ width: '100%' }}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Keyword Weight: {keywordWeight.toFixed(1)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={keywordWeight}
                onChange={(e) => {
                  const k = parseFloat(e.target.value);
                  setKeywordWeight(k);
                  setVectorWeight(parseFloat((1 - k).toFixed(1)));
                }}
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Advanced Settings */}
          <details>
            <summary style={{ cursor: 'pointer', fontWeight: '600', color: '#667eea' }}>
              Advanced Settings
            </summary>
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '0.5rem' }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                  RRF Constant (k): {rrfK}
                  <span style={{ fontSize: '0.75rem', color: '#666', marginLeft: '0.5rem' }}>
                    (higher = more conservative ranking)
                  </span>
                </label>
                <input
                  type="range"
                  min="20"
                  max="100"
                  step="10"
                  value={rrfK}
                  onChange={(e) => setRrfK(parseInt(e.target.value))}
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                  Project Key
                </label>
                <input
                  type="text"
                  value={projectKey}
                  onChange={(e) => setProjectKey(e.target.value)}
                  className="input"
                />
              </div>
            </div>
          </details>

          {/* Search Button */}
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="btn btn-primary"
          >
            {loading ? '⏳ Searching...' : '🔍 Search Documents'}
          </button>
        </form>

        {/* Error */}
        {error && (
          <div className="alert alert-error" style={{ marginTop: '1rem' }}>
            <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>✗ Error</h3>
            <p style={{ fontSize: '0.875rem' }}>{error}</p>
          </div>
        )}

        {/* Search Info */}
        {response && (
          <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '0.5rem' }}>
            <div style={{ fontSize: '0.875rem', color: '#0c4a6e' }}>
              <p><strong>Query:</strong> "{response.query}"</p>
              <p><strong>Results:</strong> {response.total} found</p>
              <p><strong>Project:</strong> {response.project_key}</p>
              <p>
                <strong>Weights:</strong> Vector: {response.config.vector_weight.toFixed(1)} |
                Keyword: {response.config.keyword_weight.toFixed(1)} |
                RRF-k: {response.config.rrf_k}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      {response && response.results.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '1rem' }}>
            Search Results ({response.results.length})
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {response.results.map((result, idx) => (
              <div
                key={result.id}
                className="card"
                style={{ borderLeft: `4px solid ${getRankSourceColor(result.rank_source)}` }}
              >
                {/* Result Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#9ca3af' }}>
                        #{idx + 1}
                      </span>
                      {result.document_title && (
                        <h3 style={{ fontSize: '1rem', fontWeight: '600', color: '#1f2937' }}>
                          {result.document_title}
                        </h3>
                      )}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                      Chunk {result.chunk_index} • ID: {result.document_id.substring(0, 8)}...
                    </div>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'end', gap: '0.25rem' }}>
                    <span
                      style={{
                        fontSize: '1.5rem',
                        fontWeight: 'bold',
                        color: getScoreColor(result.score)
                      }}
                    >
                      {(result.score * 100).toFixed(0)}%
                    </span>
                    <span style={{ fontSize: '0.625rem', color: '#6b7280' }}>
                      {result.score.toFixed(4)}
                    </span>
                    <span
                      style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '0.25rem',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        backgroundColor: `${getRankSourceColor(result.rank_source)}20`,
                        color: getRankSourceColor(result.rank_source)
                      }}
                    >
                      {result.rank_source}
                    </span>
                  </div>
                </div>

                {/* Context Summary */}
                {result.context_summary && (
                  <div
                    style={{
                      marginBottom: '0.75rem',
                      padding: '0.75rem',
                      backgroundColor: '#dbeafe',
                      borderLeft: '3px solid #3b82f6',
                      borderRadius: '0.25rem',
                      fontSize: '0.875rem'
                    }}
                  >
                    <div style={{ fontWeight: '600', color: '#1e40af', marginBottom: '0.25rem' }}>
                      Context:
                    </div>
                    <div style={{ color: '#1e3a8a' }}>
                      {result.context_summary}
                    </div>
                  </div>
                )}

                {/* Content */}
                <div style={{ fontSize: '0.875rem', color: '#374151', lineHeight: '1.6' }}>
                  {result.content}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Results */}
      {response && response.results.length === 0 && (
        <div className="card" style={{ marginTop: '2rem', textAlign: 'center', padding: '3rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤷</div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            No results found
          </h3>
          <p style={{ color: '#666', fontSize: '0.875rem' }}>
            Try adjusting your query or lowering the minimum score threshold.
          </p>
        </div>
      )}

      {/* API Info */}
      <div className="alert alert-info" style={{ marginTop: '2rem' }}>
        <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>🔌 API Endpoint</h3>
        <div style={{ fontSize: '0.875rem' }}>
          <p><strong>Hybrid Search:</strong> <code>POST {API_BASE_URL}/hybrid-search</code></p>
          <p style={{ marginTop: '0.5rem', color: '#666' }}>
            Combines vector similarity and keyword matching with RRF
          </p>
        </div>
      </div>

      {/* How It Works */}
      <div className="alert alert-info" style={{ marginTop: '1rem' }}>
        <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>📚 How Hybrid Search Works</h3>
        <ol style={{ fontSize: '0.875rem', paddingLeft: '1.25rem', margin: 0 }}>
          <li><strong>Vector Search:</strong> Finds semantically similar content using embeddings</li>
          <li><strong>Keyword Search:</strong> Finds exact keyword matches using BM25</li>
          <li><strong>RRF Fusion:</strong> Intelligently merges both rankings</li>
          <li><strong>Score Normalization:</strong> Results scored 0-1 (1 = perfect match)</li>
        </ol>
        <p style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.5rem' }}>
          <strong>Tip:</strong> Use high vector weight (0.7-0.8) for semantic search,
          high keyword weight (0.7-0.8) for exact matching, or balanced (0.5/0.5) for best overall results.
        </p>
      </div>
    </div>
  );
}

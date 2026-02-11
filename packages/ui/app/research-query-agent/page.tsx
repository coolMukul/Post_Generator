"use client";

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

interface SearchResult {
  id: string;
  documentId: string;
  documentTitle?: string;
  chunkIndex: number;
  content: string;
  contextSummary: string | null;
  score: number;
  rankSource: 'vector' | 'keyword' | 'hybrid';
  relevanceReason?: string;
}

interface AgentResult {
  query: string;
  resultsCount: number;
  results: SearchResult[];
  executionTimeMs: number;
  agentSteps: string[];
}

interface QueryHistoryItem {
  id: string;
  query: string;
  loading: boolean;
  result: AgentResult | null;
  error: string | null;
  jobId: string | null;
  minScore?: number;
  countdown?: number;
  timestamp: Date;
}

export default function ResearchQueryAgentPage() {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  // UI shows percentage (0-100). Convert to decimal when sending to API.
  const [minScorePercent, setMinScorePercent] = useState(1);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  // per-job polling refs
  const pollingRefs = useRef<Record<string, number>>({});
  const pollingCountdowns = useRef<Record<string, number>>({});
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevLenRef = useRef<number>(0);
  const [isAtBottom, setIsAtBottom] = useState(true);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50;
    setIsAtBottom(atBottom);
  };

  // Auto-scroll only when user is at (or near) bottom and new items arrive
  useEffect(() => {
    if (queryHistory.length > prevLenRef.current && isAtBottom) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
    prevLenRef.current = queryHistory.length;
  }, [queryHistory.length, isAtBottom]);

  useEffect(() => {
    return () => {
      // clear any per-job intervals on unmount
      Object.values(pollingRefs.current).forEach(id => clearInterval(id));
      pollingRefs.current = {};
      pollingCountdowns.current = {};
    };
  }, []);

  const submitQuery = async () => {
    if (!query.trim()) return;

    const historyId = Date.now().toString();
    const minScoreDecimal = Math.max(0, Math.min(1, minScorePercent / 100));

    const newQuery: QueryHistoryItem = {
      id: historyId,
      query: query.trim(),
      loading: true,
      result: null,
      error: null,
      jobId: null,
      minScore: minScoreDecimal,
      timestamp: new Date(),
    };

    setQueryHistory(prev => [...prev, newQuery]);
    setQuery('');

    try {
      const response = await fetch(`${API_URL}/agent/research-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: newQuery.query,
          maxResults,
          minScore: minScoreDecimal,
          includeContext: true,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Failed to submit agent job');
      }

      setQueryHistory(prev => prev.map(item =>
        item.id === historyId ? { ...item, jobId: data.jobId } : item
      ));

      pollJobStatus(historyId, data.jobId);
    } catch (err: any) {
      setQueryHistory(prev => prev.map(item =>
        item.id === historyId ? { ...item, loading: false, error: err.message } : item
      ));
    }
  };

  // Retry a past query using current screen settings (maxResults and minScorePercent)
  const retryQuery = async (text: string) => {
    if (!text || !text.trim()) return;

    const historyId = Date.now().toString();
    const minScoreDecimal = Math.max(0, Math.min(1, minScorePercent / 100));
    const newQuery: QueryHistoryItem = {
      id: historyId,
      query: text.trim(),
      loading: true,
      result: null,
      error: null,
      jobId: null,
      minScore: minScoreDecimal,
      timestamp: new Date(),
    };

    setQueryHistory(prev => [...prev, newQuery]);

    try {
      const response = await fetch(`${API_URL}/agent/research-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: newQuery.query,
          maxResults,
          minScore: minScoreDecimal,
          includeContext: true,
        }),
      });

      const data = await response.json();
      if (!data.success) throw new Error(data.error || 'Failed to submit agent job');

      setQueryHistory(prev => prev.map(item =>
        item.id === historyId ? { ...item, jobId: data.jobId } : item
      ));

      pollJobStatus(historyId, data.jobId);
    } catch (err: any) {
      setQueryHistory(prev => prev.map(item =>
        item.id === historyId ? { ...item, loading: false, error: err.message } : item
      ));
    }
  };

  const pollJobStatus = (historyId: string, jobId: string) => {
    const pollIntervalSec = 60;
    // initialize countdown
    pollingCountdowns.current[historyId] = pollIntervalSec;
    setQueryHistory(prev => prev.map(item => item.id === historyId ? { ...item, countdown: pollIntervalSec } : item));

    let stopped = false;

    const doPoll = async () => {
      try {
        const response = await fetch(`${API_URL}/queue/jobs/${jobId}`);
        const data = await response.json();

        if (data.state === 'completed') {
          stopped = true;
          // set result and clear interval
          setQueryHistory(prev => prev.map(item =>
            item.id === historyId ? { ...item, loading: false, result: data.returnvalue, countdown: 0 } : item
          ));
          const intId = pollingRefs.current[historyId];
          if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
          delete pollingCountdowns.current[historyId];
          return;
        }

        if (data.state === 'failed') {
          stopped = true;
          setQueryHistory(prev => prev.map(item =>
            item.id === historyId ? { ...item, loading: false, error: data.failedReason || 'Agent execution failed', countdown: 0 } : item
          ));
          const intId = pollingRefs.current[historyId];
          if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
          delete pollingCountdowns.current[historyId];
          return;
        }
      } catch (err: any) {
        stopped = true;
        setQueryHistory(prev => prev.map(item =>
          item.id === historyId ? { ...item, loading: false, error: err.message, countdown: 0 } : item
        ));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete pollingCountdowns.current[historyId];
        return;
      }
    };

    // initial poll
    doPoll();

    // per-second ticker that decrements countdown and triggers poll when reaches 0
    const intervalId = window.setInterval(async () => {
      if (stopped) {
        const id = pollingRefs.current[historyId];
        if (id) { clearInterval(id); delete pollingRefs.current[historyId]; }
        delete pollingCountdowns.current[historyId];
        return;
      }

      let next = (pollingCountdowns.current[historyId] ?? pollIntervalSec) - 1;
      pollingCountdowns.current[historyId] = next;
      setQueryHistory(prev => prev.map(item => item.id === historyId ? { ...item, countdown: next } : item));

      if (next <= 0) {
        // perform poll and reset countdown if still running
        await doPoll();
        if (!stopped) {
          pollingCountdowns.current[historyId] = pollIntervalSec;
          setQueryHistory(prev => prev.map(item => item.id === historyId ? { ...item, countdown: pollIntervalSec } : item));
        }
      }
    }, 1000);

    pollingRefs.current[historyId] = intervalId as unknown as number;
  };

  const checkJobNow = async (historyId: string, jobId: string | null) => {
    if (!jobId) return;
    try {
      const response = await fetch(`${API_URL}/queue/jobs/${jobId}`);
      const data = await response.json();

      if (data.state === 'completed') {
        // update this specific item
        setQueryHistory(prev => prev.map(item =>
          item.id === historyId ? { ...item, loading: false, result: data.returnvalue, countdown: 0 } : item
        ));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete pollingCountdowns.current[historyId];
        return;
      }

      if (data.state === 'failed') {
        setQueryHistory(prev => prev.map(item =>
          item.id === historyId ? { ...item, loading: false, error: data.failedReason || 'Agent execution failed', countdown: 0 } : item
        ));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete pollingCountdowns.current[historyId];
        return;
      }

      // still in progress: reset countdown for this item
      pollingCountdowns.current[historyId] = 60;
      setQueryHistory(prev => prev.map(item => item.id === historyId ? { ...item, countdown: 60 } : item));

      // ensure polling interval is running
      if (!pollingRefs.current[historyId]) {
        pollJobStatus(historyId, jobId);
      }
    } catch (err: any) {
      setQueryHistory(prev => prev.map(item =>
        item.id === historyId ? { ...item, loading: false, error: err.message, countdown: 0 } : item
      ));
      const intId = pollingRefs.current[historyId];
      if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
      delete pollingCountdowns.current[historyId];
    }
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f9fafb', padding: '2rem 0' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 1rem' }}>
        <div style={{ marginBottom: '1.5rem' }}>
          <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontWeight: '600' }}>
            ← Back to Home
          </Link>
        </div>

        <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', padding: '1.5rem', marginBottom: '1.5rem' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
            🤖 Research Query Agent
          </h1>
          <p style={{ color: '#666', marginBottom: '1.5rem' }}>
            Phase 4: AI-powered research assistant using hybrid RAG (vector + keyword)
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Max Results
              </label>
              <input
                type="number"
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                min={1}
                max={50}
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Min Score: {minScorePercent}%
              </label>
              <input
                type="range"
                value={minScorePercent}
                onChange={(e) => setMinScorePercent(Number(e.target.value))}
                min={0}
                max={100}
                step={1}
                className="input"
                style={{ width: '100%' }}
              />
            </div>
          </div>
        </div>

        <div ref={containerRef} onScroll={handleScroll} style={{ maxHeight: '600px', overflowY: 'auto', marginBottom: '1.5rem' }}>
          {queryHistory.map((item) => (
            <div key={item.id} style={{ marginBottom: '1.5rem' }}>
              <div style={{ backgroundColor: '#667eea', color: 'white', borderRadius: '8px', padding: '1rem', marginBottom: '0.75rem' }}>
                <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.25rem' }}>
                  🧑 You asked:
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600' }}>
                  {item.query}
                </div>
                <div style={{ fontSize: '0.75rem', opacity: 0.8, marginTop: '0.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                    <div>{item.timestamp.toLocaleTimeString()}</div>
                    {item.loading ? (
                      <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <div style={{ fontSize: '0.875rem', color: '#667eea', fontWeight: 600 }}>
                          {typeof item.countdown === 'number' && item.countdown > 0 ? `⏱️ Next check in ${item.countdown} seconds...` : 'Waiting...'}
                        </div>
                        <button
                          type="button"
                          onClick={() => checkJobNow(item.id, item.jobId)}
                          disabled={!item.jobId}
                          style={{ padding: '0.25rem 0.6rem', borderRadius: '6px', backgroundColor: '#eef2ff', border: '1px solid #c7d2fe', color: '#3730a3', fontWeight: 600, cursor: 'pointer' }}
                        >
                          Check now
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => retryQuery(item.query)}
                        style={{ padding: '0.25rem 0.5rem', borderRadius: '6px', backgroundColor: '#eefbf7', border: '1px solid #bbf7d0', color: '#065f46', fontWeight: 600, cursor: 'pointer' }}
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              </div>

              <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)', padding: '1rem' }}>
                {item.loading && (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                      <span style={{ fontSize: '1.5rem', animation: 'pulse 1.5s ease-in-out infinite' }}>🤖</span>
                      <span style={{ fontWeight: '600', color: '#667eea' }}>Agent is working...</span>
                    </div>
                    {item.jobId && (
                      <div style={{ fontSize: '0.75rem', color: '#666', fontFamily: 'monospace', marginBottom: '0.5rem' }}>
                        Job ID: {item.jobId}
                      </div>
                    )}
                  </div>
                )}

                {item.error && (
                  <div style={{ backgroundColor: '#fee', padding: '0.75rem', borderRadius: '4px', borderLeft: '4px solid #f00' }}>
                    <div style={{ fontWeight: '600', color: '#c00', marginBottom: '0.25rem' }}>❌ Error</div>
                    <div style={{ color: '#600', fontSize: '0.875rem' }}>{item.error}</div>
                  </div>
                )}

                {item.result && (
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                      <span style={{ fontSize: '1.5rem' }}>✅</span>
                      <span style={{ fontWeight: '600', color: '#10b981' }}>
                        Found {item.result.resultsCount} results in {item.result.executionTimeMs}ms
                      </span>
                    </div>

                    {typeof item.minScore === 'number' && (
                      <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.75rem' }}>
                        Min score threshold: {(item.minScore * 100).toFixed(0)}%
                      </div>
                    )}

                    {item.result.results.map((result, idx) => (
                      <div key={result.id} style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#f9fafb', borderRadius: '6px', border: '1px solid #e5e7eb' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                          <div style={{ fontWeight: '600', fontSize: '0.95rem' }}>
                            #{idx + 1}: {result.documentTitle || `Document ${result.documentId.slice(0, 8)}`}
                          </div>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <span style={{
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              backgroundColor: result.rankSource === 'hybrid' ? '#e9d5ff' : result.rankSource === 'vector' ? '#dbeafe' : '#d1fae5',
                              color: result.rankSource === 'hybrid' ? '#6b21a8' : result.rankSource === 'vector' ? '#1e40af' : '#047857',
                            }}>
                              {result.rankSource}
                            </span>
                            <span style={{
                              padding: '0.25rem 0.5rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              fontWeight: '600',
                              backgroundColor: '#fef3c7',
                              color: '#92400e',
                            }}>
                              {(result.score * 100).toFixed(1)}%
                            </span>
                          </div>
                        </div>

                        {result.relevanceReason && (
                          <div style={{ fontSize: '0.875rem', color: '#666', fontStyle: 'italic', marginBottom: '0.5rem' }}>
                            💡 {result.relevanceReason}
                          </div>
                        )}

                        {result.contextSummary && (
                          <div style={{ backgroundColor: '#eff6ff', padding: '0.75rem', borderRadius: '4px', borderLeft: '3px solid #3b82f6', marginBottom: '0.5rem' }}>
                            <div style={{ fontSize: '0.75rem', fontWeight: '600', color: '#1e40af', marginBottom: '0.25rem' }}>
                              Context Summary:
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#1e3a8a' }}>
                              {result.contextSummary}
                            </div>
                          </div>
                        )}

                        <div style={{ backgroundColor: 'white', padding: '0.75rem', borderRadius: '4px', fontSize: '0.875rem', lineHeight: '1.6', color: '#374151' }}>
                          {result.content.length > 500 ? `${result.content.slice(0, 500)}...` : result.content}
                        </div>

                        <div style={{ fontSize: '0.75rem', color: '#9ca3af', marginTop: '0.5rem' }}>
                          Chunk #{result.chunkIndex} · {result.documentId.slice(0, 12)}...
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 -2px 10px rgba(0,0,0,0.1)', padding: '1.5rem', position: 'sticky', bottom: '1rem' }}>
          <form onSubmit={(e) => { e.preventDefault(); submitQuery(); }} style={{ display: 'flex', gap: '1rem' }}>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a research question... (e.g., 'machine learning transformers')"
              className="input"
              style={{ flex: 1 }}
              disabled={queryHistory.some(q => q.loading)}
            />
            <button
              type="submit"
              disabled={!query.trim() || queryHistory.some(q => q.loading)}
              className="btn btn-primary"
              style={{ whiteSpace: 'nowrap' }}
            >
              🚀 Ask Agent
            </button>
          </form>
        </div>
      </div>

      <style jsx>{`\n        @keyframes pulse {\n          0%, 100% { opacity: 1; }\n          50% { opacity: 0.5; }\n        }\n      `}</style>
    </div>
  );
}

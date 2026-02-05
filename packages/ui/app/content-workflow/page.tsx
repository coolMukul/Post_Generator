"use client";

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3101';

interface SearchResult {
  id: string;
  documentId: string;
  documentTitle?: string;
  chunkIndex: number;
  content: string;
  contextSummary: string | null;
  score: number;
  rankSource: 'vector' | 'keyword' | 'hybrid';
}

interface Evidence {
  excerpt: string;
  documentId?: string;
  chunkIndex?: number;
  score?: number;
}

interface Insight {
  id: string;
  claim: string;
  summary?: string;
  confidence: number;
  tags?: string[];
  evidence?: Evidence[];
}

interface LinkedInPost {
  post: string;
  hashtags?: string[];
  length: number;
  tone: string;
}

interface WorkflowStep {
  name: string;
  status: 'completed' | 'failed' | 'skipped' | 'pending' | 'running';
  durationMs?: number;
  error?: string;
}

interface WorkflowResult {
  query: string;
  searchResults?: SearchResult[];
  insights?: Insight[];
  post?: LinkedInPost;
  executionTimeMs?: number;
  steps: WorkflowStep[];
}

interface HistoryItem {
  id: string;
  query: string;
  tone: string;
  maxResults: number;
  loading: boolean;
  result: WorkflowResult | null;
  error: string | null;
  jobId: string | null;
  countdown?: number;
  collapsed?: boolean;
  timestamp: Date;
  activeTab: 'steps' | 'search' | 'insights' | 'post';
}

export default function ContentWorkflowPage() {
  const [query, setQuery] = useState('');
  const [tone, setTone] = useState<'professional' | 'casual' | 'thought-leadership'>('professional');
  const [maxResults, setMaxResults] = useState(5);
  const [maxPostLength, setMaxPostLength] = useState(700);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  const pollingRefs = useRef<Record<string, number>>({});
  const countdowns = useRef<Record<string, number>>({});

  useEffect(() => {
    return () => {
      Object.values(pollingRefs.current).forEach((id) => clearInterval(id));
      pollingRefs.current = {};
      countdowns.current = {};
    };
  }, []);

  const submit = async () => {
    if (!query.trim()) return;
    const id = Date.now().toString();

    const item: HistoryItem = {
      id,
      query: query.trim(),
      tone,
      maxResults,
      loading: true,
      result: null,
      error: null,
      jobId: null,
      countdown: 60,
      collapsed: false,
      timestamp: new Date(),
      activeTab: 'steps',
    };

    setHistory((s) => [...s, item]);
    setQuery('');

    try {
      const res = await fetch(`${API_URL}/agent/content-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: item.query,
          maxResults,
          tone,
          maxPostLength
        }),
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || 'Failed to submit job');

      setHistory((s) => s.map((h) => (h.id === id ? { ...h, jobId: data.jobId } : h)));
      startPolling(id, data.jobId);
    } catch (err: any) {
      setHistory((s) => s.map((h) => (h.id === id ? { ...h, loading: false, error: err.message } : h)));
    }
  };

  const startPolling = (historyId: string, jobId: string) => {
    const intervalSec = 60; // Poll every 60 seconds
    countdowns.current[historyId] = intervalSec;
    setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: intervalSec } : h)));

    const existing = pollingRefs.current[historyId];
    if (existing) {
      clearInterval(existing as unknown as number);
      delete pollingRefs.current[historyId];
      delete countdowns.current[historyId];
    }

    let stopped = false;

    const doPoll = async () => {
      try {
        const r = await fetch(`${API_URL}/queue/jobs/${jobId}`);
        const d = await r.json();
        if (d.state === 'completed') {
          stopped = true;
          const payload = d.returnvalue || d.result || d;
          console.debug('[ContentWorkflow] received job payload', d);
          setHistory((s) => s.map((h) => (h.id === historyId ? {
            ...h,
            loading: false,
            result: payload,
            countdown: 0,
            activeTab: payload?.post ? 'post' : payload?.insights?.length ? 'insights' : 'steps'
          } : h)));
          const intId = pollingRefs.current[historyId];
          if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
          delete countdowns.current[historyId];
          return;
        }
        if (d.state === 'failed') {
          stopped = true;
          setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: d.failedReason || 'Job failed', countdown: 0 } : h)));
          const intId = pollingRefs.current[historyId];
          if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
          delete countdowns.current[historyId];
          return;
        }
      } catch (err: any) {
        stopped = true;
        setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: err.message, countdown: 0 } : h)));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete countdowns.current[historyId];
        return;
      }
    };

    doPoll();

    const intervalId = window.setInterval(async () => {
      if (stopped) {
        const iid = pollingRefs.current[historyId];
        if (iid) { clearInterval(iid); delete pollingRefs.current[historyId]; }
        delete countdowns.current[historyId];
        return;
      }
      let next = (countdowns.current[historyId] ?? intervalSec) - 1;
      countdowns.current[historyId] = next;
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: next } : h)));
      if (next <= 0) {
        await doPoll();
        if (!stopped) {
          countdowns.current[historyId] = intervalSec;
          setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: intervalSec } : h)));
        }
      }
    }, 1000);

    pollingRefs.current[historyId] = intervalId as unknown as number;
  };

  const checkNow = async (historyId: string, jobId: string | null) => {
    if (!jobId) return;
    try {
      const r = await fetch(`${API_URL}/queue/jobs/${jobId}`);
      const d = await r.json();
      if (d.state === 'completed') {
        const payload = d.returnvalue || d.result || d;
        setHistory((s) => s.map((h) => (h.id === historyId ? {
          ...h,
          loading: false,
          result: payload,
          countdown: 0,
          activeTab: payload?.post ? 'post' : payload?.insights?.length ? 'insights' : 'steps'
        } : h)));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete countdowns.current[historyId];
        return;
      }
      if (d.state === 'failed') {
        setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: d.failedReason || 'Job failed', countdown: 0 } : h)));
        const intId = pollingRefs.current[historyId];
        if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
        delete countdowns.current[historyId];
        return;
      }
      countdowns.current[historyId] = 5;
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: 60 } : h)));
      if (!pollingRefs.current[historyId]) startPolling(historyId, jobId);
    } catch (err: any) {
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: err.message, countdown: 0 } : h)));
      const intId = pollingRefs.current[historyId];
      if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
      delete countdowns.current[historyId];
    }
  };

  const retryRun = async (historyId: string) => {
    const item = history.find((h) => h.id === historyId);
    if (!item) return;

    const existing = pollingRefs.current[historyId];
    if (existing) {
      clearInterval(existing as unknown as number);
      delete pollingRefs.current[historyId];
    }
    delete countdowns.current[historyId];

    setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: true, result: null, error: null, countdown: 60 } : h)));

    try {
      const res = await fetch(`${API_URL}/agent/content-workflow`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: item.query,
          maxResults: item.maxResults,
          tone: item.tone,
          maxPostLength
        }),
      });
      const data = await res.json();
      if (!data.success) throw new Error(data.error || 'Failed to submit job');

      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, jobId: data.jobId } : h)));
      startPolling(historyId, data.jobId);
    } catch (err: any) {
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: err?.message || String(err), countdown: 0 } : h)));
    }
  };

  const toggleCollapse = (id: string) => {
    setHistory((s) => s.map((h) => (h.id === id ? { ...h, collapsed: !h.collapsed } : h)));
  };

  const setActiveTab = (id: string, tab: HistoryItem['activeTab']) => {
    setHistory((s) => s.map((h) => (h.id === id ? { ...h, activeTab: tab } : h)));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#0f172a', padding: '2rem 0' }}>
      <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '0 1rem' }}>
        <div style={{ marginBottom: '1rem' }}>
          <Link href="/" style={{ color: '#818cf8', textDecoration: 'none', fontWeight: 600 }}>← Back to Home</Link>
        </div>

        {/* Header */}
        <div style={{ backgroundColor: '#1e293b', borderRadius: 12, padding: '1.5rem', marginBottom: '1.5rem', border: '1px solid #334155' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
            <span style={{ fontSize: '2rem' }}>🚀</span>
            <h1 style={{ margin: 0, fontSize: '1.75rem', color: 'white' }}>Content Workflow</h1>
            <span style={{ background: '#7c3aed', color: 'white', padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 600 }}>Phase 4+5</span>
          </div>
          <p style={{ margin: 0, color: '#94a3b8' }}>
            Full pipeline: Research Query → Insight Extraction → LinkedIn Post Generation
          </p>

          {/* Settings */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16, marginTop: 20 }}>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#e2e8f0', marginBottom: 6 }}>Tone</label>
              <select
                value={tone}
                onChange={(e) => setTone(e.target.value as typeof tone)}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #475569', backgroundColor: '#0f172a', color: 'white' }}
              >
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="thought-leadership">Thought Leadership</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#e2e8f0', marginBottom: 6 }}>Max Results</label>
              <input
                type="number"
                min={1}
                max={20}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value))}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #475569', backgroundColor: '#0f172a', color: 'white' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13, color: '#e2e8f0', marginBottom: 6 }}>Max Post Length</label>
              <input
                type="number"
                min={100}
                max={3000}
                step={50}
                value={maxPostLength}
                onChange={(e) => setMaxPostLength(Number(e.target.value))}
                style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #475569', backgroundColor: '#0f172a', color: 'white' }}
              />
            </div>
          </div>
        </div>

        {/* History */}
        <div style={{ marginBottom: 100 }}>
          {history.map((h) => (
            <div key={h.id} style={{ marginBottom: 16 }}>
              {/* Header bar */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: '#1e293b',
                padding: '12px 16px',
                borderRadius: h.collapsed ? 12 : '12px 12px 0 0',
                border: '1px solid #334155',
                borderBottom: h.collapsed ? '1px solid #334155' : 'none'
              }}>
                <div style={{ cursor: 'pointer', flex: 1 }} onClick={() => toggleCollapse(h.id)}>
                  <div style={{ fontSize: 12, color: '#64748b', marginBottom: 2 }}>Query</div>
                  <div style={{ fontWeight: 700, color: 'white' }}>{h.query}</div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>
                    {h.timestamp.toLocaleString()} · {h.tone} tone · {h.maxResults} results
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {h.loading ? (
                    <>
                      <div style={{ fontSize: 13, color: '#818cf8', fontWeight: 700 }}>
                        {h.countdown && h.countdown > 0 ? `⏱ ${h.countdown}s` : 'Processing...'}
                      </div>
                      <button
                        onClick={() => checkNow(h.id, h.jobId)}
                        disabled={!h.jobId}
                        style={{ padding: '6px 12px', borderRadius: 6, background: '#312e81', border: 'none', color: '#a5b4fc', cursor: 'pointer' }}
                      >
                        Check now
                      </button>
                    </>
                  ) : (
                    <button
                      onClick={() => retryRun(h.id)}
                      style={{ padding: '6px 12px', borderRadius: 6, background: '#065f46', border: 'none', color: '#6ee7b7', cursor: 'pointer' }}
                    >
                      Retry
                    </button>
                  )}
                  <button
                    onClick={(e) => { e.stopPropagation(); toggleCollapse(h.id); }}
                    style={{
                      border: 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      fontSize: 20,
                      color: '#94a3b8',
                      padding: '4px 8px',
                    }}
                  >
                    {h.collapsed ? '▼' : '▲'}
                  </button>
                </div>
              </div>

              {/* Content */}
              {!h.collapsed && (
                <div style={{
                  backgroundColor: '#1e293b',
                  padding: 16,
                  borderRadius: '0 0 12px 12px',
                  border: '1px solid #334155',
                  borderTop: 'none'
                }}>
                  {/* Loading state */}
                  {h.loading && (
                    <div style={{ textAlign: 'center', padding: 20 }}>
                      <div style={{ fontSize: 32, marginBottom: 12 }}>⚙️</div>
                      <div style={{ fontWeight: 700, color: '#818cf8', marginBottom: 4 }}>Workflow running...</div>
                      {h.jobId && <div style={{ fontSize: 12, color: '#64748b', fontFamily: 'monospace' }}>Job: {h.jobId}</div>}
                    </div>
                  )}

                  {/* Error state */}
                  {h.error && (
                    <div style={{ background: '#450a0a', padding: 12, borderRadius: 8, borderLeft: '4px solid #dc2626' }}>
                      <div style={{ fontWeight: 700, color: '#fca5a5' }}>Error</div>
                      <div style={{ color: '#fecaca' }}>{h.error}</div>
                    </div>
                  )}

                  {/* Result */}
                  {h.result && (
                    <>
                      {/* Tabs */}
                      <div style={{ display: 'flex', gap: 4, marginBottom: 16, borderBottom: '1px solid #334155', paddingBottom: 8 }}>
                        {['steps', 'search', 'insights', 'post'].map((tab) => (
                          <button
                            key={tab}
                            onClick={() => setActiveTab(h.id, tab as HistoryItem['activeTab'])}
                            style={{
                              padding: '8px 16px',
                              borderRadius: '8px 8px 0 0',
                              border: 'none',
                              background: h.activeTab === tab ? '#334155' : 'transparent',
                              color: h.activeTab === tab ? 'white' : '#94a3b8',
                              cursor: 'pointer',
                              fontWeight: h.activeTab === tab ? 700 : 400,
                              textTransform: 'capitalize'
                            }}
                          >
                            {tab === 'steps' && '📋 '}
                            {tab === 'search' && '🔍 '}
                            {tab === 'insights' && '💡 '}
                            {tab === 'post' && '📝 '}
                            {tab}
                            {tab === 'search' && h.result.searchResults && ` (${h.result.searchResults.length})`}
                            {tab === 'insights' && h.result.insights && ` (${h.result.insights.length})`}
                          </button>
                        ))}
                      </div>

                      {/* Steps Tab */}
                      {h.activeTab === 'steps' && h.result.steps && (
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                            <span style={{ color: '#94a3b8' }}>Execution time:</span>
                            <span style={{ color: 'white', fontWeight: 600 }}>{h.result.executionTimeMs}ms</span>
                          </div>
                          {h.result.steps.map((step, idx) => (
                            <div
                              key={idx}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 12,
                                padding: '12px 16px',
                                background: '#0f172a',
                                borderRadius: 8,
                                marginBottom: 8,
                                border: '1px solid #334155'
                              }}
                            >
                              <span style={{ fontSize: 20 }}>
                                {step.status === 'completed' ? '✅' : step.status === 'failed' ? '❌' : step.status === 'running' ? '⏳' : '⏸️'}
                              </span>
                              <div style={{ flex: 1 }}>
                                <div style={{ color: 'white', fontWeight: 600 }}>{step.name}</div>
                                {step.error && <div style={{ color: '#f87171', fontSize: 13 }}>{step.error}</div>}
                              </div>
                              {step.durationMs !== undefined && (
                                <div style={{ color: '#64748b', fontSize: 13 }}>{step.durationMs}ms</div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      {/* Search Results Tab */}
                      {h.activeTab === 'search' && (
                        <div>
                          {h.result.searchResults && h.result.searchResults.length > 0 ? (
                            h.result.searchResults.map((r, idx) => (
                              <div
                                key={r.id || idx}
                                style={{
                                  padding: 16,
                                  background: '#0f172a',
                                  borderRadius: 8,
                                  marginBottom: 12,
                                  border: '1px solid #334155'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                  <div style={{ fontWeight: 700, color: 'white' }}>{r.documentTitle || `Document ${idx + 1}`}</div>
                                  <div style={{ display: 'flex', gap: 8 }}>
                                    <span style={{
                                      background: r.rankSource === 'hybrid' ? '#7c3aed' : r.rankSource === 'vector' ? '#0ea5e9' : '#f59e0b',
                                      color: 'white',
                                      padding: '2px 8px',
                                      borderRadius: 12,
                                      fontSize: 11
                                    }}>
                                      {r.rankSource}
                                    </span>
                                    <span style={{ color: '#10b981', fontWeight: 700, fontSize: 13 }}>
                                      {Math.round(r.score * 100)}%
                                    </span>
                                  </div>
                                </div>
                                <div style={{ color: '#cbd5e1', fontSize: 14, lineHeight: 1.6 }}>{r.content}</div>
                                {r.contextSummary && (
                                  <div style={{ color: '#64748b', fontSize: 13, marginTop: 8, fontStyle: 'italic' }}>
                                    {r.contextSummary}
                                  </div>
                                )}
                              </div>
                            ))
                          ) : (
                            <div style={{ color: '#64748b', textAlign: 'center', padding: 20 }}>No search results</div>
                          )}
                        </div>
                      )}

                      {/* Insights Tab */}
                      {h.activeTab === 'insights' && (
                        <div>
                          {h.result.insights && h.result.insights.length > 0 ? (
                            h.result.insights.map((insight, idx) => (
                              <div
                                key={insight.id || idx}
                                style={{
                                  padding: 16,
                                  background: '#0f172a',
                                  borderRadius: 8,
                                  marginBottom: 12,
                                  border: '1px solid #334155'
                                }}
                              >
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                                  <div style={{ fontWeight: 700, color: 'white', fontSize: 16 }}>{insight.claim}</div>
                                  <span style={{ color: '#10b981', fontWeight: 700 }}>
                                    {Math.round(insight.confidence * 100)}%
                                  </span>
                                </div>
                                {insight.summary && (
                                  <div style={{ color: '#cbd5e1', marginBottom: 12 }}>{insight.summary}</div>
                                )}
                                {insight.tags && insight.tags.length > 0 && (
                                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
                                    {insight.tags.map((tag) => (
                                      <span key={tag} style={{ background: '#312e81', color: '#a5b4fc', padding: '4px 10px', borderRadius: 12, fontSize: 12 }}>
                                        #{tag}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                {insight.evidence && insight.evidence.length > 0 && (
                                  <div style={{ marginTop: 12 }}>
                                    <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8, fontWeight: 600 }}>EVIDENCE</div>
                                    {insight.evidence.map((ev, eIdx) => (
                                      <div
                                        key={eIdx}
                                        style={{
                                          padding: 12,
                                          background: '#1e293b',
                                          borderRadius: 6,
                                          marginBottom: 6,
                                          borderLeft: '3px solid #7c3aed'
                                        }}
                                      >
                                        <div style={{ color: '#e2e8f0', fontSize: 13 }}>{ev.excerpt}</div>
                                        {ev.score !== undefined && (
                                          <div style={{ color: '#64748b', fontSize: 12, marginTop: 4 }}>
                                            Score: {Math.round(ev.score * 100)}%
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))
                          ) : (
                            <div style={{ color: '#64748b', textAlign: 'center', padding: 20 }}>No insights extracted</div>
                          )}
                        </div>
                      )}

                      {/* Post Tab */}
                      {h.activeTab === 'post' && (
                        <div>
                          {h.result.post ? (
                            <div style={{ background: '#0f172a', borderRadius: 8, border: '1px solid #334155', overflow: 'hidden' }}>
                              {/* Post header */}
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #334155' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                  <span style={{ fontSize: 24 }}>📱</span>
                                  <span style={{ color: 'white', fontWeight: 600 }}>LinkedIn Post Preview</span>
                                </div>
                                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                                  <span style={{ color: '#64748b', fontSize: 13 }}>{h.result.post.length} chars</span>
                                  <span style={{ background: '#334155', color: '#94a3b8', padding: '4px 10px', borderRadius: 12, fontSize: 12 }}>
                                    {h.result.post.tone}
                                  </span>
                                  <button
                                    onClick={() => copyToClipboard(h.result!.post!.post)}
                                    style={{ padding: '6px 12px', borderRadius: 6, background: '#7c3aed', border: 'none', color: 'white', cursor: 'pointer', fontSize: 13 }}
                                  >
                                    Copy
                                  </button>
                                </div>
                              </div>
                              {/* Post content */}
                              <div style={{ padding: 20 }}>
                                <div style={{
                                  color: 'white',
                                  fontSize: 15,
                                  lineHeight: 1.7,
                                  whiteSpace: 'pre-wrap',
                                  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                                }}>
                                  {h.result.post.post}
                                </div>
                                {h.result.post.hashtags && h.result.post.hashtags.length > 0 && (
                                  <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                    {h.result.post.hashtags.map((tag) => (
                                      <span key={tag} style={{ color: '#818cf8', fontWeight: 500 }}>{tag}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          ) : (
                            <div style={{ color: '#64748b', textAlign: 'center', padding: 20 }}>No post generated</div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input form - sticky at bottom */}
        <div style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: 'linear-gradient(transparent, #0f172a 20%)',
          padding: '40px 1rem 1rem',
        }}>
          <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
            <form
              onSubmit={(e) => { e.preventDefault(); submit(); }}
              style={{
                display: 'flex',
                gap: 8,
                background: '#1e293b',
                padding: 12,
                borderRadius: 12,
                border: '1px solid #334155',
                boxShadow: '0 -4px 20px rgba(0,0,0,0.3)'
              }}
            >
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter a research topic or question..."
                style={{
                  flex: 1,
                  padding: '12px 16px',
                  borderRadius: 8,
                  border: '1px solid #475569',
                  backgroundColor: '#0f172a',
                  color: 'white',
                  fontSize: 15
                }}
              />
              <button
                type="submit"
                disabled={!query.trim()}
                style={{
                  padding: '12px 24px',
                  borderRadius: 8,
                  background: query.trim() ? '#7c3aed' : '#334155',
                  color: 'white',
                  border: 'none',
                  fontWeight: 600,
                  cursor: query.trim() ? 'pointer' : 'not-allowed'
                }}
              >
                Generate Content
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

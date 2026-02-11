"use client";

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

interface InsightItem {
  id: string;
  title?: string;
  text: string;
}

interface AgentResultAny {
  insights?: InsightItem[];
  [k: string]: any;
}

interface HistoryItem {
  id: string;
  query: string;
  loading: boolean;
  result: AgentResultAny | null;
  error: string | null;
  jobId: string | null;
  countdown?: number;
  collapsed?: boolean;
  timestamp: Date;
}

export default function InsightExtractionAgentPage() {
  const [query, setQuery] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [minScorePercent, setMinScorePercent] = useState(50);
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
    const minScore = Math.max(0, Math.min(1, minScorePercent / 100));

    const item: HistoryItem = {
      id,
      query: query.trim(),
      loading: true,
      result: null,
      error: null,
      jobId: null,
      countdown: 60,
      collapsed: false,
      timestamp: new Date(),
    };

    setHistory((s) => [...s, item]);
    setQuery('');

    try {
      const res = await fetch(`${API_URL}/agent/insight-extraction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: item.query, maxResults, minScore }),
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
    const intervalSec = 60;
    countdowns.current[historyId] = intervalSec;
    setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: intervalSec } : h)));

    // Clear any existing interval for this history item to avoid duplicate pollers
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
          // normalize payload: support arrays, numeric-indexed objects, and { insights: [] }
          const payload = d.returnvalue || d.result || d;
          console.debug('[InsightExtractionUI] received job payload', d);
          let normalized: any;
          if (Array.isArray(payload)) {
            normalized = { insights: payload };
          } else if (payload && typeof payload === 'object') {
            if (Array.isArray(payload.insights)) {
              normalized = payload;
            } else {
              const keys = Object.keys(payload || {});
              const isNumericMap = keys.length > 0 && keys.every((k) => /^\d+$/.test(k));
              if (isNumericMap) normalized = { insights: keys.map((k) => (payload as any)[k]) };
              else normalized = payload;
            }
          } else {
            normalized = payload;
          }
          console.debug('[InsightExtractionUI] normalized insights to render', normalized?.insights ?? normalized);
          setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, result: normalized, countdown: 0 } : h)));
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
        console.debug('[InsightExtractionUI] received job payload (checkNow)', d);
        let normalized: any;
        if (Array.isArray(payload)) {
          normalized = { insights: payload };
        } else if (payload && typeof payload === 'object') {
          if (Array.isArray(payload.insights)) {
            normalized = payload;
          } else {
            const keys = Object.keys(payload || {});
            const isNumericMap = keys.length > 0 && keys.every((k) => /^\d+$/.test(k));
            if (isNumericMap) normalized = { insights: keys.map((k) => (payload as any)[k]) };
            else normalized = payload;
          }
        } else {
          normalized = payload;
        }
        console.debug('[InsightExtractionUI] normalized insights to render (checkNow)', normalized?.insights ?? normalized);
        setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, result: normalized, countdown: 0 } : h)));
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

      // still running -> reset countdown
      countdowns.current[historyId] = 60;
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, countdown: 60 } : h)));
      if (!pollingRefs.current[historyId]) startPolling(historyId, jobId);
    } catch (err: any) {
      setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, error: err.message, countdown: 0 } : h)));
      const intId = pollingRefs.current[historyId];
      if (intId) { clearInterval(intId); delete pollingRefs.current[historyId]; }
      delete countdowns.current[historyId];
    }
  };

  // Retry by re-running the agent for an existing history item (keeps same header)
  const retryRun = async (historyId: string) => {
    const item = history.find((h) => h.id === historyId);
    if (!item) return;

    // Clear any existing poller for this history item before retrying
    const existing = pollingRefs.current[historyId];
    if (existing) {
      clearInterval(existing as unknown as number);
      delete pollingRefs.current[historyId];
    }
    delete countdowns.current[historyId];

    // Reset the history item state
    setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: true, result: null, error: null, countdown: 60 } : h)));

    try {
      const minScore = Math.max(0, Math.min(1, minScorePercent / 100));
      const res = await fetch(`${API_URL}/agent/insight-extraction`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: item.query, maxResults, minScore }),
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

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f7fafc', padding: '2rem 0' }}>
      <div style={{ maxWidth: '900px', margin: '0 auto', padding: '0 1rem' }}>
        <div style={{ marginBottom: '1rem' }}>
          <Link href="/" style={{ color: '#4f46e5', textDecoration: 'none', fontWeight: 600 }}>← Back to Home</Link>
        </div>

        <div style={{ backgroundColor: 'white', borderRadius: 8, padding: '1.25rem', marginBottom: '1rem', boxShadow: '0 1px 3px rgba(0,0,0,0.06)' }}>
          <h2 style={{ margin: 0, fontSize: '1.5rem' }}>🔎 Insight Extraction Agent</h2>
          <p style={{ marginTop: 6, color: '#6b7280' }}>Extract concise insights from your corpus. Submits a background job and polls until complete.</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>Max Results</label>
              <input type="number" min={1} max={50} value={maxResults} onChange={(e) => setMaxResults(Number(e.target.value))} className="input" />
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>Min Score: {minScorePercent}%</label>
              <input type="range" min={0} max={100} step={1} value={minScorePercent} onChange={(e) => setMinScorePercent(Number(e.target.value))} />
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          {history.map((h) => (
            <div key={h.id} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff', padding: 12, borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ cursor: 'pointer' }} onClick={() => toggleCollapse(h.id)}>
                  <div style={{ fontSize: 13, color: '#6b7280' }}>You asked</div>
                  <div style={{ fontWeight: 700 }}>{h.query}</div>
                  <div style={{ fontSize: 12, color: '#9ca3af' }}>{h.timestamp.toLocaleString()}</div>
                </div>

                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  {h.loading ? (
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <div style={{ fontSize: 13, color: '#4f46e5', fontWeight: 700 }}>{h.countdown && h.countdown > 0 ? `⏱ ${h.countdown}s` : 'Waiting...'}</div>
                      <button onClick={() => checkNow(h.id, h.jobId)} disabled={!h.jobId} style={{ padding: '6px 10px', borderRadius: 6, background: '#eef2ff', border: '1px solid #c7d2fe', color: '#3730a3' }}>Check now</button>
                    </div>
                  ) : (
                    <button onClick={() => retryRun(h.id)} style={{ padding: '6px 10px', borderRadius: 6, background: '#ecfdf5', border: '1px solid #bbf7d0', color: '#065f46' }}>Retry</button>
                  )}

                  {/* Collapse/expand control: larger and right-aligned */}
                  <button
                    aria-label={h.collapsed ? 'Expand details' : 'Collapse details'}
                    onClick={(e) => { e.stopPropagation(); toggleCollapse(h.id); }}
                    style={{
                      border: 'none',
                      background: h.collapsed ? '#d1fae5' : 'transparent',
                      cursor: 'pointer',
                      fontSize: 26,
                      lineHeight: 1,
                      padding: '8px 12px',
                      borderRadius: 8,
                      color: h.collapsed ? '#065f46' : '#374151',
                      marginLeft: 8
                    }}
                  >
                    {h.collapsed ? '▾' : '▴'}
                  </button>
                </div>
              </div>

              {!h.collapsed && (
                <div style={{ backgroundColor: 'white', padding: 12, borderRadius: 8, marginTop: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                  {h.loading && (
                    <div style={{ marginBottom: 8 }}>
                      <div style={{ fontWeight: 700, color: '#4f46e5' }}>Agent running…</div>
                      {h.jobId && <div style={{ fontSize: 12, color: '#6b7280', fontFamily: 'monospace' }}>Job ID: {h.jobId}</div>}
                    </div>
                  )}

                  {h.error && (
                    <div style={{ background: '#fff1f2', padding: 8, borderRadius: 6, borderLeft: '4px solid #ef4444', marginBottom: 8 }}>
                      <div style={{ fontWeight: 700, color: '#b91c1c' }}>Error</div>
                      <div style={{ color: '#7f1d1d' }}>{h.error}</div>
                    </div>
                  )}

                  {h.result && (
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                        <div style={{ fontSize: 18 }}>✅</div>
                        <div style={{ fontWeight: 700, color: '#0ea5a4' }}>Insights</div>
                      </div>

                      {Array.isArray(h.result.insights) ? (
                        h.result.insights.map((ins: any, idx: number) => (
                          <div key={ins.id ?? idx} style={{ padding: 12, borderRadius: 6, background: '#f8fafc', marginBottom: 8 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <div style={{ fontWeight: 700 }}>{ins.claim ?? ins.summary ?? `Insight ${idx + 1}`}</div>
                              <div style={{ fontSize: 12, color: '#6b7280', fontWeight: 700 }}>{ins.confidence !== undefined ? `${Math.round(ins.confidence * 100)}%` : ''}</div>
                            </div>

                            {ins.summary && <div style={{ color: '#374151', marginTop: 6 }}>{ins.summary}</div>}

                            {ins.tags && ins.tags.length > 0 && (
                              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {ins.tags.map((t: string) => (
                                  <span key={t} style={{ background: '#eef2ff', color: '#3730a3', padding: '4px 8px', borderRadius: 6, fontSize: 12 }}>{t}</span>
                                ))}
                              </div>
                            )}

                            {ins.evidence && ins.evidence.length > 0 && (
                              <div style={{ marginTop: 10 }}>
                                <div style={{ fontWeight: 700, marginBottom: 6 }}>Evidence</div>
                                {ins.evidence.map((ev: any, eIdx: number) => (
                                  <div key={ev.chunkId ?? eIdx} style={{ padding: 8, borderRadius: 6, background: '#fff', border: '1px solid #e6eef8', marginBottom: 6 }}>
                                    <div style={{ fontSize: 13, color: '#0f172a', marginBottom: 4 }}>{ev.excerpt}</div>
                                    <div style={{ fontSize: 12, color: '#475569' }}>
                                      Chunk: {ev.chunkIndex ?? '-'} · Doc: {ev.documentId ? ev.documentId.slice(0, 8) : '-'} · Score: {ev.score !== undefined ? `${Math.round(ev.score * 100)}%` : 'N/A'}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        ))
                      ) : (
                        <div style={{ background: '#f3f4f6', padding: 10, borderRadius: 6 }}>
                          <pre style={{ margin: 0, overflowX: 'auto' }}>{JSON.stringify(h.result, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ position: 'sticky', bottom: 12, background: 'white', padding: 12, borderRadius: 8, boxShadow: '0 6px 18px rgba(0,0,0,0.06)' }}>
          <form onSubmit={(e) => { e.preventDefault(); submit(); }} style={{ display: 'flex', gap: 8 }}>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask for insights..." className="input" style={{ flex: 1 }} />
            <button type="submit" disabled={!query.trim()} style={{ padding: '8px 12px', borderRadius: 8, background: '#4f46e5', color: 'white' }}>Extract</button>
          </form>
        </div>
      </div>
    </div>
  );
}

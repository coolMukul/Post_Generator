"use client";

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

interface HistoryItem {
  id: string;
  title: string;
  insightsText: string;
  tone: string;
  maxLength: number;
  loading: boolean;
  result: any | null;
  error: string | null;
  jobId: string | null;
  countdown?: number;
  collapsed?: boolean;
  timestamp: Date;
}

export default function LinkedInPostAgentPage() {
  const [title, setTitle] = useState('');
  const [insightsText, setInsightsText] = useState('');
  const [tone, setTone] = useState('professional');
  const [maxLength, setMaxLength] = useState(700);
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
    if (!insightsText.trim() && !title.trim()) return;
    const id = Date.now().toString();

    const item: HistoryItem = {
      id,
      title: title.trim(),
      insightsText: insightsText.trim(),
      tone,
      maxLength,
      loading: true,
      result: null,
      error: null,
      jobId: null,
      countdown: 60,
      collapsed: false,
      timestamp: new Date(),
    };

    setHistory((s) => [...s, item]);
    setInsightsText('');
    setTitle('');

    try {
      // Parse insights: allow newline-separated simple lines
      const insights = insightsText.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).slice(0, 10).map((l) => ({ claim: l }));

      const res = await fetch(`${API_URL}/agent/linkedin-post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: item.title, insights, tone: item.tone, maxLength: item.maxLength }),
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
          console.debug('[LinkedInPostUI] received job payload', d);
          setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, result: payload, countdown: 0 } : h)));
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
        console.debug('[LinkedInPostUI] received job payload (checkNow)', d);
        setHistory((s) => s.map((h) => (h.id === historyId ? { ...h, loading: false, result: payload, countdown: 0 } : h)));
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
      const insights = item.insightsText.split(/\r?\n/).map((l) => l.trim()).filter(Boolean).slice(0, 10).map((l) => ({ claim: l }));
      const res = await fetch(`${API_URL}/agent/linkedin-post`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: item.title, insights, tone: item.tone, maxLength: item.maxLength }),
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
          <h2 style={{ margin: 0, fontSize: '1.5rem' }}>✍️ LinkedIn Post Generator</h2>
          <p style={{ marginTop: 6, color: '#6b7280' }}>Generate a LinkedIn-ready post from your insights. Uses an LLM when available.</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 }}>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>Tone</label>
              <select value={tone} onChange={(e) => setTone(e.target.value)} className="input">
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="thought-leadership">Thought leadership</option>
              </select>
            </div>
            <div>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13 }}>Max length</label>
              <input type="number" min={100} max={2000} value={maxLength} onChange={(e) => setMaxLength(Number(e.target.value))} className="input" />
            </div>
          </div>
        </div>

        <div style={{ marginBottom: 16 }}>
          {history.map((h) => (
            <div key={h.id} style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', backgroundColor: '#fff', padding: 12, borderRadius: 8, boxShadow: '0 1px 2px rgba(0,0,0,0.04)' }}>
                <div style={{ cursor: 'pointer' }} onClick={() => toggleCollapse(h.id)}>
                  <div style={{ fontSize: 13, color: '#6b7280' }}>Post</div>
                  <div style={{ fontWeight: 700 }}>{h.title || (h.insightsText ? h.insightsText.split(/\r?\n/)[0] : 'Untitled')}</div>
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
                        <div style={{ fontWeight: 700, color: '#0ea5a4' }}>Generated Post</div>
                      </div>

                      <div style={{ padding: 12, borderRadius: 6, background: '#f8fafc', marginBottom: 8 }}>
                        <div style={{ whiteSpace: 'pre-wrap', color: '#374151' }}>{h.result.post ?? JSON.stringify(h.result, null, 2)}</div>

                        {h.result.hashtags && Array.isArray(h.result.hashtags) && h.result.hashtags.length > 0 && (
                          <div style={{ marginTop: 10, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            {h.result.hashtags.map((t: string) => (
                              <span key={t} style={{ background: '#eef2ff', color: '#3730a3', padding: '4px 8px', borderRadius: 6, fontSize: 12 }}>{t}</span>
                            ))}
                          </div>
                        )}

                        <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>Length: {h.result.length ?? (h.result.post ? h.result.post.length : '-')}</div>

                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        <div style={{ position: 'sticky', bottom: 12, background: 'white', padding: 12, borderRadius: 8, boxShadow: '0 6px 18px rgba(0,0,0,0.06)' }}>
          <form onSubmit={(e) => { e.preventDefault(); submit(); }} style={{ display: 'grid', gap: 8 }}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Optional title" className="input" />
            <textarea value={insightsText} onChange={(e) => setInsightsText(e.target.value)} placeholder="Paste insights (one per line) or a short list" rows={4} className="input" />
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" disabled={!insightsText.trim() && !title.trim()} style={{ padding: '8px 12px', borderRadius: 8, background: '#4f46e5', color: 'white' }}>Generate</button>
              <div style={{ alignSelf: 'center', color: '#6b7280' }}>Tone: {tone} · Max {maxLength} chars</div>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

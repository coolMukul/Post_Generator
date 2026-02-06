'use client';

import React, { useEffect, useState, useRef } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3101';

type ChatMessage = {
  id: string;
  role: 'user' | 'agent';
  text: string;
};

export default function ResearchQueryPage() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [countdown, setCountdown] = useState<number>(60);
  const countdownRef = useRef<number | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    // clear timers on unmount
    return () => {
      if (countdownRef.current) window.clearInterval(countdownRef.current);
      if (pollIntervalRef.current) window.clearInterval(pollIntervalRef.current);
    };
  }, []);

  useEffect(() => {
    if (!jobId) return;

    // start countdown every second
    setCountdown(60);
    if (countdownRef.current) window.clearInterval(countdownRef.current);
    countdownRef.current = window.setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : 60));
    }, 1000) as unknown as number;

    // poll every 60s
    const poll = async () => {
      try {
        const res = await fetch(`${API_URL}/queue/jobs/${jobId}`);
        if (res.ok) {
          const data = await res.json();
          setJobStatus(data);

          if (data.state === 'completed' || data.state === 'failed') {
            // stop polling and countdown
            if (pollIntervalRef.current) window.clearInterval(pollIntervalRef.current);
            if (countdownRef.current) window.clearInterval(countdownRef.current);
            setCountdown(0);

            if (data.state === 'completed' && data.returnvalue) {
              const replyText = data.returnvalue.summary || JSON.stringify(data.returnvalue);
              const msg: ChatMessage = { id: `agent-${Date.now()}`, role: 'agent', text: replyText };
              setMessages((m) => [...m, msg]);
            }
          }
        }
      } catch (err) {
        console.error('Poll error', err);
      }
    };

    // immediate poll then interval
    poll();
    pollIntervalRef.current = window.setInterval(poll, 60 * 1000) as unknown as number;

    return () => {
      if (pollIntervalRef.current) window.clearInterval(pollIntervalRef.current);
      if (countdownRef.current) window.clearInterval(countdownRef.current);
    };
  }, [jobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input) return;
    setLoading(true);
    setJobId(null);
    setJobStatus(null);

    const userMsg: ChatMessage = { id: `user-${Date.now()}`, role: 'user', text: input };
    setMessages((m) => [...m, userMsg]);

    try {
      const res = await fetch(`${API_URL}/agent/research-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: input, projectKey: 'researchpaper', maxResults: 10, minScore: 0.01 }),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      setJobId(data.jobId);
      setLoading(false);
      setInput('');
    } catch (err: any) {
      setLoading(false);
      const errMsg: ChatMessage = { id: `err-${Date.now()}`, role: 'agent', text: `Error: ${err.message}` };
      setMessages((m) => [...m, errMsg]);
    }
  };

  return (
    <div className="container" style={{ maxWidth: 900, padding: '2rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontWeight: 600 }}>← Back</Link>
      </div>

      <div className="card">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Research Query Agent</h1>
        <p style={{ color: '#666' }}>Type a question; the agent will search the research corpus and return findings.</p>

        <div style={{ marginTop: '1rem', marginBottom: '1rem' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              className="input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about the research corpus..."
              style={{ flex: 1 }}
            />
            <button className="btn btn-primary" type="submit" disabled={loading}>{loading ? '⏳' : 'Ask'}</button>
          </form>
        </div>

        <div style={{ minHeight: 200, border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, background: '#fff' }}>
          {messages.length === 0 && <div style={{ color: '#666' }}>No messages yet — ask a question above.</div>}
          {messages.map(m => (
            <div key={m.id} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: '#999' }}>{m.role === 'user' ? 'You' : 'Agent'}</div>
              <div style={{ whiteSpace: 'pre-wrap', marginTop: 4 }}>{m.text}</div>
            </div>
          ))}
        </div>

        {jobId && (
          <div style={{ marginTop: 12, padding: 12, background: '#f8fafc', borderRadius: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <div>Job ID: <code>{jobId}</code></div>
              <div>Next poll in: <strong>{countdown}s</strong></div>
            </div>
            {jobStatus && (
              <div style={{ marginTop: 8, fontSize: 13 }}>
                <div><strong>Status:</strong> {jobStatus.state}</div>
                {jobStatus.progress !== undefined && (<div><strong>Progress:</strong> {jobStatus.progress}%</div>)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

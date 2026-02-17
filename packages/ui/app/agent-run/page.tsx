'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';
const POLL_INTERVAL = 5000;

interface AgentInfo {
  name: string;
  version: string;
  description: string;
  tools: string[];
  registered: boolean;
}

interface RunEntry {
  jobId: string;
  agentName: string;
  status: 'active' | 'completed' | 'failed';
  result: Record<string, unknown> | null;
  error: string | null;
  startTime: string | null;
  endTime: string | null;
}

export default function AgentRunPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [queryInput, setQueryInput] = useState('');
  const [searchMode, setSearchMode] = useState('hybrid');
  const [limit, setLimit] = useState(10);
  const [minScore, setMinScore] = useState(0);
  const [runs, setRuns] = useState<RunEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [agentsLoading, setAgentsLoading] = useState(true);
  const [runType, setRunType] = useState<'agent' | 'pipeline'>('agent');

  useEffect(() => {
    fetch(`${API_URL}/agent/list`)
      .then(res => res.json())
      .then(data => {
        setAgents(data.agents || []);
        if (data.agents?.length > 0) {
          setSelectedAgent(data.agents[0].name);
        }
      })
      .catch(err => console.error('Failed to load agents:', err))
      .finally(() => setAgentsLoading(false));
  }, []);

  const pollJob = useCallback((jobId: string, agentName: string) => {
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_URL}/queue/jobs/${jobId}`);
        const data = await res.json();

        setRuns(prev => prev.map(r => {
          if (r.jobId !== jobId) return r;
          return {
            ...r,
            status: data.state,
            result: data.returnvalue || null,
            error: data.failedReason || null,
            endTime: data.endTime || null,
          };
        }));

        if (data.state === 'completed' || data.state === 'failed') {
          clearInterval(interval);
        }
      } catch (err) {
        console.error('Poll error:', err);
      }
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, []);

  const submitAgentRun = async () => {
    if (!queryInput.trim()) return;
    setLoading(true);

    try {
      let res: Response;
      let jobId: string;
      let agentName: string;

      if (runType === 'pipeline') {
        res = await fetch(`${API_URL}/content/pipeline`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: queryInput,
            searchMode,
            limit,
            minScore: minScore / 100,
          }),
        });
        const data = await res.json();
        jobId = data.jobId;
        agentName = 'ContentPipeline';
      } else {
        res = await fetch(`${API_URL}/agent/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            agentName: selectedAgent,
            input: {
              query: queryInput,
              search_mode: searchMode,
              limit,
              min_score: minScore / 100,
            },
          }),
        });
        const data = await res.json();
        jobId = data.jobId;
        agentName = data.agentName;
      }

      const entry: RunEntry = {
        jobId,
        agentName,
        status: 'active',
        result: null,
        error: null,
        startTime: new Date().toISOString(),
        endTime: null,
      };

      setRuns(prev => [entry, ...prev]);
      pollJob(jobId, agentName);
    } catch (err) {
      console.error('Submit error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container" style={{ maxWidth: '1000px', margin: '0 auto', padding: '2rem' }}>
      <header style={{ marginBottom: '2rem' }}>
        <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontSize: '0.875rem' }}>
          &larr; Back to Dashboard
        </Link>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginTop: '0.5rem', color: 'white' }}>
          Agent Run
        </h1>
        <p style={{ color: '#999', fontSize: '0.875rem' }}>
          Phase 4+5: Submit agent runs and content pipeline jobs
        </p>
      </header>

      {/* Run Type Selector */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1.5rem', backgroundColor: '#1a1a2e', borderRadius: '0.75rem', border: '1px solid #333' }}>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
          <button
            onClick={() => setRunType('agent')}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '0.5rem',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: runType === 'agent' ? '#667eea' : '#2a2a3e',
              color: 'white',
            }}
          >
            Agent Run
          </button>
          <button
            onClick={() => setRunType('pipeline')}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '0.5rem',
              border: 'none',
              cursor: 'pointer',
              fontWeight: '600',
              backgroundColor: runType === 'pipeline' ? '#667eea' : '#2a2a3e',
              color: 'white',
            }}
          >
            Content Pipeline
          </button>
        </div>

        {/* Agent Selector (only for agent runs) */}
        {runType === 'agent' && (
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#ccc', fontSize: '0.875rem', fontWeight: '600' }}>
              Agent
            </label>
            {agentsLoading ? (
              <p style={{ color: '#999' }}>Loading agents...</p>
            ) : agents.length === 0 ? (
              <p style={{ color: '#f87171' }}>No agents available. Start the API server.</p>
            ) : (
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '0.5rem',
                  border: '1px solid #444',
                  backgroundColor: '#16162a',
                  color: 'white',
                  fontSize: '0.875rem',
                }}
              >
                {agents.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name} v{a.version} — {a.description.slice(0, 60)}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}

        {/* Query Input */}
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#ccc', fontSize: '0.875rem', fontWeight: '600' }}>
            Query
          </label>
          <textarea
            value={queryInput}
            onChange={(e) => setQueryInput(e.target.value)}
            placeholder="Enter your research query..."
            rows={3}
            style={{
              width: '100%',
              padding: '0.75rem',
              borderRadius: '0.5rem',
              border: '1px solid #444',
              backgroundColor: '#16162a',
              color: 'white',
              fontSize: '0.875rem',
              resize: 'vertical',
            }}
          />
        </div>

        {/* Parameters */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: '#ccc', fontSize: '0.75rem' }}>
              Search Mode
            </label>
            <select
              value={searchMode}
              onChange={(e) => setSearchMode(e.target.value)}
              style={{ width: '100%', padding: '0.5rem', borderRadius: '0.375rem', border: '1px solid #444', backgroundColor: '#16162a', color: 'white', fontSize: '0.875rem' }}
            >
              <option value="hybrid">Hybrid</option>
              <option value="vector">Vector</option>
              <option value="keyword">Keyword</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: '#ccc', fontSize: '0.75rem' }}>
              Max Results: {limit}
            </label>
            <input
              type="range"
              min={1}
              max={50}
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.25rem', color: '#ccc', fontSize: '0.75rem' }}>
              Min Score: {minScore}%
            </label>
            <input
              type="range"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(Number(e.target.value))}
              style={{ width: '100%' }}
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          onClick={submitAgentRun}
          disabled={loading || !queryInput.trim()}
          style={{
            width: '100%',
            padding: '0.75rem',
            borderRadius: '0.5rem',
            border: 'none',
            backgroundColor: loading ? '#4a5568' : '#667eea',
            color: 'white',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? 'Submitting...' : runType === 'pipeline' ? 'Run Content Pipeline' : `Run ${selectedAgent}`}
        </button>
      </div>

      {/* Run History */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: '600', marginBottom: '1rem', color: 'white' }}>
          Run History
        </h2>
        {runs.length === 0 ? (
          <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#999', backgroundColor: '#1a1a2e', borderRadius: '0.75rem', border: '1px solid #333' }}>
            No runs yet. Submit an agent run above.
          </div>
        ) : (
          runs.map((run) => (
            <div
              key={run.jobId}
              className="card"
              style={{
                marginBottom: '1rem',
                padding: '1.25rem',
                backgroundColor: '#1a1a2e',
                borderRadius: '0.75rem',
                border: `1px solid ${run.status === 'completed' ? '#10b981' : run.status === 'failed' ? '#ef4444' : '#667eea'}`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                <div>
                  <span style={{ fontWeight: '600', color: 'white' }}>{run.agentName}</span>
                  <span style={{ marginLeft: '0.75rem', fontSize: '0.75rem', color: '#999' }}>
                    {run.jobId.slice(0, 8)}...
                  </span>
                </div>
                <span
                  style={{
                    padding: '0.25rem 0.75rem',
                    borderRadius: '1rem',
                    fontSize: '0.75rem',
                    fontWeight: '600',
                    backgroundColor:
                      run.status === 'completed' ? '#10b981' :
                      run.status === 'failed' ? '#ef4444' : '#667eea',
                    color: 'white',
                  }}
                >
                  {run.status === 'active' ? 'Running...' : run.status}
                </span>
              </div>

              {run.startTime && (
                <p style={{ fontSize: '0.75rem', color: '#999', marginBottom: '0.5rem' }}>
                  Started: {new Date(run.startTime).toLocaleString()}
                  {run.endTime && ` | Ended: ${new Date(run.endTime).toLocaleString()}`}
                </p>
              )}

              {run.status === 'failed' && run.error && (
                <div style={{ padding: '0.75rem', backgroundColor: '#2d1515', borderRadius: '0.375rem', color: '#f87171', fontSize: '0.875rem', marginTop: '0.5rem' }}>
                  Error: {run.error}
                </div>
              )}

              {run.status === 'completed' && run.result && (
                <div style={{ marginTop: '0.75rem' }}>
                  {/* Show key fields from agent result */}
                  {run.result.output && typeof run.result.output === 'object' && (
                    <div>
                      {(run.result.output as Record<string, unknown>).findings && (
                        <div style={{ marginBottom: '0.75rem' }}>
                          <h4 style={{ color: '#10b981', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.25rem' }}>Findings</h4>
                          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#ccc' }}>
                            {((run.result.output as Record<string, unknown>).findings as string[]).slice(0, 5).map((f, i) => (
                              <li key={i} style={{ marginBottom: '0.25rem' }}>{f}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(run.result.output as Record<string, unknown>).confidence !== undefined && (
                        <p style={{ fontSize: '0.8rem', color: '#999' }}>
                          Confidence: {((run.result.output as Record<string, unknown>).confidence as number * 100).toFixed(1)}%
                        </p>
                      )}
                    </div>
                  )}

                  {/* Show draft from content pipeline */}
                  {run.result.draft && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <h4 style={{ color: '#667eea', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.25rem' }}>Generated Draft</h4>
                      <div style={{ padding: '0.75rem', backgroundColor: '#16162a', borderRadius: '0.375rem', fontSize: '0.8rem', color: '#ccc', whiteSpace: 'pre-wrap' }}>
                        {run.result.draft as string}
                      </div>
                    </div>
                  )}

                  {run.result.insights && Array.isArray(run.result.insights) && (run.result.insights as string[]).length > 0 && (
                    <div style={{ marginBottom: '0.75rem' }}>
                      <h4 style={{ color: '#06b6d4', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.25rem' }}>Insights</h4>
                      <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: '#ccc' }}>
                        {(run.result.insights as string[]).slice(0, 5).map((ins, i) => (
                          <li key={i} style={{ marginBottom: '0.25rem' }}>{ins}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Expandable JSON */}
                  <details style={{ marginTop: '0.5rem' }}>
                    <summary style={{ color: '#667eea', cursor: 'pointer', fontSize: '0.8rem' }}>
                      View full JSON
                    </summary>
                    <pre style={{ padding: '0.75rem', backgroundColor: '#16162a', borderRadius: '0.375rem', fontSize: '0.7rem', color: '#999', overflow: 'auto', maxHeight: '300px', marginTop: '0.5rem' }}>
                      {JSON.stringify(run.result, null, 2)}
                    </pre>
                  </details>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

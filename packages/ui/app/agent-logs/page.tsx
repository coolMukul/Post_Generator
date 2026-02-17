'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

interface AgentInfo {
  name: string;
  version: string;
  description: string;
  tools: string[];
  registered: boolean;
}

interface LogEntry {
  id: string;
  timestamp: string;
  sender: string;
  recipient: string[];
  channel: string;
  related_task_id: string | null;
  related_job_id: string | null;
  summary: string;
  message: string;
  attachments: string[];
  follow_up_required: boolean;
  follow_up_actions: string[];
  privacy: string;
}

export default function AgentLogsPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [logEntries, setLogEntries] = useState<LogEntry[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [expandedEntries, setExpandedEntries] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch(`${API_URL}/agent/list`)
      .then(res => res.json())
      .then(data => setAgents(data.agents || []))
      .catch(err => console.error('Failed to load agents:', err));
  }, []);

  useEffect(() => {
    const sampleEntries: LogEntry[] = [
      {
        id: 'c0a1b2c3-d4e5-4f6a-8b7c-9d0e1f2a3b4c',
        timestamp: '2026-02-17T10:00:00Z',
        sender: 'Coordinator',
        recipient: ['EngineerAgent', 'UIAgent', 'TODOManagerAgent', 'ResearchAgent'],
        channel: 'coordinator',
        related_task_id: null,
        related_job_id: null,
        summary: 'Phase 4+5 kickoff: agent framework, workflow nodes, and UI for agent runs.',
        message: 'Coordinator decomposes Phase 4 (Agent Framework & Core Tools) and Phase 5 (Multi-Stage Content Agents) into task assignments. Phase 3 hybrid_retrieve is reused via POST /search/submit and GET /queue/jobs/{job_id}.',
        attachments: [
          'mukDocs/agent-manifests/ResearchAgent.manifest.json',
          'mukDocs/agent-manifests/EngineerAgent.manifest.json',
          'mukDocs/agent-manifests/UIAgent.manifest.json',
          'mukDocs/agent-manifests/TODOManagerAgent.manifest.json',
        ],
        follow_up_required: true,
        follow_up_actions: [
          'EngineerAgent: Create agent manifest templates',
          'EngineerAgent: Implement agent registry skeleton',
          'UIAgent: Build agent run and logs UI pages',
        ],
        privacy: 'public',
      },
      {
        id: 'a1b2c3d4-0001-4f5a-8b6c-000000000001',
        timestamp: '2026-02-17T10:05:00Z',
        sender: 'EngineerAgent',
        recipient: ['Coordinator'],
        channel: 'coordinator',
        related_task_id: '7a9f4b2c-1d3e-4f5a-8b6c-0d1e2f3a4b5c',
        related_job_id: null,
        summary: 'Agent manifests created in mukDocs/agent-manifests/',
        message: 'Created 4 agent manifest JSON files: ResearchAgent, EngineerAgent, UIAgent, TODOManagerAgent. Each includes name, version, tools, input/output schemas, time_budget.',
        attachments: [],
        follow_up_required: false,
        follow_up_actions: [],
        privacy: 'public',
      },
      {
        id: 'a1b2c3d4-0002-4f5a-8b6c-000000000002',
        timestamp: '2026-02-17T10:15:00Z',
        sender: 'EngineerAgent',
        recipient: ['Coordinator'],
        channel: 'coordinator',
        related_task_id: 'a1b2c3d4-5e6f-7a8b-9c0d-1e2f3a4b5c6d',
        related_job_id: null,
        summary: 'Agent registry and base agent class implemented.',
        message: 'Implemented AgentRegistry (load_manifests, register_agent, create_agent) and BaseAgent (abstract execute, run lifecycle, tool registration). ResearchAgent is the first concrete implementation.',
        attachments: ['packages/workers/src/agents/registry.py', 'packages/workers/src/agents/base_agent.py'],
        follow_up_required: false,
        follow_up_actions: [],
        privacy: 'public',
      },
      {
        id: 'a1b2c3d4-0003-4f5a-8b6c-000000000003',
        timestamp: '2026-02-17T10:30:00Z',
        sender: 'EngineerAgent',
        recipient: ['Coordinator'],
        channel: 'coordinator',
        related_task_id: 'd4e5f6a7-8b9c-0d1e-2f3a-4b5c6d7e8f9a',
        related_job_id: null,
        summary: 'Phase 5 workflow nodes and content pipeline implemented.',
        message: 'Built insight_extraction, draft_generation, citation_validation nodes and LangGraph StateGraph orchestrator. Pipeline: retrieval -> insight_extraction -> draft_generation -> citation_validation.',
        attachments: ['packages/workers/src/agents/workflows/content_pipeline.py'],
        follow_up_required: false,
        follow_up_actions: [],
        privacy: 'public',
      },
      {
        id: 'a1b2c3d4-0004-4f5a-8b6c-000000000004',
        timestamp: '2026-02-17T10:45:00Z',
        sender: 'UIAgent',
        recipient: ['Coordinator'],
        channel: 'coordinator',
        related_task_id: 'e5f6a7b8-9c0d-1e2f-3a4b-5c6d7e8f9a0b',
        related_job_id: null,
        summary: 'Agent run and logs UI pages implemented.',
        message: 'Created /agent-run page (submit agent runs + content pipeline, poll results, show findings/insights/draft) and /agent-logs page (display team interaction entries with filtering).',
        attachments: ['packages/ui/app/agent-run/page.tsx', 'packages/ui/app/agent-logs/page.tsx'],
        follow_up_required: false,
        follow_up_actions: [],
        privacy: 'public',
      },
    ];
    setLogEntries(sampleEntries);
  }, []);

  const toggleExpand = (id: string) => {
    setExpandedEntries(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const filteredEntries = selectedAgent === 'all'
    ? logEntries
    : logEntries.filter(e => e.sender === selectedAgent || e.recipient.includes(selectedAgent));

  const channelColors: Record<string, string> = {
    coordinator: '#667eea',
    direct: '#10b981',
    job: '#f59e0b',
    ui: '#06b6d4',
  };

  return (
    <div className="container" style={{ maxWidth: '1000px', margin: '0 auto', padding: '2rem' }}>
      <header style={{ marginBottom: '2rem' }}>
        <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontSize: '0.875rem' }}>
          &larr; Back to Dashboard
        </Link>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginTop: '0.5rem', color: 'white' }}>
          Agent Logs
        </h1>
        <p style={{ color: '#999', fontSize: '0.875rem' }}>
          Team interaction log — newest first
        </p>
      </header>

      {/* Filter Bar */}
      <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <button
          onClick={() => setSelectedAgent('all')}
          style={{
            padding: '0.375rem 0.875rem',
            borderRadius: '1rem',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: '600',
            backgroundColor: selectedAgent === 'all' ? '#667eea' : '#2a2a3e',
            color: 'white',
          }}
        >
          All
        </button>
        <button
          onClick={() => setSelectedAgent('Coordinator')}
          style={{
            padding: '0.375rem 0.875rem',
            borderRadius: '1rem',
            border: 'none',
            cursor: 'pointer',
            fontSize: '0.75rem',
            fontWeight: '600',
            backgroundColor: selectedAgent === 'Coordinator' ? '#667eea' : '#2a2a3e',
            color: 'white',
          }}
        >
          Coordinator
        </button>
        {agents.map((a) => (
          <button
            key={a.name}
            onClick={() => setSelectedAgent(a.name)}
            style={{
              padding: '0.375rem 0.875rem',
              borderRadius: '1rem',
              border: 'none',
              cursor: 'pointer',
              fontSize: '0.75rem',
              fontWeight: '600',
              backgroundColor: selectedAgent === a.name ? '#667eea' : '#2a2a3e',
              color: 'white',
            }}
          >
            {a.name}
          </button>
        ))}
      </div>

      {/* Log Entries */}
      <div>
        {filteredEntries.length === 0 ? (
          <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#999', backgroundColor: '#1a1a2e', borderRadius: '0.75rem', border: '1px solid #333' }}>
            No log entries match the current filter.
          </div>
        ) : (
          [...filteredEntries].reverse().map((entry) => (
            <div
              key={entry.id}
              className="card"
              style={{
                marginBottom: '0.75rem',
                padding: '1rem',
                backgroundColor: '#1a1a2e',
                borderRadius: '0.75rem',
                border: '1px solid #333',
                cursor: 'pointer',
              }}
              onClick={() => toggleExpand(entry.id)}
            >
              {/* Header Row */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <span style={{
                    padding: '0.125rem 0.5rem',
                    borderRadius: '0.25rem',
                    fontSize: '0.7rem',
                    fontWeight: '600',
                    backgroundColor: channelColors[entry.channel] || '#666',
                    color: 'white',
                  }}>
                    {entry.channel}
                  </span>
                  <span style={{ fontWeight: '600', color: 'white', fontSize: '0.875rem' }}>
                    {entry.sender}
                  </span>
                  <span style={{ color: '#666', fontSize: '0.75rem' }}>
                    &rarr; {entry.recipient.join(', ')}
                  </span>
                </div>
                <span style={{ color: '#999', fontSize: '0.7rem', whiteSpace: 'nowrap' }}>
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              </div>

              {/* Summary */}
              <p style={{ color: '#ccc', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                {entry.summary}
              </p>

              {/* Follow-up Badge */}
              {entry.follow_up_required && (
                <span style={{
                  display: 'inline-block',
                  padding: '0.125rem 0.5rem',
                  borderRadius: '0.25rem',
                  fontSize: '0.65rem',
                  fontWeight: '600',
                  backgroundColor: '#f59e0b',
                  color: '#000',
                  marginTop: '0.25rem',
                }}>
                  Follow-up Required
                </span>
              )}

              {/* Expanded Details */}
              {expandedEntries.has(entry.id) && (
                <div style={{ marginTop: '0.75rem', borderTop: '1px solid #333', paddingTop: '0.75rem' }}>
                  <p style={{ color: '#999', fontSize: '0.8rem', marginBottom: '0.5rem', whiteSpace: 'pre-wrap' }}>
                    {entry.message}
                  </p>

                  {entry.attachments.length > 0 && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{ color: '#667eea', fontSize: '0.75rem', fontWeight: '600' }}>Attachments:</span>
                      <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem', color: '#999' }}>
                        {entry.attachments.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {entry.follow_up_actions.length > 0 && (
                    <div>
                      <span style={{ color: '#f59e0b', fontSize: '0.75rem', fontWeight: '600' }}>Follow-up Actions:</span>
                      <ul style={{ paddingLeft: '1.25rem', fontSize: '0.75rem', color: '#999' }}>
                        {entry.follow_up_actions.map((a, i) => (
                          <li key={i}>{a}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', fontSize: '0.7rem', color: '#666' }}>
                    <span>ID: {entry.id.slice(0, 8)}...</span>
                    {entry.related_task_id && <span>Task: {entry.related_task_id.slice(0, 8)}...</span>}
                    {entry.related_job_id && <span>Job: {entry.related_job_id.slice(0, 8)}...</span>}
                    <span>Privacy: {entry.privacy}</span>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

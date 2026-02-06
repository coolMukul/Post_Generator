'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

type SubmitMode = 'url' | 'file';

interface JobResult {
  job_id: string;
  status: string;
  created_at: string;
  message?: string;
}

interface JobStatus {
  job_id: string;
  status: 'pending' | 'in_progress' | 'success' | 'failed';
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  result?: any;
  error?: string | null;
  progress?: number;
}

export default function IngestPage() {
  // Get API base URL from environment variable
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

  const [mode, setMode] = useState<SubmitMode>('url');
  const [url, setUrl] = useState('');
  const [title, setTitle] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [polling, setPolling] = useState(false);

  // Poll job status
  useEffect(() => {
    if (!result?.job_id || !polling) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/jobs/${result.job_id}`);
        if (response.ok) {
          const data = await response.json();
          setJobStatus(data);

          // Stop polling if job is complete or failed
          if (data.status === 'success' || data.status === 'failed') {
            setPolling(false);
          }
        }
      } catch (err) {
        console.error('Failed to fetch job status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [result?.job_id, polling, API_BASE_URL]);

  const handleSubmitUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setJobStatus(null);

    try {
      const response = await fetch(`${API_BASE_URL}/pdf/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          title: title || undefined,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setPolling(true); // Start polling for job status
      setUrl('');
      setTitle('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitFile = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('File upload is not yet implemented in the API. Please use URL submission for now.');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return '#10b981';
      case 'failed': return '#ef4444';
      case 'in_progress': return '#3b82f6';
      case 'pending': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return '✓';
      case 'failed': return '✗';
      case 'in_progress': return '⟳';
      case 'pending': return '⏳';
      default: return '◯';
    }
  };

  return (
    <div className="container" style={{ maxWidth: '900px', padding: '2rem' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <Link href="/" style={{ color: '#667eea', textDecoration: 'none', fontWeight: '600' }}>
          ← Back to Home
        </Link>
      </div>

      <div className="card">
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', marginBottom: '0.5rem' }}>
          📄 Document Ingestion
        </h1>
        <p style={{ color: '#666', marginBottom: '2rem' }}>
          Phase 2: Test the complete paper processing pipeline
        </p>

        {/* Mode Toggle */}
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
          <button
            onClick={() => setMode('url')}
            className={`btn ${mode === 'url' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ flex: 1 }}
          >
            📎 Submit URL
          </button>
          <button
            onClick={() => setMode('file')}
            className={`btn ${mode === 'file' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ flex: 1, opacity: 0.5, cursor: 'not-allowed' }}
            title="File upload not yet implemented in API"
          >
            📤 Upload File (Coming Soon)
          </button>
        </div>

        {/* URL Form */}
        {mode === 'url' && (
          <form onSubmit={handleSubmitUrl} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Document URL *
              </label>
              <input
                type="url"
                required
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://arxiv.org/pdf/2301.12345.pdf"
                className="input"
              />
              <p style={{ fontSize: '0.75rem', color: '#666', marginTop: '0.25rem' }}>
                Supports arXiv URLs and direct PDF links
              </p>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Title (optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Auto-extracted if not provided"
                className="input"
              />
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary">
              {loading ? '⏳ Processing...' : '🚀 Ingest Document'}
            </button>
          </form>
        )}

        {/* File Upload Form */}
        {mode === 'file' && (
          <form onSubmit={handleSubmitFile} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                Document Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="My Research Paper"
                className="input"
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                PDF File *
              </label>
              <input
                type="file"
                required
                accept=".pdf,application/pdf"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="input"
                style={{ padding: '0.5rem' }}
              />
              {file && (
                <p style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.5rem' }}>
                  Selected: {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                </p>
              )}
            </div>

            <button type="submit" disabled={loading || !file} className="btn btn-primary">
              {loading ? '⏳ Processing...' : '🚀 Ingest Document'}
            </button>
          </form>
        )}

        {/* Job Status */}
        {result && (
          <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: '0.5rem' }}>
            <h3 style={{ fontWeight: '600', marginBottom: '1rem', color: '#0369a1' }}>
              {result.message || 'Job Queued Successfully'}
            </h3>
            <div style={{ fontSize: '0.875rem', color: '#0c4a6e' }}>
              <p><strong>Job ID:</strong> <code>{result.job_id}</code></p>
              <p><strong>Status:</strong> <code>{result.status}</code></p>
              <p><strong>Created:</strong> <code>{new Date(result.created_at).toLocaleString()}</code></p>
            </div>

            {/* Real-time job status */}
            {jobStatus && (
              <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'white', borderRadius: '0.375rem', border: '1px solid #e5e7eb' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '1.5rem' }}>{getStatusIcon(jobStatus.status)}</span>
                  <strong style={{ color: getStatusColor(jobStatus.status) }}>
                    {jobStatus.status.toUpperCase().replace('_', ' ')}
                  </strong>
                </div>

                {jobStatus.progress !== undefined && jobStatus.progress > 0 && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                      <span>Progress</span>
                      <span>{jobStatus.progress}%</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${jobStatus.progress}%`,
                        height: '100%',
                        backgroundColor: getStatusColor(jobStatus.status),
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                )}

                {jobStatus.status === 'success' && jobStatus.result && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: '#d1fae5', borderRadius: '0.375rem' }}>
                    <p style={{ fontSize: '0.875rem', color: '#065f46' }}>
                      ✓ Document processed successfully!
                    </p>
                    {jobStatus.result.chunks_processed && (
                      <p style={{ fontSize: '0.75rem', color: '#065f46', marginTop: '0.25rem' }}>
                        Processed {jobStatus.result.chunks_processed} chunks
                      </p>
                    )}
                    {jobStatus.result.document_id && (
                      <p style={{ fontSize: '0.75rem', color: '#065f46', marginTop: '0.25rem' }}>
                        Document ID: <code>{jobStatus.result.document_id}</code>
                      </p>
                    )}
                  </div>
                )}

                {jobStatus.status === 'failed' && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: '#fee2e2', borderRadius: '0.375rem' }}>
                    <p style={{ fontSize: '0.875rem', color: '#991b1b' }}>
                      ✗ {jobStatus.error || 'Job failed'}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="alert alert-error" style={{ marginTop: '1rem' }}>
            <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>✗ Error</h3>
            <p style={{ fontSize: '0.875rem' }}>{error}</p>
          </div>
        )}

        {/* API Info */}
        <div className="alert alert-info" style={{ marginTop: '2rem' }}>
          <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>🔌 API Endpoints</h3>
          <div style={{ fontSize: '0.875rem' }}>
            <p><strong>Submit PDF:</strong> <code>POST {API_BASE_URL}/pdf/process</code></p>
            <p><strong>Job Status:</strong> <code>GET {API_BASE_URL}/jobs/:jobId</code></p>
            <p style={{ marginTop: '0.5rem', color: '#666' }}>
              Make sure your API server is running at {API_BASE_URL}
            </p>
          </div>
        </div>

        {/* Pipeline Info */}
        <div className="alert alert-info" style={{ marginTop: '1rem' }}>
          <h3 style={{ fontWeight: '600', marginBottom: '0.5rem' }}>📋 Pipeline Steps</h3>
          <ol style={{ fontSize: '0.875rem', paddingLeft: '1.25rem', margin: 0 }}>
            <li>Download PDF from URL</li>
            <li>Parse with LlamaParse → Markdown</li>
            <li>Chunk into 1500-token segments</li>
            <li>Generate contextual summaries (GPT-4)</li>
            <li>Generate embeddings (OpenAI)</li>
            <li>Store in PostgreSQL + pgvector</li>
          </ol>
        </div>
      </div>
    </div>
  );
}


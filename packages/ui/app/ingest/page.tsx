'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

type SubmitMode = 'url' | 'file';

interface JobResult {
  documentId: string;
  projectDocumentId: string;
  jobId: string;
  status: string;
}

interface JobStatus {
  id: string;
  state: string;
  progress: number;
  data: any;
  returnvalue?: any;
  failedReason?: string;
  logs?: string[];
}

export default function IngestPage() {
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
    if (!result?.jobId || !polling) return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:3101/queue/jobs/${result.jobId}`);
        if (response.ok) {
          const data = await response.json();
          setJobStatus(data);
          
          // Stop polling if job is complete or failed
          if (data.state === 'completed' || data.state === 'failed') {
            setPolling(false);
          }
        }
      } catch (err) {
        console.error('Failed to fetch job status:', err);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(interval);
  }, [result?.jobId, polling]);

  const handleSubmitUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setJobStatus(null);

    try {
      const response = await fetch('http://localhost:3101/documents/submit-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          title: title || undefined,
          projectKey: 'researchpaper',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP ${response.status}`);
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
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);
    setJobStatus(null);

    try {
      // Convert file to base64
      const reader = new FileReader();
      const base64Content = await new Promise<string>((resolve, reject) => {
        reader.onload = () => {
          const result = reader.result as string;
          resolve(result.split(',')[1]); // Remove data:...;base64, prefix
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });

      const response = await fetch('http://localhost:3101/documents/submit-file', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          fileType: file.type || 'application/pdf',
          fileSize: file.size,
          projectKey: 'researchpaper',
          base64Content,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.message || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setPolling(true); // Start polling for job status
      setTitle('');
      setFile(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'completed': return '#10b981';
      case 'failed': return '#ef4444';
      case 'active': return '#3b82f6';
      case 'waiting': return '#f59e0b';
      default: return '#6b7280';
    }
  };

  const getStatusIcon = (state: string) => {
    switch (state) {
      case 'completed': return '✓';
      case 'failed': return '✗';
      case 'active': return '⟳';
      case 'waiting': return '⏳';
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
            style={{ flex: 1 }}
          >
            📤 Upload File
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
              Job Queued Successfully
            </h3>
            <div style={{ fontSize: '0.875rem', color: '#0c4a6e' }}>
              <p><strong>Document ID:</strong> <code>{result.documentId}</code></p>
              <p><strong>Job ID:</strong> <code>{result.jobId}</code></p>
            </div>

            {/* Real-time job status */}
            {jobStatus && (
              <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'white', borderRadius: '0.375rem', border: '1px solid #e5e7eb' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                  <span style={{ fontSize: '1.5rem' }}>{getStatusIcon(jobStatus.state)}</span>
                  <strong style={{ color: getStatusColor(jobStatus.state) }}>
                    {jobStatus.state.toUpperCase()}
                  </strong>
                </div>
                
                {jobStatus.progress > 0 && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                      <span>Progress</span>
                      <span>{jobStatus.progress}%</span>
                    </div>
                    <div style={{ width: '100%', height: '8px', backgroundColor: '#e5e7eb', borderRadius: '4px', overflow: 'hidden' }}>
                      <div style={{ 
                        width: `${jobStatus.progress}%`, 
                        height: '100%', 
                        backgroundColor: getStatusColor(jobStatus.state),
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                  </div>
                )}

                {jobStatus.logs && jobStatus.logs.length > 0 && (
                  <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#666' }}>
                    <strong>Latest Log:</strong>
                    <p style={{ marginTop: '0.25rem', fontFamily: 'monospace', backgroundColor: '#f9fafb', padding: '0.5rem', borderRadius: '0.25rem' }}>
                      {jobStatus.logs[jobStatus.logs.length - 1]}
                    </p>
                  </div>
                )}

                {jobStatus.state === 'completed' && jobStatus.returnvalue && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: '#d1fae5', borderRadius: '0.375rem' }}>
                    <p style={{ fontSize: '0.875rem', color: '#065f46' }}>
                      ✓ Document processed successfully!
                      {jobStatus.returnvalue.chunksProcessed && (
                        <span> ({jobStatus.returnvalue.chunksProcessed} chunks embedded)</span>
                      )}
                    </p>
                  </div>
                )}

                {jobStatus.state === 'failed' && (
                  <div style={{ marginTop: '0.75rem', padding: '0.75rem', backgroundColor: '#fee2e2', borderRadius: '0.375rem' }}>
                    <p style={{ fontSize: '0.875rem', color: '#991b1b' }}>
                      ✗ {jobStatus.failedReason || 'Job failed'}
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

        {/* Pipeline Info */}

        <div className="alert alert-info" style={{ marginTop: '2rem' }}>
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


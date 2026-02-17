import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="container">
      <header style={{ textAlign: 'center', marginBottom: '3rem', color: 'white' }}>
        <h1 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '1rem' }}>
          Research Insight
        </h1>
        <p style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
          AI-Powered LinkedIn Content from Academic Research
        </p>
        <p style={{ fontSize: '1rem', opacity: 0.8 }}>
          Personal Learning Project - Phase 5 Active
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <Link href="/ingest" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Document Ingestion
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Submit research papers via URL or file upload
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 2 Complete
          </div>
        </Link>

        <Link href="/hybrid-search" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Hybrid Retrieval System
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Search and retrieve relevant research insights
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 3 Complete
          </div>
        </Link>

        <Link href="/research-query-agent" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Research Query Agent
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            AI agent with LangGraph for intelligent retrieval
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 4 Complete
          </div>
        </Link>

        <Link href="/agent-run" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Agent Run
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Submit agent runs and content pipeline jobs, poll results
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#667eea', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 4+5 Active
          </div>
        </Link>

        <Link href="/agent-logs" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Agent Logs
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            View team interaction logs and agent communication
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#667eea', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 4+5 Active
          </div>
        </Link>

        <Link href="/insight-extraction-agent" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Insight Extraction Agent
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Extract concise insights from the ingested corpus
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#06b6d4', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 5 Active
          </div>
        </Link>

        <Link href="/linkedin-post-agent" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Content Generation
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            AI-generated LinkedIn posts from research
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#06b6d4', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 5 Active
          </div>
        </Link>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>
          Implementation Status
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.875rem' }}>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Phase 1: Foundation
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Phase 2: Document Ingestion
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Phase 3: Hybrid Retrieval (RRF)
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Phase 4: Agent Framework
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#eff6ff', borderRadius: '0.375rem' }}>
            Phase 5: Content Pipeline (Active)
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Multi-Provider Embeddings
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Agent Registry + Manifests
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            LangGraph Workflows
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            Team Interaction Logging
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>
          Architecture Stack
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', fontSize: '0.875rem', textAlign: 'center' }}>
          <div>
            <strong style={{ color: '#667eea' }}>Frontend</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>Next.js 15<br/>React 19</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>API</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>FastAPI<br/>Pydantic</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Workers</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>LangChain<br/>LangGraph</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>AI</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>OpenAI / Gemini<br/>Multi-Provider</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Database</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>PostgreSQL<br/>pgvector</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Queue</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>Redis<br/>BLPOP</p>
          </div>
        </div>
      </div>

      <footer style={{ textAlign: 'center', marginTop: '3rem', padding: '1.5rem', color: '#666', fontSize: '0.875rem' }}>
        <p>Built from scratch as a learning project</p>
        <p style={{ marginTop: '0.5rem' }}>Zero code reused from emtech-impulse - Safe for public portfolio</p>
      </footer>
    </div>
  );
}

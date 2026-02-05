import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="container">
      <header style={{ textAlign: 'center', marginBottom: '3rem', color: 'white' }}>
        <h1 style={{ fontSize: '3rem', fontWeight: 'bold', marginBottom: '1rem' }}>
          🔬 Research Insight
        </h1>
        <p style={{ fontSize: '1.25rem', marginBottom: '0.5rem' }}>
          AI-Powered LinkedIn Content from Academic Research
        </p>
        <p style={{ fontSize: '1rem', opacity: 0.8 }}>
          Personal Learning Project - Phase 4 & 5 Active
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <Link href="/ingest" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Document Ingestion
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Submit research papers via URL or file upload
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            ✓ Phase 2 Complete
          </div>
        </Link>

        <Link href="/hybrid-search" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔍</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Hybrid Retrieval System
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Search and retrieve relevant research insights
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            ✓ Phase 3 Complete
          </div>
        </Link>

        <Link href="/research-query-agent" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🤖</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Research Query Agent
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            AI agent with LangGraph for intelligent retrieval
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#10b981', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            ✓ Phase 4 Active
          </div>
        </Link>

        <Link href="/insight-extraction-agent" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔎</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem' }}>
            Insight Extraction Agent
          </h2>
          <p style={{ color: '#666', marginBottom: '1rem' }}>
            Extract concise insights from the ingested corpus
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#06b6d4', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Beta
          </div>
        </Link>

        <Link href="/content-workflow" className="card" style={{ textDecoration: 'none', color: 'inherit', cursor: 'pointer', transition: 'transform 0.2s', background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)', border: '2px solid #7c3aed' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🚀</div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', marginBottom: '0.5rem', color: 'white' }}>
            Content Workflow
          </h2>
          <p style={{ color: '#a5b4fc', marginBottom: '1rem' }}>
            Full pipeline: Research → Insights → LinkedIn Post
          </p>
          <div style={{ display: 'inline-block', padding: '0.25rem 0.75rem', backgroundColor: '#7c3aed', color: 'white', borderRadius: '1rem', fontSize: '0.75rem', fontWeight: '600' }}>
            Phase 4+5 Active
          </div>
        </Link>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>
          ✅ Implementation Status
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.875rem' }}>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Paper Downloader
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ LlamaParse Integration
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Document Chunking
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Contextual Summaries
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Embedding Service
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Vector Database
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Hybrid Search (RRF)
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ LangGraph Agent
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ API Endpoints
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Agent Framework
          </div>
          <div style={{ padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '0.375rem' }}>
            ✓ Content Workflow
          </div>
        </div>
      </div>

      <div className="card">
        <h3 style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '1rem' }}>
          🏗️ Architecture Stack
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', fontSize: '0.875rem', textAlign: 'center' }}>
          <div>
            <strong style={{ color: '#667eea' }}>Frontend</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>Next.js 15<br/>React 19</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>API</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>Fastify<br/>BullMQ</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Workers</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>LangChain<br/>LlamaIndex</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>AI</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>OpenAI<br/>GPT-4</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Database</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>PostgreSQL<br/>pgvector</p>
          </div>
          <div>
            <strong style={{ color: '#667eea' }}>Queue</strong>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>Redis<br/>BullMQ</p>
          </div>
        </div>
      </div>

      <footer style={{ textAlign: 'center', marginTop: '3rem', padding: '1.5rem', color: '#666', fontSize: '0.875rem' }}>
        <p>Built from scratch as a learning project</p>
        <p style={{ marginTop: '0.5rem' }}>Zero code reused from emtech-impulse • Safe for public portfolio</p>
      </footer>
    </div>
  );
}
// ...existing code ends at the closing brace of the HomePage component

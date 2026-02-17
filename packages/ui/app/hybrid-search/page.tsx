 'use client';
 import React from 'react';

 import { useState } from 'react';
 import Link from 'next/link';

 interface SearchResult {
   id: string;
   documentId: string;
   documentTitle?: string;
   chunkIndex: number;
   content: string;
   contextSummary: string | null;
   score: number;
   rankSource: 'vector' | 'keyword' | 'hybrid';
   metadata: Record<string, any>;
 }

 interface SearchResponse {
   success: boolean;
   query: string;
   searchMode: string;
   resultsCount: number;
   results: SearchResult[];
   error?: string;
 }

 const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3201';

 export default function SearchPage() {
   const [query, setQuery] = useState('machine learning');
   const [searchMode, setSearchMode] = useState<'hybrid' | 'vector' | 'keyword'>('hybrid');
  const [limit, setLimit] = useState(10);
  // UI shows percentage (0-100). Convert to decimal when sending to API.
  const [minScorePercent, setMinScorePercent] = useState(30);
   const [vectorWeight, setVectorWeight] = useState(0.7);
   const [keywordWeight, setKeywordWeight] = useState(0.3);

   const [loading, setLoading] = useState(false);
   const [results, setResults] = useState<SearchResult[]>([]);
   const [searchInfo, setSearchInfo] = useState<{ query: string; mode: string; count: number } | null>(null);
   const [error, setError] = useState<string | null>(null);
   const [totalDocs, setTotalDocs] = useState<number | null>(null);
   const [jobId, setJobId] = useState<string | null>(null);
   const [jobStatus, setJobStatus] = useState<string>('');
   const [nextPollIn, setNextPollIn] = useState<number>(0);

   // Fetch total document count on mount
   React.useEffect(() => {
     fetch(`${API_BASE}/documents/count`)
       .then(res => res.json())
       .then(data => setTotalDocs(data.count))
       .catch(() => setTotalDocs(null));
   }, []);

   const handleSearch = async (e: React.FormEvent) => {
     e.preventDefault();

     if (!query.trim()) {
       setError('Please enter a search query');
       return;
     }

     setLoading(true);
     setError(null);
     setResults([]);
     setSearchInfo(null);
     setJobId(null);
     setJobStatus('submitting');
     setNextPollIn(0);

     try {
       // Submit search job
       const submitResponse = await fetch(`${API_BASE}/search/submit`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query,
          searchMode,
          limit,
          minScore: Math.max(0, Math.min(1, minScorePercent / 100)),
          vectorWeight,
          keywordWeight,
        }),
       });

       const submitData = await submitResponse.json();

       if (!submitData.jobId) {
         throw new Error('Failed to submit search job');
       }

       const newJobId = submitData.jobId as string;
       setJobId(newJobId);
       setJobStatus('queued');

       // Poll for job completion
       pollJobStatus(newJobId);
     } catch (err: any) {
       setError(err.message || 'Failed to submit search');
       console.error('Search submit error:', err);
       setLoading(false);
     }
   };

   const pollJobStatus = async (jobId: string) => {
     const pollInterval = 5; // Poll every 5 seconds
     let countdownInterval: NodeJS.Timeout;

     const poll = async () => {
       try {
         // Use existing queue endpoint
         const statusResponse = await fetch(`${API_BASE}/queue/jobs/${jobId}`);
         const statusData = await statusResponse.json();

         setJobStatus(statusData.state || statusData.status || 'unknown');

         if (statusData.state === 'completed' || statusData.status === 'completed') {
           // Job completed successfully
           clearInterval(countdownInterval);
           const result = statusData.returnvalue || statusData.result || {};
           setResults(result.results || []);
           setSearchInfo({
             query: result.query || query,
             mode: result.searchMode || searchMode,
             count: result.resultsCount || (result.results || []).length,
           });
           setLoading(false);
           setNextPollIn(0);
           return;
         }

         if (statusData.state === 'failed' || statusData.status === 'failed') {
           // Job failed
           clearInterval(countdownInterval);
           setError(statusData.failedReason || statusData.error || 'Search job failed');
           setLoading(false);
           setNextPollIn(0);
           return;
         }

         // Job still processing, schedule next poll
         setNextPollIn(pollInterval);

         // Start countdown
         let timeLeft = pollInterval;
         countdownInterval = setInterval(() => {
           timeLeft--;
           setNextPollIn(timeLeft);
           if (timeLeft <= 0) {
             clearInterval(countdownInterval);
           }
         }, 1000);

         // Schedule next poll
         setTimeout(() => {
           clearInterval(countdownInterval);
           poll();
         }, pollInterval * 1000);
       } catch (err: any) {
         clearInterval(countdownInterval);
         setError(err.message || 'Failed to check search status');
         console.error('Job status check error:', err);
         setLoading(false);
         setNextPollIn(0);
       }
     };

     poll();
   };

   const getRankSourceColor = (source: string) => {
     switch (source) {
       case 'vector': return 'bg-blue-500/20 text-blue-300 border border-blue-500/30';
       case 'keyword': return 'bg-green-500/20 text-green-300 border border-green-500/30';
       case 'hybrid': return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
       default: return 'bg-gray-500/20 text-gray-300 border border-gray-500/30';
     }
   };

   const getScoreColor = (score: number) => {
     if (score >= 0.8) return 'text-emerald-400 font-bold';
     if (score >= 0.6) return 'text-blue-400 font-semibold';
     if (score >= 0.4) return 'text-yellow-400';
     return 'text-gray-400';
   };

   const getScoreBarWidth = (score: number) => `${Math.round(score * 100)}%`;

   const getScoreBarColor = (score: number) => {
     if (score >= 0.8) return 'bg-emerald-500';
     if (score >= 0.6) return 'bg-blue-500';
     if (score >= 0.4) return 'bg-yellow-500';
     return 'bg-gray-500';
   };

   return (
     <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-6 md:p-10">
       <div className="max-w-4xl mx-auto">
         {/* Header */}
         <div className="mb-8">
           <Link href="/" className="text-slate-400 hover:text-white transition-colors text-sm mb-6 inline-flex items-center gap-1">
             <span>&#8592;</span> Back to Home
           </Link>
           <div className="flex items-center gap-3 mb-2">
             <h1 className="text-3xl md:text-4xl font-bold text-white tracking-tight">
               Hybrid Retrieval
             </h1>
             {totalDocs !== null && (
               <span className="px-3 py-1 bg-blue-500/15 text-blue-400 text-sm rounded-full border border-blue-500/20">
                 {totalDocs} docs
               </span>
             )}
           </div>
           <p className="text-slate-400 text-sm">
             Search and retrieve relevant research insights using vector, keyword, or hybrid search.
           </p>
         </div>

         {/* Search Card */}
         <div className="bg-slate-800/50 backdrop-blur border border-slate-700/50 rounded-xl p-6 mb-6">
           <form onSubmit={handleSearch} className="space-y-5">
             {/* Query Input */}
             <div>
               <label className="block text-slate-300 text-sm font-medium mb-1.5">
                 Search Query
               </label>
               <div className="flex gap-2">
                 <input
                   type="text"
                   value={query}
                   onChange={(e) => setQuery(e.target.value)}
                   placeholder="e.g., transformer architecture, attention mechanisms..."
                   className="flex-1 px-4 py-2.5 bg-slate-900/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-sm"
                   required
                 />
                 <button
                   type="submit"
                   disabled={loading || !query.trim()}
                   className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm whitespace-nowrap"
                 >
                   {loading ? (
                     <span className="flex items-center gap-2">
                       <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                         <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                         <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                       </svg>
                       {nextPollIn > 0 ? `${nextPollIn}s` : 'Searching...'}
                     </span>
                   ) : 'Search'}
                 </button>
               </div>
             </div>

             {/* Options Row */}
             <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
               {/* Search Mode */}
               <div>
                 <label className="block text-slate-400 text-xs font-medium mb-1">
                   Mode
                 </label>
                 <select
                   value={searchMode}
                   onChange={(e) => setSearchMode(e.target.value as any)}
                   className="w-full px-3 py-2 bg-slate-900/50 border border-slate-600/50 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                 >
                   <option value="hybrid">Hybrid</option>
                   <option value="vector">Vector</option>
                   <option value="keyword">Keyword</option>
                 </select>
               </div>

               {/* Limit */}
               <div>
                 <label className="block text-slate-400 text-xs font-medium mb-1">
                   Max Results: {limit}
                 </label>
                 <input
                   type="range"
                   min="5"
                   max="50"
                   step="5"
                   value={limit}
                   onChange={(e) => setLimit(parseInt(e.target.value))}
                   className="w-full accent-blue-500 mt-1.5"
                 />
               </div>

               {/* Min Score */}
               <div>
                 <label className="block text-slate-400 text-xs font-medium mb-1">
                   Min Score: {minScorePercent}%
                 </label>
                 <input
                   type="range"
                   min="0"
                   max="100"
                   step="5"
                   value={minScorePercent}
                   onChange={(e) => setMinScorePercent(parseInt(e.target.value))}
                   className="w-full accent-blue-500 mt-1.5"
                 />
               </div>

               {/* Weights */}
               {searchMode === 'hybrid' && (
                 <div>
                   <label className="block text-slate-400 text-xs font-medium mb-1">
                     V:{vectorWeight.toFixed(1)} / K:{keywordWeight.toFixed(1)}
                   </label>
                   <input
                     type="range"
                     min="0"
                     max="1"
                     step="0.1"
                     value={vectorWeight}
                     onChange={(e) => {
                       const v = parseFloat(e.target.value);
                       setVectorWeight(v);
                       setKeywordWeight(1 - v);
                     }}
                     className="w-full accent-blue-500 mt-1.5"
                   />
                 </div>
               )}
             </div>
           </form>

           {/* Job Status */}
           {loading && jobId && (
             <div className="mt-4 px-4 py-2.5 bg-blue-500/10 border border-blue-500/20 rounded-lg flex items-center justify-between text-sm">
               <span className="text-blue-300">
                 <span className="text-blue-400 font-mono text-xs">{jobId.slice(0, 8)}...</span>
               </span>
               <span className="text-blue-300 capitalize">{jobStatus}</span>
             </div>
           )}

           {/* Error */}
           {error && (
             <div className="mt-4 px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-300 text-sm">
               {error}
             </div>
           )}
         </div>

         {/* Results Summary */}
         {searchInfo && (
           <div className="flex items-center justify-between mb-4 px-1">
             <p className="text-slate-400 text-sm">
               <span className="text-white font-medium">{searchInfo.count}</span> results for{' '}
               <span className="text-white">&ldquo;{searchInfo.query}&rdquo;</span>
             </p>
             <span className="text-slate-500 text-xs uppercase tracking-wider">{searchInfo.mode}</span>
           </div>
         )}

         {/* Results */}
         {results && results.length > 0 && (
           <div className="space-y-3">
             {results.map((result, idx) => (
               <div
                 key={result.id}
                 className="bg-slate-800/40 backdrop-blur border border-slate-700/40 rounded-xl p-5 hover:border-slate-600/60 transition-colors"
               >
                 {/* Top row: rank, title, score */}
                 <div className="flex items-start justify-between gap-4 mb-3">
                   <div className="flex items-center gap-3 min-w-0">
                     <span className="text-slate-500 font-mono text-sm flex-shrink-0">
                       {String(idx + 1).padStart(2, '0')}
                     </span>
                     <div className="min-w-0">
                       {result.documentTitle && (
                         <h3 className="text-white font-medium text-sm truncate">
                           {result.documentTitle}
                         </h3>
                       )}
                       <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                         <span>Chunk {result.chunkIndex}</span>
                         {result.metadata?.pageNumber && (
                           <>
                             <span>&middot;</span>
                             <span>Page {result.metadata.pageNumber}</span>
                           </>
                         )}
                       </div>
                     </div>
                   </div>
                   <div className="flex items-center gap-2 flex-shrink-0">
                     <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRankSourceColor(result.rankSource)}`}>
                       {result.rankSource}
                     </span>
                     <span className={`text-lg tabular-nums ${getScoreColor(result.score)}`}>
                       {(result.score * 100).toFixed(0)}%
                     </span>
                   </div>
                 </div>

                 {/* Score bar */}
                 <div className="w-full h-1 bg-slate-700/50 rounded-full mb-3 overflow-hidden">
                   <div
                     className={`h-full rounded-full transition-all ${getScoreBarColor(result.score)}`}
                     style={{ width: getScoreBarWidth(result.score) }}
                   />
                 </div>

                 {/* Context Summary */}
                 {result.contextSummary && (
                   <div className="mb-3 px-3 py-2 bg-blue-500/5 border-l-2 border-blue-500/40 rounded-r text-sm text-blue-200/80">
                     {result.contextSummary}
                   </div>
                 )}

                 {/* Content */}
                 <div className="text-slate-300 text-sm leading-relaxed">
                   {result.content}
                 </div>
               </div>
             ))}
           </div>
         )}

         {/* No Results */}
         {!loading && searchInfo && (!results || results.length === 0) && (
           <div className="bg-slate-800/40 border border-slate-700/40 rounded-xl p-10 text-center">
             <p className="text-slate-400 text-sm">
               No results found. Try adjusting your query or lowering the minimum score.
             </p>
           </div>
         )}
       </div>
     </div>
   );
 }

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

 const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3101';

 export default function SearchPage() {
   const [query, setQuery] = useState('');
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
     const pollInterval = 60; // Poll every 60 seconds
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
       case 'vector': return 'bg-blue-100 text-blue-800';
       case 'keyword': return 'bg-green-100 text-green-800';
       case 'hybrid': return 'bg-purple-100 text-purple-800';
       default: return 'bg-gray-100 text-gray-800';
     }
   };

   const getScoreColor = (score: number) => {
     if (score >= 0.8) return 'text-green-600 font-bold';
     if (score >= 0.6) return 'text-blue-600 font-semibold';
     if (score >= 0.4) return 'text-yellow-600';
     return 'text-gray-600';
   };

   return (
     <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-8 text-[1.25rem] md:text-[1.35rem]">
       <div className="max-w-3xl w-full">
         {/* Header */}
         <div className="text-center mb-10">
           <Link href="/" className="text-white/80 hover:text-white mb-4 inline-block text-lg md:text-xl">
             ← Back to Home
           </Link>
           <h1 className="text-5xl font-extrabold text-white mb-2">
             <span role="img" aria-label="search">🔍</span> Hybrid Retrieval System
           </h1>
           <p className="text-white/90 text-2xl mb-2">
             Phase 3: Search and retrieve relevant research insights
           </p>
           {totalDocs !== null && (
             <div className="text-blue-200 text-lg mt-2">Total documents in DB: <b>{totalDocs}</b></div>
           )}
         </div>

         {/* Main Card */}
         <div className="bg-white rounded-2xl shadow-2xl p-10 mb-8">
           <form onSubmit={handleSearch} className="space-y-6">
             {/* Query Input */}
             <div>
               <label className="block text-gray-700 font-semibold mb-2 text-sm">
                 Search Query *
               </label>
               <input
                 type="text"
                 value={query}
                 onChange={(e) => setQuery(e.target.value)}
                 placeholder="e.g., transformer architecture, attention mechanisms, BERT..."
                 className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
                 required
               />
             </div>

             {/* Search Options Row */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               {/* Search Mode */}
               <div>
                 <label className="block text-gray-700 font-semibold mb-2 text-sm">
                   Search Mode
                 </label>
                 <select
                   value={searchMode}
                   onChange={(e) => setSearchMode(e.target.value as any)}
                   className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                 >
                   <option value="hybrid">Hybrid (Best Overall)</option>
                   <option value="vector">Vector (Semantic)</option>
                   <option value="keyword">Keyword (Exact)</option>
                 </select>
               </div>

               {/* Limit */}
               <div>
                 <label className="block text-gray-700 font-semibold mb-2 text-sm">
                   Max Results: {limit}
                 </label>
                 <input
                   type="range"
                   min="5"
                   max="50"
                   step="5"
                   value={limit}
                   onChange={(e) => setLimit(parseInt(e.target.value))}
                   className="w-full accent-blue-600"
                 />
               </div>
             </div>

             {/* Min Score and Advanced */}
             <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
               <div>
                 <label className="block text-gray-700 font-semibold mb-2 text-sm flex items-center gap-2">
                   Min Score: {minScorePercent}%
                   <span title="Only results with a score above this threshold are shown. Lower to see more, raise to see only the best matches." className="text-blue-400 cursor-help text-base">ⓘ</span>
                 </label>
                 <input
                   type="range"
                   min="0"
                   max="100"
                   step="1"
                   value={minScorePercent}
                   onChange={(e) => setMinScorePercent(parseInt(e.target.value))}
                   className="w-full accent-blue-600"
                 />
               </div>

               {searchMode === 'hybrid' && (
                 <div>
                   <label className="block text-gray-700 font-semibold mb-2 text-sm">
                     Weights (V:{vectorWeight.toFixed(1)}/K:{keywordWeight.toFixed(1)})
                   </label>
                   <div className="flex gap-2">
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
                       className="w-full accent-blue-600"
                     />
                   </div>
                 </div>
               )}
             </div>

             {/* Search Button */}
             <button
               type="submit"
               disabled={loading || !query.trim()}
               className="w-full bg-blue-600 text-white py-4 rounded-lg font-bold text-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
             >
               {loading ? (
                 nextPollIn > 0 
                   ? `🔄 ${jobStatus} - Next check in ${nextPollIn}s` 
                   : `🔄 ${jobStatus === 'submitting' ? 'Submitting...' : jobStatus === 'queued' ? 'Queued...' : 'Checking status...'}`
               ) : '🔍 Search Documents'}
             </button>
           </form>

           {/* Job Status Info */}
           {loading && jobId && (
             <div className="mt-4 bg-blue-50 border border-blue-200 text-blue-700 px-4 py-3 rounded-lg">
               <div className="flex items-center justify-between">
                 <span><strong>Job ID:</strong> {jobId}</span>
                 <span><strong>Status:</strong> {jobStatus}</span>
               </div>
               {nextPollIn > 0 && (
                 <div className="mt-2 text-sm">
                   Checking status again in <strong>{nextPollIn}</strong> seconds...
                 </div>
               )}
             </div>
           )}

           {/* Error Message */}
           {error && (
             <div className="mt-4 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
               <strong>Error:</strong> {error}
             </div>
           )}

           {/* Search Info */}
           {searchInfo && (
             <div className="mt-6 pt-6 border-t border-gray-200 text-xl flex flex-col md:flex-row md:items-center md:justify-between gap-2">
               <div>
                 <span className="text-gray-700">Query:</span>
                 <span className="ml-2 font-bold text-gray-900">"{searchInfo.query}"</span>
               </div>
               <div className="flex gap-6 text-gray-700">
                 <span>Mode: <b>{searchInfo.mode}</b></span>
                 <span>Found: <b>{searchInfo.count}</b>{totalDocs !== null && (
                   <span className="ml-2 text-gray-500">/ {totalDocs} docs</span>
                 )}</span>
               </div>
             </div>
           )}
         </div>

         {/* Results Section */}
         {results && results.length > 0 && (
           <div className="space-y-4 mt-6">
             {results.map((result, idx) => (
               <div
                 key={result.id}
                 className="bg-white rounded-xl shadow-md p-5 hover:shadow-lg transition-shadow border border-gray-100"
               >
                 {/* Result Header */}
                 <div className="flex items-start justify-between mb-3">
                   <div className="flex-1">
                     <div className="flex items-center gap-3 mb-1">
                       <span className="text-xl font-bold text-gray-400">#{idx + 1}</span>
                       {result.documentTitle && (
                         <h3 className="text-base font-semibold text-gray-800">
                           {result.documentTitle}
                         </h3>
                       )}
                     </div>
                     <div className="flex items-center gap-2 text-xs text-gray-500">
                       <span>Chunk {result.chunkIndex}</span>
                       {result.metadata?.pageNumber && (
                         <>
                           <span>•</span>
                           <span>Page {result.metadata.pageNumber}</span>
                         </>
                       )}
                     </div>
                   </div>
                   <div className="flex flex-col items-end gap-1">
                     <span className={`text-xl font-bold ${getScoreColor(result.score)}`}>{(result.score * 100).toFixed(0)}%</span>
                     <span className="text-xs text-gray-500">Score: {result.score.toFixed(4)}</span>
                     <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getRankSourceColor(result.rankSource)}`}>{result.rankSource}</span>
                   </div>
                 </div>

                 {/* Context Summary */}
                 {result.contextSummary && (
                   <div className="mb-3 p-3 bg-blue-50 border-l-3 border-blue-400 rounded text-xs">
                     <div className="font-semibold text-blue-800 mb-1">Context:</div>
                     <div className="text-blue-900">{result.contextSummary}</div>
                   </div>
                 )}

                 {/* Content */}
                 <div className="text-gray-700 leading-relaxed text-sm">
                   {result.content}
                 </div>
               </div>
             ))}
           </div>
         )}

         {/* No Results */}
         {!loading && searchInfo && (!results || results.length === 0) && (
           <div className="bg-white rounded-xl shadow-md p-8 text-center border border-gray-100">
             <div className="text-5xl mb-3">🤷</div>
             <h3 className="text-lg font-semibold text-gray-800 mb-2">
               No results found
             </h3>
             <p className="text-gray-600 text-sm">
               Try adjusting your query or lowering the minimum score.
             </p>
           </div>
         )}
       </div>
     </div>
   );
 }

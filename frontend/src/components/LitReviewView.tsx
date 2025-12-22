import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Sparkles,
  FileText,
  Loader2,
  AlertCircle,
  Network,
  GitCompare,
  BookOpen,
  Check,
  ChevronDown,
  ChevronRight,
  Search,
  Save,
  FolderOpen,
  Trash2,
  X,
} from 'lucide-react';
import {
  getPapers,
  clusterPapers,
  comparePapers,
  synthesizePapers,
  findSimilarPapers,
  saveClusteringResult,
  getSavedSessions,
  deleteSession,
  type PaperInfo,
  type ClusterResponse,
  type CompareResponse,
  type SynthesizeResponse,
  type SimilarPapersResponse,
  type ClusteringSession,
} from '@/api';

interface LitReviewViewProps {
  onBack: () => void;
}

type TabType = 'cluster' | 'compare' | 'synthesize';

export function LitReviewView({ onBack }: LitReviewViewProps) {
  const [papers, setPapers] = useState<PaperInfo[]>([]);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('cluster');

  // Results state
  const [clusterResult, setClusterResult] = useState<ClusterResponse | null>(null);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [synthesisResult, setSynthesisResult] = useState<SynthesizeResponse | null>(null);
  const [similarPapers, setSimilarPapers] = useState<SimilarPapersResponse | null>(null);

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);

  // Clustering options
  const [clusterMethod, setClusterMethod] = useState<'hierarchical' | 'kmeans' | 'dbscan'>('hierarchical');
  const [numClusters, setNumClusters] = useState<number>(3);

  // Synthesis options
  const [focusQuestion, setFocusQuestion] = useState('');

  // Expanded clusters
  const [expandedClusters, setExpandedClusters] = useState<Set<number>>(new Set());

  // Saved sessions state
  const [savedSessions, setSavedSessions] = useState<ClusteringSession[]>([]);
  const [showSavedSessions, setShowSavedSessions] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [sessionName, setSessionName] = useState('');

  useEffect(() => {
    loadPapers();
    loadSavedSessions();
  }, []);

  async function loadPapers() {
    try {
      setIsLoading(true);
      const data = await getPapers();
      setPapers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load papers');
    } finally {
      setIsLoading(false);
    }
  }

  async function loadSavedSessions() {
    try {
      const sessions = await getSavedSessions();
      setSavedSessions(sessions);
    } catch {
      // Silently fail - saved sessions are optional
    }
  }

  async function handleSaveCluster() {
    if (!clusterResult || !sessionName.trim()) return;

    setIsProcessing(true);
    try {
      await saveClusteringResult(
        sessionName.trim(),
        clusterResult.method,
        clusterResult.clusters,
        clusterResult.total_papers,
        clusterResult.outliers
      );
      await loadSavedSessions();
      setSaveDialogOpen(false);
      setSessionName('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDeleteSession(sessionId: string) {
    try {
      await deleteSession(sessionId);
      setSavedSessions(prev => prev.filter(s => s.session_id !== sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    }
  }

  function loadSavedSession(session: ClusteringSession) {
    // Convert saved session back to ClusterResponse format
    setClusterResult({
      method: session.method,
      total_papers: session.total_papers,
      num_clusters: session.clusters.length,
      clusters: session.clusters.map((c, i) => ({
        id: i,
        papers: c.pdf_ids,
        size: c.pdf_ids.length,
        topics: c.topics,
        summary: null,
      })),
      outliers: session.outliers,
    });
    setExpandedClusters(new Set(session.clusters.map((_, i) => i)));
    setShowSavedSessions(false);
  }

  function togglePaperSelection(pdfId: string) {
    setSelectedPapers(prev => {
      const next = new Set(prev);
      if (next.has(pdfId)) {
        next.delete(pdfId);
      } else {
        next.add(pdfId);
      }
      return next;
    });
  }

  function selectAllPapers() {
    if (selectedPapers.size === papers.length) {
      setSelectedPapers(new Set());
    } else {
      setSelectedPapers(new Set(papers.map(p => p.pdf_id)));
    }
  }

  async function handleCluster() {
    if (selectedPapers.size < 2) {
      setError('Select at least 2 papers to cluster');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setClusterResult(null);

    try {
      const params = clusterMethod === 'kmeans'
        ? { n_clusters: Math.min(numClusters, selectedPapers.size) }
        : {};

      const result = await clusterPapers(
        Array.from(selectedPapers),
        clusterMethod,
        params
      );
      setClusterResult(result);
      // Expand all clusters by default
      setExpandedClusters(new Set(result.clusters.map(c => c.id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Clustering failed');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleCompare() {
    if (selectedPapers.size < 2 || selectedPapers.size > 5) {
      setError('Select 2-5 papers to compare');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setCompareResult(null);

    try {
      const result = await comparePapers(Array.from(selectedPapers));
      setCompareResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleSynthesize() {
    if (selectedPapers.size < 1) {
      setError('Select at least 1 paper to synthesize');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setSynthesisResult(null);

    try {
      const result = await synthesizePapers(
        Array.from(selectedPapers),
        focusQuestion || undefined
      );
      setSynthesisResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Synthesis failed');
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleFindSimilar(pdfId: string) {
    setIsProcessing(true);
    setError(null);
    setSimilarPapers(null);

    try {
      const result = await findSimilarPapers(pdfId, 5);
      setSimilarPapers(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to find similar papers');
    } finally {
      setIsProcessing(false);
    }
  }

  function toggleClusterExpanded(clusterId: number) {
    setExpandedClusters(prev => {
      const next = new Set(prev);
      if (next.has(clusterId)) {
        next.delete(clusterId);
      } else {
        next.add(clusterId);
      }
      return next;
    });
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#41337A] mx-auto mb-4" />
          <p className="text-gray-600">Loading papers...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50 flex flex-col">
      {/* Header */}
      <header className="px-6 md:px-12 py-6 border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="p-2 hover:bg-gray-100 rounded-xl transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-xl flex items-center justify-center shadow-lg shadow-[#41337A]/20">
                <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <span className="text-xl" style={{ fontWeight: 600, letterSpacing: '-0.02em' }}>Literature Review</span>
                <p className="text-sm text-gray-500">Analyze and synthesize your papers</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Papers Sidebar */}
        <aside className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between mb-2">
              <h3 style={{ fontWeight: 600 }}>Select Papers</h3>
              <span className="px-2 py-1 bg-[#41337A]/10 text-[#41337A] rounded-full text-xs" style={{ fontWeight: 600 }}>
                {selectedPapers.size}/{papers.length}
              </span>
            </div>
            <button
              onClick={selectAllPapers}
              className="text-sm text-[#41337A] hover:underline"
            >
              {selectedPapers.size === papers.length ? 'Deselect All' : 'Select All'}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {papers.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <FileText className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                <p>No papers uploaded yet</p>
              </div>
            ) : (
              papers.map((paper) => (
                <button
                  key={paper.pdf_id}
                  onClick={() => togglePaperSelection(paper.pdf_id)}
                  className={`w-full p-3 rounded-xl text-left transition-all duration-200 flex items-center gap-3 ${
                    selectedPapers.has(paper.pdf_id)
                      ? 'bg-[#41337A]/10 border-2 border-[#41337A]/30'
                      : 'bg-gray-50 border-2 border-transparent hover:bg-gray-100'
                  }`}
                >
                  <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${
                    selectedPapers.has(paper.pdf_id)
                      ? 'bg-[#41337A] text-white'
                      : 'border-2 border-gray-300'
                  }`}>
                    {selectedPapers.has(paper.pdf_id) && <Check className="w-3 h-3" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate" style={{ fontWeight: 500 }}>
                      {paper.filename.replace('.pdf', '')}
                    </p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleFindSimilar(paper.pdf_id);
                    }}
                    className="p-1 hover:bg-gray-200 rounded-lg transition-colors"
                    title="Find similar papers"
                  >
                    <Search className="w-4 h-4 text-gray-500" />
                  </button>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Tabs */}
          <div className="px-6 py-4 bg-white border-b border-gray-200">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveTab('cluster')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  activeTab === 'cluster'
                    ? 'bg-[#41337A] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <Network className="w-4 h-4" />
                Cluster
              </button>
              <button
                onClick={() => setActiveTab('compare')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  activeTab === 'compare'
                    ? 'bg-[#41337A] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <GitCompare className="w-4 h-4" />
                Compare
              </button>
              <button
                onClick={() => setActiveTab('synthesize')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl transition-all ${
                  activeTab === 'synthesize'
                    ? 'bg-[#41337A] text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                <BookOpen className="w-4 h-4" />
                Synthesize
              </button>
            </div>
          </div>

          {/* Tab Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            {/* Similar Papers Result */}
            {similarPapers && (
              <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
                <h4 className="font-semibold text-blue-800 mb-2">
                  Papers similar to "{similarPapers.query_paper}"
                </h4>
                <div className="space-y-2">
                  {similarPapers.similar_papers.map((sp) => (
                    <div key={sp.pdf_id} className="flex items-center justify-between bg-white p-2 rounded-lg">
                      <span className="text-sm">{sp.pdf_id}</span>
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full">
                        {(sp.similarity_score * 100).toFixed(1)}% similar
                      </span>
                    </div>
                  ))}
                </div>
                <button
                  onClick={() => setSimilarPapers(null)}
                  className="mt-3 text-sm text-blue-600 hover:underline"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Cluster Tab */}
            {activeTab === 'cluster' && (
              <div>
                <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
                  <h3 className="text-lg mb-4" style={{ fontWeight: 600 }}>Clustering Options</h3>

                  <div className="grid grid-cols-2 gap-4 mb-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-2">Method</label>
                      <select
                        value={clusterMethod}
                        onChange={(e) => setClusterMethod(e.target.value as typeof clusterMethod)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                      >
                        <option value="hierarchical">Hierarchical (Recommended)</option>
                        <option value="kmeans">K-Means</option>
                        <option value="dbscan">DBSCAN</option>
                      </select>
                    </div>

                    {clusterMethod === 'kmeans' && (
                      <div>
                        <label className="block text-sm text-gray-600 mb-2">Number of Clusters</label>
                        <input
                          type="number"
                          min={2}
                          max={Math.max(2, selectedPapers.size)}
                          value={numClusters}
                          onChange={(e) => setNumClusters(parseInt(e.target.value) || 2)}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                        />
                      </div>
                    )}
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={handleCluster}
                      disabled={isProcessing || selectedPapers.size < 2}
                      className="px-6 py-3 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                      {isProcessing ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Clustering...
                        </>
                      ) : (
                        <>
                          <Network className="w-4 h-4" />
                          Cluster Papers
                        </>
                      )}
                    </button>

                    {savedSessions.length > 0 && (
                      <button
                        onClick={() => setShowSavedSessions(!showSavedSessions)}
                        className="px-4 py-3 border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 transition-all flex items-center gap-2"
                      >
                        <FolderOpen className="w-4 h-4" />
                        Load Saved ({savedSessions.length})
                      </button>
                    )}
                  </div>
                </div>

                {/* Saved Sessions Dropdown */}
                {showSavedSessions && savedSessions.length > 0 && (
                  <div className="bg-white rounded-2xl border border-gray-200 p-4 mb-6">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="text-sm font-semibold text-gray-700">Saved Clustering Sessions</h4>
                      <button
                        onClick={() => setShowSavedSessions(false)}
                        className="p-1 hover:bg-gray-100 rounded"
                      >
                        <X className="w-4 h-4 text-gray-500" />
                      </button>
                    </div>
                    <div className="space-y-2">
                      {savedSessions.map((session) => (
                        <div
                          key={session.session_id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                        >
                          <button
                            onClick={() => loadSavedSession(session)}
                            className="flex-1 text-left"
                          >
                            <p className="text-sm font-medium">{session.name}</p>
                            <p className="text-xs text-gray-500">
                              {session.clusters.length} clusters, {session.total_papers} papers
                            </p>
                          </button>
                          <button
                            onClick={() => handleDeleteSession(session.session_id)}
                            className="p-2 text-red-500 hover:bg-red-50 rounded-lg"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Cluster Results */}
                {clusterResult && (
                  <div className="bg-white rounded-2xl border border-gray-200 p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg" style={{ fontWeight: 600 }}>
                        Clustering Results
                      </h3>
                      <div className="flex items-center gap-3">
                        <span className="text-sm text-gray-500">
                          {clusterResult.num_clusters} clusters from {clusterResult.total_papers} papers
                        </span>
                        <button
                          onClick={() => setSaveDialogOpen(true)}
                          className="px-3 py-1.5 text-sm bg-[#41337A]/10 text-[#41337A] rounded-lg hover:bg-[#41337A]/20 transition-colors flex items-center gap-1.5"
                        >
                          <Save className="w-3.5 h-3.5" />
                          Save
                        </button>
                      </div>
                    </div>

                    {/* Save Dialog */}
                    {saveDialogOpen && (
                      <div className="mb-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Save this clustering result
                        </label>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={sessionName}
                            onChange={(e) => setSessionName(e.target.value)}
                            placeholder="Enter a name for this session..."
                            className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                          />
                          <button
                            onClick={handleSaveCluster}
                            disabled={isProcessing || !sessionName.trim()}
                            className="px-4 py-2 bg-[#41337A] text-white rounded-lg hover:bg-[#5a4a9f] disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                          >
                            {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                            Save
                          </button>
                          <button
                            onClick={() => {
                              setSaveDialogOpen(false);
                              setSessionName('');
                            }}
                            className="px-3 py-2 text-gray-600 hover:bg-gray-200 rounded-lg"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    <div className="space-y-3">
                      {clusterResult.clusters.map((cluster) => (
                        <div
                          key={cluster.id}
                          className="border border-gray-200 rounded-xl overflow-hidden"
                        >
                          <button
                            onClick={() => toggleClusterExpanded(cluster.id)}
                            className="w-full px-4 py-3 bg-gray-50 flex items-center justify-between hover:bg-gray-100 transition-colors"
                          >
                            <div className="flex items-center gap-3">
                              {expandedClusters.has(cluster.id) ? (
                                <ChevronDown className="w-4 h-4 text-gray-500" />
                              ) : (
                                <ChevronRight className="w-4 h-4 text-gray-500" />
                              )}
                              <span style={{ fontWeight: 500 }}>Cluster {cluster.id + 1}</span>
                              <span className="px-2 py-0.5 bg-[#41337A]/10 text-[#41337A] rounded-full text-xs">
                                {cluster.size} papers
                              </span>
                            </div>
                            {cluster.topics.length > 0 && (
                              <div className="flex gap-1">
                                {cluster.topics.slice(0, 3).map((topic, i) => (
                                  <span
                                    key={i}
                                    className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full text-xs"
                                  >
                                    {topic}
                                  </span>
                                ))}
                              </div>
                            )}
                          </button>

                          {expandedClusters.has(cluster.id) && (
                            <div className="px-4 py-3 space-y-2">
                              {cluster.papers.map((paperId) => (
                                <div
                                  key={paperId}
                                  className="flex items-center gap-2 text-sm text-gray-700"
                                >
                                  <FileText className="w-4 h-4 text-gray-400" />
                                  {paperId}
                                </div>
                              ))}
                              {cluster.summary && (
                                <p className="text-sm text-gray-600 mt-3 pt-3 border-t border-gray-100">
                                  {cluster.summary}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>

                    {clusterResult.outliers && clusterResult.outliers.length > 0 && (
                      <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
                        <h4 className="text-sm font-semibold text-amber-800 mb-2">
                          Outliers ({clusterResult.outliers.length})
                        </h4>
                        <p className="text-sm text-amber-700">
                          These papers didn't fit into any cluster: {clusterResult.outliers.join(', ')}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Compare Tab */}
            {activeTab === 'compare' && (
              <div>
                <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
                  <h3 className="text-lg mb-2" style={{ fontWeight: 600 }}>Compare Papers</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Select 2-5 papers to compare their methodologies, findings, and themes.
                  </p>

                  <button
                    onClick={handleCompare}
                    disabled={isProcessing || selectedPapers.size < 2 || selectedPapers.size > 5}
                    className="px-6 py-3 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Comparing...
                      </>
                    ) : (
                      <>
                        <GitCompare className="w-4 h-4" />
                        Compare {selectedPapers.size} Papers
                      </>
                    )}
                  </button>
                </div>

                {/* Compare Results */}
                {compareResult && (
                  <div className="space-y-4">
                    <div className="bg-white rounded-2xl border border-gray-200 p-6">
                      <h4 className="text-lg mb-3" style={{ fontWeight: 600 }}>Key Themes</h4>
                      <div className="flex flex-wrap gap-2">
                        {compareResult.key_themes.map((theme, i) => (
                          <span
                            key={i}
                            className="px-3 py-1 bg-[#41337A]/10 text-[#41337A] rounded-full text-sm"
                          >
                            {theme}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3 text-green-700" style={{ fontWeight: 600 }}>
                          Similarities
                        </h4>
                        <ul className="space-y-2">
                          {compareResult.similarities.map((sim, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                              <span className="text-green-500 mt-1">+</span>
                              {sim}
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3 text-orange-700" style={{ fontWeight: 600 }}>
                          Differences
                        </h4>
                        <ul className="space-y-2">
                          {compareResult.differences.map((diff, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                              <span className="text-orange-500 mt-1">~</span>
                              {diff}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {compareResult.methodology_comparison && (
                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3" style={{ fontWeight: 600 }}>
                          Methodology Comparison
                        </h4>
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">
                          {compareResult.methodology_comparison}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Synthesize Tab */}
            {activeTab === 'synthesize' && (
              <div>
                <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
                  <h3 className="text-lg mb-2" style={{ fontWeight: 600 }}>Synthesize Findings</h3>
                  <p className="text-sm text-gray-600 mb-4">
                    Generate a synthesis of findings across selected papers.
                  </p>

                  <div className="mb-4">
                    <label className="block text-sm text-gray-600 mb-2">
                      Focus Question (optional)
                    </label>
                    <input
                      type="text"
                      value={focusQuestion}
                      onChange={(e) => setFocusQuestion(e.target.value)}
                      placeholder="e.g., What are the main methodological approaches used?"
                      className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                    />
                  </div>

                  <button
                    onClick={handleSynthesize}
                    disabled={isProcessing || selectedPapers.size < 1}
                    className="px-6 py-3 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isProcessing ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Synthesizing...
                      </>
                    ) : (
                      <>
                        <BookOpen className="w-4 h-4" />
                        Synthesize {selectedPapers.size} Papers
                      </>
                    )}
                  </button>
                </div>

                {/* Synthesis Results */}
                {synthesisResult && (
                  <div className="space-y-4">
                    <div className="bg-white rounded-2xl border border-gray-200 p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-lg" style={{ fontWeight: 600 }}>Synthesis</h4>
                        <span className={`px-2 py-1 rounded-full text-xs ${
                          synthesisResult.confidence === 'high'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-yellow-100 text-yellow-700'
                        }`}>
                          {synthesisResult.confidence} confidence
                        </span>
                      </div>
                      <div className="prose prose-sm max-w-none text-gray-700">
                        <p className="whitespace-pre-wrap">{synthesisResult.synthesis}</p>
                      </div>
                    </div>

                    {synthesisResult.findings_comparison && (
                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3" style={{ fontWeight: 600 }}>
                          Findings Comparison
                        </h4>
                        <div className="prose prose-sm max-w-none text-gray-700">
                          <p className="whitespace-pre-wrap">{synthesisResult.findings_comparison}</p>
                        </div>
                      </div>
                    )}

                    {synthesisResult.methodology_comparison && (
                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3" style={{ fontWeight: 600 }}>
                          Methodology Overview
                        </h4>
                        <div className="prose prose-sm max-w-none text-gray-700">
                          <p className="whitespace-pre-wrap">{synthesisResult.methodology_comparison}</p>
                        </div>
                      </div>
                    )}

                    {synthesisResult.citations.length > 0 && (
                      <div className="bg-white rounded-2xl border border-gray-200 p-6">
                        <h4 className="text-lg mb-3" style={{ fontWeight: 600 }}>
                          Citations ({synthesisResult.citations.length})
                        </h4>
                        <div className="space-y-3">
                          {synthesisResult.citations.map((citation) => (
                            <div
                              key={citation.id}
                              className="p-3 bg-gray-50 rounded-lg border border-gray-100"
                            >
                              <div className="flex items-center gap-2 mb-2">
                                <span className="px-2 py-0.5 bg-[#41337A]/10 text-[#41337A] rounded text-xs font-mono">
                                  [{citation.id}]
                                </span>
                                <span className="text-sm font-medium">{citation.document}</span>
                                <span className="text-xs text-gray-500">({citation.section})</span>
                              </div>
                              <p className="text-sm text-gray-600">{citation.text}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

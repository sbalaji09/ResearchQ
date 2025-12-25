import { useState, useEffect } from 'react';
import {
  ArrowLeft,
  FileText,
  Loader2,
  AlertCircle,
  Check,
  Download,
  Eye,
  Sparkles,
  FileDown,
} from 'lucide-react';
import {
  getPapers,
  generateLiteratureReview,
  exportLiteratureReview,
  type PaperInfo,
  type LiteratureReviewResult,
} from '@/api';

interface LiteratureReviewExportProps {
  onBack: () => void;
  sessionId?: string;
}

type CitationStyle = 'apa' | 'mla' | 'chicago';

export function LiteratureReviewExport({ onBack, sessionId }: LiteratureReviewExportProps) {
  const [papers, setPapers] = useState<PaperInfo[]>([]);
  const [selectedPapers, setSelectedPapers] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [title, setTitle] = useState('');
  const [citationStyle, setCitationStyle] = useState<CitationStyle>('apa');

  // generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [reviewResult, setReviewResult] = useState<LiteratureReviewResult | null>(null);

  // export state
  const [isExporting, setIsExporting] = useState<string | null>(null);

  // preview tab
  const [previewSection, setPreviewSection] = useState<string>('introduction');

  useEffect(() => {
    loadPapers();
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

  async function handleGenerate() {
    if (selectedPapers.size < 1) {
      setError('Select at least 1 paper to generate a review');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setReviewResult(null);

    try {
      const result = await generateLiteratureReview(
        sessionId || 'default',
        Array.from(selectedPapers),
        title || undefined,
        citationStyle
      );
      setReviewResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate review');
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleExport(format: 'markdown' | 'latex' | 'docx') {
    if (!reviewResult) return;

    setIsExporting(format);
    setError(null);

    try {
      const blob = await exportLiteratureReview(
        sessionId || 'default',
        format,
        reviewResult
      );

      // create download link
      const url = window.URL.createObjectURL(blob as Blob);
      const a = document.createElement('a');
      a.href = url;

      const extensions: Record<string, string> = {
        markdown: 'md',
        latex: 'tex',
        docx: 'docx',
      };
      a.download = `${reviewResult.title || 'literature-review'}.${extensions[format]}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to export as ${format}`);
    } finally {
      setIsExporting(null);
    }
  }

  const sections = [
    { key: 'introduction', label: 'Introduction' },
    { key: 'methodology_overview', label: 'Methodology' },
    { key: 'key_findings', label: 'Key Findings' },
    { key: 'research_gaps', label: 'Research Gaps' },
    { key: 'conclusion', label: 'Conclusion' },
    { key: 'references', label: 'References' },
  ];

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
                <FileDown className="w-5 h-5 text-white" strokeWidth={2.5} />
              </div>
              <div>
                <span className="text-xl" style={{ fontWeight: 600, letterSpacing: '-0.02em' }}>Export Literature Review</span>
                <p className="text-sm text-gray-500">Generate and export your review</p>
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
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto p-6">
            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700">
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="text-sm">{error}</span>
              </div>
            )}

            {/* Generation Form */}
            <div className="bg-white rounded-2xl border border-gray-200 p-6 mb-6">
              <h3 className="text-lg mb-4" style={{ fontWeight: 600 }}>Review Settings</h3>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm text-gray-600 mb-2">Review Title</label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g., Literature Review on Machine Learning"
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-600 mb-2">Citation Style</label>
                  <select
                    value={citationStyle}
                    onChange={(e) => setCitationStyle(e.target.value as CitationStyle)}
                    className="w-full px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#41337A]"
                  >
                    <option value="apa">APA (American Psychological Association)</option>
                    <option value="mla">MLA (Modern Language Association)</option>
                    <option value="chicago">Chicago</option>
                  </select>
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={isGenerating || selectedPapers.size < 1}
                className="px-6 py-3 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Generating Review...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Generate Review
                  </>
                )}
              </button>
            </div>

            {/* Preview Panel */}
            {reviewResult && (
              <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                  <div className="flex items-center gap-3">
                    <Eye className="w-5 h-5 text-[#41337A]" />
                    <h3 className="text-lg" style={{ fontWeight: 600 }}>Preview</h3>
                  </div>

                  {/* Export Buttons */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleExport('markdown')}
                      disabled={isExporting !== null}
                      className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {isExporting === 'markdown' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      .md
                    </button>
                    <button
                      onClick={() => handleExport('latex')}
                      disabled={isExporting !== null}
                      className="flex items-center gap-2 px-3 py-2 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
                    >
                      {isExporting === 'latex' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      .tex
                    </button>
                    <button
                      onClick={() => handleExport('docx')}
                      disabled={isExporting !== null}
                      className="flex items-center gap-2 px-3 py-2 text-sm bg-[#41337A] text-white hover:bg-[#5a4a9f] rounded-lg transition-colors disabled:opacity-50"
                    >
                      {isExporting === 'docx' ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Download className="w-4 h-4" />
                      )}
                      .docx
                    </button>
                  </div>
                </div>

                {/* Section Tabs */}
                <div className="flex border-b border-gray-200 px-6 overflow-x-auto">
                  {sections.map((section) => (
                    <button
                      key={section.key}
                      onClick={() => setPreviewSection(section.key)}
                      className={`px-4 py-3 text-sm whitespace-nowrap border-b-2 transition-colors ${
                        previewSection === section.key
                          ? 'border-[#41337A] text-[#41337A] font-medium'
                          : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                    >
                      {section.label}
                    </button>
                  ))}
                </div>

                {/* Section Content */}
                <div className="p-6 max-h-96 overflow-y-auto">
                  {previewSection === 'references' ? (
                    <div className="space-y-3">
                      {reviewResult.references.map((ref, i) => (
                        <div key={i} className="text-sm text-gray-700 pl-6 -indent-6">
                          [{i + 1}] {ref.authors.join(', ')} ({ref.year}). <em>{ref.title}</em>.
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="prose prose-sm max-w-none text-gray-700">
                      <h2 className="text-lg font-semibold mb-3">
                        {sections.find(s => s.key === previewSection)?.label}
                      </h2>
                      <p className="whitespace-pre-wrap">
                        {reviewResult[previewSection as keyof Omit<LiteratureReviewResult, 'references' | 'title'>]}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

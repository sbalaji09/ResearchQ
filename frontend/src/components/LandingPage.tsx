import { Upload, FileText, MessageSquare, Sparkles, ArrowRight } from 'lucide-react';

interface LandingPageProps {
  onUpload: () => void;
  onViewPapers: () => void;
  hasPapers: boolean;
}

export function LandingPage({ onUpload, onViewPapers, hasPapers }: LandingPageProps) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-8 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 bg-[#41337A] rounded-lg flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-[#41337A]">ResearchQ</h1>
        </div>
        
        {hasPapers && (
          <button
            onClick={onViewPapers}
            className="text-[#41337A] hover:text-[#41337A]/80 transition-colors flex items-center gap-2"
          >
            View Papers
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </header>

      {/* Hero Section */}
      <main className="flex-1 flex items-center justify-center px-8 pb-16">
        <div className="max-w-4xl mx-auto text-center">
          {/* Main Headline */}
          <div className="mb-8">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#41337A]/5 rounded-full mb-6">
              <Sparkles className="w-4 h-4 text-[#41337A]" />
              <span className="text-sm text-[#41337A]">AI-Powered Research Assistant</span>
            </div>
            
            <h2 className="mb-6" style={{ fontSize: '3.5rem', lineHeight: '1.1', fontWeight: 600 }}>
              Ask questions about your
              <br />
              <span className="text-[#41337A]">research papers</span>
            </h2>
            
            <p className="text-xl text-gray-600 max-w-2xl mx-auto mb-12">
              Upload your research papers and get instant answers to your questions.
              ResearchQ uses advanced AI to understand and analyze academic content.
            </p>
          </div>

          {/* CTA Button */}
          <button
            onClick={onUpload}
            className="bg-[#41337A] text-white px-8 py-4 rounded-xl hover:bg-[#41337A]/90 transition-all shadow-lg shadow-[#41337A]/20 hover:shadow-xl hover:shadow-[#41337A]/30 hover:-translate-y-0.5 flex items-center gap-3 mx-auto group"
            style={{ fontSize: '1.125rem', fontWeight: 500 }}
          >
            <Upload className="w-5 h-5" />
            Upload Research Papers
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Features Grid */}
          <div className="grid md:grid-cols-3 gap-8 mt-24">
            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-[#41337A]/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <Upload className="w-6 h-6 text-[#41337A]" />
              </div>
              <h3 className="mb-3">Upload Papers</h3>
              <p className="text-gray-600">
                Simply drag and drop your PDF research papers to get started
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-[#41337A]/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <MessageSquare className="w-6 h-6 text-[#41337A]" />
              </div>
              <h3 className="mb-3">Ask Questions</h3>
              <p className="text-gray-600">
                Ask natural language questions about methodology, findings, and more
              </p>
            </div>

            <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
              <div className="w-12 h-12 bg-[#41337A]/10 rounded-xl flex items-center justify-center mb-4 mx-auto">
                <FileText className="w-6 h-6 text-[#41337A]" />
              </div>
              <h3 className="mb-3">Get Insights</h3>
              <p className="text-gray-600">
                Receive accurate answers backed by citations from your papers
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-6 text-center text-sm text-gray-500 border-t border-gray-200">
        <p>ResearchQ — Your AI Research Assistant</p>
      </footer>
    </div>
  );
}

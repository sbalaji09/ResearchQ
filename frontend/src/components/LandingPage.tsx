import { Upload, FileText, MessageSquare, Zap, ArrowRight, Sparkles, Lock, BookOpen } from 'lucide-react';

interface LandingPageProps {
  onUpload: () => void;
  onViewPapers: () => void;
  onLitReview: () => void;
  hasPapers: boolean;
}

export function LandingPage({ onUpload, onViewPapers, onLitReview, hasPapers }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Header */}
      <header className="px-6 md:px-12 py-6 flex items-center justify-between max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="absolute inset-0 bg-[#41337A] blur-xl opacity-20 rounded-full"></div>
            <div className="relative w-11 h-11 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-xl flex items-center justify-center shadow-lg">
              <Sparkles className="w-5 h-5 text-white" strokeWidth={2.5} />
            </div>
          </div>
          <span className="text-xl" style={{ fontWeight: 600, letterSpacing: '-0.02em' }}>ResearchQ</span>
        </div>
        
        {hasPapers && (
          <div className="flex items-center gap-2">
            <button
              onClick={onLitReview}
              className="text-gray-700 hover:text-[#41337A] transition-colors flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-100"
            >
              <BookOpen className="w-4 h-4" />
              Literature Review
            </button>
            <button
              onClick={onViewPapers}
              className="text-gray-700 hover:text-[#41337A] transition-colors flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-100"
            >
              My Papers
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </header>

      {/* Hero Section */}
      <section className="px-6 md:px-12 pt-20 pb-32 max-w-7xl mx-auto">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#41337A]/10 to-purple-100/50 rounded-full mb-8 border border-[#41337A]/10">
            <div className="w-2 h-2 bg-[#41337A] rounded-full animate-pulse"></div>
            <span className="text-sm text-[#41337A]" style={{ fontWeight: 500 }}>
              AI-Powered Research Analysis
            </span>
          </div>
          
          {/* Headline */}
          <h1 
            className="mb-6 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-600 bg-clip-text text-transparent"
            style={{ 
              fontSize: '4rem', 
              lineHeight: '1.1', 
              fontWeight: 700,
              letterSpacing: '-0.03em'
            }}
          >
            Unlock insights from
            <br />
            your research papers
          </h1>
          
          <p 
            className="text-gray-600 max-w-2xl mx-auto mb-12 leading-relaxed"
            style={{ fontSize: '1.25rem' }}
          >
            Upload your academic papers and have intelligent conversations with AI 
            that understands the methodology, findings, and implications.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-20">
            <button
              onClick={onUpload}
              className="group relative px-8 py-4 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white rounded-xl hover:shadow-2xl hover:shadow-[#41337A]/30 transition-all duration-300 hover:-translate-y-0.5 flex items-center gap-3"
              style={{ fontSize: '1.0625rem', fontWeight: 500 }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-[#5a4a9f] to-[#41337A] rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
              <span className="relative flex items-center gap-3">
                <Upload className="w-5 h-5" />
                Get Started
                <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
            </button>
            
            <button
              className="px-8 py-4 bg-white text-gray-700 rounded-xl border-2 border-gray-200 hover:border-[#41337A]/30 hover:bg-gray-50 transition-all duration-300 flex items-center gap-2"
              style={{ fontSize: '1.0625rem', fontWeight: 500 }}
            >
              Learn More
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-wrap justify-center gap-8 text-sm text-gray-500">
            <div className="flex items-center gap-2">
              <Lock className="w-4 h-4" />
              <span>Secure & Private</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span>Instant Analysis</span>
            </div>
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>PDF Support</span>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="px-6 md:px-12 py-24 bg-white">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 
              className="mb-4"
              style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}
            >
              Everything you need to understand research
            </h2>
            <p className="text-gray-600 text-lg max-w-2xl mx-auto">
              Powerful AI tools designed specifically for academic research
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {/* Feature 1 */}
            <div className="group p-8 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200 hover:border-[#41337A]/20 hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg shadow-[#41337A]/20">
                <Upload className="w-7 h-7 text-white" />
              </div>
              <h3 className="mb-3" style={{ fontSize: '1.25rem' }}>
                Simple Upload
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Drag and drop your PDF research papers. Our AI processes them instantly, 
                extracting key information and building a searchable knowledge base.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="group p-8 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200 hover:border-[#41337A]/20 hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg shadow-[#41337A]/20">
                <MessageSquare className="w-7 h-7 text-white" />
              </div>
              <h3 className="mb-3" style={{ fontSize: '1.25rem' }}>
                Natural Conversations
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Ask questions in plain English. Get accurate answers about methodology, 
                results, limitations, and implications directly from your papers.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="group p-8 rounded-2xl bg-gradient-to-br from-gray-50 to-white border border-gray-200 hover:border-[#41337A]/20 hover:shadow-xl transition-all duration-300">
              <div className="w-14 h-14 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300 shadow-lg shadow-[#41337A]/20">
                <Zap className="w-7 h-7 text-white" />
              </div>
              <h3 className="mb-3" style={{ fontSize: '1.25rem' }}>
                Instant Insights
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Get immediate responses backed by citations. Understand complex 
                research faster with AI that knows academic contexts and terminology.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="px-6 md:px-12 py-24">
        <div className="max-w-4xl mx-auto text-center bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-3xl p-12 md:p-16 relative overflow-hidden">
          <div className="absolute inset-0 bg-grid-white/10 [mask-image:radial-gradient(white,transparent_70%)]"></div>
          <div className="relative">
            <h2 
              className="text-white mb-4"
              style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}
            >
              Ready to accelerate your research?
            </h2>
            <p className="text-purple-100 text-lg mb-8 max-w-2xl mx-auto">
              Join researchers who are saving hours of time with AI-powered paper analysis
            </p>
            <button
              onClick={onUpload}
              className="bg-white text-[#41337A] px-8 py-4 rounded-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-0.5 inline-flex items-center gap-3"
              style={{ fontSize: '1.0625rem', fontWeight: 600 }}
            >
              <Upload className="w-5 h-5" />
              Upload Your First Paper
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="px-6 md:px-12 py-8 border-t border-gray-200">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-[#41337A] to-[#5a4a9f] rounded-lg flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-gray-600">© 2024 ResearchQ</span>
          </div>
          <p className="text-sm text-gray-500">
            AI-powered research assistant for academics
          </p>
        </div>
      </footer>
    </div>
  );
}

import { useState, useEffect, useRef } from 'react';
import { LandingPage } from './components/LandingPage';
import { UploadPage } from './components/UploadPage';
import { PapersView } from './components/PapersView';
import { LitReviewView } from './components/LitReviewView';
import { cleanupSession } from './api';

type View = 'landing' | 'upload' | 'papers' | 'litreview';

export default function App() {
  const [currentView, setCurrentView] = useState<View>('landing');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedPapers, setUploadedPapers] = useState<Array<{
    id: string;
    title: string;
    file: File;
    uploadDate: Date;
  }>>([]);

  // Use ref to access current sessionId in cleanup handler
  const sessionIdRef = useRef<string | null>(null);
  sessionIdRef.current = sessionId;

  // Cleanup on page unload
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (sessionIdRef.current) {
        cleanupSession(sessionIdRef.current);
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  const handleUpload = (files: File[], newSessionId?: string) => {
    // Update session ID if provided
    if (newSessionId && !sessionId) {
      setSessionId(newSessionId);
    }

    const newPapers = files.map(file => ({
      id: Math.random().toString(36).substring(7),
      title: file.name,
      file,
      uploadDate: new Date()
    }));
    setUploadedPapers([...uploadedPapers, ...newPapers]);
    setCurrentView('papers');
  };

  const handleClearPapers = () => {
    setUploadedPapers([]);
    setCurrentView('landing');
  };

  return (
    <div className="min-h-screen bg-background">
      {currentView === 'landing' && (
        <LandingPage
          onUpload={() => setCurrentView('upload')}
          onViewPapers={() => setCurrentView('papers')}
          onLitReview={() => setCurrentView('litreview')}
          hasPapers={uploadedPapers.length > 0}
        />
      )}
      {currentView === 'upload' && (
        <UploadPage
          onUpload={handleUpload}
          onBack={() => setCurrentView('landing')}
          sessionId={sessionId}
        />
      )}
      {currentView === 'papers' && (
        <PapersView
          papers={uploadedPapers}
          onBack={() => setCurrentView('landing')}
          onUploadMore={() => setCurrentView('upload')}
          onClearPapers={handleClearPapers}
          onLitReview={() => setCurrentView('litreview')}
        />
      )}
      {currentView === 'litreview' && (
        <LitReviewView
          onBack={() => setCurrentView('papers')}
        />
      )}
    </div>
  );
}

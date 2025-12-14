import { useState } from 'react';
import { LandingPage } from './components/LandingPage';
import { UploadPage } from './components/UploadPage';
import { PapersView } from './components/PapersView';

type View = 'landing' | 'upload' | 'papers';

export default function App() {
  const [currentView, setCurrentView] = useState<View>('landing');
  const [uploadedPapers, setUploadedPapers] = useState<Array<{
    id: string;
    title: string;
    file: File;
    uploadDate: Date;
  }>>([]);

  const handleUpload = (files: File[]) => {
    const newPapers = files.map(file => ({
      id: Math.random().toString(36).substring(7),
      title: file.name,
      file,
      uploadDate: new Date()
    }));
    setUploadedPapers([...uploadedPapers, ...newPapers]);
    setCurrentView('papers');
  };

  return (
    <div className="min-h-screen bg-background">
      {currentView === 'landing' && (
        <LandingPage 
          onUpload={() => setCurrentView('upload')}
          onViewPapers={() => setCurrentView('papers')}
          hasPapers={uploadedPapers.length > 0}
        />
      )}
      {currentView === 'upload' && (
        <UploadPage 
          onUpload={handleUpload}
          onBack={() => setCurrentView('landing')}
        />
      )}
      {currentView === 'papers' && (
        <PapersView 
          papers={uploadedPapers}
          onBack={() => setCurrentView('landing')}
          onUploadMore={() => setCurrentView('upload')}
        />
      )}
    </div>
  );
}

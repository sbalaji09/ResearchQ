import { useState, useCallback } from 'react';
import { Upload, File, X, ArrowLeft, Sparkles, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react';
import { uploadPaper } from '@/api';

interface UploadPageProps {
  onUpload: (files: File[], sessionId?: string) => void;
  onBack: () => void;
  sessionId: string | null;
}

interface FileUploadStatus {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function UploadPage({ onUpload, onBack, sessionId }: UploadPageProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<FileUploadStatus[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files).filter(
      file => file.type === 'application/pdf'
    );

    if (files.length > 0) {
      const newFiles = files.map(file => ({ file, status: 'pending' as const }));
      setSelectedFiles(prev => [...prev, ...newFiles]);
      setError(null);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      const newFiles = files.map(file => ({ file, status: 'pending' as const }));
      setSelectedFiles(prev => [...prev, ...newFiles]);
      setError(null);
    }
    // Reset input so same file can be selected again
    e.target.value = '';
  }, []);

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0 || isUploading) return;

    setIsUploading(true);
    setError(null);

    let currentSessionId = sessionId;
    const successfulFiles: File[] = [];

    // Upload files sequentially to maintain session tracking
    for (let i = 0; i < selectedFiles.length; i++) {
      const fileStatus = selectedFiles[i];
      if (fileStatus.status === 'success') continue;

      // Update status to uploading
      setSelectedFiles(prev => prev.map((f, idx) =>
        idx === i ? { ...f, status: 'uploading' as const } : f
      ));

      try {
        const response = await uploadPaper(fileStatus.file, currentSessionId || undefined);
        // Track session ID from first successful upload
        if (!currentSessionId) {
          currentSessionId = response.session_id;
        }
        successfulFiles.push(fileStatus.file);

        // Update status to success
        setSelectedFiles(prev => prev.map((f, idx) =>
          idx === i ? { ...f, status: 'success' as const } : f
        ));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed";
        // Update status to error
        setSelectedFiles(prev => prev.map((f, idx) =>
          idx === i ? { ...f, status: 'error' as const, error: msg } : f
        ));
      }
    }

    setIsUploading(false);

    // If any files uploaded successfully, notify parent
    if (successfulFiles.length > 0) {
      onUpload(successfulFiles, currentSessionId || undefined);
    }
  };

  const pendingCount = selectedFiles.filter(f => f.status === 'pending').length;
  const uploadingCount = selectedFiles.filter(f => f.status === 'uploading').length;
  const successCount = selectedFiles.filter(f => f.status === 'success').length;
  const errorCount = selectedFiles.filter(f => f.status === 'error').length;

  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
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
              <span className="text-xl" style={{ fontWeight: 600, letterSpacing: '-0.02em' }}>ResearchQ</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 md:px-12 py-16 max-w-5xl mx-auto">
        <div className="mb-12 text-center">
          <h2
            className="mb-3"
            style={{ fontSize: '2.5rem', fontWeight: 700, letterSpacing: '-0.02em' }}
          >
            Upload Research Papers
          </h2>
          <p className="text-gray-600 text-lg">
            Add PDF files to start asking questions about your research
          </p>
        </div>

        {/* Upload Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-3xl transition-all duration-300 bg-white overflow-hidden mb-6 ${
            isDragging
              ? 'border-[#41337A] bg-gradient-to-br from-[#41337A]/5 to-purple-50/50 scale-[1.01]'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <div className="p-12 text-center">
            <div className={`relative w-16 h-16 mx-auto mb-4 transition-all duration-300 ${
              isDragging ? 'scale-110' : ''
            }`}>
              <div className={`absolute inset-0 rounded-2xl transition-all duration-300 ${
                isDragging
                  ? 'bg-gradient-to-br from-[#41337A] to-[#5a4a9f] shadow-2xl shadow-[#41337A]/40'
                  : 'bg-gradient-to-br from-gray-100 to-gray-200'
              }`}></div>
              <div className="relative w-full h-full flex items-center justify-center">
                <Upload className={`w-7 h-7 transition-colors duration-300 ${
                  isDragging ? 'text-white' : 'text-gray-400'
                }`} strokeWidth={2} />
              </div>
            </div>

            <h3 className="mb-2" style={{ fontSize: '1.125rem', fontWeight: 600 }}>
              {isDragging ? 'Drop your files here' : 'Drag & drop PDF files'}
            </h3>
            <p className="text-gray-500 mb-4 text-sm">or click below to browse</p>

            <label className="inline-flex items-center gap-2 bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-5 py-2.5 rounded-xl hover:shadow-xl hover:shadow-[#41337A]/30 transition-all duration-300 hover:-translate-y-0.5 cursor-pointer text-sm">
              <File className="w-4 h-4" />
              <span style={{ fontWeight: 500 }}>Choose Files</span>
              <input
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>

            <p className="text-xs text-gray-400 mt-4">Supports PDF files up to 50MB each</p>
          </div>
        </div>

        {/* Selected Files List */}
        {selectedFiles.length > 0 && (
          <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden mb-6">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h3 style={{ fontWeight: 600 }}>Selected Papers</h3>
                <span className="px-2.5 py-1 bg-[#41337A]/10 text-[#41337A] rounded-full text-xs" style={{ fontWeight: 600 }}>
                  {selectedFiles.length}
                </span>
              </div>
              {successCount > 0 && (
                <span className="text-sm text-green-600 flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  {successCount} uploaded
                </span>
              )}
            </div>

            <div className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
              {selectedFiles.map((fileStatus, index) => (
                <div key={index} className="px-5 py-3 flex items-center gap-4">
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                    fileStatus.status === 'success'
                      ? 'bg-green-100'
                      : fileStatus.status === 'error'
                      ? 'bg-red-100'
                      : fileStatus.status === 'uploading'
                      ? 'bg-[#41337A]/10'
                      : 'bg-gray-100'
                  }`}>
                    {fileStatus.status === 'uploading' ? (
                      <Loader2 className="w-5 h-5 text-[#41337A] animate-spin" />
                    ) : fileStatus.status === 'success' ? (
                      <CheckCircle2 className="w-5 h-5 text-green-600" />
                    ) : fileStatus.status === 'error' ? (
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    ) : (
                      <File className="w-5 h-5 text-gray-500" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate" style={{ fontWeight: 500 }}>
                      {fileStatus.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {fileStatus.status === 'error' && fileStatus.error
                        ? <span className="text-red-500">{fileStatus.error}</span>
                        : fileStatus.status === 'uploading'
                        ? 'Uploading...'
                        : fileStatus.status === 'success'
                        ? 'Uploaded successfully'
                        : `${(fileStatus.file.size / 1024 / 1024).toFixed(2)} MB`
                      }
                    </p>
                  </div>

                  {fileStatus.status !== 'uploading' && fileStatus.status !== 'success' && (
                    <button
                      onClick={() => removeFile(index)}
                      className="p-2 hover:bg-red-50 rounded-lg transition-all duration-300"
                      title="Remove file"
                    >
                      <X className="w-4 h-4 text-red-500" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Upload button */}
        {selectedFiles.length > 0 && (pendingCount > 0 || errorCount > 0) && (
          <button
            onClick={handleUpload}
            disabled={isUploading || (pendingCount === 0 && errorCount === 0)}
            className={`w-full bg-gradient-to-r from-[#41337A] to-[#5a4a9f] text-white px-6 py-4 rounded-xl transition-all duration-300 flex items-center justify-center gap-2 ${
              isUploading
                ? 'opacity-70 cursor-not-allowed'
                : 'hover:shadow-2xl hover:shadow-[#41337A]/30 hover:-translate-y-0.5'
            }`}
            style={{ fontWeight: 600 }}
          >
            {isUploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Uploading {uploadingCount > 0 ? `(${successCount + 1}/${selectedFiles.length})` : '...'}
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Upload {pendingCount + errorCount} Paper{pendingCount + errorCount > 1 ? 's' : ''}
              </>
            )}
          </button>
        )}

        {/* All done - proceed button */}
        {selectedFiles.length > 0 && successCount === selectedFiles.length && (
          <div className="text-center">
            <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-xl flex items-center justify-center gap-3 text-green-700">
              <CheckCircle2 className="w-5 h-5" />
              <span>All papers uploaded successfully!</span>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

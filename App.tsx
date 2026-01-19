
import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DocumentAnalyzerCard from './components/DocumentAnalyzerCard';
import DocumentHistoryTable from './components/DocumentHistoryTable';
import RegisterLoginCard from './components/RegisterLoginCard'; // New import
import { LOCAL_STORAGE_USER_ID_KEY } from './constants'; // New import

const App: React.FC = () => {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [lastAnalyzedDocumentId, setLastAnalyzedDocumentId] = useState<string | null>(null);
  const [appError, setAppError] = useState<string | null>(null);

  // Check for stored user ID on app load
  useEffect(() => {
    const storedUserId = localStorage.getItem(LOCAL_STORAGE_USER_ID_KEY);
    if (storedUserId) {
      setCurrentUserId(storedUserId);
    }
  }, []);

  const handleDocumentAnalyzed = (documentId: string) => {
    setLastAnalyzedDocumentId(documentId);
    setAppError(null); // Clear any previous app-level errors
  };

  const handleAnalysisError = (error: string) => {
    setAppError(error);
  };

  const handleLoginSuccess = (userId: string) => {
    setCurrentUserId(userId);
    setAppError(null); // Clear any login-related errors
  };

  const handleLogout = () => {
    setCurrentUserId(null);
    setAppError(null);
    setLastAnalyzedDocumentId(null); // Clear analysis history as well
  };

  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-gray-900 text-gray-100">
      <Sidebar currentUserId={currentUserId} onLogout={handleLogout} />
      <main className="flex-1 p-4 md:ml-64 lg:p-8"> {/* Adjusted margin for sidebar */}
        <div className="container mx-auto space-y-8">
          {appError && (
            <div className="bg-red-800 text-red-100 p-4 rounded-lg text-center mb-6">
              <h3 className="font-bold text-lg">Грешка в приложението:</h3>
              <p>{appError}</p>
              <p className="text-sm mt-2">Моля, опитайте отново или се свържете с поддръжката, ако проблемът продължава.</p>
            </div>
          )}

          {!currentUserId ? (
            <section id="register-login">
              <RegisterLoginCard onLoginSuccess={handleLoginSuccess} onLoginError={handleAnalysisError} />
            </section>
          ) : (
            <>
              <section id="analyze-document">
                <DocumentAnalyzerCard onDocumentAnalyzed={handleDocumentAnalyzed} onAnalysisError={handleAnalysisError} currentUserId={currentUserId} />
              </section>

              <section id="document-history">
                <DocumentHistoryTable currentUserId={currentUserId} lastAnalyzedDocumentId={lastAnalyzedDocumentId} />
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;
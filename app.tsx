import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import DocumentAnalyzerCard from './components/DocumentAnalyzerCard';
import DocumentHistoryTable from './components/DocumentHistoryTable';
// import RegisterLoginCard from './components/RegisterLoginCard'; // DEPRECATED: Replaced by multi-step authentication flow
import EmailInputCard from './components/EmailInputCard'; // New component
import AuthMethodChooserCard from './components/AuthMethodChooserCard'; // New component
import PasswordLoginCard from './components/PasswordLoginCard'; // New component
import OtpRequestCard from './components/OtpRequestCard'; // New component
import OtpVerificationCard from './components/OtpVerificationCard'; // New component
import { LOCAL_STORAGE_USER_ID_KEY, LOCAL_STORAGE_USER_VERIFIED_KEY } from './constants';
import { UserResponse } from './types'; // Assuming UserResponse now includes is_verified

type AuthFlowState = 'email_input' | 'choose_method' | 'register_with_password' | 'login_with_password' | 'request_otp' | 'verify_otp' | 'authenticated';

const App: React.FC = () => {
  const [currentUserId, setCurrentUserId] = useState<string | null>(null);
  const [isUserVerified, setIsUserVerified] = useState<boolean>(false);
  const [lastAnalyzedDocumentId, setLastAnalyzedDocumentId] = useState<string | null>(null);
  const [appError, setAppError] = useState<string | null>(null);

  const [currentAuthFlowState, setCurrentAuthFlowState] = useState<AuthFlowState>('email_input');
  const [tempEmail, setTempEmail] = useState<string | null>(null); // To carry email between flow steps

  // Check for stored user ID and verification status on app load
  useEffect(() => {
    const storedUserId = localStorage.getItem(LOCAL_STORAGE_USER_ID_KEY);
    const storedVerifiedStatus = localStorage.getItem(LOCAL_STORAGE_USER_VERIFIED_KEY);

    if (storedUserId) {
      setCurrentUserId(storedUserId);
      setIsUserVerified(storedVerifiedStatus === 'true');
      setCurrentAuthFlowState('authenticated');
    } else {
      setCurrentAuthFlowState('email_input');
    }
  }, []);

  const handleLoginSuccess = useCallback((userData: UserResponse) => {
    setCurrentUserId(userData.id);
    setIsUserVerified(userData.is_verified);
    localStorage.setItem(LOCAL_STORAGE_USER_ID_KEY, userData.id);
    localStorage.setItem(LOCAL_STORAGE_USER_VERIFIED_KEY, String(userData.is_verified));
    setCurrentAuthFlowState('authenticated');
    setAppError(null);
  }, []);

  const handleLogout = useCallback(() => {
    setCurrentUserId(null);
    setIsUserVerified(false);
    localStorage.removeItem(LOCAL_STORAGE_USER_ID_KEY);
    localStorage.removeItem(LOCAL_STORAGE_USER_VERIFIED_KEY);
    setLastAnalyzedDocumentId(null);
    setAppError(null);
    setTempEmail(null);
    setCurrentAuthFlowState('email_input'); // Reset to initial state
  }, []);

  const handleDocumentAnalyzed = (documentId: string) => {
    setLastAnalyzedDocumentId(documentId);
    setAppError(null);
  };

  const handleAnalysisError = (error: string) => {
    setAppError(error);
  };

  const handleEmailSubmitted = (email: string) => {
    setTempEmail(email);
    setCurrentAuthFlowState('choose_method');
    setAppError(null);
  };

  // Render authentication flow based on state
  const renderAuthFlow = () => {
    switch (currentAuthFlowState) {
      case 'email_input':
        return <EmailInputCard onEmailSubmitted={handleEmailSubmitted} onLoginError={handleAnalysisError} />;
      case 'choose_method':
        if (!tempEmail) {
          setCurrentAuthFlowState('email_input'); // Fallback if email is lost
          return null;
        }
        return (
          <AuthMethodChooserCard
            email={tempEmail}
            onChoosePassword={() => setCurrentAuthFlowState('login_with_password')}
            onChooseOtp={() => setCurrentAuthFlowState('request_otp')}
            onBack={() => setCurrentAuthFlowState('email_input')}
            onLoginSuccess={handleLoginSuccess} // Pass through for direct registration
            onLoginError={handleAnalysisError}
          />
        );
      case 'login_with_password':
        if (!tempEmail) {
          setCurrentAuthFlowState('email_input');
          return null;
        }
        return (
          <PasswordLoginCard
            email={tempEmail}
            onLoginSuccess={handleLoginSuccess}
            onLoginError={handleAnalysisError}
            onBack={() => setCurrentAuthFlowState('choose_method')}
          />
        );
      case 'request_otp':
        if (!tempEmail) {
          setCurrentAuthFlowState('email_input');
          return null;
        }
        return (
          <OtpRequestCard
            email={tempEmail}
            onRequestSuccess={() => setCurrentAuthFlowState('verify_otp')}
            onRequestError={handleAnalysisError}
            onBack={() => setCurrentAuthFlowState('choose_method')}
          />
        );
      case 'verify_otp':
        if (!tempEmail) {
          setCurrentAuthFlowState('email_input');
          return null;
        }
        return (
          <OtpVerificationCard
            email={tempEmail}
            onVerificationSuccess={handleLoginSuccess}
            onVerificationError={handleAnalysisError}
            onBack={() => setCurrentAuthFlowState('request_otp')}
          />
        );
      default:
        return null; // Should not happen in 'authenticated' state
    }
  };

  return (
    <div className="flex flex-col md:flex-row min-h-screen bg-gray-900 text-gray-100">
      <Sidebar currentUserId={currentUserId} isUserVerified={isUserVerified} onLogout={handleLogout} />
      <main className="flex-1 p-4 md:ml-64 lg:p-8">
        <div className="container mx-auto space-y-8">
          {appError && (
            <div className="bg-red-800 text-red-100 p-4 rounded-lg text-center mb-6">
              <h3 className="font-bold text-lg">Грешка в приложението:</h3>
              <p>{appError}</p>
              <p className="text-sm mt-2">Моля, опитайте отново или се свържете с поддръжката, ако проблемът продължава.</p>
            </div>
          )}

          {currentAuthFlowState !== 'authenticated' ? (
            <section id="auth-flow">
              {renderAuthFlow()}
            </section>
          ) : (
            <>
              <section id="analyze-document">
                <DocumentAnalyzerCard onDocumentAnalyzed={handleDocumentAnalyzed} onAnalysisError={handleAnalysisError} currentUserId={currentUserId} isUserVerified={isUserVerified} />
              </section>

              <section id="document-history">
                <DocumentHistoryTable currentUserId={currentUserId} isUserVerified={isUserVerified} lastAnalyzedDocumentId={lastAnalyzedDocumentId} />
              </section>
            </>
          )}
        </div>
      </main>
    </div>
  );
};

export default App;

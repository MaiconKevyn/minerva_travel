
import React, { lazy, Suspense } from 'react';
import { Route, Routes, BrowserRouter as Router } from 'react-router-dom';
import { Toaster } from 'sonner';
import ScrollToTop from './components/ScrollToTop';
import { AuthProvider } from './contexts/AuthContext.jsx';
import { ConversationalGuideProvider } from './contexts/ConversationalGuideContext.jsx';
import { ThemeProvider } from './contexts/ThemeContext.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';

const HomePage = lazy(() => import('./pages/HomePage.jsx'));
const SignupPage = lazy(() => import('./pages/SignupPage.jsx'));
const LoginPage = lazy(() => import('./pages/LoginPage.jsx'));
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage.jsx'));
const DashboardPage = lazy(() => import('./pages/DashboardPage.jsx'));
const PricingPage = lazy(() => import('./pages/PricingPage.jsx'));
const ProtectedCreateGuidePage = lazy(() => import('./pages/ProtectedCreateGuidePage.jsx'));
const PrivacyPage = lazy(() => import('./pages/PrivacyPage.jsx'));
const TermsPage = lazy(() => import('./pages/TermsPage.jsx'));

const PageFallback = () => (
  <div
    className="flex min-h-screen items-center justify-center bg-background text-foreground"
    role="status"
    aria-live="polite"
  >
    Carregando página...
  </div>
);

function App() {
  const focusMainContent = (event) => {
    event.preventDefault();
    const main = document.getElementById('main-content');
    if (!main) return;
    window.history.replaceState(window.history.state, '', '#main-content');
    main.focus();
    main.scrollIntoView({ block: 'start' });
  };

  return (
    <ThemeProvider>
      <AuthProvider>
        <Router>
          <a
            href="#main-content"
            onClick={focusMainContent}
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-lg focus:bg-primary focus:px-4 focus:py-3 focus:font-bold focus:text-primary-foreground"
          >
            Pular para o conteúdo principal
          </a>
          <ScrollToTop />
          <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/pricing" element={<PricingPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/privacy" element={<PrivacyPage />} />
            <Route path="/terms" element={<TermsPage />} />

            <Route path="/dashboard" element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } />

            <Route path="/create" element={
              <ConversationalGuideProvider>
                <ProtectedCreateGuidePage />
              </ConversationalGuideProvider>
            } />

            {/* Catch-all route for 404s */}
            <Route path="*" element={
              <div className="min-h-screen flex flex-col items-center justify-center bg-background text-center p-4 transition-colors duration-200">
                <h1 className="text-6xl font-serif font-bold text-primary mb-4">404</h1>
                <p className="text-xl text-muted-foreground mb-8 font-medium">Ops! Parece que você se perdeu nesta aventura.</p>
                <a href="/" className="px-8 py-4 bg-secondary text-white rounded-full font-medium hover:bg-secondary/90 transition-colors">
                  Voltar ao Início
                </a>
              </div>
            } />
          </Routes>
          </Suspense>
          <Toaster
            toastOptions={{
              className: 'bg-card font-medium border-2 border-primary/20 text-foreground rounded-2xl shadow-xl',
            }}
          />
        </Router>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

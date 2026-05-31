
import React from 'react';
import { Route, Routes, BrowserRouter as Router } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import ScrollToTop from './components/ScrollToTop';
import HomePage from './pages/HomePage.jsx';
import CreateGuidePage from './pages/CreateGuidePage.jsx';

function App() {
  return (
    <Router>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/create" element={<CreateGuidePage />} />
        {/* Catch-all route for 404s */}
        <Route path="*" element={
          <div className="min-h-screen flex flex-col items-center justify-center bg-[#FDFBF7] text-center p-4">
            <h1 className="text-6xl font-serif font-bold text-primary mb-4">404</h1>
            <p className="text-xl text-muted-foreground mb-8 font-medium">Ops! Parece que você se perdeu nesta aventura.</p>
            <a href="/" className="px-8 py-4 bg-secondary text-white rounded-full font-medium hover:bg-secondary/90 transition-colors">
              Voltar ao Início
            </a>
          </div>
        } />
      </Routes>
      <Toaster 
        toastOptions={{
          className: 'bg-white font-medium border-2 border-primary/20 text-foreground rounded-2xl shadow-xl',
        }}
      />
    </Router>
  );
}

export default App;

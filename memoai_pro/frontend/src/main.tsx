import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';

import App from './App';
import { AuthProvider } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';
import { ToastProvider } from './context/ToastContext';
import './styles/global.css';
import './styles/app.css';
import PwaPrompts from './pwa/PwaPrompts';
import { initPwa } from './pwa/pwa';

initPwa();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <App />
            <PwaPrompts />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </BrowserRouter>
  </StrictMode>,
);

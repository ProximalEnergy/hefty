import * as Sentry from '@sentry/react'
import '@tanstack/react-query'
import { AxiosError } from 'axios'
import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App.tsx'
import { ThemeProvider } from './contexts/ThemeContext.tsx'
import './index.css'

// Initialize Sentry only in production
if (import.meta.env.VITE_ENVIRONMENT === 'PRODUCTION') {
  Sentry.init({
    dsn: 'https://8ff693545e0977d5bf3710df789065bd@o4506555874672640.ingest.sentry.io/4506592803094528',
    tracePropagationTargets: ['localhost', /^https:\/\/yourserver\.io\/api/],
    integrations: [
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],
    // Performance Monitoring
    tracesSampleRate: 0.0, //  Capture 0% of the transactions
    // Session Replay
    replaysSessionSampleRate: 0.1, // This sets the sample rate at 10%. You may want to change it to 100% while in development and then sample at a lower rate in production.
    replaysOnErrorSampleRate: 1.0, // If you're not already sampling the entire session, change the sample rate to 100% when sampling sessions where errors occur.
  })
}

// Define default error type for react-query
type ErrorData = {
  detail: string
}

declare module '@tanstack/react-query' {
  interface Register {
    defaultError: AxiosError<ErrorData>
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)

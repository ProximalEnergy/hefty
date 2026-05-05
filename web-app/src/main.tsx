import { PostHogProvider } from '@posthog/react'
import * as Sentry from '@sentry/react'
import '@tanstack/react-query'
import { AxiosError } from 'axios'
import type { PostHogConfig } from 'posthog-js'
import { StrictMode } from 'react'
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

const posthogOptions: Partial<PostHogConfig> = {
  api_host: import.meta.env.VITE_PUBLIC_POSTHOG_HOST,
  autocapture: false,
  capture_pageview: false,
  defaults: '2026-01-30',
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <PostHogProvider
      apiKey={import.meta.env.VITE_PUBLIC_POSTHOG_KEY}
      options={posthogOptions}
    >
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </PostHogProvider>
    ,
  </StrictMode>,
)

let calculatedBaseURL: string

if (import.meta.env.VITE_ENVIRONMENT === 'PRODUCTION') {
  calculatedBaseURL = 'https://api.proximal.energy'
} else if (import.meta.env.VITE_ENVIRONMENT === 'STAGING') {
  calculatedBaseURL = 'https://api.staging.proximal.energy'
} else {
  calculatedBaseURL = 'http://127.0.0.1:8000' // Default to DEV
}

export const baseURL = calculatedBaseURL

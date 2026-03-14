const environment = import.meta.env.VITE_ENVIRONMENT
const apiBaseUrlOverride = import.meta.env.VITE_API_BASE_URL?.trim()

let calculatedBaseURL: string

if (apiBaseUrlOverride) {
  calculatedBaseURL = apiBaseUrlOverride
} else if (environment === 'PRODUCTION') {
  calculatedBaseURL = 'https://api.proximal.energy'
} else if (environment === 'STAGING') {
  calculatedBaseURL = 'https://api.staging.proximal.energy'
} else if (environment === 'SANDBOX') {
  calculatedBaseURL = 'https://api.sandbox.proximal.energy'
} else {
  calculatedBaseURL = 'http://127.0.0.1:8000' // Default to DEV
}

export const baseURL = calculatedBaseURL

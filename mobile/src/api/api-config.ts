type ApiEnvironment = 'PRODUCTION' | 'STAGING' | 'SANDBOX' | 'DEMO' | string | undefined;

const apiBaseUrlOverride = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
const environment: ApiEnvironment = process.env.EXPO_PUBLIC_ENVIRONMENT;

function getEnvironmentBaseUrl(environmentName: ApiEnvironment) {
  switch (environmentName) {
    case 'PRODUCTION':
      return 'https://api.proximal.energy';
    case 'STAGING':
      return 'https://api.staging.proximal.energy';
    case 'SANDBOX':
      return 'https://api.sandbox.proximal.energy';
    case 'DEMO':
      return 'https://api.demo.proximal.energy';
    default:
      return 'http://127.0.0.1:8000';
  }
}

export const apiBaseUrl = apiBaseUrlOverride || getEnvironmentBaseUrl(environment);

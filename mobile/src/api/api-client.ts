import { apiBaseUrl } from '@/api/api-config';

export type QueryParams = Record<
  string,
  string | number | boolean | null | undefined | (string | number)[]
>;

type GetToken = (options?: { template?: string }) => Promise<string | null>;

function buildQueryString(queryParams: QueryParams) {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(queryParams)) {
    if (value === undefined || value === null) {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        searchParams.append(key, String(item));
      }
      continue;
    }

    searchParams.append(key, String(value));
  }

  const query = searchParams.toString();
  return query ? `?${query}` : '';
}

async function request<T>(
  getToken: GetToken,
  path: string,
  queryParams: QueryParams = {},
) {
  const token = await getToken({ template: 'default' });
  const url = `${apiBaseUrl}${path}${buildQueryString(queryParams)}`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export function createApiClient(getToken: GetToken) {
  return {
    get<T>(path: string, queryParams: QueryParams = {}) {
      return request<T>(getToken, path, queryParams);
    },
  };
}

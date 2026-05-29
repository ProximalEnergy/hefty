import { useAuth } from '@clerk/expo';
import { useQuery, type UseQueryOptions } from '@tanstack/react-query';

import { createApiClient, type QueryParams } from '@/api/api-client';

export type Project = {
  project_id: string;
  name_long: string;
  name_short?: string;
};

type UseGetProjectsOptions = {
  queryParams?: QueryParams;
  queryOptions?: Omit<UseQueryOptions<Project[], Error>, 'queryKey' | 'queryFn'>;
};

export function useGetProjects({ queryParams = {}, queryOptions = {} }: UseGetProjectsOptions = {}) {
  const auth = useAuth();
  const { getToken, isLoaded, isSignedIn } = auth;
  const api = createApiClient(getToken);
  const isReadyForApi = isLoaded && isSignedIn === true;
  const isEnabled = isReadyForApi && queryOptions.enabled !== false;

  return useQuery<Project[], Error>({
    queryKey: ['getProjects', queryParams],
    queryFn: async () => {
      return api.get<Project[]>('/v1/operational/projects', queryParams);
    },
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    ...queryOptions,
    enabled: isEnabled,
  });
}

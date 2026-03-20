import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

import { UserProjectLabel } from '../user_project_labels'

const URL_GET_USER_PROJECT_LABELS_BY_PROJECT_ID =
  '/v1/operational/projects/{project_id}/user-project-labels'

export const useGetUserProjectLabelsByProjectId = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { project_id: string } //Can we pull this in from the schema.d.ts type as well?
  queryOptions?: Partial<UseQueryOptions<UserProjectLabel[]>>
}) => {
  const axiosConfig = {
    url: URL_GET_USER_PROJECT_LABELS_BY_PROJECT_ID,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<UserProjectLabel[]>({
    axiosConfig,
    queryName: 'getUserProjectLabelsByProjectId',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

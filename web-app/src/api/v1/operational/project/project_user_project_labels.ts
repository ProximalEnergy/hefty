import { UserProjectLabel } from '@/api/v1/operational/user_project_labels'
import { useCustomQuery } from '@/hooks/api'
import { QUERY_TIME } from '@/utils/queryTiming'
import { UseQueryOptions } from '@tanstack/react-query'

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
    staleTime: QUERY_TIME.NEVER,
  }

  return useCustomQuery<UserProjectLabel[]>({
    axiosConfig,
    queryName: 'getUserProjectLabelsByProjectId',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/react'
import { UseQueryOptions, useMutation } from '@tanstack/react-query'
import axios from 'axios'

interface ProjectSystemFileStatus {
  bucket_name: string
  file_key: string
  exists: boolean
}

export const useGetProjectSystemFileStatus = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/commissioning/projects/{project_id}/system/file-status',
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 60_000,
  }

  return useCustomQuery<ProjectSystemFileStatus>({
    axiosConfig,
    queryName: 'getProjectSystemFileStatus',
    pathParams: { project_id: pathParams.projectId },
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useImportProjectSystem = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const token = await getToken({ template: 'default' })

      const response = await axios({
        method: 'put',
        url: `${baseURL}/v1/commissioning/projects/${projectId}/system/import`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}

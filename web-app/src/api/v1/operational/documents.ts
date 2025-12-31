import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface ProjectDocument {
  document_id: string
  name: string
  url: string
  contract_name?: string
}

export const useGetProjectDocuments = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/documents`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  }

  return useCustomQuery<ProjectDocument[]>({
    axiosConfig,
    queryName: 'getProjectDocuments',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useUploadProjectDocument = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      projectId,
      file,
    }: {
      projectId: string
      file: File
    }) => {
      const token = await getToken({ template: 'default' })
      const formData = new FormData()
      formData.append('file', file)

      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/documents`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        data: formData,
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getProjectDocuments', { projectId: variables.projectId }],
      })
    },
  })
}

export const useDeleteProjectDocument = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      projectId,
      documentId,
    }: {
      projectId: string
      documentId: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/projects/${projectId}/documents/${documentId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getProjectDocuments', { projectId: variables.projectId }],
      })
    },
  })
}

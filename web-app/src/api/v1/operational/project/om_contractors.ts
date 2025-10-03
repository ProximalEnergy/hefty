import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseMutationResult,
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export interface OMContractorScope {
  om_contractor_scope_id: number
  project_id: string
  company_id: string
  company_name_short?: string
  company_name_long?: string
  scope_json: {
    device_type_ids: number[]
  }
  contractor_addressee?: string | null
  contractor_email?: string | null
  contractor_phone?: string | null
}

export const useGetOMContractorScopes = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/om-contractors/`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<OMContractorScope[]>({
    axiosConfig,
    queryName: 'getOMContractorScopes',
    pathParams,
    queryOptions,
  })
}

export const useCreateOMContractorScope = ({
  projectId,
}: {
  projectId: string
}): UseMutationResult<
  any,
  unknown,
  {
    company_id: string
    device_type_ids: number[]
    contractor_addressee?: string
    contractor_email?: string
    contractor_phone?: string
  }
> => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload) => {
      const token = await getToken({ template: 'default' })
      const data = {
        company_id: payload.company_id,
        scope_json: { device_type_ids: payload.device_type_ids },
        contractor_addressee: payload.contractor_addressee,
        contractor_email: payload.contractor_email,
        contractor_phone: payload.contractor_phone,
      }
      const path = `/v1/operational/projects/${projectId}/om-contractors/`
      const apiUrl = `${baseURL}${path}`
      const res = await axios({
        method: 'post',
        url: apiUrl,
        headers: { Authorization: `Bearer ${token}` },
        data,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getOMContractorScopes'] })
    },
  })
}

export const useUpdateOMContractorScope = ({
  projectId,
}: {
  projectId: string
}): UseMutationResult<
  any,
  unknown,
  {
    om_contractor_scope_id: number
    device_type_ids: number[]
    contractor_addressee?: string
    contractor_email?: string
    contractor_phone?: string
  }
> => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload) => {
      const token = await getToken({ template: 'default' })
      const data = {
        scope_json: { device_type_ids: payload.device_type_ids },
        contractor_addressee: payload.contractor_addressee,
        contractor_email: payload.contractor_email,
        contractor_phone: payload.contractor_phone,
      }
      const path = `/v1/operational/projects/${projectId}/om-contractors/${payload.om_contractor_scope_id}`
      const apiUrl = `${baseURL}${path}`
      const res = await axios({
        method: 'put',
        url: apiUrl,
        headers: { Authorization: `Bearer ${token}` },
        data,
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getOMContractorScopes'] })
    },
  })
}

export const useDeleteOMContractorScope = ({
  projectId,
}: {
  projectId: string
}): UseMutationResult<
  any,
  unknown,
  {
    om_contractor_scope_id: number
  }
> => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (payload) => {
      const token = await getToken({ template: 'default' })
      const path = `/v1/operational/projects/${projectId}/om-contractors/${payload.om_contractor_scope_id}`
      const apiUrl = `${baseURL}${path}`
      const res = await axios({
        method: 'delete',
        url: apiUrl,
        headers: { Authorization: `Bearer ${token}` },
      })
      return res.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getOMContractorScopes'] })
    },
  })
}

import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface Contract {
  contract_id: number
  project_id: string
  document_id: string
  company_id_provider: string
  company_id_counter: string
  execution_date: string
  name_short: string
  name_long: string
  document_url?: string
  s3_key?: string
  openai_file_id?: string
  // New optional fields
  contract_category_id?: number | null
  category_name_short?: string | null
  category_name_long?: string | null
  term_start_date?: string | null
  term_end_date?: string | null
  counter_contact_addressee?: string | null
  counter_contact_email?: string | null
  counter_contact_address?: string | null
  contract_summary?: string | null
}

export const useGetProjectContracts = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/contracts/`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<Contract[]>({
    axiosConfig,
    queryName: 'getProjectContracts',
    pathParams,
    queryParams: {},
    queryOptions: queryOptions,
  })
}

export const useCreateContract = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      document_id,
      company_id_provider,
      company_id_counter,
      execution_date,
      contract_category_name_short,
      contract_category_id,
      term_start_date,
      term_end_date,
      counter_contact_addressee,
      counter_contact_email,
      counter_contact_address,
      contract_summary,
    }: {
      project_id: string
      document_id: string
      company_id_provider: string
      company_id_counter: string
      execution_date: string
      contract_category_name_short?: string | null
      contract_category_id?: number | null
      term_start_date?: string | null
      term_end_date?: string | null
      counter_contact_addressee?: string | null
      counter_contact_email?: string | null
      counter_contact_address?: string | null
      contract_summary?: string | null
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${project_id}/contracts/`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          project_id,
          document_id,
          company_id_provider,
          company_id_counter,
          execution_date,
          contract_category_name_short,
          contract_category_id,
          term_start_date,
          term_end_date,
          counter_contact_addressee,
          counter_contact_email,
          counter_contact_address,
          contract_summary,
        },
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getProjectContracts', { projectId: variables.project_id }],
      })
      queryClient.invalidateQueries({
        queryKey: ['getProjectDocuments', { projectId: variables.project_id }],
      })
    },
  })
}

export const useAnalyzeContractDocument = () => {
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
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${projectId}/contracts/analyze-document/${documentId}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: ['getProjectContracts', { projectId: variables.projectId }],
      })
    },
  })
}

export const useGetContractKPIs = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; contractId: number }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/contracts/${pathParams.contractId}/kpis`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 30_000,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<any[]>({
    axiosConfig,
    queryName: 'getContractKPIs',
    pathParams,
    queryParams: {},
    queryOptions,
  })
}

interface ContractCategory {
  contract_category_id: number
  name_short: string
  name_long: string
}

export const useGetContractCategories = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
} = {}) => {
  const axiosConfig = {
    url: `/v1/operational/contract-categories/`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<ContractCategory[]>({
    axiosConfig,
    queryName: 'getContractCategories',
    pathParams: {},
    queryParams: {},
    queryOptions,
  })
}

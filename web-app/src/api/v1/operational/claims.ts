import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

// --- Types ---

export interface ClaimConfig {
  claim_config_id: number
  submitter_company_id: string
  counterparty_company_id: string
  project_id: string | null
  default_submission_channel: string
  default_contact: string | null
  portal_url: string | null
  counterparty_name: string | null
}

export interface ClaimListItem {
  claim_id: number
  claim_config_id: number
  status: string
  summary: string | null
  external_reference: string | null
  counterparty_name: string | null
  created_at: string | null
  updated_at: string | null
  device_count: number
  claim_event_ids?: number[]
}

interface ClaimDevice {
  claim_device_id: number
  claim_id: number
  device_id: number
  event_id: number | null
  oem_serial_number: string | null
  oem_part_number: string | null
  notes: string | null
  device_name: string | null
}

interface ClaimUpdateEntry {
  claim_update_id: number
  claim_id: number
  update_type: string
  from_status: string | null
  to_status: string | null
  message: string | null
  user_id: string
  created_at: string
  user_name: string | null
}

interface ClaimAttachment {
  claim_id: number
  s3_key: string
  filename: string
  content_type: string | null
  uploaded_at: string | null
  url: string | null
  claim_update_id: number | null
}

interface ClaimDetail {
  claim_id: number
  claim_config_id: number
  status: string
  summary: string | null
  external_reference: string | null
  counterparty_name: string | null
  created_at: string | null
  updated_at: string | null
  devices: ClaimDevice[]
  updates: ClaimUpdateEntry[]
  attachments: ClaimAttachment[]
}

// --- Query Hooks ---

const BASE = '/v1/operational/projects'
const CLAIM_EVENT_DATA_CSV_URL =
  '/v1/operational/projects/{project_id}/claims/event-data-csv'

function filenameFromContentDisposition(
  value: string | undefined,
): string | null {
  if (!value) return null
  const match = value.match(/filename="?([^"]+)"?/i)
  return match?.[1] ?? null
}

export const useGetClaimConfigs = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) =>
  useCustomQuery<ClaimConfig[]>({
    axiosConfig: {
      url: `${BASE}/${pathParams.projectId}/claims/configs`,
    },
    queryName: 'getClaimConfigs',
    pathParams,
    queryOptions: {
      refetchOnWindowFocus: false,
      staleTime: QUERY_TIME.FIVE_MINUTES,
      ...queryOptions,
    },
  })

export const useGetProjectClaims = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) =>
  useCustomQuery<ClaimListItem[]>({
    axiosConfig: {
      url: `${BASE}/${pathParams.projectId}/claims`,
    },
    queryName: 'getProjectClaims',
    pathParams,
    queryOptions: {
      refetchOnWindowFocus: false,
      staleTime: QUERY_TIME.ONE_MINUTE,
      ...queryOptions,
    },
  })

export const useGetClaimById = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; claimId: string }
  queryOptions?: Partial<UseQueryOptions>
}) =>
  useCustomQuery<ClaimDetail>({
    axiosConfig: {
      url: `${BASE}/${pathParams.projectId}/claims/${pathParams.claimId}`,
    },
    queryName: 'getClaimById',
    pathParams,
    queryOptions: {
      refetchOnWindowFocus: false,
      staleTime: QUERY_TIME.THIRTY_SECONDS,
      ...queryOptions,
    },
  })

// --- Mutation Hooks ---

export const useCreateClaimConfig = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string
      data: {
        counterparty_company_id: string
        default_submission_channel: string
        default_contact?: string
        portal_url?: string
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.post(`${baseURL}${BASE}/${projectId}/claims/configs`, data, {
        headers: { Authorization: `Bearer ${token}` },
      })
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: ['getClaimConfigs', { projectId: v.projectId }],
      }),
  })
}

export const useUpdateClaimConfig = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimConfigId,
      data,
    }: {
      projectId: string
      claimConfigId: number
      data: {
        counterparty_company_id?: string
        default_submission_channel?: string
        default_contact?: string | null
        portal_url?: string | null
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.patch(
        `${baseURL}${BASE}/${projectId}/claims/configs/${claimConfigId}`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: ['getClaimConfigs', { projectId: v.projectId }],
      }),
  })
}

export const useDeleteClaimConfig = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimConfigId,
    }: {
      projectId: string
      claimConfigId: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.delete(
        `${baseURL}${BASE}/${projectId}/claims/configs/${claimConfigId}`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: ['getClaimConfigs', { projectId: v.projectId }],
      }),
  })
}

export const useCreateClaim = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      data,
    }: {
      projectId: string
      data: {
        claim_config_id: number
        summary?: string
        external_reference?: string
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.post<ClaimListItem>(
        `${baseURL}${BASE}/${projectId}/claims`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      }),
  })
}

export const useUpdateClaim = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      data,
    }: {
      projectId: string
      claimId: number
      data: {
        summary?: string | null
        external_reference?: string | null
        status?: string | null
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.patch<ClaimListItem>(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      })
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
    },
  })
}

export const useDeleteClaim = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
    }: {
      projectId: string
      claimId: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.delete(`${baseURL}${BASE}/${projectId}/claims/${claimId}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      }),
  })
}

export const useAddClaimDevice = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      data,
    }: {
      projectId: string
      claimId: number
      data: {
        device_id: number
        event_id?: number
        oem_serial_number?: string
        oem_part_number?: string
        notes?: string
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.post(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/devices`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      })
    },
  })
}

export const useUpdateClaimDevice = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      claimDeviceId,
      data,
    }: {
      projectId: string
      claimId: number
      claimDeviceId: number
      data: {
        device_id?: number
        event_id?: number | null
        oem_serial_number?: string | null
        oem_part_number?: string | null
        notes?: string | null
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.patch(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/devices/${claimDeviceId}`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      })
    },
  })
}

export const useRemoveClaimDevice = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      claimDeviceId,
    }: {
      projectId: string
      claimId: number
      claimDeviceId: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.delete(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/devices/${claimDeviceId}`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      })
    },
  })
}

export const useAddClaimUpdate = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      data,
    }: {
      projectId: string
      claimId: number
      data: {
        update_type: string
        from_status?: string
        to_status?: string
        message?: string
        created_at?: string
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.post(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/updates`,
        data,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) =>
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      }),
  })
}

export const useUploadClaimAttachment = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      file,
      claimUpdateId,
    }: {
      projectId: string
      claimId: number
      file: File
      claimUpdateId?: number
    }) => {
      const token = await getToken({ template: 'default' })
      const formData = new FormData()
      formData.append('file', file)
      if (claimUpdateId !== undefined) {
        formData.append('claim_update_id', String(claimUpdateId))
      }
      return axios.post(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/attachments`,
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
          },
        },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: [
          'getClaimAttachments',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
    },
  })
}

export const useDeleteClaimAttachment = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      filename,
    }: {
      projectId: string
      claimId: number
      filename: string
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.delete(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/attachments/${encodeURIComponent(filename)}`,
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: [
          'getClaimAttachments',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
    },
  })
}

export const useSubmitClaim = () => {
  const { getToken } = useAuth()
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      claimId,
      data,
    }: {
      projectId: string
      claimId: number
      data?: {
        email_subject?: string | null
        email_body?: string | null
        to_emails?: string[] | null
        cc_emails?: string[] | null
        bcc_emails?: string[] | null
      }
    }) => {
      const token = await getToken({ template: 'default' })
      return axios.post(
        `${baseURL}${BASE}/${projectId}/claims/${claimId}/submit`,
        data ?? {},
        { headers: { Authorization: `Bearer ${token}` } },
      )
    },
    onSuccess: (_, v) => {
      qc.invalidateQueries({
        queryKey: ['getProjectClaims', { projectId: v.projectId }],
      })
      qc.invalidateQueries({
        queryKey: [
          'getClaimById',
          { projectId: v.projectId, claimId: String(v.claimId) },
        ],
      })
    },
  })
}

export async function fetchClaimEventDataCsv({
  token,
  projectId,
  eventId,
  signal,
}: {
  token: string
  projectId: string
  eventId: number
  signal?: AbortSignal
}): Promise<File> {
  const url = CLAIM_EVENT_DATA_CSV_URL.replace(
    '{project_id}',
    encodeURIComponent(projectId),
  )
  const response = await axios.get(`${baseURL}${url}`, {
    headers: { Authorization: `Bearer ${token}` },
    params: { event_id: eventId },
    responseType: 'blob',
    signal,
  })
  const filename =
    filenameFromContentDisposition(response.headers['content-disposition']) ??
    `event-${eventId}.csv`
  return new File([response.data], filename, { type: 'text/csv' })
}

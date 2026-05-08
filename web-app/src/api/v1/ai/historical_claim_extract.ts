import { baseURL } from '@/urlConfig'
import axios from 'axios'

interface HistoricalClaimConfigOption {
  claim_config_id: number
  counterparty_name: string | null
}

interface HistoricalClaimDeviceOption {
  device_id: number
  device_name: string | null
  device_type_id: number | null
  device_type_name: string | null
}

interface HistoricalClaimDeviceTypeOption {
  device_type_id: number
  device_type_name: string
}

interface HistoricalClaimContext {
  project_id?: string | null
  project_name: string
  company_name: string
  claim_configs: HistoricalClaimConfigOption[]
  devices: HistoricalClaimDeviceOption[]
  device_types: HistoricalClaimDeviceTypeOption[]
}

interface ExtractedClaimDevice {
  device_id: number | null
  device_type_id: number | null
  device_name_hint: string
  oem_serial_number: string
  oem_part_number: string
  notes: string
  event_id: number | null
}

interface ExtractedClaimUpdate {
  update_type: string
  message: string
  occurred_at: string | null
  from_status: string | null
  to_status: string | null
}

export interface CandidateEvent {
  event_id: number
  device_id: number
  time_start: string
  time_end: string | null
  failure_mode: string | null
}

export interface HistoricalClaimExtractResponse {
  claim_config_id: number | null
  oem_name_suggested: string | null
  summary: string
  external_reference: string | null
  status: string
  claim_date: string | null
  devices: ExtractedClaimDevice[]
  updates: ExtractedClaimUpdate[]
  device_event_candidates: Record<number, CandidateEvent[]>
}

export async function requestHistoricalClaimExtract(
  token: string,
  args: {
    projectId: string
    context: HistoricalClaimContext
    files: File[]
    model?: string
  },
): Promise<HistoricalClaimExtractResponse> {
  const formData = new FormData()
  const context = {
    ...args.context,
    project_id: args.projectId,
  }
  const encodedProjectId = encodeURIComponent(args.projectId)
  const path = `/v1/ai/projects/${encodedProjectId}/historical-claim-extract`
  const url = `${baseURL}${path}`
  formData.append('context_json', JSON.stringify(context))
  for (const file of args.files) {
    formData.append('files', file)
  }
  if (args.model) {
    formData.append('model', args.model)
  }
  const response = await axios({
    method: 'post',
    url,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'multipart/form-data',
    },
    data: formData,
  })
  return response.data as HistoricalClaimExtractResponse
}

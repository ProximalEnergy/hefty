import { baseURL } from '@/urlConfig'
import axios from 'axios'

interface ClaimDevicePayload {
  device_name: string
  device_brand: string
  device_model: string
  oem_serial_number: string
  oem_part_number: string
  notes: string
  event_id?: number | null
}

interface ClaimEventPayload {
  event_id?: number | null
  device_id?: number | null
  time_start: string
  time_end: string
  failure_mode: string
  root_cause: string
}

interface ClaimContextPayload {
  project?: {
    address?: string
    elevation?: string | number | null
  }
  project_name: string
  company_name: string
  user_first_name: string
  user_last_name: string
  user_email: string
  claim_id_display: string
  phone: string
  summary: string
  external_reference: string
  oem_name: string
  today_date_display: string
  declaration_date_display: string
  first_issue_date_display: string
  previous_claim_example?: unknown
  events: ClaimEventPayload[]
  devices: ClaimDevicePayload[]
}

interface VisionPagePayload {
  page_number: number
  image_base64: string
  media_type: string
}

interface AcroFieldPayload {
  field_name: string
  field_type: string
  page: number
  x: number
  y: number
  width: number
  height: number
  rect: number[]
  existing_value: string
  nearby_label?: string | null
  nearby_label_source?: 'left' | 'above' | null
}

interface WarrantyClaimPdfAssistRequest {
  mode: 'acro' | 'vision'
  claim_context: ClaimContextPayload
  model?: string | null
  acro_fields?: AcroFieldPayload[] | null
  pages?: VisionPagePayload[] | null
}

interface PdfAnnotationSuggestion {
  page: number
  x: number
  y: number
  text: string
  font_size: number
}

interface WarrantyClaimPdfAssistResponse {
  acro_values?: Record<string, string> | null
  annotations?: PdfAnnotationSuggestion[] | null
}

export async function requestWarrantyClaimPdfAssist(
  token: string,
  args: {
    body: WarrantyClaimPdfAssistRequest
  },
): Promise<WarrantyClaimPdfAssistResponse> {
  const path = '/v1/ai/warranty-claim-pdf-assist'
  const url = `${baseURL}${path}`
  const response = await axios({
    method: 'post',
    url,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: args.body,
  })
  return response.data as WarrantyClaimPdfAssistResponse
}

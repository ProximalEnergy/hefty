import { baseURL } from '@/urlConfig'
import axios from 'axios'

interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
}

interface TimeseriesData {
  index: string[]
  unit: Record<string, string>
  data: Record<string, (number | null)[]>
}

export interface SCADADataPoint {
  sensor_type_id: number
  sensor_type_name?: string
  unit?: string
  x: string[]
  y: (number | null)[]
}

interface BatterySettlementAnalysisRequest {
  project_id: string
  project_name?: string
  start: string
  end: string
  qse_data?: TimeseriesData
  calculated_data?: TimeseriesData
  scada_data?: SCADADataPoint[]
  conversation_history?: ConversationMessage[]
  user_message?: string
  model?: string
}

export async function requestBatterySettlementAnalysis(
  token: string,
  request: BatterySettlementAnalysisRequest,
): Promise<string> {
  const response = await axios({
    method: 'post',
    url: `${baseURL}/v1/ai/battery-settlement-analysis`,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    data: request,
  })

  return response.data.content as string
}

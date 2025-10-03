import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import { useMutation } from '@tanstack/react-query'
import axios from 'axios'

// Define the type for the data your mutate function will receive
interface BackfillData {
  project_id: string | undefined
  project_name_short: string | undefined
  energy_model_version: string
  simulation_start: string | Date | null
  simulation_end: string | Date | null
  single_diode_model: string
  soiling: string
  degradation: string
  dc_wiring_to_combiner: string
  dc_wiring_to_inverter: string
  use_poa_only: boolean
  use_median_irr_sensor: boolean
}

export const useSubmitBackfill = () => {
  const { getToken } = useAuth()

  // Define response type for the mutation
  interface BackfillResponse {
    success: boolean
    message: string
    data?: Record<string, unknown>
  }

  // Specify the type of the variables the mutation function receives: BackfillData
  return useMutation<BackfillResponse, Error, BackfillData>({
    mutationFn: async (data: BackfillData) => {
      // Auth
      const token = await getToken({ template: 'default' })

      // Query Parameters
      const queryParamKeys = [
        'project_name_short',
        'energy_model_version',
        'simulation_start',
        'simulation_end',
      ]

      const params = new URLSearchParams()
      const bodyData: Record<string, string | number | boolean | Date> = {}

      // Use Object.entries to iterate over the properties of the 'data' object
      for (const [key, value] of Object.entries(data)) {
        // Skip null/undefined values, or handle specifically if needed
        if (value === null || value === undefined) {
          continue
        }

        // Convert value to string for URLSearchParams, handle Date objects
        const stringValue =
          value instanceof Date ? value.toISOString() : String(value)

        if (queryParamKeys.includes(key)) {
          // Append keys designated as query parameters
          params.append(key, stringValue)
        } else {
          // Add all other properties from BackfillData to the request body
          bodyData[key] = value
        }
      }

      // Extract projectId for path parameter and construct the API URL with query parameters
      const projectId = data.project_id
      const url = `${baseURL}/v1/protected/${projectId}/pv-expected-energy/backfill?${params.toString()}`

      return axios({
        method: 'post',
        url: url,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json', // Correct for sending JSON body
        },
        data: bodyData, // Send the constructed body object
      })
    },

    onError: (error, variables) => {
      // 'variables' is also available in onError
      console.error('Backfill submission failed:', error)
      console.error('Failed with variables:', variables)
      // Optional: show an error notification
    },
  })
}

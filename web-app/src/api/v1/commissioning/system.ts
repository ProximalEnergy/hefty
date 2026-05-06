import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useAuth } from '@clerk/react'
import { UseQueryOptions, useMutation } from '@tanstack/react-query'
import axios from 'axios'

interface ProjectSystemFileStatus {
  bucket_name: string
  file_key: string
  exists: boolean
}

interface InverterMetStationMappingResponse {
  rows_updated: number
  inverters_mapped: number
  met_stations_available: number
}

const PROJECT_SYSTEM_URL = '/v1/commissioning/system/{project_id}'

export const useGetProjectSystemFileStatus = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { project_id: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `${PROJECT_SYSTEM_URL}/file-status`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: QUERY_TIME.ONE_MINUTE,
  }

  return useCustomQuery<ProjectSystemFileStatus>({
    axiosConfig,
    queryName: 'getProjectSystemFileStatus',
    pathParams,
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
        url: `${baseURL}/v1/commissioning/system/${projectId}/import`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}

export const useMapInvertersToMetStations = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const token = await getToken({ template: 'default' })

      const response = await axios<InverterMetStationMappingResponse>({
        method: 'put',
        url:
          `${baseURL}/v1/commissioning/system/${projectId}` +
          '/map-inverters-to-met-stations',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}

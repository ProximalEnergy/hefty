import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

export const useGetUniqueTagTypes = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    limit?: number
    include_null_sensor_types?: boolean
    only_null_sensor_types?: boolean
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/project-tag-explorer/unique-tag-types`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 300000, // 5 minutes
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<any[]>({
    axiosConfig,
    queryName: 'getUniqueTagTypes',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useGetTagPatternSamples = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; tagPattern: string }
  queryParams?: { start?: string; end?: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/project-tag-explorer/tag-pattern-samples/${encodeURIComponent(pathParams.tagPattern)}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 300000, // 5 minutes
    enabled: false, // Don't fetch automatically, only when called
  }

  queryOptions = { ...defaultQueryOptions, ...queryOptions }

  return useCustomQuery<any>({
    axiosConfig,
    queryName: 'getTagPatternSamples',
    pathParams,
    queryParams: queryParams,
    queryOptions: queryOptions,
  })
}

export const useAssignSensorTypeMutation = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      projectId,
      tagNameShort,
      sensorTypeId,
    }: {
      projectId: string
      tagNameShort: string
      sensorTypeId: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        baseURL: baseURL,
        url: `/v1/protected/web-application/projects/${projectId}/project-tag-explorer/assign-sensor-type`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          project_id: projectId,
          tag_name_short: tagNameShort,
          sensor_type_id: sensorTypeId,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getUniqueTagTypes'] })
      queryClient.invalidateQueries({ queryKey: ['getSensorTypeAssignments'] })
    },
  })
}

export const useAssignPatternSensorTypeMutation = () => {
  const { getToken } = useAuth()
  return useMutation({
    mutationFn: async ({
      projectId,
      tagPattern,
      sensorTypeId,
      unitScale,
      unitOffset,
    }: {
      projectId: string
      tagPattern: string
      sensorTypeId: number
      unitScale?: number | null
      unitOffset?: number | null
    }) => {
      const token = await getToken({ template: 'default' })
      const response = await axios({
        method: 'post',
        baseURL: baseURL,
        url: `/v1/protected/web-application/projects/${projectId}/project-tag-explorer/assign-pattern-sensor-type`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          project_id: projectId,
          tag_pattern: tagPattern,
          sensor_type_id: sensorTypeId,
          unit_scale: unitScale,
          unit_offset: unitOffset,
        },
      })
      return response.data
    },
  })
}

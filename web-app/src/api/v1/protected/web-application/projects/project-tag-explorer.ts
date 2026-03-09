import { useCustomQuery } from '@/hooks/api'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query'
import axios from 'axios'

interface TagPatternTag {
  tag_id: number
  name_scada: string
  name_short: string | null
  device_id: number
  sensor_type_id: number | null
}

interface UniqueTagType {
  project_id: string
  project_name: string
  project_name_short: string
  sensor_type_id: number
  device_type_id: number | null
  device_type_name: string | null
  scada_type: string | null
  unit_scada: string | null
  unit_offset: number | null
  unit_scale: number | null
  tag_pattern: string
  count: number
  examples: unknown[]
  sample_tag_id: number | null
}

interface TagPatternSample {
  tag_name: string
  tag_id: number
  sample_values: (number | string)[]
  timestamps: string[]
  is_numeric: boolean
  value_range: string
  total_unique_values: number
}

interface TagPatternSamplesResponse {
  tag_pattern: string
  sample_tags: TagPatternSample[]
  total_sample_tags: number
}

export const usePutUniqueTagPatterns = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ projectId }: { projectId: string }) => {
      const token = await getToken()
      const response = await axios.put(
        `${baseURL}/v1/protected/web-application/projects/${projectId}/project-tag-explorer/unique-tag-patterns`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      )
      return response.data
    },
    onSuccess: () => {
      // Invalidate and refetch unique tag types after successful population
      queryClient.invalidateQueries({
        queryKey: ['getUniqueTagTypes'],
      })
    },
  })
}

export const useGetTagsByPattern = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; tagPattern: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/project-tag-explorer/tag-pattern-tags/${encodeURIComponent(pathParams.tagPattern)}`,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 300000,
    enabled: false,
  }

  return useCustomQuery<TagPatternTag[]>({
    axiosConfig,
    queryName: 'getTagsByPattern',
    pathParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 300000, // 5 minutes
  }

  return useCustomQuery<UniqueTagType[]>({
    axiosConfig,
    queryName: 'getUniqueTagTypes',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    enabled: false,
  }

  return useCustomQuery<TagPatternSamplesResponse>({
    axiosConfig,
    queryName: 'getTagPatternSamples',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
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
      unitScada,
    }: {
      projectId: string
      tagPattern: string
      sensorTypeId: number
      unitScale: number | null
      unitOffset: number | null
      unitScada: string | null
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
          unit_scada: unitScada,
        },
      })
      return response.data
    },
  })
}

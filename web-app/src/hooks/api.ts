import { KPIType } from '@/api/v1/operational/kpi_types'
import * as types from '@/hooks/types'
import { StatisticType } from '@/hooks/types'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  UseQueryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import { Table, tableFromIPC } from 'apache-arrow'
import axios, { AxiosRequestConfig } from 'axios'
import { FeatureCollection } from 'geojson'
import qs from 'qs'

type PathParams = Record<string, string | number | boolean | null | undefined>

function interpolatePath(url: string, pathParams: object): string {
  if (!pathParams || Object.keys(pathParams).length === 0) return url

  const params = pathParams as PathParams

  return url.replace(/{([^}]+)}/g, (_match, key) => {
    const value = params[key as keyof PathParams]
    if (value === undefined || value === null) {
      throw new Error(`Missing path param "${key}" for URL "${url}"`)
    }
    return encodeURIComponent(String(value))
  })
}

export const useCustomQuery = <T>({
  axiosConfig,
  queryName,
  pathParams = {},
  queryParams = {},
  queryOptions = {},
}: {
  axiosConfig: AxiosRequestConfig
  queryName: string
  pathParams?: object
  queryParams?: object
  queryOptions?: object
}) => {
  const { getToken } = useAuth()

  const queryKey: unknown[] = [queryName]

  // If pathParams is not empty, add it to queryKey
  if (Object.keys(pathParams).length !== 0) {
    queryKey.push(pathParams)
  }

  // If queryParams is not empty, add it to queryKey
  if (Object.keys(queryParams).length !== 0) {
    queryKey.push(queryParams)
  }

  const queryFn = async (): Promise<T> => {
    const token = await getToken({ template: 'default' })

    const url =
      axiosConfig.url != null
        ? interpolatePath(axiosConfig.url, pathParams)
        : undefined

    const response = await axios({
      ...axiosConfig,
      url,
      baseURL: baseURL,
      headers: {
        Authorization: `Bearer ${token}`,
      },
      params: queryParams, // Add this line to pass query parameters
      paramsSerializer: (params) => {
        return qs.stringify(params, { arrayFormat: 'repeat' })
      },
    })
    return response.data
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: () => queryFn(),
    ...queryOptions,
  })
}

export const useCustomQueryArrow = ({
  axiosConfig,
  queryName,
  pathParams = {},
  queryParams = {},
  queryOptions = {},
}: {
  axiosConfig: AxiosRequestConfig
  queryName: string
  pathParams?: object
  queryParams?: object
  queryOptions?: object
}) => {
  const { getToken } = useAuth()

  const queryKey: unknown[] = [queryName]

  if (Object.keys(pathParams).length !== 0) {
    queryKey.push(pathParams)
  }

  if (Object.keys(queryParams).length !== 0) {
    queryKey.push(queryParams)
  }

  const queryFn = async (): Promise<Table | null> => {
    const token = await getToken({ template: 'default' })
    const response = await axios({
      ...axiosConfig,
      baseURL: baseURL,
      headers: {
        Authorization: `Bearer ${token}`,
      },
      responseType: 'arraybuffer',
      params: queryParams,
      paramsSerializer: (params) => {
        return qs.stringify(params, { arrayFormat: 'repeat' })
      },
    })
    if (response.data.byteLength < 16) {
      return null
    }
    return tableFromIPC(response.data)
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: () => queryFn(),
    ...queryOptions,
  })
}

export const useCreateFeedbackMutation = () => {
  const { getToken } = useAuth()
  return useMutation({
    mutationFn: async (feedback: FormData) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/feedback`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: feedback,
      })
    },
  })
}

export const useUpdateNotificationSubscription = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      subscribe,
    }: {
      project_id: string
      subscribe: boolean
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/admin/subscriptions/notifications/${project_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          subscribe,
        },
      })
    },
    onMutate: async (newSubscription) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['getSubscriptions'] })

      // Snapshot the previous value
      const previousSubscriptions = queryClient.getQueryData<
        types.UserSubscription[]
      >(['getSubscriptions'])

      // Optimistically update the new value
      queryClient.setQueryData(
        ['getSubscriptions'],
        (oldSubscriptions: types.UserSubscription[]) => {
          return oldSubscriptions?.map((subscription) => {
            if (
              subscription.operational_project_id === newSubscription.project_id
            ) {
              return {
                ...subscription,
                notifications: newSubscription.subscribe,
              }
            }
            return subscription
          })
        },
      )

      // Return a context object with the snapshotted value
      return { previousSubscriptions }
    },
    onError: (_err, _newSubscription, context) => {
      queryClient.setQueryData(
        ['getSubscriptions'],
        context?.previousSubscriptions,
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['getSubscriptions'] })
    },
  })
}

export const useUpdateReportSubscription = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      subscribe,
    }: {
      project_id: string
      subscribe: boolean
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/admin/subscriptions/reports/${project_id}`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          subscribe,
        },
      })
    },
    onMutate: async (newSubscription) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['getSubscriptions'] })

      // Snapshot the previous value
      const previousSubscriptions = queryClient.getQueryData<
        types.UserSubscription[]
      >(['getSubscriptions'])

      // Optimistically update the new value
      queryClient.setQueryData(
        ['getSubscriptions'],
        (oldSubscriptions: types.UserSubscription[]) => {
          return oldSubscriptions?.map((subscription) => {
            if (
              subscription.operational_project_id === newSubscription.project_id
            ) {
              return {
                ...subscription,
                reports: newSubscription.subscribe,
              }
            }
            return subscription
          })
        },
      )

      // Return a context object with the snapshotted value
      return { previousSubscriptions }
    },
    onError: (_err, _newSubscription, context) => {
      queryClient.setQueryData(
        ['getSubscriptions'],
        context?.previousSubscriptions,
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['getSubscriptions'] })
    },
  })
}

export const useGetDevice = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; deviceId: string }
  queryParams?: { deep?: boolean }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/devices/${pathParams.deviceId}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<types.Device>({
    axiosConfig,
    queryName: 'getDevice',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

// V2 devices endpoint with POST support and pagination
export const useGetDevicesV2 = ({
  pathParams,
  filters,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  filters: {
    device_ids?: number[]
    device_type_ids?: number[]
    parent_device_ids?: (number | null)[]
    name_short?: string
    name_long?: string
    device_id_descendent_of?: number | null
    deep?: boolean
    with_tags?: boolean
    limit?: number | null
    offset?: number
    format?: string
    fields?: string[]
  }
  queryOptions?: Partial<UseQueryOptions<types.Device[]>>
}) => {
  const { getToken } = useAuth()

  const queryKey = ['getDevicesV2', pathParams, filters]

  const queryFn = async (): Promise<types.Device[]> => {
    const token = await getToken({ template: 'default' })
    const response = await axios({
      method: 'post',
      url: `${baseURL}/v1/operational/projects/${pathParams.projectId}/devices/`,
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      data: filters,
    })
    return response.data
  }

  return useQuery({
    queryKey: queryKey,
    queryFn: queryFn,
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    ...queryOptions,
  })
}

export const useGetTags = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/tags/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<types.Tag[]>({
    axiosConfig,
    queryName: 'getTags',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetKPIAlerts = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: { kpi_type_id?: number }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/kpi-data/kpi-alerts/`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.KPIAlertProps[]>({
    axiosConfig,
    queryName: 'getKPIAlerts',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEvents = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    device_id?: string
    open?: boolean
    event_ids?: number[]
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.Event[]>({
    axiosConfig,
    queryName: 'getEvents',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetPaginatedEvents = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    page?: number
    page_size?: number
    open?: boolean
    sort_column?: string
    sort_direction?: string
    device_type_ids?: number[]
    device_ids?: number[]
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/paginated-events`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.PaginatedEvent[]>({
    axiosConfig,
    queryName: 'getPaginatedEvents',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetUptimeTable = ({
  pathParams,
  queryParams = {
    start: '',
    end: '',
    project_id: '',
  },
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start: string
    end: string
    project_id: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/events/uptime`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.UptimeData[]>({
    axiosConfig,
    queryName: 'getUptimeTable',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useUpdateRootCause = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({
      project_id,
      event_id,
      root_cause_id,
    }: {
      project_id: string
      event_id: number
      root_cause_id?: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${project_id}/events/${event_id}/root-cause`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          root_cause_id: root_cause_id ?? -1,
        },
      })
    },
    onMutate: async (newRootCause) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['getRootCauses'] })
      await queryClient.cancelQueries({ queryKey: ['getEvents'] })

      // Snapshot the previous values
      const previousRootCauses = queryClient.getQueryData<types.RootCause[]>([
        'getRootCauses',
      ])
      const previousEvents = queryClient.getQueriesData({
        queryKey: ['getEvents'],
      })

      // Optimistically update the root causes
      queryClient.setQueryData(
        ['getRootCauses'],
        (oldRootCauses: types.RootCause[]) => {
          return oldRootCauses?.map((rootCause) => {
            if (rootCause.root_cause_id === newRootCause.root_cause_id) {
              return {
                ...rootCause,
                root_cause_id: newRootCause.root_cause_id,
              }
            }
            return rootCause
          })
        },
      )

      // Optimistically update the events data
      queryClient.setQueriesData(
        { queryKey: ['getEvents'] },
        (oldEvents: types.Event[] | undefined) => {
          if (!oldEvents) return oldEvents
          return oldEvents.map((event) => {
            if (event.event_id === newRootCause.event_id) {
              return {
                ...event,
                root_cause_id: newRootCause.root_cause_id,
              }
            }
            return event
          })
        },
      )

      return { previousRootCauses, previousEvents }
    },
    onError: (_err, _newRootCause, context) => {
      queryClient.setQueryData(['getRootCauses'], context?.previousRootCauses)
      // Restore previous events data
      if (context?.previousEvents) {
        context.previousEvents.forEach(([queryKey, data]) => {
          queryClient.setQueryData(queryKey, data)
        })
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['getRootCauses'] })
      queryClient.invalidateQueries({ queryKey: ['getEvents'] })
    },
  })
}

export const useGetWeather = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/project-weather`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 15 * 60 * 1000, // 15 minutes
  }

  return useCustomQuery<types.WeatherResponse>({
    axiosConfig,
    queryName: 'getWeather',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetForecast = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/gis/${pathParams.projectId}/project-weather-forecast`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 15 * 60 * 1000, // 15 minutes
  }

  return useCustomQuery<types.ForecastResponse>({
    axiosConfig,
    queryName: 'getForecast',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetHeatmap = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; sensorTypeName: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/heatmap/${pathParams.sensorTypeName}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.DataHeatmap>({
    axiosConfig,
    queryName: 'getHeatmap',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISPCS = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/gis/pcs`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.GISPCS>({
    axiosConfig,
    queryName: 'getPCSPerformance',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISCombinerBlock = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string; blockId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/gis/combiner/${pathParams.blockId}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 60 * 1000,
  }

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISCombinerBlock',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISTrackerByBlock = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string; blockId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/gis/tracker-by-block/${pathParams.blockId}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  }

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISTrackerByBlock',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetGISBessEnclosure = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/gis/bess-enclosure`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<FeatureCollection>({
    axiosConfig,
    queryName: 'getGISBessEnclosure',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetEquipmentAnalysisCombiner = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: {
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/combiner`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.EquipmentAnalysisCombiner>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisCombiner',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResources = ({
  queryParams = {},
  queryOptions = {},
}: {
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: '/v1/development/ercot/resources',
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<types.Resource[]>({
    axiosConfig,
    queryName: 'getResources',
    pathParams: {},
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResource = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { resourceId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/resources/${pathParams.resourceId}`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<types.Resource>({
    axiosConfig,
    queryName: 'getResource',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetResourceNetPower = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { resourceId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/development/ercot/resources/${pathParams.resourceId}/net-power`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<types.DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getResourceNetPower',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAddKPIAlert = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      alert_name,
      comparison,
      duration_value,
      kpi_type_id,
      statistic,
      notify,
      threshold_value,
      triggered,
    }: {
      project_id: string
      alert_name: string
      comparison: string | null
      duration_value: string | null
      kpi_type_id: string | null
      statistic: StatisticType | null
      notify: boolean
      threshold_value: number | null | string
      triggered: boolean | null
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'post',
        url: `${baseURL}/v1/operational/projects/${project_id}/kpi-data/kpi-alerts`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          project_id,
          alert_name,
          comparison,
          duration_value,
          kpi_type_id,
          statistic,
          notify,
          threshold_value,
          triggered,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getKPIAlerts'] })
    },
  })
}

export const useUpdateKPIAlert = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      kpi_alert_id,
      project_id,
      alert_name,
      comparison,
      duration_value,
      kpi_type_id,
      statistic,
      notify,
      threshold_value,
      triggered,
    }: {
      kpi_alert_id: number
      project_id: string
      alert_name: string
      comparison: string | null
      duration_value: string | null
      kpi_type_id: string | null
      statistic: StatisticType | null
      notify: boolean
      threshold_value: number | null | string
      triggered: boolean | null
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'put',
        url: `${baseURL}/v1/operational/projects/${project_id}/kpi-data/update-kpi-alert`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: {
          kpi_alert_id,
          project_id,
          alert_name,
          comparison,
          duration_value,
          kpi_type_id,
          statistic,
          notify,
          threshold_value,
          triggered,
        },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getKPIAlerts'] })
    },
  })
}

export const useDeleteKPIAlert = () => {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({
      project_id,
      alert_id,
    }: {
      project_id: string
      alert_id: number
    }) => {
      const token = await getToken({ template: 'default' })
      return axios({
        method: 'delete',
        url: `${baseURL}/v1/operational/projects/${project_id}/kpi-data/kpi-alerts/`,
        headers: {
          Authorization: `Bearer ${token}`,
        },
        data: { alert_id },
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['getKPIAlerts'] })
    },
  })
}

export const useGetTriggeredKPIAlerts = ({
  queryOptions = {},
}: {
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-data/user-triggered-alerts`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 60,
  }

  return useCustomQuery<types.KPIAlertProps[]>({
    axiosConfig,
    queryName: 'getUserTriggeredAlerts',
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetKPIType = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { kpiTypeId: number }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/operational/kpi-types/${pathParams.kpiTypeId}`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
  }

  return useCustomQuery<KPIType>({
    axiosConfig,
    queryName: 'getKPIType',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetSunburstData = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/sunburst-data`,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
  }

  return useCustomQuery<types.SunburstProps>({
    axiosConfig,
    queryName: 'getSunburstData',
    pathParams,
    queryParams: {},
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetClearskyPOA = ({
  pathParams,
  queryOptions = {},
  queryParams = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: {
    start?: string
    end?: string
    resample_rate?: string
  }
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/clearsky-poa`,
    params: queryParams,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
  }

  return useCustomQuery<types.DataTimeSeries[]>({
    axiosConfig,
    queryName: 'getClearskyPOA',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useGetDegradationPOA = ({
  pathParams,
  queryOptions = {},
  queryParams = {},
}: {
  pathParams: { projectId: string }
  queryOptions?: Partial<UseQueryOptions>
  queryParams?: {
    start?: string
    end?: string
  }
}) => {
  const axiosConfig = {
    url: `/v1/analytics/${pathParams.projectId}/degradation-poa`,
    params: queryParams,
  }
  const defaultQueryOptions: Partial<UseQueryOptions> = {
    staleTime: 5 * 60 * 1000,
  }

  return useCustomQuery<types.DegradationPOA>({
    axiosConfig,
    queryName: 'getDegradationPOA',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

export const useAnalyzeCombinerSwaps = () => {
  const { getToken } = useAuth()

  return useMutation({
    mutationFn: async ({
      projectId,
      analysisDate,
      blockNames,
    }: {
      projectId: string
      analysisDate?: string
      blockNames?: string[]
    }) => {
      const token = await getToken({ template: 'default' })

      // Convert parameters to query string
      const params = new URLSearchParams({
        project_id: projectId,
        ...(analysisDate && { analysis_date: analysisDate }),
        ...(blockNames?.length && { block_names: blockNames.join(',') }),
      })

      const response = await axios({
        method: 'GET',
        baseURL: baseURL,
        url: `/v1/analytics/${projectId}/combiner-correlation-analysis?${params.toString()}`,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      })

      return response.data
    },
  })
}

export const useValidateCombinerData = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams: {
    deviceIds?: number[]
    start?: string
    end?: string
  }
  queryOptions?: Partial<UseQueryOptions>
}) => {
  // Transform the parameters to match API expectations
  const transformedParams = {
    start: queryParams.start,
    end: queryParams.end,
    device_ids: queryParams.deviceIds,
  }

  const axiosConfig = {
    url: `/v1/operational/projects/${pathParams.projectId}/qc/combiner-swaps/validate-combiner-data`,
    params: transformedParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    // Only enable the query if we have all required parameters
    enabled: !!(
      queryParams.start &&
      queryParams.end &&
      queryParams.deviceIds &&
      queryParams.deviceIds.length > 0
    ),
  }

  return useCustomQuery<{ isValid: boolean; message?: string }>({
    axiosConfig,
    queryName: 'validateCombinerData',
    pathParams,
    queryParams: transformedParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

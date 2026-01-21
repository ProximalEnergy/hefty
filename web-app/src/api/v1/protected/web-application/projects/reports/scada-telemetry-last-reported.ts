import { paths } from '@/api/schema'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const URL =
  '/v1/protected/web-application/projects/{project_id}/reports/scada-telemetry-last-reported'

type get = paths[typeof URL]['get']
type getPathParams = get['parameters']['path']

export const useGetSCADATelemetryLastReported = ({
  pathParams,
  queryOptions = {},
}: {
  pathParams: getPathParams
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const extractFilename = (headerValue: string | undefined) => {
    if (!headerValue) return null
    const match = headerValue.match(/filename="([^"]+)"/)
    if (match?.[1]) return match[1]
    const fallbackMatch = headerValue.match(/filename=([^;]+)/)
    return fallbackMatch?.[1]?.trim() ?? null
  }

  const axiosConfig = {
    url: URL,
    responseType: 'blob' as const,
    transformResponse: (
      data: Blob,
      headers?: Record<string, string>,
    ): { blob: Blob; filename: string | null } => {
      const headerValue =
        headers?.['content-disposition'] ?? headers?.['Content-Disposition']
      return {
        blob: data,
        filename: extractFilename(headerValue),
      }
    },
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: Infinity,
    enabled: false,
  }

  return useCustomQuery<{ blob: Blob; filename: string | null }>({
    axiosConfig,
    queryName: 'getSCADATelemetryLastReported',
    pathParams,
    queryOptions: {
      ...defaultQueryOptions,
      ...queryOptions,
    },
  })
}

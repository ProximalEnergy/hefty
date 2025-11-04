import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface EquipmentAnalysisBESSPCS {
  x: string[]
  y: number[]
  name: string
}

export const useGetEquipmentAnalysisBESSPCS = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/bess-pcs`,
    params: queryParams,
  }

  const defaultQueryOptions: Partial<UseQueryOptions> = {}

  return useCustomQuery<EquipmentAnalysisBESSPCS[]>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisBESSPCS',
    pathParams,
    queryParams: queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

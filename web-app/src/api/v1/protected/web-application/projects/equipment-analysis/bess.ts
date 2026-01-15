import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

interface Data {
  x: string[]
  y: number[]
  name: string
}

interface EquipmentAnalysisBESS {
  bess_enclosure: Data[]
  bess_bank: Data[]
  bess_string: Data[]
}

export const useGetEquipmentAnalysisBESS = ({
  pathParams,
  queryParams = {},
  queryOptions = {},
}: {
  pathParams: { projectId: string }
  queryParams?: object
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: `/v1/protected/web-application/projects/${pathParams.projectId}/equipment-analysis/bess`,
  }

  const defaultQueryOptions = {}

  return useCustomQuery<EquipmentAnalysisBESS>({
    axiosConfig,
    queryName: 'getEquipmentAnalysisBESS',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

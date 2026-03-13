import { Endpoint } from '@/api/utils'
import { useCustomQuery } from '@/hooks/api'
import { UseQueryOptions } from '@tanstack/react-query'

const URL_GET_CMMS_TICKETS =
  '/v1/operational/projects/{project_id}/cmms-tickets/v2'
type GetCMMSTickets = Endpoint<typeof URL_GET_CMMS_TICKETS, 'get'>
type ExtractTicket<T> = T extends { data: Array<infer Item> } ? Item : never

export type CMMSTicket = ExtractTicket<GetCMMSTickets['Response']>

export const useGetCMMSTickets = ({
  pathParams,
  queryParams,
  queryOptions = {},
}: {
  pathParams: { project_id: GetCMMSTickets['PathParams']['project_id'] }
  queryParams?: GetCMMSTickets['QueryParams']
  queryOptions?: Partial<UseQueryOptions>
}) => {
  const axiosConfig = {
    url: URL_GET_CMMS_TICKETS,
  }

  const defaultQueryOptions = {
    refetchOnWindowFocus: false,
    staleTime: 1000 * 60 * 5,
  }

  return useCustomQuery<GetCMMSTickets['Response']>({
    axiosConfig,
    queryName: 'getCMMSTickets',
    pathParams,
    queryParams,
    queryOptions: { ...defaultQueryOptions, ...queryOptions },
  })
}

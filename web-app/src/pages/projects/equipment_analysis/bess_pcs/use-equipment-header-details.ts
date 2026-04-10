import { DeviceTypeEnum } from '@/api/enumerations'
import {
  type OMContractorScope,
  useGetOMContractorScopes,
} from '@/api/v1/operational/project/om_contractors'
import { QUERY_TIME } from '@/utils/queryTiming'
import { useMemo } from 'react'

type UseEquipmentHeaderDetailsParams = {
  projectId?: string
}

type EquipmentHeaderDetails = {
  serviceContractor: OMContractorScope | null
  epcContractor: OMContractorScope | null
  isLoading: boolean
}

const queryOptions = {
  staleTime: QUERY_TIME.NEVER,
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  refetchOnReconnect: false,
}

export function useEquipmentHeaderDetails({
  projectId,
}: UseEquipmentHeaderDetailsParams): EquipmentHeaderDetails {
  const contractorScopes = useGetOMContractorScopes({
    pathParams: {
      projectId: projectId || '-1',
    },
    queryOptions: {
      enabled: !!projectId,
      ...queryOptions,
    },
  })

  const pcsContractors = useMemo(() => {
    if (!contractorScopes.data) {
      return []
    }

    return contractorScopes.data.filter((scope) =>
      scope.scope_json?.device_type_ids?.includes(DeviceTypeEnum.BESS_PCS),
    )
  }, [contractorScopes.data])

  return {
    serviceContractor: pcsContractors[0] || null,
    epcContractor: pcsContractors[1] || null,
    isLoading: contractorScopes.isLoading,
  }
}

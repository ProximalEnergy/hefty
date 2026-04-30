import { getKPIThresholdbyDate } from '@/pages/projects/kpis/ProjectKPIHome.utils'

type ContractKpiThresholdData = {
  values?: { [key: string]: number }
}

type ContractKpiThresholdLookup = ReadonlyMap<
  number,
  { threshold?: ContractKpiThresholdData | null }
>

export const getCurrentContractKpiThreshold = ({
  contractKPIMap,
  kpiTypeId,
}: {
  contractKPIMap: ContractKpiThresholdLookup
  kpiTypeId: number
}) => {
  const contractKPI = contractKPIMap.get(kpiTypeId)
  if (!contractKPI?.threshold?.values) return null

  return getKPIThresholdbyDate(contractKPI.threshold, new Date(), 'discrete')
}

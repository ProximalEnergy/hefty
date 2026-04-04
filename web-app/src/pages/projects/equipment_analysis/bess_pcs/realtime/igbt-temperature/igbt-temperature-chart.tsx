import { IGBTTemperatureChart as SharedIGBTTemperatureChart } from '@/components/bess-pcs/IGBTTemperatureChart'

type IGBTTemperatureChartProps = {
  maxCapacityMWac: number | null
}

export function IGBTTemperatureChart({
  maxCapacityMWac,
}: IGBTTemperatureChartProps) {
  return <SharedIGBTTemperatureChart maxCapacityMWac={maxCapacityMWac} />
}

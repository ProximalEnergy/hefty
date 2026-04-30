import type { MantineTheme } from '@mantine/core'

interface ContractKPIStatusColorParams {
  theme: MantineTheme
  value: number | null | undefined
  threshold: number | null | undefined
  unit?: string | null
}

export const getContractKPIStatusColor = ({
  theme,
  value,
  threshold,
  unit,
}: ContractKPIStatusColorParams): string => {
  if (
    value === null ||
    value === undefined ||
    threshold === null ||
    threshold === undefined
  ) {
    return theme.colors.gray[4]
  }

  const normalizedThreshold = unit === '%' ? threshold * 100 : threshold
  const percentage =
    normalizedThreshold === 0
      ? value >= 0
        ? 100
        : 0
      : (value / normalizedThreshold) * 100

  if (percentage >= 100) {
    return theme.colors.green[6]
  }
  if (percentage >= 90) {
    return theme.colors.orange[6]
  }
  return theme.colors.red[6]
}

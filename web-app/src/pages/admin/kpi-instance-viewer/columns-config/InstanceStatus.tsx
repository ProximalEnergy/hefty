// Instance status component for KPI Instance Viewer
import { Box, useMantineTheme } from '@mantine/core'
import { IconEye, IconEyeOff, IconX } from '@tabler/icons-react'

import { setValue } from '../kpi-instance-state'
import type { KPIInstanceState } from '../kpi-instance-state'

type InstanceStatusProps = {
  status: boolean | null
  kpiTypeId: number
  projectId: string
  setKPIInstanceState: (
    updater: (prev: KPIInstanceState) => KPIInstanceState,
  ) => void
}

const InstanceStatus = ({
  status,
  kpiTypeId,
  projectId,
  setKPIInstanceState,
}: InstanceStatusProps) => {
  const theme = useMantineTheme()

  const handleClick = () => {
    const newValue = status === null ? false : status === false ? true : null
    setKPIInstanceState((prev) =>
      setValue(prev, kpiTypeId, projectId, newValue),
    )
  }

  const renderIcon = () => {
    if (status === null) {
      return <IconX size={16} color="red" />
    }

    return status ? (
      <IconEye size={16} color={theme.colors.blue[6]} />
    ) : (
      <IconEyeOff size={16} />
    )
  }

  return (
    <Box
      onClick={handleClick}
      style={{
        cursor: 'pointer',
        userSelect: 'none',
        display: 'inline-flex',
        alignItems: 'center',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.opacity = '0.7'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.opacity = '1'
      }}
    >
      {renderIcon()}
    </Box>
  )
}

export default InstanceStatus

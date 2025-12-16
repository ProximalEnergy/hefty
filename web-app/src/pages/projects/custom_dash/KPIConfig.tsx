import { KPITypeWithContractInfo } from '@/api/v1/operational/kpi_types'
import {
  Button,
  Group,
  Select,
  Skeleton,
  Stack,
  Title,
  Tooltip,
} from '@mantine/core'
import { UseQueryResult } from '@tanstack/react-query'
import { AxiosError } from 'axios'
import { useState } from 'react'

import { KPIConfig as KPIConfigType } from './CustomDash'

const KPIConfig = ({
  mode,
  stack,
  kpiTypes,
  onAdd,
  initialConfig,
}: {
  mode: 'create' | 'edit'
  stack: { close: (drawerId: 'kpi-config') => void }
  kpiTypes: UseQueryResult<KPITypeWithContractInfo[], AxiosError<unknown>>
  onAdd: (config: KPIConfigType) => void
  initialConfig?: KPIConfigType
}) => {
  const [selectedKpiTypeId, setSelectedKpiTypeId] = useState<string | null>(
    initialConfig?.kpiTypeId ?? null,
  )

  const addKPI = () => {
    if (!selectedKpiTypeId) {
      // You might want to show an error message here
      return
    }

    const config: KPIConfigType = {
      kpiTypeId: selectedKpiTypeId,
    }

    onAdd(config)
  }
  const kpiTypesData = kpiTypes.data
    ?.filter((kpiType) => kpiType.is_visible)
    .sort((a, b) => a.name_long.localeCompare(b.name_long))
  const allowCreate = !!selectedKpiTypeId
  return (
    <Stack>
      {mode === 'create' && <Title>Add KPI Card</Title>}
      {mode === 'edit' && <Title>Edit KPI Card</Title>}
      {kpiTypes.isLoading ? (
        <Skeleton height={60} />
      ) : (
        <Select
          data={kpiTypesData?.map((kpiType) => ({
            value: kpiType.kpi_type_id.toString(),
            label: kpiType.name_long,
          }))}
          label="KPI"
          placeholder="Select KPI..."
          value={selectedKpiTypeId}
          onChange={setSelectedKpiTypeId}
          searchable
        />
      )}

      <Group justify="flex-end">
        <Button variant="default" onClick={() => stack.close('kpi-config')}>
          Return
        </Button>
        <Tooltip
          label="All fields must be completed to add component."
          disabled={allowCreate}
        >
          <Button onClick={addKPI} disabled={!allowCreate}>
            {mode === 'edit' ? 'Update KPI Component' : 'Add KPI Component'}
          </Button>
        </Tooltip>
      </Group>
    </Stack>
  )
}

export default KPIConfig

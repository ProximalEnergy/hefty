import { Box, Group, SimpleGrid, Stack } from '@mantine/core'

import {
  EquipmentSummary,
  type EquipmentSummaryStat,
} from './equipment-summary'
import { InstallDetails } from './install-details'
import { ServiceDetails } from './service-details'
import { useBessPcsStaticData } from './use-bess-pcs-static-data'
import { useEquipmentHeaderDetails } from './use-equipment-header-details'
import { useEquipmentSummary } from './use-equipment-summary'

type EquipmentHeaderProps = {
  projectId?: string
  isAdmin: boolean
  placedInServiceDate?: string | null
  poi: number | null
}

const formatNumber = (value: number | null) => {
  if (value === null) {
    return 'N/A'
  }

  return value.toFixed(2)
}

const formatInteger = (value: number | null) => {
  if (value === null) {
    return 'N/A'
  }

  return value.toString()
}

export function EquipmentHeader({
  projectId,
  isAdmin,
  placedInServiceDate,
  poi,
}: EquipmentHeaderProps) {
  const staticData = useBessPcsStaticData({ projectId })
  const summary = useEquipmentSummary({ staticData })
  const details = useEquipmentHeaderDetails({ projectId })

  const showPcsValues = !summary.isPcsLoading && !summary.hasPcsError
  const showChildValues =
    showPcsValues &&
    !summary.isChildDevicesLoading &&
    !summary.hasChildDevicesError

  const summaryStats: EquipmentSummaryStat[] = [
    {
      label: 'MWac per device',
      value: showPcsValues ? formatNumber(summary.mwacPerDevice) : 'N/A',
    },
    {
      label: 'Total MWac',
      value: showPcsValues ? formatNumber(summary.totalMwac) : 'N/A',
      detail:
        showPcsValues && poi !== null && summary.totalMwac !== null
          ? `POI limit: ${poi.toFixed(2)} MWac`
          : undefined,
    },
    ...summary.childDeviceSummary.map((item) => ({
      label: item.label,
      value: showChildValues ? formatInteger(item.total) : 'N/A',
      detail: (() => {
        if (!showChildValues) {
          return undefined
        }

        return item.perPcs !== null ? `${item.perPcs} per PCS` : undefined
      })(),
    })),
  ]

  const modalStats: EquipmentSummaryStat[] = [
    {
      label: 'Count on site',
      value: summary.deviceCount.toString(),
    },
    {
      label: 'MWac per device',
      value: showPcsValues ? formatNumber(summary.mwacPerDevice) : 'N/A',
    },
    {
      label: 'Total MWac',
      value: showPcsValues ? formatNumber(summary.totalMwac) : 'N/A',
    },
  ]

  if (poi !== null) {
    modalStats.push({
      label: 'POI limit',
      value: `${poi.toFixed(2)} MWac`,
    })
  }

  return (
    <Stack gap="md">
      <Group align="flex-start" wrap="wrap" style={{ width: '100%' }}>
        <Box style={{ flex: '1 1 0', minWidth: 0 }}>
          <EquipmentSummary
            title={summary.title}
            countLabel={summary.countLabel}
            imageAlt={summary.title}
            imageSrc={summary.imageSrc}
            imageFallbackSrc={summary.imageFallbackSrc}
            imagePlaceholderSrc={summary.imagePlaceholderSrc}
            isLoadingImage={summary.isDeviceModelsLoading}
            stats={summaryStats}
            modalStats={modalStats}
          />
        </Box>

        <Box style={{ flex: '0 0 auto', marginLeft: 'auto' }}>
          <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
            <InstallDetails
              projectId={projectId}
              isAdmin={isAdmin}
              placedInServiceDate={placedInServiceDate}
              epcContractor={details.epcContractor}
              isContractorLoading={details.isLoading}
            />

            <ServiceDetails
              projectId={projectId}
              isAdmin={isAdmin}
              serviceContractor={details.serviceContractor}
              isContractorLoading={details.isLoading}
            />
          </SimpleGrid>
        </Box>
      </Group>
    </Stack>
  )
}

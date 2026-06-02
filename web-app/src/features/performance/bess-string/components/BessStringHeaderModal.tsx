import type { BessStringSpec } from '@/api/v1/operational/bess_strings'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useResizePlotlyCharts } from '@/hooks/useResizePlotlyCharts'
import {
  Box,
  Image,
  Modal,
  SimpleGrid,
  Skeleton,
  Stack,
  Tabs,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import type { PlotType } from 'plotly.js'
import type { ReactNode, SyntheticEvent } from 'react'
import { useRef, useState } from 'react'

import {
  formatAuxiliaryFrequency,
  formatBmsAccuracyRanges,
  formatDimensions,
  formatKw,
  formatKwh,
  formatSpecValue,
  formatStandards,
  formatTempRange,
  formatVoltageRange,
  parsePowerLimitMap,
  powerLimitMapToMwGrid,
} from '@/features/performance/bess-string/utils/bess-string-spec-format'

type BessStringHeaderModalProps = {
  opened: boolean
  onClose: () => void
  title: string
  deviceModelImageUrl: string
  deviceModelImageFallbackUrl: string
  onDeviceModelImageError: (event: SyntheticEvent<HTMLImageElement>) => void
  bessString: BessStringSpec | null
  isLoading: boolean
  brand: string | null
  model: string | null
  deviceCount: number
  mwdcPerDevice: number | null
  totalMWdc: number | null
  poiMwac: number | null
}

function SpecField({
  label,
  value,
}: {
  label: string
  value: string | null | undefined
}) {
  if (!value || value === 'N/A') {
    return null
  }

  return (
    <Text size="sm" c="dimmed">
      {label}:{' '}
      <Text component="span" fw={500}>
        {value}
      </Text>
    </Text>
  )
}

function SpecSection({
  title,
  children,
}: {
  title: string
  children: ReactNode
}) {
  return (
    <Stack gap="xs">
      <Text size="xs" fw={700} c="dimmed" tt="uppercase">
        {title}
      </Text>
      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
        {children}
      </SimpleGrid>
    </Stack>
  )
}

function PowerLimitHeatmap({
  title,
  limitMap,
}: {
  title: string
  limitMap: Record<string, unknown> | null | undefined
}) {
  const parsed = parsePowerLimitMap(limitMap)
  const z = parsed ? powerLimitMapToMwGrid(parsed) : null

  if (!parsed || !z || !parsed.soc_pct || !parsed.temperature_c) {
    return (
      <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
        No {title.toLowerCase()} data available
      </Text>
    )
  }

  const xLabels = parsed.soc_pct.map((value) => String(value))
  const yLabels = parsed.temperature_c.map((value) => String(value))

  return (
    <Box w="100%" maw="100%" mx="auto" style={{ overflow: 'hidden' }}>
      <PlotlyPlot
        data={[
          {
            x: xLabels,
            y: yLabels,
            z,
            type: 'heatmap' as PlotType,
            colorscale: 'Blues',
            colorbar: { title: { text: 'MW' } },
            hovertemplate:
              'SOC: %{x}<br>Temp: %{y} °C<br>Power: %{z:.2f} MW<extra></extra>',
          },
        ]}
        layout={{
          title: { text: title, font: { size: 12 } },
          xaxis: { title: { text: 'SOC (%)' } },
          yaxis: { title: { text: 'Temperature (°C)' } },
          height: 320,
          margin: { l: 70, r: 40, t: 40, b: 55 },
          autosize: true,
        }}
        config={{ displayModeBar: true, responsive: true }}
      />
    </Box>
  )
}

export function BessStringHeaderModal({
  opened,
  onClose,
  title,
  deviceModelImageUrl,
  onDeviceModelImageError,
  bessString,
  isLoading,
  brand,
  model,
  deviceCount,
  mwdcPerDevice,
  totalMWdc,
  poiMwac,
}: BessStringHeaderModalProps) {
  const colorScheme = useComputedColorScheme()
  const [modalActiveTab, setModalActiveTab] = useState('overview')
  const modalContentRef = useRef<HTMLDivElement>(null)

  useResizePlotlyCharts({
    containerRef: modalContentRef,
    enabled: opened,
    dependency: modalActiveTab,
  })

  const imageFilter =
    colorScheme === 'dark' ? 'invert(1) brightness(0.7)' : 'none'

  return (
    <Modal
      opened={opened}
      onClose={onClose}
      title={title}
      size="xl"
      yOffset="5vh"
    >
      <div ref={modalContentRef}>
        {isLoading ? (
          <Skeleton height={400} />
        ) : bessString ? (
          <Tabs
            value={modalActiveTab}
            onChange={(value) => setModalActiveTab(value || 'overview')}
            defaultValue="overview"
            variant="outline"
          >
            <Tabs.List>
              <Tabs.Tab value="overview">Overview</Tabs.Tab>
              <Tabs.Tab value="bms">BMS</Tabs.Tab>
              <Tabs.Tab value="environmental">Environmental</Tabs.Tab>
              <Tabs.Tab value="power-limits">Power Limits</Tabs.Tab>
            </Tabs.List>

            <Tabs.Panel value="overview" pt="md">
              <Stack gap="md">
                <Image
                  src={deviceModelImageUrl}
                  alt={title}
                  style={{ filter: imageFilter }}
                  maw={280}
                  mah={280}
                  fit="contain"
                  radius="md"
                  mx="auto"
                  onError={onDeviceModelImageError}
                />
                <SpecSection title="Identity">
                  <SpecField
                    label="Manufacturer"
                    value={formatSpecValue(brand)}
                  />
                  <SpecField label="Model" value={formatSpecValue(model)} />
                  <SpecField
                    label="Configuration"
                    value={formatSpecValue(bessString.configuration)}
                  />
                  <SpecField
                    label="Chemistry"
                    value={formatSpecValue(bessString.chemistry)}
                  />
                </SpecSection>

                <SpecSection title="Electrical ratings">
                  <SpecField
                    label="Nominal energy"
                    value={formatKwh(bessString.nominal_energy_kwh)}
                  />
                  <SpecField
                    label="Nominal power"
                    value={formatKw(bessString.nominal_power_kw)}
                  />
                  <SpecField
                    label="Max charge power"
                    value={formatKw(bessString.charge_power_max_kw)}
                  />
                  <SpecField
                    label="Max discharge power"
                    value={formatKw(bessString.discharge_power_max_kw)}
                  />
                  <SpecField
                    label="Operating voltage"
                    value={formatVoltageRange(
                      bessString.operating_voltage_min_v,
                      bessString.operating_voltage_max_v,
                    )}
                  />
                </SpecSection>

                <SpecSection title="String configuration">
                  <SpecField
                    label="Cells in series"
                    value={formatSpecValue(bessString.cells_in_series)}
                  />
                  <SpecField
                    label="Strings in parallel"
                    value={formatSpecValue(bessString.strings_in_parallel)}
                  />
                  <SpecField
                    label="Module count"
                    value={formatSpecValue(bessString.module_count)}
                  />
                </SpecSection>

                <SpecSection title="Site summary">
                  <SpecField
                    label="Count on site"
                    value={String(deviceCount)}
                  />
                  <SpecField
                    label="MWdc per device"
                    value={
                      mwdcPerDevice !== null ? mwdcPerDevice.toFixed(2) : 'N/A'
                    }
                  />
                  <SpecField
                    label="Total MWdc"
                    value={totalMWdc !== null ? totalMWdc.toFixed(2) : 'N/A'}
                  />
                  {poiMwac != null && (
                    <SpecField
                      label="POI limit"
                      value={`${poiMwac.toFixed(2)} MWac`}
                    />
                  )}
                </SpecSection>

                <SpecSection title="Physical">
                  <SpecField
                    label="Dimensions (W × D × H)"
                    value={formatDimensions(bessString)}
                  />
                  <SpecField
                    label="Weight"
                    value={
                      bessString.weight_kg != null
                        ? `${bessString.weight_kg.toFixed(0)} kg`
                        : 'N/A'
                    }
                  />
                </SpecSection>
              </Stack>
            </Tabs.Panel>

            <Tabs.Panel value="bms" pt="md">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <SpecField
                  label="BMS supply voltage"
                  value={
                    bessString.bms_supply_voltage_vdc != null
                      ? `${bessString.bms_supply_voltage_vdc} Vdc`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Cell voltage accuracy"
                  value={formatBmsAccuracyRanges(
                    bessString.bms_cell_voltage_accuracy_mv,
                    'mV',
                  )}
                />
                <SpecField
                  label="Total voltage accuracy"
                  value={
                    bessString.bms_total_voltage_accuracy_pct != null
                      ? `±${bessString.bms_total_voltage_accuracy_pct}%`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Total voltage detection"
                  value={formatVoltageRange(
                    bessString.bms_total_voltage_detection_min_v,
                    bessString.bms_total_voltage_detection_max_v,
                  )}
                />
                <SpecField
                  label="Current accuracy"
                  value={
                    bessString.bms_current_accuracy_pct != null
                      ? `±${bessString.bms_current_accuracy_pct}%`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Current range"
                  value={
                    bessString.bms_current_min_a != null &&
                    bessString.bms_current_max_a != null
                      ? `${bessString.bms_current_min_a} – ${bessString.bms_current_max_a} A`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Temperature accuracy"
                  value={formatBmsAccuracyRanges(
                    bessString.bms_temperature_accuracy_c,
                    '°C',
                  )}
                />
                <SpecField
                  label="SOC accuracy"
                  value={
                    bessString.bms_soc_accuracy_pct != null
                      ? `±${bessString.bms_soc_accuracy_pct}%`
                      : 'N/A'
                  }
                />
              </SimpleGrid>
              {bessString.bms_soc_accuracy_notes && (
                <Text size="sm" c="dimmed" mt="md">
                  Notes:{' '}
                  <Text component="span" fw={500}>
                    {bessString.bms_soc_accuracy_notes}
                  </Text>
                </Text>
              )}
            </Tabs.Panel>

            <Tabs.Panel value="environmental" pt="md">
              <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
                <SpecField
                  label="Battery enclosure"
                  value={formatSpecValue(bessString.enclosure_rating_battery)}
                />
                <SpecField
                  label="Electrical enclosure"
                  value={formatSpecValue(
                    bessString.enclosure_rating_electrical,
                  )}
                />
                <SpecField
                  label="Anti-corrosion"
                  value={formatSpecValue(bessString.anti_corrosion_rating)}
                />
                <SpecField
                  label="Operating temperature"
                  value={formatTempRange(
                    bessString.operating_temp_min_c,
                    bessString.operating_temp_max_c,
                  )}
                />
                <SpecField
                  label="Storage temperature"
                  value={formatTempRange(
                    bessString.storage_temp_min_c,
                    bessString.storage_temp_max_c,
                  )}
                />
                <SpecField
                  label="Relative humidity"
                  value={
                    bessString.relative_humidity_min_pct != null &&
                    bessString.relative_humidity_max_pct != null
                      ? `${bessString.relative_humidity_min_pct} – ${bessString.relative_humidity_max_pct}%`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Max altitude"
                  value={
                    bessString.altitude_max_m != null
                      ? `${bessString.altitude_max_m.toFixed(0)} m`
                      : 'N/A'
                  }
                />
                <SpecField
                  label="Thermal management"
                  value={formatSpecValue(bessString.thermal_management_method)}
                />
                <SpecField
                  label="Auxiliary power phase"
                  value={formatSpecValue(bessString.auxiliary_power_phase)}
                />
                <SpecField
                  label="Auxiliary AC voltage"
                  value={formatVoltageRange(
                    bessString.auxiliary_power_ac_min_v,
                    bessString.auxiliary_power_ac_max_v,
                  )}
                />
                <SpecField
                  label="Auxiliary frequency"
                  value={formatAuxiliaryFrequency(
                    bessString.auxiliary_power_frequency_hz,
                  )}
                />
                <SpecField
                  label="Standards"
                  value={formatStandards(bessString.standards)}
                />
              </SimpleGrid>
            </Tabs.Panel>

            <Tabs.Panel value="power-limits" pt="md">
              <Stack gap="lg">
                <PowerLimitHeatmap
                  title="Charge Power Limit"
                  limitMap={bessString.charge_power_limit_map}
                />
                <PowerLimitHeatmap
                  title="Discharge Power Limit"
                  limitMap={bessString.discharge_power_limit_map}
                />
              </Stack>
            </Tabs.Panel>
          </Tabs>
        ) : (
          <Stack gap="md">
            <Image
              src={deviceModelImageUrl}
              alt={title}
              style={{ filter: imageFilter }}
              maw={280}
              mah={280}
              fit="contain"
              radius="md"
              mx="auto"
              onError={onDeviceModelImageError}
            />
            <Text
              size="sm"
              c="dimmed"
              style={{ fontStyle: 'italic' }}
              ta="center"
            >
              No technical information available
            </Text>
          </Stack>
        )}
      </div>
    </Modal>
  )
}

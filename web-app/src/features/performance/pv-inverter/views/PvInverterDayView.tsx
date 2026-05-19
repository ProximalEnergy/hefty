import CustomCard from '@/components/CustomCard'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { PcsHeatmap } from '@/features/performance/pv-inverter/components/PcsHeatmap'
import { RingProgressCard } from '@/features/performance/pv-inverter/components/RingProgressCard'
import { usePvInverterContext } from '@/features/performance/pv-inverter/hooks/use-pv-inverter-context'
import { usePvInverterDayViewModel } from '@/features/performance/pv-inverter/hooks/use-pv-inverter-day-view-model'
import { colorFromPercent } from '@/features/performance/pv-inverter/utils/color-from-percent'
import {
  ActionIcon,
  Button,
  Checkbox,
  Group,
  Skeleton,
  Slider,
  Stack,
} from '@mantine/core'
import {
  IconExternalLink,
  IconPlayerPauseFilled,
  IconPlayerPlayFilled,
} from '@tabler/icons-react'
import { Link } from 'react-router'

type PvInverterDayViewProps = {
  context: ReturnType<typeof usePvInverterContext>
}

export function PvInverterDayView({ context }: PvInverterDayViewProps) {
  const model = usePvInverterDayViewModel({ context })
  const energyPath = `/projects/${context.projectId}/kpis/type/6`
  const energyQuery = `start=${model.startLink}&end=${model.endLink}`

  return (
    <Stack ref={model.tabPanelRef} gap="md" style={{ flex: 1, minHeight: 0 }}>
      <Skeleton visible={model.data.isLoading}>
        <Group>
          <AdvancedDatePicker
            maxDays={1}
            includeTodayInDateRange
            disableQuickActions
            defaultRange="today"
            includeClearButton={false}
          />
          {model.includeEnergy && model.produced?.[0]?.value ? (
            <Link
              to={`${energyPath}?${energyQuery}`}
              style={{ textDecoration: 'none', color: 'inherit' }}
            >
              <Button rightSection={<IconExternalLink size={16} />}>
                Daily Energy: {model.produced?.[0]?.value} MWh
              </Button>
            </Link>
          ) : null}
          {model.dataLength && model.dataLength > 1 && (
            <>
              <Slider
                value={model.sliderValue}
                label={model.getTimeFromSliderValue(model.sliderValue)}
                onChange={model.setSliderValue}
                min={0}
                max={
                  model.data.data?.total_power_output.value.length
                    ? model.data.data.total_power_output.value.length - 1
                    : 0
                }
                step={1}
                style={{ flex: 1 }}
              />
              <ActionIcon onClick={model.togglePlay}>
                {model.isPlaying ? (
                  <IconPlayerPauseFilled size={16} />
                ) : (
                  <IconPlayerPlayFilled size={16} />
                )}
              </ActionIcon>
            </>
          )}
        </Group>
      </Skeleton>
      <Group w="100%" justify="space-evenly" align="flex-end">
        <RingProgressCard
          title="AC Capacity (MW)"
          subtitle="Out of nameplate capacity"
          value={
            model.data.data?.total_power_output.value[
              model.dataLength && model.dataLength > 1 ? model.sliderValue : 0
            ] ?? null
          }
          total={model.data.data?.total_power_output.total_nameplate ?? null}
          isLoading={model.data.isLoading}
          color="grey"
        />
        <RingProgressCard
          title="Blocks"
          subtitle="Generating Power"
          value={
            model.data.data?.generating_power_block.value[
              model.dataLength && model.dataLength > 1 ? model.sliderValue : 0
            ] ?? null
          }
          total={model.data.data?.generating_power_block.total ?? null}
          isLoading={model.data.isLoading}
          color={
            model.data.data
              ? colorFromPercent(
                  model.data.data.generating_power_block.value[
                    model.dataLength && model.dataLength > 1
                      ? model.sliderValue
                      : 0
                  ],
                  model.data.data.generating_power_block.total,
                )
              : 'grey'
          }
        />
        <RingProgressCard
          title="PCSs"
          subtitle="Generating Power"
          value={
            model.data.data?.generating_power_pcs.value[
              model.dataLength && model.dataLength > 1 ? model.sliderValue : 0
            ] ?? null
          }
          total={model.data.data?.generating_power_pcs.total ?? null}
          isLoading={model.data.isLoading}
          color={
            model.data.data
              ? colorFromPercent(
                  model.data.data.generating_power_pcs.value[
                    model.dataLength && model.dataLength > 1
                      ? model.sliderValue
                      : 0
                  ],
                  model.data.data.generating_power_pcs.total,
                )
              : 'grey'
          }
        />
      </Group>
      <CustomCard
        title="Block Output Distribution"
        style={{ height: '250px' }}
        info="This plot shows the power output of each block."
        headerChildren={
          <Checkbox
            label="Normalize by DC Input"
            value={model.blockNormalize ? 'true' : 'false'}
            onChange={(event) =>
              model.setBlockNormalize(event.currentTarget.checked)
            }
          />
        }
      >
        <PlotlyPlot
          data={
            model.data.data && [
              {
                x: model.blockData?.x,
                y: model.blockData?.y[
                  model.dataLength && model.dataLength > 1
                    ? model.sliderValue
                    : 0
                ],
                customdata: model.blockData?.customdata,
                type: 'bar',
              },
            ]
          }
          layout={
            model.data.data && {
              xaxis: { type: 'category', title: { text: 'Block' } },
              yaxis: {
                range: [
                  0,
                  model.blockData ? model.blockData.yaxis_range_max : 1,
                ],
                title: {
                  text: model.blockNormalize ? 'Power (%)' : 'Power (MW)',
                },
              },
            }
          }
          isLoading={model.data.isLoading}
          error={model.data.error}
        />
      </CustomCard>
      <CustomCard
        title="PCS Output Distribution"
        style={{ height: '250px' }}
        info="This plot shows the power output of each PCS."
        headerChildren={
          <Checkbox
            label="Normalize by DC Input"
            value={model.pcsNormalize ? 'true' : 'false'}
            onChange={(event) =>
              model.setPcsNormalize(event.currentTarget.checked)
            }
          />
        }
      >
        <PlotlyPlot
          data={
            model.data.data && [
              {
                x: model.pcsData?.x,
                y: model.pcsData?.y[
                  model.dataLength && model.dataLength > 1
                    ? model.sliderValue
                    : 0
                ],
                customdata: model.pcsData?.customdata,
                type: 'bar',
              },
            ]
          }
          layout={
            model.data.data && {
              xaxis: { type: 'category', title: { text: 'PCS' } },
              yaxis: {
                range: [0, model.pcsData ? model.pcsData.yaxis_range_max : 1],
                title: {
                  text: model.pcsNormalize ? 'Power (%)' : 'Power (MW)',
                },
              },
            }
          }
          isLoading={model.data.isLoading}
          error={model.data.error}
        />
      </CustomCard>
      {model.hasPCSModules && (
        <CustomCard
          title="PCS Module Output Distribution"
          style={{ height: '250px' }}
        >
          <PlotlyPlot
            data={
              model.data.data && [
                {
                  x: model.data.data.pcs_module_power_distribution?.x,
                  y: model.data.data.pcs_module_power_distribution?.y[
                    model.dataLength && model.dataLength > 1
                      ? model.sliderValue
                      : 0
                  ],
                  customdata:
                    model.data.data.pcs_module_power_distribution?.customdata,
                  type: 'bar',
                },
              ]
            }
            layout={
              model.data.data && {
                xaxis: {
                  type: 'category',
                  title: { text: 'PCS Module' },
                },
                yaxis: {
                  range: [
                    0,
                    (model.data.data.pcs_module_power_distribution
                      ?.yaxis_range_max ?? 1) * 1.05,
                  ],
                  title: { text: 'Power (MW)' },
                },
              }
            }
            isLoading={model.data.isLoading}
            error={model.data.error}
          />
        </CustomCard>
      )}
      <CustomCard
        title={
          'PCS Power Heatmap' +
          (model.dataLength && model.dataLength > 1 ? '' : ' (Last 24 hours)')
        }
        style={{ height: '500px' }}
        info="This plot shows the power output of each PCS over time."
      >
        <PcsHeatmap
          projectId={context.projectId}
          startQuery={model.startQuery}
          endQuery={model.endQuery}
        />
      </CustomCard>
    </Stack>
  )
}

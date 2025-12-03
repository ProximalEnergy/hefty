import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  SensorTypeEnum,
} from '@/api/enumerations'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { ProjectTypeId } from '@/api/v1/operational/project_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import { SensorType } from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import { useGetDevicesV2 } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import {
  ActionIcon,
  Tooltip,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { IconArrowBackUp } from '@tabler/icons-react'
import { UseQueryOptions } from '@tanstack/react-query'
import {
  Background,
  Controls,
  Edge,
  Handle,
  Node,
  NodeMouseHandler,
  NodeProps,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dayjs from 'dayjs'
import isSameOrBefore from 'dayjs/plugin/isSameOrBefore'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import 'react'
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

import { BlockHeader } from './BlockHeader'
import { PowerFlowEdge } from './PowerFlowEdge'

dayjs.extend(isSameOrBefore)
dayjs.extend(timezone)
dayjs.extend(utc)

const SLDGlobalStyles = () => {
  const theme = useMantineTheme()
  return (
    <style>{`
      .react-flow__controls button {
        background-color: ${theme.white};
        border-bottom-color: ${theme.colors.gray[4]};
        &:hover {
          background-color: ${theme.colors.gray[1]};
        }
      }

      .dark .react-flow__controls button {
        background-color: ${theme.colors.dark[6]};
        border-bottom-color: ${theme.colors.dark[4]};
        fill: ${theme.colors.dark[0]};
        &:hover {
          background-color: ${theme.colors.dark[5]};
        }
      }

      .dark .react-flow__background {
        background-color: ${theme.colors.dark[7]};
      }
    `}</style>
  )
}

const useNodeColorScheme = () => {
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const isDarkMode = computedColorScheme === 'dark'

  return {
    isDarkMode,
    // Label and text colors
    labelColor: isDarkMode ? theme.colors.dark[0] : theme.colors.dark[9],
    textColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],

    // Stroke colors
    strokeColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],
    strongStrokeColor: isDarkMode ? theme.colors.dark[0] : theme.colors.dark[9],

    // Fill colors for batteries/strings
    emptyFillColor: isDarkMode ? theme.colors.dark[6] : theme.colors.gray[0],
    unusableFillColor: isDarkMode ? theme.colors.dark[5] : theme.colors.gray[2],
    stringIconEmptyFill: isDarkMode ? theme.colors.dark[7] : theme.white,

    // Bus and connection colors
    busColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],
    mainBusColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],
    connectionColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],

    // Other component colors
    terminalColor: isDarkMode ? theme.colors.dark[2] : theme.colors.gray[7],
  }
}

const roundDownToNearest5Minutes = (d: dayjs.Dayjs) => {
  const roundedMinutes = Math.floor(d.minute() / 5) * 5
  return d.minute(roundedMinutes).second(0).millisecond(0)
}

type AllSensors = { [key: number]: { value: number | null; name: string } }

// Define specific data types for each node type
type TransformerData = {
  label: string
  tooltip_label?: string
  block_device_id?: number
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type ProjectMeterData = {
  label: string
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type PCSData = {
  label: string
  tooltip_label?: string
  block_device_id?: number
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type BankData = {
  label: string
  tooltip_label?: string
  soc: number
  soh: number
  faulted_capacity: number
  is_charging?: boolean
  block_device_id?: number
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type StringData = {
  label: string
  tooltip_label?: string
  soc: number
  soh: number
  faulted_capacity: number
  is_charging?: boolean
  block_device_id?: number
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type BusData = {
  is_ac?: boolean
  x_spacing_pcs?: number
  ac_bus_width?: number
  num_pcs?: number
  battery_spacing_y?: number
  dc_bus_height?: number
  num_batteries_per_pcs?: number
  // For project-level bus
  is_project_bus?: boolean
  block_layouts?: { x_offset: number; transformer_node: CustomNode }[]
  project_bus_width?: number
  project_bus_x_start?: number
  // For vertical bus (BESS MV circuit layout)
  is_vertical_bus?: boolean
  circuit_positions?: number[]
  vertical_bus_height?: number
  vertical_bus_start_y?: number
  all_sensors?: AllSensors
  sensorTypeMap: Map<number, SensorType>
}

type GridData = {
  label: string
}

type CircuitLabelData = {
  label: string
}

// Create a discriminated union of custom node types
type CustomNode =
  | Node<TransformerData, 'transformer'>
  | Node<PCSData, 'pcs'>
  | Node<BankData, 'battery'>
  | Node<StringData, 'string'>
  | Node<BusData, 'bus'>
  | Node<ProjectMeterData, 'project_meter'>
  | Node<GridData, 'grid'>
  | Node<BusData, 'verticalConnection'>
  | Node<CircuitLabelData, 'circuitLabel'>

type NodeWithBlockDeviceId =
  | Node<TransformerData, 'transformer'>
  | Node<PCSData, 'pcs'>
  | Node<BankData, 'battery'>
  | Node<StringData, 'string'>

const hasBlockDeviceId = (node: CustomNode): node is NodeWithBlockDeviceId => {
  const data = node.data as { block_device_id?: unknown } | undefined

  return typeof data?.block_device_id === 'number'
}

const BESSTooltipContent = ({
  label,
  sensors,
  isBank,
  is_charging,
}: {
  label: string
  sensors?: AllSensors
  isBank: boolean
  is_charging?: boolean
}) => {
  if (!sensors) return <div>{label}</div>

  const socVal = isBank ? sensors[44]?.value : sensors[45]?.value
  const voltageVal = isBank ? sensors[51]?.value : sensors[58]?.value
  const currentVal = isBank ? sensors[50]?.value : sensors[57]?.value
  const sohVal = isBank ? sensors[56]?.value : sensors[59]?.value
  const minTemp = isBank ? sensors[53]?.value : sensors[64]?.value
  const maxTemp = isBank ? sensors[52]?.value : sensors[63]?.value
  const minCellVoltage = isBank ? sensors[55]?.value : sensors[61]?.value
  const maxCellVoltage = isBank ? sensors[54]?.value : sensors[60]?.value

  const formatPercent = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'N/A'
    return `${(val * 100).toFixed(1)}%`
  }

  return (
    <>
      <div>{label}</div>
      <hr />
      <div>SOC: {formatPercent(socVal)}</div>
      <div>
        Voltage:{' '}
        {voltageVal !== null && voltageVal !== undefined
          ? `${voltageVal.toFixed(1)} V`
          : 'N/A'}
      </div>
      <div>
        Current:{' '}
        {currentVal !== null && currentVal !== undefined
          ? `${currentVal.toFixed(1)} A`
          : 'N/A'}
      </div>
      <div>
        Power:{' '}
        {(() => {
          if (
            voltageVal !== null &&
            voltageVal !== undefined &&
            currentVal !== null &&
            currentVal !== undefined
          ) {
            let powerCalc = (voltageVal * currentVal) / 1000
            if (is_charging !== undefined) {
              powerCalc = is_charging
                ? -Math.abs(powerCalc)
                : Math.abs(powerCalc)
            }
            return `${powerCalc.toFixed(1)} kW`
          }
          return 'N/A'
        })()}
      </div>
      <div>
        Temperatures:{' '}
        {minTemp !== null &&
        minTemp !== undefined &&
        maxTemp !== null &&
        maxTemp !== undefined
          ? `${minTemp.toFixed(1)} - ${maxTemp.toFixed(1)} °C`
          : 'N/A'}
      </div>
      <div>
        Cell Voltages:{' '}
        {minCellVoltage !== null &&
        minCellVoltage !== undefined &&
        maxCellVoltage !== null &&
        maxCellVoltage !== undefined
          ? `${minCellVoltage.toFixed(4)} - ${maxCellVoltage.toFixed(4)} V`
          : 'N/A'}
      </div>
      <div>SOH: {formatPercent(sohVal)}</div>
    </>
  )
}

const renderAllSensors = (
  sensors: AllSensors | undefined,
  sensorTypeMap: Map<number, SensorType>,
  preferredOrder: number[] = [],
) => {
  if (!sensors) return null

  const getUnit = (sensorTypeId: number): string => {
    const sensorType = sensorTypeMap.get(sensorTypeId)
    return sensorType?.unit || ''
  }

  const sortedSensorEntries = Object.entries(sensors)
    .filter(
      ([, sensor]) => sensor.name && sensor.name.toLowerCase() !== 'unknown',
    )
    .sort(([keyA, sensorA], [keyB, sensorB]) => {
      const indexA = preferredOrder.indexOf(Number(keyA))
      const indexB = preferredOrder.indexOf(Number(keyB))

      if (indexA !== -1 && indexB !== -1) {
        return indexA - indexB // Both are in the preferred list, sort by their order in the list
      }
      if (indexA !== -1) {
        return -1 // A is in the list, B is not, so A comes first
      }
      if (indexB !== -1) {
        return 1 // B is in the list, A is not, so B comes first
      }
      // Neither are in the list, sort by original name
      return sensorA.name.localeCompare(sensorB.name)
    })

  return (
    <>
      <hr />
      {sortedSensorEntries.map(([key, sensor]) => {
        let value = 'N/A'
        if (sensor.value !== null && typeof sensor.value === 'number') {
          const unit = getUnit(Number(key))
          let displayValue = sensor.value

          if (unit === '%') {
            displayValue *= 100
          }

          let precision = 2
          if (unit === 'MW') {
            precision = 3
          } else if (key === '82') {
            precision = 4
          }
          value = `${displayValue.toFixed(precision)} ${unit}`.trim()
        }
        return (
          <div key={key}>
            {sensor.name}: {value}
          </div>
        )
      })}
    </>
  )
}

// Custom node components with correct props typing
const TransformerNode = ({ data }: NodeProps<Node<TransformerData>>) => {
  const { labelColor, strokeColor } = useNodeColorScheme()

  const tooltipContent = (
    <>
      <div>{data.tooltip_label || data.label}</div>
      {renderAllSensors(data.all_sensors, data.sensorTypeMap)}
    </>
  )

  return (
    <Tooltip label={tooltipContent} withArrow>
      <div
        style={{
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
        }}
      >
        {/* Label positioned above transformer */}
        <div
          style={{
            position: 'absolute',
            top: '-80px',
            left: 'calc(50% + 20px)',
            transform: 'translateX(-50%)',
            fontSize: '14px',
            fontWeight: 'bold',
            whiteSpace: 'nowrap',
            textAlign: 'center',
            color: labelColor,
            zIndex: 10,
          }}
        >
          {data.label}
        </div>
        <div style={{ position: 'relative' }}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 25 100 110"
            width="100"
            height="110"
            fill="none"
            stroke={strokeColor}
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {/* coils */}
            <circle cx="50" cy="60" r="33" />
            <circle cx="50" cy="100" r="33" />
          </svg>
          {/* Top target handle */}
          <Handle
            type="target"
            position={Position.Top}
            style={{ top: '2px' }}
          />
          {/* Bottom source and target handles overlap */}
          <Handle
            id="bottom-source"
            type="source"
            position={Position.Bottom}
            style={{ top: 'auto', bottom: '2px' }}
          />
          <Handle
            id="bottom-target"
            type="target"
            position={Position.Bottom}
            style={{ top: 'auto', bottom: '2px' }}
          />
        </div>
      </div>
    </Tooltip>
  )
}

const ProjectMeterNode = ({ data }: NodeProps<Node<ProjectMeterData>>) => {
  const { strongStrokeColor } = useNodeColorScheme()

  const tooltipContent = (
    <>
      <div>{data.label}</div>
      {renderAllSensors(
        data.all_sensors,
        data.sensorTypeMap,
        // meter_active_power, meter_reactive_power, meter_power_factor, meter_frequency
        [1, 8, 12, 11],
      )}
    </>
  )

  const activePower = data.all_sensors?.[1]?.value ?? null
  const reactivePower = data.all_sensors?.[8]?.value ?? null

  return (
    <Tooltip label={tooltipContent} withArrow>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{ position: 'relative' }}>
          <svg
            viewBox="0 0 100 100"
            width="80"
            height="80"
            fill="none"
            stroke={strongStrokeColor}
            strokeWidth="6"
          >
            <circle cx="50" cy="50" r="45" />
            <text
              x="50"
              y="55"
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="40"
              fontWeight="bold"
              fill={strongStrokeColor}
              stroke="none"
            >
              M
            </text>
          </svg>
          <Handle
            type="target"
            position={Position.Top}
            style={{ top: '-2px' }}
          />
          <Handle
            type="source"
            position={Position.Bottom}
            style={{ bottom: '2px' }}
          />
        </div>
        <div
          style={{
            fontSize: '12px',
            whiteSpace: 'nowrap',
          }}
        >
          <div>{data.label}</div>
          <div>
            P: {activePower !== null ? activePower.toFixed(2) : 'N/A'} MW
          </div>
          <div>
            Q: {reactivePower !== null ? reactivePower.toFixed(1) : 'N/A'} VAR
          </div>
        </div>
      </div>
    </Tooltip>
  )
}

const PCSNode = ({ data }: NodeProps<Node<PCSData>>) => {
  const { strokeColor } = useNodeColorScheme()

  const acPower = data.all_sensors?.[31]?.value ?? null
  const reactivePower = data.all_sensors?.[68]?.value ?? null
  const tooltipContent = (
    <>
      <div>{data.tooltip_label || data.label}</div>
      {renderAllSensors(
        data.all_sensors,
        data.sensorTypeMap,
        // bess_pcs_ac_power, bess_pcs_reactive_power
        [31, 68],
      )}
    </>
  )
  return (
    <Tooltip label={tooltipContent} withArrow>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
        }}
      >
        <div style={{ position: 'relative' }}>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 120 120"
            width="75"
            height="75"
            fill="none"
            stroke={strokeColor}
            strokeWidth="6"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{ transform: 'rotate(180deg)' }}
          >
            <rect x="6" y="6" width="108" height="108" rx="2" ry="2" />
            <line x1="6" y1="6" x2="114" y2="114" />
            <path d="M14 88 Q28 60 42 88 T70 88" />
            <line x1="75" y1="32" x2="104" y2="32" />
            <line x1="75" y1="46" x2="104" y2="46" />
          </svg>
          <Handle
            type="target"
            position={Position.Top}
            style={{ top: '-2px' }}
          />
          <Handle
            type="source"
            position={Position.Bottom}
            style={{ top: 'auto', bottom: '2px' }}
          />
        </div>
        {data.label && (
          <div style={{ fontSize: '8px', whiteSpace: 'nowrap' }}>
            <div>{data.label}</div>
            <div>
              AC Power: {acPower !== null ? acPower.toFixed(2) : 'N/A'} MW
            </div>
            <div>
              Reactive Power:{' '}
              {reactivePower !== null ? reactivePower.toFixed(1) : 'N/A'} VAR
            </div>
          </div>
        )}
      </div>
    </Tooltip>
  )
}

const BatteryNode = ({ data }: NodeProps<Node<BankData>>) => {
  const { strongStrokeColor, emptyFillColor, unusableFillColor, textColor } =
    useNodeColorScheme()

  const { all_sensors, is_charging } = data
  const soc = (all_sensors?.[44]?.value ?? 0) * 100 // bess_bank_soc_percent
  const soh = (all_sensors?.[56]?.value ?? 0) * 100 // bess_bank_soh_percent
  const unusable_capacity = 100 - soh
  const voltage = all_sensors?.[51]?.value // bess_bank_voltage
  const current = all_sensors?.[50]?.value // bess_bank_current

  let powerCalc =
    voltage !== null &&
    voltage !== undefined &&
    current !== null &&
    current !== undefined
      ? (voltage * current) / 1000
      : null

  if (powerCalc !== null) {
    powerCalc = is_charging ? -Math.abs(powerCalc) : Math.abs(powerCalc)
  }

  const power = powerCalc !== null ? powerCalc.toFixed(1) : null

  const healthy_capacity = soh
  const red_width = 0 // No faulted capacity for now
  const green_width = (soc / 100) * healthy_capacity
  const white_width = healthy_capacity - green_width
  const gray_width = unusable_capacity

  const green_x = red_width
  const white_x = green_x + green_width
  const gray_x = white_x + white_width

  const tooltipContent = (
    <BESSTooltipContent
      label={data.tooltip_label || data.label}
      sensors={all_sensors}
      isBank
      is_charging={is_charging}
    />
  )

  return (
    <Tooltip label={tooltipContent} withArrow>
      <div
        style={{
          position: 'relative',
          width: 60,
          textAlign: 'center',
        }}
      >
        <div style={{ position: 'relative' }}>
          <Handle type="target" position={Position.Left} />
          {power !== null && (
            <div
              style={{
                position: 'absolute',
                left: -60,
                top: -8,
                fontSize: '10px',
                color: textColor,
                width: '60px',
                textAlign: 'center',
              }}
            >
              {power !== null ? Number(power) : null} kW
            </div>
          )}
          <Handle type="source" position={Position.Right} />
          <svg
            width="100%"
            height="24"
            viewBox="0 0 100 24"
            preserveAspectRatio="none"
            style={{ display: 'block' }}
          >
            <rect
              x="0"
              y="0"
              width="100"
              height="24"
              fill="none"
              stroke={strongStrokeColor}
              strokeWidth="2"
            />
            <rect x="0" y="0" width={red_width} height="24" fill="red" />
            <rect
              x={green_x}
              y="0"
              width={green_width}
              height="24"
              fill="green"
            />
            <rect
              x={white_x}
              y="0"
              width={white_width}
              height="24"
              fill={emptyFillColor}
            />
            <rect
              x={gray_x}
              y="0"
              width={gray_width}
              height="24"
              fill={unusableFillColor}
            />
          </svg>
        </div>
        {data.label && (
          <div style={{ fontSize: '10px' }}>SoC: {soc.toFixed(1)}%</div>
        )}
      </div>
    </Tooltip>
  )
}

const StringIcon = ({
  soc,
  soh,
  faulted_capacity,
}: {
  soc: number
  soh: number
  faulted_capacity: number
}) => {
  const { strokeColor, terminalColor, stringIconEmptyFill, unusableFillColor } =
    useNodeColorScheme()

  const healthy_capacity = soh - faulted_capacity
  // The widths are percentages, scaled to the inner container width of the SVG
  const container_width = 32 // inner width of battery icon (34px - 2px padding)
  const red_width = (faulted_capacity / 100) * container_width
  const green_width = ((soc / 100) * healthy_capacity * container_width) / 100
  const white_width =
    ((healthy_capacity - (soc / 100) * healthy_capacity) * container_width) /
    100
  const gray_width = ((100 - soh) * container_width) / 100

  const green_x = 2 + red_width
  const white_x = green_x + green_width
  const gray_x = white_x + white_width

  return (
    <svg width="40" height="20" viewBox="0 0 40 20" fill="none">
      <rect
        x="1"
        y="3"
        width="34"
        height="14"
        rx="2"
        ry="2"
        fill={stringIconEmptyFill}
        stroke={strokeColor}
        strokeWidth="1"
      />
      {/* The bar inside the icon */}
      <rect x="2" y="4" width={red_width} height="12" fill="red" />
      <rect x={green_x} y="4" width={green_width} height="12" fill="green" />
      <rect
        x={white_x}
        y="4"
        width={white_width}
        height="12"
        fill={stringIconEmptyFill}
      />
      <rect
        x={gray_x}
        y="4"
        width={gray_width}
        height="12"
        fill={unusableFillColor}
      />
      {/* The positive terminal */}
      <rect x="34" y="7" width="4" height="6" rx="1" fill={terminalColor} />
    </svg>
  )
}

const StringNode = ({ data }: NodeProps<Node<StringData>>) => {
  const { label, soc, soh, faulted_capacity, all_sensors, is_charging } = data
  const tooltipContent = (
    <BESSTooltipContent
      label={data.tooltip_label || label}
      sensors={all_sensors}
      isBank={false}
      is_charging={is_charging}
    />
  )
  return (
    <Tooltip label={tooltipContent} withArrow>
      <div
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          gap: '5px',
        }}
      >
        <Handle type="target" position={Position.Left} />
        <StringIcon soc={soc} soh={soh} faulted_capacity={faulted_capacity} />
        {label && (
          <div style={{ fontSize: '10px', whiteSpace: 'nowrap' }}>{label}</div>
        )}
      </div>
    </Tooltip>
  )
}

const BusNode = ({ data }: NodeProps<Node<BusData>>) => {
  const handles: React.JSX.Element[] = []

  // Check if this is the main vertical bus (used in BESS MV circuit layout)
  if (data.is_vertical_bus) {
    // Add top handle for revenue meter connection
    handles.push(
      <Handle
        key="vertical-bus-top"
        type="target"
        id="vertical-bus-top"
        position={Position.Top}
        style={{ top: '0px' }}
      />,
    )

    // Add right-side and left-side source handles for each circuit connection
    if (data.circuit_positions) {
      data.circuit_positions.forEach((circuitY: number, index: number) => {
        const busHeight = data.vertical_bus_height || 1
        const busStartY = data.vertical_bus_start_y || 0
        const relativeY = circuitY - busStartY
        const position_percent = (relativeY / busHeight) * 100

        // Right-side handle for even indices (right-side circuits)
        handles.push(
          <Handle
            key={`vertical-bus-circuit-right-${index}`}
            type="source"
            id={`vertical-bus-circuit-right-${index}`}
            position={Position.Right}
            style={{ top: `${position_percent}%` }}
          />,
        )

        // Left-side handle for odd indices (left-side circuits)
        handles.push(
          <Handle
            key={`vertical-bus-circuit-left-${index}`}
            type="source"
            id={`vertical-bus-circuit-left-${index}`}
            position={Position.Left}
            style={{ top: `${position_percent}%` }}
          />,
        )
      })
    }

    return <>{handles}</>
  }

  if (data.is_project_bus && data.project_bus_width) {
    // Add middle handle for revenue meter
    handles.push(
      <Handle
        key="proj-bus-meter"
        type="target"
        id="proj-bus-meter"
        position={Position.Top}
        style={{ left: '50%' }}
      />,
    )

    // Handle for traditional block layout with transformers
    if (data.block_layouts) {
      data.block_layouts.forEach(
        (
          layout: { x_offset: number; transformer_node: CustomNode },
          i: number,
        ) => {
          const transformer = layout.transformer_node
          if (transformer.position) {
            const handle_x_abs = transformer.position.x + 50 // center of transformer
            const busStartX = data.project_bus_x_start || 0
            const position_percent =
              ((handle_x_abs - busStartX) / (data.project_bus_width || 1)) * 100

            handles.push(
              <Handle
                key={`proj-bus-source-${i}`}
                type="source"
                id={`proj-bus-source-${i}`}
                position={Position.Bottom}
                style={{ left: `${position_percent}%` }}
              />,
            )
          }
        },
      )
    } else {
      // Handle for multi-row PCS layout - add handles for each row
      // We'll add handles dynamically based on the row buses that connect to this main bus
      for (let i = 0; i < 10; i++) {
        // Support up to 10 rows
        handles.push(
          <Handle
            key={`proj-bus-row-${i}`}
            type="source"
            id={`proj-bus-row-${i}`}
            position={Position.Bottom}
            style={{ left: `${10 + i * 10}%` }} // Distribute across the bus
          />,
        )
      }
    }
  } else if (data.is_ac) {
    if (
      data.num_pcs === undefined ||
      data.x_spacing_pcs === undefined ||
      data.ac_bus_width === undefined
    )
      return null
    // AC bus for num_pcs
    handles.push(
      <Handle
        key="ac-top-source"
        id="ac-top-source"
        type="source"
        position={Position.Top}
        style={{ top: '2px' }}
      />,
    )
    // Add left-side target handle for vertical bus connection (BESS MV circuit layout)
    handles.push(
      <Handle
        key="ac-left-target"
        id="ac-left-target"
        type="target"
        position={Position.Left}
        style={{ left: '0px' }}
      />,
    )
    // Add right-side target handle for left-side circuits
    handles.push(
      <Handle
        key="ac-right-target"
        id="ac-right-target"
        type="target"
        position={Position.Right}
        style={{ right: '0px' }}
      />,
    )
    for (let i = 0; i < data.num_pcs; i++) {
      const position =
        data.num_pcs > 1
          ? (i * data.x_spacing_pcs * 100) / data.ac_bus_width
          : 50
      handles.push(
        <Handle
          key={`ac-source-${i}`}
          type="source"
          id={`ac-bus-source-${i}`}
          position={Position.Bottom}
          style={{ left: `${position}%` }}
        />,
      )
    }
  } else {
    if (
      data.num_batteries_per_pcs === undefined ||
      data.battery_spacing_y === undefined ||
      data.dc_bus_height === undefined
    )
      return null
    // DC bus for num_batteries_per_pcs
    handles.push(
      <Handle key="dc-target" type="target" position={Position.Top} />,
    )
    for (let j = 0; j < data.num_batteries_per_pcs; j++) {
      const position =
        data.num_batteries_per_pcs > 1
          ? (j * data.battery_spacing_y * 100) / data.dc_bus_height
          : 50
      handles.push(
        <Handle
          key={`dc-source-${j}`}
          type="source"
          id={`dc-bus-source-${j}`}
          position={Position.Right}
          style={{ top: `${position}%` }}
        />,
      )
    }
  }
  return <>{handles}</>
}

const GridNode = ({ data: _data }: NodeProps<Node<GridData>>) => {
  const { strongStrokeColor } = useNodeColorScheme()

  return (
    <div style={{ position: 'relative' }}>
      <svg
        viewBox="0 0 100 100"
        width="60"
        height="60"
        fill="none"
        stroke={strongStrokeColor}
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Legs */}
        <line x1="30" y1="95" x2="50" y2="10" />
        <line x1="70" y1="95" x2="50" y2="10" />
        {/* Cross-bars */}
        <line x1="35" y1="70" x2="65" y2="70" />
        <line x1="40" y1="50" x2="60" y2="50" />
        <line x1="45" y1="30" x2="55" y2="30" />
        {/* Transmission line */}
        <line x1="10" y1="5" x2="90" y2="5" />
        <line x1="10" y1="15" x2="90" y2="15" />
      </svg>
      {/* Bottom handle to connect to revenue meter */}
      <Handle
        type="source"
        position={Position.Bottom}
        style={{ bottom: '2px' }}
      />
    </div>
  )
}

const VerticalConnectionNode = ({ data: _data }: NodeProps<Node<BusData>>) => {
  const { connectionColor } = useNodeColorScheme()
  return (
    <>
      {/* Small connection point */}
      <div
        style={{
          width: 4,
          height: 4,
          background: connectionColor,
          borderRadius: '50%',
        }}
      />
      {/* Right source handle for circuit bus connection */}
      <Handle
        id="right-source"
        type="source"
        position={Position.Right}
        style={{ right: '-2px' }}
      />
      {/* Left source handle for circuit bus connection */}
      <Handle
        id="left-source"
        type="source"
        position={Position.Left}
        style={{ left: '-2px' }}
      />
    </>
  )
}

const CircuitLabelNode = ({ data }: NodeProps<Node<CircuitLabelData>>) => {
  const { labelColor } = useNodeColorScheme()
  return (
    <div
      style={{
        fontSize: '24px',
        fontWeight: 'bold',
        color: labelColor,
        textAlign: 'center',
        whiteSpace: 'nowrap',
        userSelect: 'none',
        pointerEvents: 'none',
      }}
    >
      {data.label}
    </div>
  )
}

function SnapshotSLDContent() {
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: project, isLoading: isProjectLoading } = useSelectProject(
    projectId!,
  )
  const { data: blockDevices, isLoading: areBlockDevicesLoading } =
    useGetDevicesV2({
      pathParams: { projectId: projectId || '-1' },
      filters: { device_type_ids: [1, 6, 12] },
    })
  const { data: sensorTypes } = useGetSensorTypes({})
  const { isDarkMode, busColor, mainBusColor } = useNodeColorScheme()

  const [selectedBlockId, setSelectedBlockId] = useState<number | null>(null)
  const { fitView } = useReactFlow()

  const [timestamp, setTimestamp] = useState<dayjs.Dayjs | null>(null)
  const [isLive, setIsLive] = useState<boolean>(true)
  const [viewStartDate, setViewStartDate] = useState<dayjs.Dayjs | null>(null)
  const [viewEndDate, setViewEndDate] = useState<dayjs.Dayjs | null>(null)

  const fallbackTriggered = useRef(false)

  // This effect will run once the project is loaded and set the initial timestamp.
  useEffect(() => {
    if (project && timestamp === null) {
      const timezone = project.time_zone || 'America/Chicago'
      const tsParam = searchParams.get('ts')

      if (tsParam) {
        const parsedTs = dayjs(tsParam)
        if (parsedTs.isValid()) {
          setTimestamp(parsedTs)
          setIsLive(false)
          setViewStartDate(parsedTs.subtract(7, 'days').startOf('day'))
          setViewEndDate(parsedTs)
          return
        }
      }

      // Default to live mode
      const now = roundDownToNearest5Minutes(dayjs().tz(timezone))
      setTimestamp(now)
      setIsLive(true)
      setViewStartDate(now.subtract(7, 'days').startOf('day'))
      setViewEndDate(now)
    }
  }, [project, searchParams, timestamp])

  // This effect updates the URL when the timestamp changes.
  useEffect(() => {
    if (timestamp === null) return // Don't run until initialized

    setSearchParams(
      (prev) => {
        const newParams = new URLSearchParams(prev)
        if (isLive) {
          newParams.delete('ts')
        } else {
          newParams.set('ts', timestamp.toISOString())
        }
        return newParams
      },
      { replace: true },
    )
  }, [timestamp, isLive, setSearchParams])

  useEffect(() => {
    if (blockDevices && blockDevices.length > 0 && !selectedBlockId) {
      const projectDevice = blockDevices.find(
        (d) => d.device_type_id === DeviceTypeEnum.PROJECT,
      )
      setSelectedBlockId(projectDevice?.device_id || blockDevices[0].device_id)
    }
  }, [blockDevices, selectedBlockId])

  // Determine the currently selected top-level device (project or block)
  const selectedDevice = useMemo(() => {
    return blockDevices?.find((d) => d.device_id === selectedBlockId) || null
  }, [blockDevices, selectedBlockId])

  // Choose which device types to pull in descendant query
  const descendantDeviceTypeIds = useMemo(() => {
    if (!selectedDevice) return undefined
    if (selectedDevice.device_type_id === DeviceTypeEnum.PROJECT) {
      // Project view – include blocks and their major components
      return [
        1, 2, 3, 5, 6, 7, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,
        24, 25, 26, 27, 32,
      ]
    }
    if ([6, 12].includes(selectedDevice.device_type_id)) {
      // Block view – only need components inside the block
      return [
        2, 3, 6, 9, 11, 12, 13, 15, 16, 17, 18, 19, 20, 24, 25, 26, 27, 32, 33,
      ]
    }
    return undefined
  }, [selectedDevice])

  const { data: devices, isLoading: areDevicesLoading } = useGetDevicesV2({
    pathParams: { projectId: projectId || '-1' },
    filters: {
      deep: true,
      device_id_descendent_of: selectedBlockId,
      ...(descendantDeviceTypeIds
        ? { device_type_ids: descendantDeviceTypeIds }
        : {}),
    },
    queryOptions: {
      enabled: !!selectedBlockId,
    },
  })

  const timeSeriesQueryOptions = useMemo<Partial<UseQueryOptions>>(
    () => ({
      enabled:
        !!devices && devices.length > 0 && !!projectId && timestamp !== null,
      keepPreviousData: true,
    }),
    [devices, projectId, timestamp],
  )

  const { data: timeSeriesData, isFetching: isTimeSeriesFetching } =
    useGetTimeSeries({
      pathParams: { projectId: projectId || '-1' },
      queryParams: {
        device_ids: devices?.map((d) => d.device_id),
        start: timestamp
          ? timestamp.subtract(2, 'seconds').toISOString()
          : undefined,
        end: timestamp ? timestamp.add(2, 'seconds').toISOString() : undefined,
        interval: '1s',
      },
      queryOptions: timeSeriesQueryOptions,
    })

  const deviceDataMap = useMemo(() => {
    if (!timeSeriesData) return new Map()

    const map = new Map<
      number,
      { [key: number]: { value: number | null; name: string } }
    >()

    timeSeriesData.forEach((ts) => {
      if (ts.device_id && ts.sensor_type_id) {
        if (!map.has(ts.device_id)) {
          map.set(ts.device_id, {})
        }

        // Find the last valid value in the y array
        let lastValue = null
        if (ts.y) {
          for (let i = ts.y.length - 1; i >= 0; i--) {
            if (ts.y[i] !== null) {
              lastValue = ts.y[i]
              break
            }
          }
        }

        let valueToStore = lastValue
        // Heuristic to detect if voltage is in mV
        if (
          ts.sensor_type_id === SensorTypeEnum.BESS_CELL_VOLTAGE &&
          lastValue !== null &&
          lastValue > 5
        ) {
          valueToStore = lastValue / 1000
        }

        map.get(ts.device_id)![ts.sensor_type_id] = {
          value: valueToStore,
          name: ts.name,
        }
      }
    })
    return map
  }, [timeSeriesData])

  const sensorTypeMap = useMemo(() => {
    if (!sensorTypes) return new Map()
    return new Map(sensorTypes.map((st) => [st.sensor_type_id, st]))
  }, [sensorTypes])

  const socStats = useMemo(() => {
    if (!devices || devices.length === 0 || deviceDataMap.size === 0) {
      return null
    }

    const bess_bank_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
    )
    const bess_string_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
    )

    // Use banks if available, otherwise fall back to strings
    const targetDevices =
      bess_bank_devices.length > 0 ? bess_bank_devices : bess_string_devices
    const soc_sensor_id =
      bess_bank_devices.length > 0
        ? SensorTypeEnum.BESS_BANK_SOC_PERCENT
        : SensorTypeEnum.BESS_STRING_SOC_PERCENT

    if (targetDevices.length === 0) {
      return null
    }

    let totalSoc = 0
    let count = 0
    let minSoc: number | null = null
    let maxSoc: number | null = null

    targetDevices.forEach((device) => {
      const deviceData = deviceDataMap.get(device.device_id)
      const soc = deviceData?.[soc_sensor_id]?.value
      if (soc !== undefined && soc !== null) {
        totalSoc += soc
        count++
        if (minSoc === null || soc < minSoc) {
          minSoc = soc
        }
        if (maxSoc === null || soc > maxSoc) {
          maxSoc = soc
        }
      }
    })

    if (count === 0 || minSoc === null || maxSoc === null) {
      return null
    }

    return {
      avg: totalSoc / count,
      spread: (maxSoc - minSoc) * 100,
    }
  }, [devices, deviceDataMap])

  const cellTempStats = useMemo(() => {
    if (!devices || devices.length === 0 || deviceDataMap.size === 0) {
      return null
    }

    const bess_bank_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
    )
    const bess_string_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
    )

    // Use banks if available, otherwise fall back to strings
    const targetDevices =
      bess_bank_devices.length > 0 ? bess_bank_devices : bess_string_devices
    const min_temp_sensor_id = bess_bank_devices.length > 0 ? 53 : 64
    const max_temp_sensor_id = bess_bank_devices.length > 0 ? 52 : 63

    if (targetDevices.length === 0) {
      return null
    }

    const allTemps: number[] = []

    targetDevices.forEach((device) => {
      const deviceData = deviceDataMap.get(device.device_id)
      const minTemp = deviceData?.[min_temp_sensor_id]?.value
      const maxTemp = deviceData?.[max_temp_sensor_id]?.value

      if (minTemp !== null && minTemp !== undefined) {
        allTemps.push(minTemp)
      }
      if (maxTemp !== null && maxTemp !== undefined) {
        allTemps.push(maxTemp)
      }
    })

    if (allTemps.length === 0) {
      return null
    }

    const totalTemp = allTemps.reduce((sum, temp) => sum + temp, 0)
    const avg = totalTemp / allTemps.length
    const min = Math.min(...allTemps)
    const max = Math.max(...allTemps)
    const spread = max - min

    return {
      avg,
      spread,
    }
  }, [devices, deviceDataMap])

  const sohStats = useMemo(() => {
    if (!devices || devices.length === 0 || deviceDataMap.size === 0) {
      return null
    }

    const bess_bank_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
    )
    const bess_string_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
    )

    // Use banks if available, otherwise fall back to strings
    const targetDevices =
      bess_bank_devices.length > 0 ? bess_bank_devices : bess_string_devices
    const soh_sensor_id = bess_bank_devices.length > 0 ? 56 : 59

    if (targetDevices.length === 0) {
      return null
    }

    let totalSoh = 0
    let count = 0
    let minSoh: number | null = null
    let maxSoh: number | null = null

    targetDevices.forEach((device) => {
      const deviceData = deviceDataMap.get(device.device_id)
      const soh = deviceData?.[soh_sensor_id]?.value
      if (soh !== undefined && soh !== null) {
        totalSoh += soh
        count++
        if (minSoh === null || soh < minSoh) {
          minSoh = soh
        }
        if (maxSoh === null || soh > maxSoh) {
          maxSoh = soh
        }
      }
    })

    if (count === 0 || minSoh === null || maxSoh === null) {
      return null
    }

    return {
      avg: totalSoh / count,
      spread: (maxSoh - minSoh) * 100,
    }
  }, [devices, deviceDataMap])

  const activePcsCount = useMemo(() => {
    if (!devices || devices.length === 0 || deviceDataMap.size === 0) {
      return null
    }

    const bess_pcs_devices = devices.filter(
      (d) => d.device_type_id === DeviceTypeEnum.BESS_PCS,
    )
    const totalPcs = bess_pcs_devices.length

    if (totalPcs === 0) {
      return { active: 0, total: 0 }
    }

    let activeCount = 0

    bess_pcs_devices.forEach((pcs) => {
      const deviceData = deviceDataMap.get(pcs.device_id)
      const activePower = deviceData?.[31]?.value // bess_pcs_ac_power
      const reactivePower = deviceData?.[68]?.value // bess_pcs_reactive_power

      if (
        (activePower !== undefined &&
          activePower !== null &&
          activePower !== 0) ||
        (reactivePower !== undefined &&
          reactivePower !== null &&
          reactivePower !== 0)
      ) {
        activeCount++
      }
    })

    return { active: activeCount, total: totalPcs }
  }, [devices, deviceDataMap])

  useEffect(() => {
    // Fallback to 24 hours ago if no "now" data is available on load
    if (
      !isTimeSeriesFetching &&
      isLive &&
      !fallbackTriggered.current &&
      devices &&
      devices.length > 0
    ) {
      let hasData = false
      for (const deviceSensors of deviceDataMap.values()) {
        for (const sensor of Object.values(deviceSensors) as {
          value: number | null
          name: string
        }[]) {
          if (sensor.value !== null) {
            hasData = true
            break
          }
        }
        if (hasData) break
      }

      if (!hasData) {
        const timezone = project?.time_zone || 'America/Chicago'
        const now = roundDownToNearest5Minutes(dayjs().tz(timezone))
        setTimestamp(now.subtract(24, 'hours'))
        setIsLive(false)
        fallbackTriggered.current = true
      }
    }
  }, [
    isTimeSeriesFetching,
    deviceDataMap,
    isLive,
    devices,
    project?.time_zone,
    setTimestamp,
    setIsLive,
  ])

  const memoizedNodeTypes = useMemo(
    () => ({
      transformer: TransformerNode,
      pcs: PCSNode,
      battery: BatteryNode,
      string: StringNode,
      bus: BusNode,
      project_meter: ProjectMeterNode,
      grid: GridNode,
      verticalConnection: VerticalConnectionNode,
      circuitLabel: CircuitLabelNode,
    }),
    [],
  )

  const memoizedEdgeTypes = useMemo(() => ({ powerFlow: PowerFlowEdge }), [])

  const { nodes, edges } = useMemo<{
    nodes: CustomNode[]
    edges: Edge[]
  }>(() => {
    const selectedDevice = blockDevices?.find(
      (d) => d.device_id === selectedBlockId,
    )
    if (!devices || !selectedDevice) {
      return { nodes: [], edges: [] }
    }

    const generateSingleSnapshotSld = (
      blockDescendantDevices: typeof devices,
      showStrings: boolean,
      xOffset = 0,
      blockIndex = 0,
      blockDeviceId?: number,
    ) => {
      const transformer_device = blockDescendantDevices.find(
        (d) => d.device_type_id === DeviceTypeEnum.BESS_MVT,
      )
      const bess_pcs_devices = blockDescendantDevices.filter(
        (d) => d.device_type_id === DeviceTypeEnum.BESS_PCS,
      )
      const bess_bank_devices = blockDescendantDevices.filter(
        (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
      )
      const bess_string_devices = showStrings
        ? blockDescendantDevices.filter(
            (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
          )
        : []

      // Use strings as battery equivalents when no banks exist
      const batteryEquivalents =
        bess_bank_devices.length > 0 ? bess_bank_devices : bess_string_devices
      const useBanks = bess_bank_devices.length > 0

      const total_block_power = bess_pcs_devices.reduce((acc, pcs) => {
        const d = deviceDataMap.get(pcs.device_id)
        return acc + (d?.[31]?.value ?? 0) // bess_pcs_ac_power
      }, 0)
      const is_block_charging = total_block_power < -0.01 // Add small threshold
      const is_block_discharging = total_block_power > 0.01 // Add small threshold

      const bankIdToStringsMap = new Map<number, typeof devices>()
      if (showStrings) {
        bess_string_devices.forEach((s) => {
          if (s.parent_device_id) {
            if (!bankIdToStringsMap.has(s.parent_device_id)) {
              bankIdToStringsMap.set(s.parent_device_id, [])
            }
            bankIdToStringsMap.get(s.parent_device_id)!.push(s)
          }
        })
      }

      const num_pcs = bess_pcs_devices.length
      if (num_pcs === 0) {
        return {
          nodes: [],
          edges: [],
          width: 0,
          transformerNode: null,
          total_block_power: 0,
          is_block_charging: false,
          is_block_discharging: false,
        }
      }
      const num_batteries_per_pcs = Math.ceil(
        batteryEquivalents.length / num_pcs,
      )

      // Dynamically calculate spacing based on the number of PCS units.
      // Provides wider spacing for fewer units and gets tighter for more.
      const x_spacing_pcs = Math.max(120, 200 - num_pcs * 10)

      let battery_spacing_y = 40
      const y_spacing_strings = 25
      if (showStrings) {
        let maxStrings = 0
        bankIdToStringsMap.forEach((strings) => {
          if (strings.length > maxStrings) maxStrings = strings.length
        })
        battery_spacing_y = Math.max(40, maxStrings * y_spacing_strings)
      }

      const x_start_pcs = 100 + xOffset
      const ac_bus_width = (num_pcs - 1) * x_spacing_pcs
      const dc_bus_height = (num_batteries_per_pcs - 1) * battery_spacing_y

      const stringAreaWidth =
        showStrings && bankIdToStringsMap.size > 0 ? 120 : 0
      const blockWidth = num_pcs * x_spacing_pcs + stringAreaWidth

      const transformerNode: CustomNode = {
        id: `transformer-${blockIndex}`,
        type: 'transformer',
        position: { x: x_start_pcs + ac_bus_width / 2 - 50, y: 0 },
        data: {
          label: transformer_device?.name_long || 'MV Transformer',
          tooltip_label: transformer_device?.name_full || 'MV Transformer',
          block_device_id: blockDeviceId,
          all_sensors: transformer_device
            ? deviceDataMap.get(transformer_device.device_id)
            : undefined,
          sensorTypeMap,
        },
      }

      const pcsNodes: CustomNode[] = bess_pcs_devices.map(
        (pcsDevice, i) =>
          ({
            id: `pcs-${blockIndex}-${i + 1}`,
            type: 'pcs' as const,
            position: { x: x_start_pcs + i * x_spacing_pcs - 37.5, y: 200 },
            data: {
              label: pcsDevice.name_full || `PCS ${i + 1}`,
              tooltip_label: pcsDevice.name_full || `PCS ${i + 1}`,
              block_device_id: blockDeviceId,
              all_sensors: deviceDataMap.get(pcsDevice.device_id),
              sensorTypeMap,
            },
          }) as CustomNode,
      )

      const dcBusNodes: CustomNode[] = Array.from(
        { length: num_pcs },
        (_, i) =>
          ({
            id: `dc-bus-${blockIndex}-${i + 1}`,
            type: 'bus',
            position: { x: x_start_pcs + i * x_spacing_pcs - 2, y: 300 },
            data: {
              is_ac: false,
              num_batteries_per_pcs,
              battery_spacing_y,
              dc_bus_height,
              all_sensors: deviceDataMap.get(bess_pcs_devices[i].device_id),
              sensorTypeMap,
            },
            style: {
              width: 4,
              height: dc_bus_height,
              backgroundColor: busColor,
            },
          }) as CustomNode,
      )

      const stringNodes: CustomNode[] = []
      const stringEdges: Edge[] = []

      const batteryNodes: CustomNode[] = batteryEquivalents
        .map((device, index) => {
          const i = Math.floor(index / num_batteries_per_pcs) // PCS index
          const j = index % num_batteries_per_pcs // Battery index within PCS group

          if (i >= num_pcs) return null // Don't create batteries for non-existent PCS

          const pcsDevice = bess_pcs_devices[i]
          const pcsData = deviceDataMap.get(pcsDevice.device_id)
          const pcsPower = pcsData?.[31]?.value
          const isCharging = pcsPower != null && pcsPower < -0.1

          const nodeId = useBanks
            ? `battery-${blockIndex}-${i + 1}-${j + 1}`
            : `string-${blockIndex}-${i + 1}-${j + 1}`
          const nodePosition = {
            x: x_start_pcs + i * x_spacing_pcs + 70,
            y: 300 + j * battery_spacing_y - 12,
          }

          const deviceData = deviceDataMap.get(device.device_id)

          if (useBanks) {
            // Handle bank nodes (existing logic)
            if (showStrings) {
              const childStrings =
                bankIdToStringsMap.get(device.device_id) || []
              childStrings.forEach((stringDevice, k) => {
                const stringNodeId = `string-${blockIndex}-${i + 1}-${j + 1}-${k + 1}`
                const bankCenterY = nodePosition.y + 12
                const totalStringsHeight =
                  childStrings.length * y_spacing_strings
                const stringStartY =
                  bankCenterY - totalStringsHeight / 2 + y_spacing_strings / 2

                const stringSensorData = deviceDataMap.get(
                  stringDevice.device_id,
                )
                const sohFraction = stringSensorData?.[59]?.value // bess_string_soh_percent
                const sohPercent =
                  sohFraction !== undefined && sohFraction !== null
                    ? sohFraction * 100
                    : 100
                const faultedCapacityPercent = 100 - sohPercent

                stringNodes.push({
                  id: stringNodeId,
                  type: 'string',
                  position: {
                    x: nodePosition.x + 120,
                    y: stringStartY + k * y_spacing_strings - 10,
                  },
                  data: {
                    label: stringDevice.name_full || `String ${k + 1}`,
                    tooltip_label: stringDevice.name_full || `String ${k + 1}`,
                    soc:
                      (deviceDataMap.get(stringDevice.device_id)?.[45]?.value ?? // bess_string_soc_percent
                        0) * 100,
                    soh: sohPercent,
                    faulted_capacity: faultedCapacityPercent,
                    is_charging: isCharging,
                    block_device_id: blockDeviceId,
                    all_sensors: deviceDataMap.get(stringDevice.device_id),
                    sensorTypeMap,
                  },
                })
                stringEdges.push({
                  id: `e-${nodeId}-${stringNodeId}`,
                  source: nodeId,
                  target: stringNodeId,
                  type: 'smoothstep',
                })
              })
            }

            return {
              id: nodeId,
              type: 'battery' as const,
              position: nodePosition,
              data: {
                label: device.name_full || `Battery ${i + 1}-${j + 1}`,
                tooltip_label: device.name_full || `Battery ${i + 1}-${j + 1}`,
                soc: (deviceData?.[44]?.value ?? 0) * 100, // bess_bank_soc_percent
                soh: 90 + Math.floor(Math.random() * 11),
                faulted_capacity: 0,
                is_charging: isCharging,
                block_device_id: blockDeviceId,
                all_sensors: deviceData,
                sensorTypeMap,
              },
            } as CustomNode
          } else {
            // Handle string nodes directly connected to DC bus
            const sohFraction = deviceData?.[59]?.value // bess_string_soh_percent
            const sohPercent =
              sohFraction !== undefined && sohFraction !== null
                ? sohFraction * 100
                : 100
            const faultedCapacityPercent = 100 - sohPercent

            return {
              id: nodeId,
              type: 'string' as const,
              position: nodePosition,
              data: {
                label: device.name_full || `String ${i + 1}-${j + 1}`,
                tooltip_label: device.name_full || `String ${i + 1}-${j + 1}`,
                soc: (deviceData?.[45]?.value ?? 0) * 100, // bess_string_soc_percent
                soh: sohPercent,
                faulted_capacity: faultedCapacityPercent,
                is_charging: isCharging,
                block_device_id: blockDeviceId,
                all_sensors: deviceData,
                sensorTypeMap,
              },
            } as CustomNode
          }
        })
        .filter((node): node is CustomNode => node !== null)

      const nodes: CustomNode[] = [
        transformerNode,
        ...pcsNodes,
        ...dcBusNodes,
        ...batteryNodes,
        ...stringNodes,
      ]
      const edges: Edge[] = []

      const pcsToDcBusEdges = bess_pcs_devices.map((pcsDevice, i) => {
        const pcsData = deviceDataMap.get(pcsDevice.device_id)
        const power = pcsData?.[31]?.value // bess_pcs_ac_power
        const isCharging = power != null && power < -0.1
        const isDischarging = power != null && power > 0.1
        return {
          id: `e-pcs-${blockIndex}-${i + 1}-dc-bus-${blockIndex}-${i + 1}`,
          source: `pcs-${blockIndex}-${i + 1}`,
          target: `dc-bus-${blockIndex}-${i + 1}`,
          type: 'powerFlow',
          data: {
            isCharging,
            isDischarging,
            power,
          },
        }
      })

      const dcBusToBatteryEdges = Array.from({ length: num_pcs }, (_, i) =>
        Array.from({ length: num_batteries_per_pcs }, (_, j) => {
          const pcsDevice = bess_pcs_devices[i]
          const pcsData = deviceDataMap.get(pcsDevice.device_id)
          const power = pcsData?.[31]?.value // bess_pcs_ac_power
          const isCharging = power != null && power < -0.1
          const isDischarging = power != null && power > 0.1
          const targetType = useBanks ? 'battery' : 'string'
          const targetId = `${targetType}-${blockIndex}-${i + 1}-${j + 1}`
          return {
            id: `e-dc-bus-${blockIndex}-${i + 1}-${targetType}-${blockIndex}-${i + 1}-${j + 1}`,
            source: `dc-bus-${blockIndex}-${i + 1}`,
            target: targetId,
            type: 'powerFlow',
            sourceHandle: `dc-bus-source-${j}`,
            data: {
              isCharging,
              isDischarging,
              power,
            },
          }
        }),
      ).flat()

      edges.push(...pcsToDcBusEdges, ...dcBusToBatteryEdges, ...stringEdges)

      if (num_pcs > 1) {
        const acBusNode: CustomNode = {
          id: `ac-bus-${blockIndex}`,
          type: 'bus',
          position: { x: x_start_pcs, y: 150 },
          data: {
            is_ac: true,
            num_pcs,
            x_spacing_pcs,
            ac_bus_width,
            all_sensors: deviceDataMap.get(bess_pcs_devices[0].device_id),
            sensorTypeMap,
          },
          style: {
            width: ac_bus_width,
            height: 4,
            backgroundColor: busColor,
          },
        }
        nodes.splice(1, 0, acBusNode)

        const transformerToBusEdge = {
          id: `e-transformer-${blockIndex}-ac-bus-${blockIndex}`,
          source: `ac-bus-${blockIndex}`,
          sourceHandle: 'ac-top-source',
          target: `transformer-${blockIndex}`,
          type: 'powerFlow',
          targetHandle: 'bottom-target',
          data: {
            isCharging: is_block_discharging, // Discharging (positive power) flows UP (bus to transformer)
            isDischarging: is_block_charging, // Charging (negative power) flows DOWN (transformer to bus)
            power: total_block_power,
          },
        }
        const busToPcsEdges = bess_pcs_devices.map((pcsDevice, i) => {
          const pcsData = deviceDataMap.get(pcsDevice.device_id)
          const power = pcsData?.[31]?.value // bess_pcs_ac_power
          const isCharging = power != null && power < -0.1
          const isDischarging = power != null && power > 0.1
          return {
            id: `e-ac-bus-${blockIndex}-pcs-${blockIndex}-${i + 1}`,
            source: `ac-bus-${blockIndex}`,
            target: `pcs-${blockIndex}-${i + 1}`,
            type: 'powerFlow',
            sourceHandle: `ac-bus-source-${i}`,
            data: {
              isCharging,
              isDischarging,
              power,
            },
          }
        })
        edges.unshift(transformerToBusEdge, ...busToPcsEdges)
      } else {
        // num_pcs === 1
        const pcsDevice = bess_pcs_devices[0]
        const pcsData = deviceDataMap.get(pcsDevice.device_id)
        const power = pcsData?.[31]?.value // bess_pcs_ac_power
        const isCharging = power != null && power < -0.1
        const isDischarging = power != null && power > 0.1
        const transformerToPcsEdge = {
          id: `e-transformer-${blockIndex}-pcs-${blockIndex}-1`,
          source: `transformer-${blockIndex}`,
          target: `pcs-${blockIndex}-1`,
          type: 'powerFlow',
          data: {
            isCharging,
            isDischarging,
            power,
          },
        }
        edges.unshift(transformerToPcsEdge)
      }

      return {
        nodes,
        edges,
        width: blockWidth,
        transformerNode,
        total_block_power,
        is_block_charging,
        is_block_discharging,
      }
    }

    if (
      selectedDevice.device_type_id === DeviceTypeEnum.BLOCK ||
      selectedDevice.device_type_id === DeviceTypeEnum.BESS_BLOCK
    ) {
      // It's a single block
      const { nodes, edges } = generateSingleSnapshotSld(
        devices,
        true,
        0,
        0,
        selectedDevice.device_id,
      )
      return { nodes, edges }
    } else if (selectedDevice.device_type_id === DeviceTypeEnum.PROJECT) {
      // It's the project
      const finalNodes: CustomNode[] = []
      const finalEdges: Edge[] = []

      const childBlocks =
        devices.filter((d) => d.parent_device_id === selectedBlockId) || []

      // Check for BESS MV Circuits (device_type_id = BESS_MV_CIRCUIT) connected to project
      const mvCircuits = devices.filter(
        (d) =>
          d.device_type_id === DeviceTypeEnum.BESS_MV_CIRCUIT &&
          d.parent_device_id === selectedBlockId,
      )

      if (mvCircuits.length > 0) {
        // Handle new hierarchy: Project -> BESS MV Circuit -> Transformer -> PCS -> Banks/Strings
        const CIRCUIT_SPACING = 700 // Increased spacing for strings layout
        const VERTICAL_BUS_X = -700 // Left side for vertical connections (shifted further left)
        let total_project_power = 0

        const transformerNodes: CustomNode[] = []
        const pcsNodes: CustomNode[] = []
        const dcBusNodes: CustomNode[] = []
        const batteryNodes: CustomNode[] = []
        const circuitBusNodes: CustomNode[] = []
        const verticalConnectionNodes: CustomNode[] = []
        const circuitLabelNodes: CustomNode[] = []

        mvCircuits.forEach((circuit, circuitIndex) => {
          // Pair circuits so left and right circuits share the same Y position
          const pairIndex = Math.floor(circuitIndex / 2)
          const circuitY = 200 + pairIndex * CIRCUIT_SPACING

          // Find PCS devices for this circuit
          const circuitPcsDevices = devices.filter(
            (d) =>
              d.device_type_id === DeviceTypeEnum.BESS_PCS &&
              d.device_id_path?.includes(circuit.device_id_path || ''),
          )

          if (circuitPcsDevices.length > 0) {
            const numPcs = circuitPcsDevices.length
            const PCS_SPACING = 120
            const circuitWidth = (numPcs - 1) * PCS_SPACING

            // Alternate circuit sides: even indices (0,2,4...) on right, odd indices (1,3,5...) on left
            const isRightSide = circuitIndex % 2 === 0
            const circuitStartX = isRightSide ? -500 : -circuitWidth - 900

            // Create AC bus for this circuit
            const circuitBusNode: CustomNode = {
              id: `circuit-ac-bus-${circuitIndex}`,
              type: 'bus',
              position: { x: circuitStartX, y: circuitY },
              data: {
                is_ac: true,
                num_pcs: numPcs,
                x_spacing_pcs: PCS_SPACING,
                ac_bus_width: circuitWidth,
                all_sensors: deviceDataMap.get(circuitPcsDevices[0].device_id),
                sensorTypeMap,
              },
              style: {
                width: circuitWidth,
                height: 4,
                backgroundColor: busColor,
              },
            }
            circuitBusNodes.push(circuitBusNode)

            // Create circuit label above the bus
            const circuitLabelNode: CustomNode = {
              id: `circuit-label-${circuitIndex}`,
              type: 'circuitLabel',
              position: {
                x: circuitStartX + circuitWidth / 2 - 100, // Center label above bus
                y: circuitY - 80, // Position 50px higher above the horizontal circuit bar
              },
              data: {
                label: circuit.name_full || `Circuit ${circuitIndex + 1}`,
              },
            }
            circuitLabelNodes.push(circuitLabelNode)

            // Create vertical connection point for this circuit
            // Position connection points at the edge of the vertical bus
            const connectionX = isRightSide
              ? VERTICAL_BUS_X + 4 // Right edge of vertical bus
              : VERTICAL_BUS_X - 4 // Left edge of vertical bus
            const verticalConnectionNode: CustomNode = {
              id: `vertical-connection-${circuitIndex}`,
              type: 'verticalConnection',
              position: { x: connectionX, y: circuitY },
              data: {
                is_ac: false,
                all_sensors: deviceDataMap.get(circuit.device_id),
                sensorTypeMap,
              },
            }
            verticalConnectionNodes.push(verticalConnectionNode)

            // Create PCS nodes and individual transformers for this circuit
            circuitPcsDevices.forEach((pcsDevice, pcsIndex) => {
              const pcsX = circuitStartX + pcsIndex * PCS_SPACING - 37.5
              const pcsY = circuitY + 240 // PCS further below transformers

              // Find transformer that is the parent of this PCS
              const pcsTransformer = devices.find(
                (d) =>
                  d.device_type_id === DeviceTypeEnum.BESS_MVT &&
                  d.device_id === pcsDevice.parent_device_id,
              )

              // Create transformer node for this PCS
              if (pcsTransformer) {
                const transformerNode: CustomNode = {
                  id: `circuit-${circuitIndex}-transformer-${pcsIndex + 1}`,
                  type: 'transformer',
                  position: { x: pcsX + 37.5 - 50, y: circuitY + 60 }, // transformer centered below bus handle and above PCS
                  data: {
                    label:
                      pcsTransformer.name_long || `Transformer ${pcsIndex + 1}`,
                    tooltip_label:
                      pcsTransformer.name_full || `Transformer ${pcsIndex + 1}`,
                    block_device_id: circuit.device_id,
                    all_sensors: deviceDataMap.get(pcsTransformer.device_id),
                    sensorTypeMap,
                  },
                }
                transformerNodes.push(transformerNode)
              }

              const pcsNode: CustomNode = {
                id: `circuit-${circuitIndex}-pcs-${pcsIndex + 1}`,
                type: 'pcs',
                position: { x: pcsX, y: pcsY },
                data: {
                  label:
                    PCS_SPACING >= 200
                      ? pcsDevice.name_full || `PCS ${pcsIndex + 1}`
                      : '', // Hide label if spacing < 200px
                  tooltip_label: pcsDevice.name_full || `PCS ${pcsIndex + 1}`,
                  block_device_id: circuit.device_id,
                  all_sensors: deviceDataMap.get(pcsDevice.device_id),
                  sensorTypeMap,
                },
              }
              pcsNodes.push(pcsNode)

              // Add to total project power
              const pcsData = deviceDataMap.get(pcsDevice.device_id)
              const power = pcsData?.[31]?.value ?? 0 // bess_pcs_ac_power
              total_project_power += power

              // Find battery/string devices for this PCS
              // First check for direct connections
              const directBankDevicesForPcs = devices.filter(
                (d) =>
                  d.parent_device_id === pcsDevice.device_id &&
                  d.device_type_id === DeviceTypeEnum.BESS_BANK,
              )
              const directStringDevicesForPcs = devices.filter(
                (d) =>
                  d.parent_device_id === pcsDevice.device_id &&
                  d.device_type_id === DeviceTypeEnum.BESS_STRING,
              )

              // Also check for connections through bess_pcs_module_group (device_type_id = BESS_PCS_MODULE_GROUP)
              const moduleGroups = devices.filter(
                (d) =>
                  d.parent_device_id === pcsDevice.device_id &&
                  d.device_type_id === DeviceTypeEnum.BESS_PCS_MODULE_GROUP,
              )

              const bankDevicesFromModuleGroups = devices.filter(
                (d) =>
                  d.device_type_id === DeviceTypeEnum.BESS_BANK &&
                  moduleGroups.some(
                    (mg) => mg.device_id === d.parent_device_id,
                  ),
              )
              const stringDevicesFromModuleGroups = devices.filter(
                (d) =>
                  d.device_type_id === DeviceTypeEnum.BESS_STRING &&
                  moduleGroups.some(
                    (mg) => mg.device_id === d.parent_device_id,
                  ),
              )

              // Combine direct and module group connections
              const bankDevicesForPcs = [
                ...directBankDevicesForPcs,
                ...bankDevicesFromModuleGroups,
              ]
              const stringDevicesForPcs = [
                ...directStringDevicesForPcs,
                ...stringDevicesFromModuleGroups,
              ]

              const useBanks = bankDevicesForPcs.length > 0
              const batteryDevicesForPcs = useBanks
                ? bankDevicesForPcs
                : stringDevicesForPcs

              if (batteryDevicesForPcs.length > 0) {
                const batterySpacing = useBanks ? 40 : 30 // Tighter spacing for strings
                const dcBusHeight =
                  (batteryDevicesForPcs.length - 1) * batterySpacing

                // Create DC bus for this PCS
                const dcBusNode: CustomNode = {
                  id: `circuit-${circuitIndex}-dc-bus-${pcsIndex + 1}`,
                  type: 'bus',
                  position: { x: pcsX + 35, y: pcsY + 100 },
                  data: {
                    is_ac: false,
                    num_batteries_per_pcs: batteryDevicesForPcs.length,
                    battery_spacing_y: batterySpacing,
                    dc_bus_height: dcBusHeight,
                    all_sensors: deviceDataMap.get(pcsDevice.device_id),
                    sensorTypeMap,
                  },
                  style: {
                    width: 4,
                    height: dcBusHeight,
                    backgroundColor: busColor,
                  },
                }
                dcBusNodes.push(dcBusNode)

                // Create battery/string nodes
                batteryDevicesForPcs.forEach((batteryDevice, j) => {
                  const batteryX = pcsX + 80
                  const batteryY = pcsY + 100 + j * batterySpacing - 10
                  const deviceData = deviceDataMap.get(batteryDevice.device_id)

                  if (useBanks) {
                    const batteryNode: CustomNode = {
                      id: `circuit-${circuitIndex}-battery-${pcsIndex + 1}-${j + 1}`,
                      type: 'battery',
                      position: { x: batteryX, y: batteryY },
                      data: {
                        label:
                          PCS_SPACING >= 200
                            ? batteryDevice.name_full ||
                              `Battery ${pcsIndex + 1}-${j + 1}`
                            : '',
                        tooltip_label:
                          batteryDevice.name_full ||
                          `Battery ${pcsIndex + 1}-${j + 1}`,
                        soc: (deviceData?.[44]?.value ?? 0) * 100, // bess_bank_soc_percent
                        soh: (deviceData?.[56]?.value ?? 0.9) * 100, // bess_bank_soh_percent
                        faulted_capacity: 0,
                        is_charging: power < -0.1,
                        block_device_id: circuit.device_id,
                        all_sensors: deviceData,
                        sensorTypeMap,
                      },
                    }
                    batteryNodes.push(batteryNode)
                  } else {
                    // Show all strings directly under PCS
                    const sohFraction = deviceData?.[59]?.value // bess_string_soh_percent
                    const sohPercent =
                      sohFraction !== undefined && sohFraction !== null
                        ? sohFraction * 100
                        : 100
                    const faultedCapacityPercent = 100 - sohPercent

                    const stringNode: CustomNode = {
                      id: `circuit-${circuitIndex}-string-${pcsIndex + 1}-${j + 1}`,
                      type: 'string',
                      position: { x: batteryX, y: batteryY },
                      data: {
                        label:
                          PCS_SPACING >= 200
                            ? batteryDevice.name_full ||
                              `String ${pcsIndex + 1}-${j + 1}`
                            : '',
                        tooltip_label:
                          batteryDevice.name_full ||
                          `String ${pcsIndex + 1}-${j + 1}`,
                        soc: (deviceData?.[45]?.value ?? 0) * 100, // bess_string_soc_percent
                        soh: sohPercent,
                        faulted_capacity: faultedCapacityPercent,
                        is_charging: power < -0.1,
                        block_device_id: circuit.device_id,
                        all_sensors: deviceData,
                        sensorTypeMap,
                      },
                    }
                    batteryNodes.push(stringNode)
                  }
                })

                // Create edges for PCS to DC bus
                const isCharging = power < -0.1
                const isDischarging = power > 0.1

                finalEdges.push({
                  id: `e-circuit-${circuitIndex}-pcs-${pcsIndex + 1}-dc-bus`,
                  source: `circuit-${circuitIndex}-pcs-${pcsIndex + 1}`,
                  target: `circuit-${circuitIndex}-dc-bus-${pcsIndex + 1}`,
                  type: 'powerFlow',
                  data: { isCharging, isDischarging, power },
                })

                // Create edges from DC bus to batteries/strings
                batteryDevicesForPcs.forEach((_, j) => {
                  const targetType = useBanks ? 'battery' : 'string'
                  finalEdges.push({
                    id: `e-circuit-${circuitIndex}-dc-bus-${pcsIndex + 1}-${targetType}-${j + 1}`,
                    source: `circuit-${circuitIndex}-dc-bus-${pcsIndex + 1}`,
                    target: `circuit-${circuitIndex}-${targetType}-${pcsIndex + 1}-${j + 1}`,
                    type: 'powerFlow',
                    sourceHandle: `dc-bus-source-${j}`,
                    data: { isCharging, isDischarging, power },
                  })
                })
              }

              // Create edge from circuit bus to transformer
              const isCharging = power < -0.1
              const isDischarging = power > 0.1

              if (pcsTransformer) {
                finalEdges.push({
                  id: `e-circuit-${circuitIndex}-bus-transformer-${pcsIndex + 1}`,
                  source: `circuit-ac-bus-${circuitIndex}`,
                  target: `circuit-${circuitIndex}-transformer-${pcsIndex + 1}`,
                  type: 'powerFlow',
                  sourceHandle: `ac-bus-source-${pcsIndex}`,
                  data: { isCharging, isDischarging, power },
                })
              } else {
                // Fallback: direct connection if no transformer found
                finalEdges.push({
                  id: `e-circuit-${circuitIndex}-bus-pcs-${pcsIndex + 1}`,
                  source: `circuit-ac-bus-${circuitIndex}`,
                  target: `circuit-${circuitIndex}-pcs-${pcsIndex + 1}`,
                  type: 'powerFlow',
                  sourceHandle: `ac-bus-source-${pcsIndex}`,
                  data: { isCharging, isDischarging, power },
                })
              }
            })

            // Create edges from individual transformers to their respective PCS
            circuitPcsDevices.forEach((pcsDevice, pcsIndex) => {
              const pcsData = deviceDataMap.get(pcsDevice.device_id)
              const power = pcsData?.[31]?.value // bess_pcs_ac_power
              const isCharging = power < -0.1
              const isDischarging = power > 0.1

              finalEdges.push({
                id: `e-circuit-${circuitIndex}-transformer-${pcsIndex + 1}-pcs-${pcsIndex + 1}`,
                source: `circuit-${circuitIndex}-transformer-${pcsIndex + 1}`,
                sourceHandle: 'bottom-source',
                target: `circuit-${circuitIndex}-pcs-${pcsIndex + 1}`,
                type: 'powerFlow',
                data: { isCharging, isDischarging, power },
              })
            })

            // Create edge from vertical connection to circuit (horizontal connection)
            const sourceHandle = isRightSide ? 'right-source' : 'left-source'
            const targetHandle = isRightSide
              ? 'ac-left-target'
              : 'ac-right-target'

            finalEdges.push({
              id: `e-vertical-to-circuit-${circuitIndex}`,
              source: `vertical-connection-${circuitIndex}`,
              sourceHandle: sourceHandle,
              target: `circuit-ac-bus-${circuitIndex}`,
              targetHandle: targetHandle,
              type: 'smoothstep',
              data: { isCharging: false, isDischarging: false, power: 0 },
            })
          }
        })

        // Create main vertical bus connecting all circuits
        // Calculate unique Y positions (paired circuits share same Y)
        const uniqueYPositions = mvCircuits.map((_, i) => {
          const pairIndex = Math.floor(i / 2)
          return 200 + pairIndex * CIRCUIT_SPACING
        })
        const minY = Math.min(...uniqueYPositions) - 100
        const maxY = Math.max(...uniqueYPositions) + 100
        const verticalBusHeight = maxY - minY

        const mainVerticalBus: CustomNode = {
          id: 'project-vertical-bus',
          type: 'bus',
          position: { x: VERTICAL_BUS_X, y: minY },
          data: {
            is_ac: false,
            is_vertical_bus: true,
            circuit_positions: uniqueYPositions,
            vertical_bus_height: verticalBusHeight,
            vertical_bus_start_y: minY,
            all_sensors: deviceDataMap.get(selectedDevice.device_id),
            sensorTypeMap,
          },
          style: {
            width: 4,
            height: verticalBusHeight,
            backgroundColor: mainBusColor,
          },
        }

        // Create revenue meter
        const projectMeterNode: CustomNode = {
          id: 'project-meter',
          type: 'project_meter',
          position: { x: VERTICAL_BUS_X - 40, y: minY - 150 },
          data: {
            label: 'Revenue Meter',
            all_sensors: deviceDataMap.get(selectedDevice.device_id),
            sensorTypeMap,
          },
        }

        // Create grid node
        const gridNode: CustomNode = {
          id: 'project-grid',
          type: 'grid',
          position: { x: VERTICAL_BUS_X - 30, y: minY - 270 },
          data: { label: 'Grid' },
        }

        finalNodes.push(
          mainVerticalBus,
          projectMeterNode,
          gridNode,
          ...transformerNodes,
          ...circuitBusNodes,
          ...circuitLabelNodes,
          ...verticalConnectionNodes,
          ...pcsNodes,
          ...dcBusNodes,
          ...batteryNodes,
        )

        const is_project_discharging = total_project_power > 0.001
        const is_project_charging = total_project_power < -0.001

        // Create edges from vertical bus to each circuit connection point
        verticalConnectionNodes.forEach((connectionNode, i) => {
          const isRightSide = i % 2 === 0
          const sourceHandle = isRightSide
            ? `vertical-bus-circuit-right-${i}`
            : `vertical-bus-circuit-left-${i}`

          finalEdges.push({
            id: `e-vertical-bus-connection-${i}`,
            source: 'project-vertical-bus',
            sourceHandle: sourceHandle,
            target: connectionNode.id,
            type: 'straight',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power / mvCircuits.length,
            },
          })
        })

        // Create meter and grid connections
        finalEdges.push(
          {
            id: 'e-meter-to-vertical-bus',
            source: 'project-meter',
            target: 'project-vertical-bus',
            targetHandle: 'vertical-bus-top',
            type: 'powerFlow',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power,
            },
          },
          {
            id: 'e-grid-to-meter',
            source: 'project-grid',
            target: 'project-meter',
            type: 'powerFlow',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power,
            },
          },
        )

        return { nodes: finalNodes, edges: finalEdges }
      }

      // Fallback: Check if PCS units are directly connected to project level (legacy)
      const directPcsDevices = devices.filter(
        (d) =>
          d.device_type_id === DeviceTypeEnum.BESS_PCS &&
          d.parent_device_id === selectedBlockId,
      )

      if (directPcsDevices.length > 0) {
        // Handle direct PCS connections with multi-row layout
        const MAX_PCS_PER_ROW = 20
        const PCS_SPACING = 120
        const ROW_SPACING = 300
        const totalPcs = directPcsDevices.length
        const numRows = Math.ceil(totalPcs / MAX_PCS_PER_ROW)

        let total_project_power = 0
        const rowBusNodes: CustomNode[] = []
        const pcsNodes: CustomNode[] = []
        const dcBusNodes: CustomNode[] = []
        const batteryNodes: CustomNode[] = []

        // Create nodes for each row of PCS units
        for (let row = 0; row < numRows; row++) {
          const pcsInThisRow = directPcsDevices.slice(
            row * MAX_PCS_PER_ROW,
            (row + 1) * MAX_PCS_PER_ROW,
          )
          const numPcsInRow = pcsInThisRow.length
          const rowWidth = (numPcsInRow - 1) * PCS_SPACING
          const rowStartX = -rowWidth / 2
          const rowY = 150 + row * ROW_SPACING

          // Create AC bus for this row
          const rowBusNode: CustomNode = {
            id: `project-ac-bus-row-${row}`,
            type: 'bus',
            position: { x: rowStartX, y: rowY },
            data: {
              is_ac: true,
              num_pcs: numPcsInRow,
              x_spacing_pcs: PCS_SPACING,
              ac_bus_width: rowWidth,
              all_sensors: deviceDataMap.get(pcsInThisRow[0].device_id),
              sensorTypeMap,
            },
            style: {
              width: rowWidth,
              height: 4,
              backgroundColor: busColor,
            },
          }
          rowBusNodes.push(rowBusNode)

          // Create PCS nodes for this row
          pcsInThisRow.forEach((pcsDevice, i) => {
            const pcsIndex = row * MAX_PCS_PER_ROW + i
            const pcsX = rowStartX + i * PCS_SPACING - 37.5
            const pcsY = rowY + 50

            const pcsNode: CustomNode = {
              id: `project-pcs-${pcsIndex + 1}`,
              type: 'pcs',
              position: { x: pcsX, y: pcsY },
              data: {
                label: pcsDevice.name_full || `PCS ${pcsIndex + 1}`,
                tooltip_label: pcsDevice.name_full || `PCS ${pcsIndex + 1}`,
                block_device_id: selectedDevice.device_id,
                all_sensors: deviceDataMap.get(pcsDevice.device_id),
                sensorTypeMap,
              },
            }
            pcsNodes.push(pcsNode)

            // Add to total project power
            const pcsData = deviceDataMap.get(pcsDevice.device_id)
            const power = pcsData?.[31]?.value ?? 0 // bess_pcs_ac_power
            total_project_power += power

            // Find battery/string devices for this PCS
            const batteryDevicesForPcs = devices.filter(
              (d) =>
                d.parent_device_id === pcsDevice.device_id &&
                (d.device_type_id === DeviceTypeEnum.BESS_BANK ||
                  d.device_type_id === DeviceTypeEnum.BESS_STRING),
            )

            if (batteryDevicesForPcs.length > 0) {
              const useBanks = batteryDevicesForPcs.some(
                (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
              )
              const batterySpacing = 40
              const dcBusHeight =
                (batteryDevicesForPcs.length - 1) * batterySpacing

              // Create DC bus for this PCS
              const dcBusNode: CustomNode = {
                id: `project-dc-bus-${pcsIndex + 1}`,
                type: 'bus',
                position: { x: pcsX + 35, y: pcsY + 100 },
                data: {
                  is_ac: false,
                  num_batteries_per_pcs: batteryDevicesForPcs.length,
                  battery_spacing_y: batterySpacing,
                  dc_bus_height: dcBusHeight,
                  all_sensors: deviceDataMap.get(pcsDevice.device_id),
                  sensorTypeMap,
                },
                style: {
                  width: 4,
                  height: dcBusHeight,
                  backgroundColor: busColor,
                },
              }
              dcBusNodes.push(dcBusNode)

              // Create battery/string nodes
              batteryDevicesForPcs.forEach((batteryDevice, j) => {
                const batteryX = pcsX + 110
                const batteryY = pcsY + 100 + j * batterySpacing - 12
                const deviceData = deviceDataMap.get(batteryDevice.device_id)

                if (
                  useBanks &&
                  batteryDevice.device_type_id === DeviceTypeEnum.BESS_BANK
                ) {
                  const batteryNode: CustomNode = {
                    id: `project-battery-${pcsIndex + 1}-${j + 1}`,
                    type: 'battery',
                    position: { x: batteryX, y: batteryY },
                    data: {
                      label:
                        batteryDevice.name_full ||
                        `Battery ${pcsIndex + 1}-${j + 1}`,
                      tooltip_label:
                        batteryDevice.name_full ||
                        `Battery ${pcsIndex + 1}-${j + 1}`,
                      soc: (deviceData?.[44]?.value ?? 0) * 100, // bess_bank_soc_percent
                      soh: (deviceData?.[56]?.value ?? 0.9) * 100, // bess_bank_soh_percent
                      faulted_capacity: 0,
                      is_charging: power < -0.1,
                      block_device_id: selectedDevice.device_id,
                      all_sensors: deviceData,
                      sensorTypeMap,
                    },
                  }
                  batteryNodes.push(batteryNode)
                } else if (
                  batteryDevice.device_type_id === DeviceTypeEnum.BESS_STRING
                ) {
                  const sohFraction = deviceData?.[59]?.value // bess_string_soh_percent
                  const sohPercent =
                    sohFraction !== undefined && sohFraction !== null
                      ? sohFraction * 100
                      : 100
                  const faultedCapacityPercent = 100 - sohPercent

                  const stringNode: CustomNode = {
                    id: `project-string-${pcsIndex + 1}-${j + 1}`,
                    type: 'string',
                    position: { x: batteryX, y: batteryY },
                    data: {
                      label:
                        batteryDevice.name_full ||
                        `String ${pcsIndex + 1}-${j + 1}`,
                      tooltip_label:
                        batteryDevice.name_full ||
                        `String ${pcsIndex + 1}-${j + 1}`,
                      soc: (deviceData?.[45]?.value ?? 0) * 100, // bess_string_soc_percent
                      soh: sohPercent,
                      faulted_capacity: faultedCapacityPercent,
                      is_charging: power < -0.1,
                      block_device_id: selectedDevice.device_id,
                      all_sensors: deviceData,
                      sensorTypeMap,
                    },
                  }
                  batteryNodes.push(stringNode)
                }
              })

              // Create edges for PCS to DC bus
              const pcsDataForEdge = deviceDataMap.get(pcsDevice.device_id)
              const powerForEdge = pcsDataForEdge?.[31]?.value // bess_pcs_ac_power
              const isCharging = powerForEdge != null && powerForEdge < -0.1
              const isDischarging = powerForEdge != null && powerForEdge > 0.1

              finalEdges.push({
                id: `e-project-pcs-${pcsIndex + 1}-dc-bus`,
                source: `project-pcs-${pcsIndex + 1}`,
                target: `project-dc-bus-${pcsIndex + 1}`,
                type: 'powerFlow',
                data: { isCharging, isDischarging, power },
              })

              // Create edges from DC bus to batteries/strings
              batteryDevicesForPcs.forEach((_, j) => {
                const targetType =
                  useBanks &&
                  batteryDevicesForPcs[j].device_type_id ===
                    DeviceTypeEnum.BESS_BANK
                    ? 'battery'
                    : 'string'
                finalEdges.push({
                  id: `e-project-dc-bus-${pcsIndex + 1}-${targetType}-${j + 1}`,
                  source: `project-dc-bus-${pcsIndex + 1}`,
                  target: `project-${targetType}-${pcsIndex + 1}-${j + 1}`,
                  type: 'powerFlow',
                  sourceHandle: `dc-bus-source-${j}`,
                  data: { isCharging, isDischarging, power: powerForEdge },
                })
              })
            }

            // Create edge from row bus to PCS
            const pcsDataForBus = deviceDataMap.get(pcsDevice.device_id)
            const powerForBus = pcsDataForBus?.[31]?.value // bess_pcs_ac_power
            const isChargingBus = powerForBus != null && powerForBus < -0.1
            const isDischargingBus = powerForBus != null && powerForBus > 0.1

            finalEdges.push({
              id: `e-project-bus-row-${row}-pcs-${pcsIndex + 1}`,
              source: `project-ac-bus-row-${row}`,
              target: `project-pcs-${pcsIndex + 1}`,
              type: 'powerFlow',
              sourceHandle: `ac-bus-source-${i}`,
              data: {
                isCharging: isChargingBus,
                isDischarging: isDischargingBus,
                power: powerForBus,
              },
            })
          })
        }

        // Create main project bus connecting all row buses
        const allRowCenters = rowBusNodes.map(
          (bus) => bus.position.x + ((bus.style?.width as number) || 0) / 2,
        )
        const minX = Math.min(...allRowCenters) - 200
        const maxX = Math.max(...allRowCenters) + 200
        const mainBusWidth = maxX - minX
        const mainBusY = 50

        const projectMainBus: CustomNode = {
          id: 'project-main-bus',
          type: 'bus',
          position: { x: minX, y: mainBusY },
          data: {
            is_project_bus: true,
            project_bus_x_start: minX,
            project_bus_width: mainBusWidth,
            all_sensors: deviceDataMap.get(selectedDevice.device_id),
            sensorTypeMap,
          },
          style: {
            width: mainBusWidth,
            height: 6,
            backgroundColor: mainBusColor,
          },
        }

        // Create revenue meter
        const projectMeterNode: CustomNode = {
          id: 'project-meter',
          type: 'project_meter',
          position: { x: minX + mainBusWidth / 2 - 40, y: -150 },
          data: {
            label: 'Revenue Meter',
            all_sensors: deviceDataMap.get(selectedDevice.device_id),
            sensorTypeMap,
          },
        }

        // Create grid node
        const gridNode: CustomNode = {
          id: 'project-grid',
          type: 'grid',
          position: {
            x: projectMeterNode.position.x + 10,
            y: projectMeterNode.position.y - 120,
          },
          data: { label: 'Grid' },
        }

        finalNodes.push(
          projectMainBus,
          projectMeterNode,
          gridNode,
          ...rowBusNodes,
          ...pcsNodes,
          ...dcBusNodes,
          ...batteryNodes,
        )

        const is_project_discharging = total_project_power > 0.001
        const is_project_charging = total_project_power < -0.001

        // Create edges from main bus to row buses
        rowBusNodes.forEach((rowBus, i) => {
          // const rowCenterX =
          //   rowBus.position.x + ((rowBus.style?.width as number) || 0) / 2
          // const busStartX = projectMainBus.position.x
          // const position_percent =
          //   ((rowCenterX - busStartX) / mainBusWidth) * 100

          // Add handle to main bus for this row
          const handleId = `proj-bus-row-${i}`

          finalEdges.push({
            id: `e-main-bus-row-${i}`,
            source: 'project-main-bus',
            target: rowBus.id,
            type: 'powerFlow',
            sourceHandle: handleId,
            targetHandle: 'ac-top-source',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power / numRows, // Distribute power across rows
            },
          })
        })

        // Create meter and grid connections
        finalEdges.push(
          {
            id: 'e-bus-to-meter',
            source: 'project-meter',
            target: 'project-main-bus',
            type: 'powerFlow',
            targetHandle: 'proj-bus-meter',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power,
            },
          },
          {
            id: 'e-grid-to-meter',
            source: 'project-grid',
            target: 'project-meter',
            type: 'powerFlow',
            data: {
              isCharging: is_project_charging,
              isDischarging: is_project_discharging,
              power: total_project_power,
            },
          },
        )

        return { nodes: finalNodes, edges: finalEdges }
      }

      // Original block-based layout logic
      let currentXOffset = 0
      const blockLayouts: {
        x_offset: number
        transformer_node: CustomNode
        total_block_power: number
        is_block_charging: boolean
        is_block_discharging: boolean
      }[] = []

      // Dynamically calculate spacing based on the number of blocks.
      const numBlocks = childBlocks.length
      const blockSpacing = Math.max(50, 215 - numBlocks * 15)

      childBlocks.forEach((block, i) => {
        const blockDescendants = devices.filter(
          (d) =>
            d.device_id_path?.startsWith(block.device_id_path || '') &&
            d.device_id !== block.device_id,
        )

        // Determine if we should show strings based on whether banks exist
        const hasBanks = blockDescendants.some(
          (d) => d.device_type_id === DeviceTypeEnum.BESS_BANK,
        )
        const showStrings =
          !hasBanks &&
          blockDescendants.some(
            (d) => d.device_type_id === DeviceTypeEnum.BESS_STRING,
          )

        const {
          nodes,
          edges,
          width,
          transformerNode,
          total_block_power,
          is_block_charging,
          is_block_discharging,
        } = generateSingleSnapshotSld(
          blockDescendants,
          showStrings,
          currentXOffset,
          i,
          block.device_id,
        )

        if (transformerNode) {
          blockLayouts.push({
            x_offset: currentXOffset,
            transformer_node: transformerNode,
            total_block_power,
            is_block_charging,
            is_block_discharging,
          })
        }
        finalNodes.push(...nodes)
        finalEdges.push(...edges)
        currentXOffset += width + blockSpacing
      })

      if (childBlocks.length > 1) {
        // Find the min and max x-coordinates of the transformer centers
        const transformer_centers_x = blockLayouts.map(
          (layout) => layout.transformer_node.position.x + 50,
        )
        const minX = Math.min(...transformer_centers_x)
        const maxX = Math.max(...transformer_centers_x)

        const mainBusWidth = maxX - minX

        const projectMeterNode: CustomNode = {
          id: 'project-meter',
          type: 'project_meter',
          position: { x: minX + mainBusWidth / 2 - 40, y: -250 },
          data: {
            label: 'Revenue Meter',
            all_sensors: deviceDataMap.get(selectedDevice.device_id),
            sensorTypeMap,
          },
        }
        finalNodes.push(projectMeterNode)

        const mainBusNode: CustomNode = {
          id: 'project-main-bus',
          type: 'bus',
          position: { x: minX, y: -100 },
          data: {
            is_project_bus: true,
            block_layouts: blockLayouts,
            project_bus_x_start: minX,
            project_bus_width: mainBusWidth,
            all_sensors: deviceDataMap.get(devices[0].device_id),
            sensorTypeMap,
          },
          style: {
            width: mainBusWidth,
            height: 6,
            backgroundColor: mainBusColor,
          },
        }
        finalNodes.unshift(mainBusNode)

        const total_project_power = blockLayouts.reduce(
          (sum, b) => sum + b.total_block_power,
          0,
        )
        const is_project_discharging = total_project_power > 0.001
        const is_project_charging = total_project_power < -0.001

        finalEdges.push({
          id: 'e-bus-to-meter',
          source: 'project-meter',
          target: 'project-main-bus',
          type: 'powerFlow',
          targetHandle: 'proj-bus-meter',
          data: {
            isCharging: is_project_charging,
            isDischarging: is_project_discharging,
            power: total_project_power,
          },
        })

        blockLayouts.forEach((layout, i) => {
          finalEdges.unshift({
            id: `e-main-bus-to-transformer-${i}`,
            source: 'project-main-bus',
            target: layout.transformer_node.id,
            type: 'powerFlow',
            sourceHandle: `proj-bus-source-${i}`,
            data: {
              isCharging: layout.is_block_charging,
              isDischarging: layout.is_block_discharging,
              power: layout.total_block_power,
            },
          })
        })

        // Add grid node above the revenue meter
        const gridNode: CustomNode = {
          id: 'project-grid',
          type: 'grid',
          position: {
            x: projectMeterNode.position.x + 10,
            y: projectMeterNode.position.y - 120,
          },
          data: { label: 'Grid' },
        }
        finalNodes.push(gridNode)

        // Edge between grid and meter
        finalEdges.push({
          id: 'e-grid-to-meter',
          source: 'project-grid',
          target: 'project-meter',
          type: 'powerFlow',
          data: {
            isCharging: is_project_charging,
            isDischarging: is_project_discharging,
            power: total_project_power,
          },
        })
      }

      return { nodes: finalNodes, edges: finalEdges }
    }

    return { nodes: [], edges: [] }
  }, [
    devices,
    blockDevices,
    selectedBlockId,
    deviceDataMap,
    sensorTypeMap,
    busColor,
    mainBusColor,
  ])

  useEffect(() => {
    if (nodes.length > 0) {
      fitView({ padding: 0.1, duration: 200 })
    }
  }, [nodes, fitView])

  const onNodeClick = useCallback<NodeMouseHandler<CustomNode>>(
    (_, node) => {
      if (!hasBlockDeviceId(node)) {
        return
      }

      const blockDeviceId = node.data.block_device_id

      if (blockDeviceId === undefined) {
        return
      }

      if (selectedBlockId !== blockDeviceId) {
        setSelectedBlockId(blockDeviceId)
      }
    },
    [selectedBlockId],
  )

  const projectDeviceId = useMemo(() => {
    return (
      blockDevices?.find((d) => d.device_type_id === DeviceTypeEnum.PROJECT)
        ?.device_id || null
    )
  }, [blockDevices])

  if (
    isProjectLoading ||
    areBlockDevicesLoading ||
    (areDevicesLoading && selectedBlockId) ||
    timestamp === null ||
    viewStartDate === null ||
    viewEndDate === null
  ) {
    return <PageLoader />
  }

  // Restrict access for PV-only projects
  if (project?.project_type_id !== ProjectTypeEnum.BESS) {
    return (
      <div style={{ padding: '2rem' }}>
        Single-Line Diagram is not available for this project type.
      </div>
    )
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        padding: '1rem',
        boxSizing: 'border-box',
      }}
    >
      <SLDGlobalStyles />
      <BlockHeader
        timezone={project?.time_zone}
        blockDevices={blockDevices}
        selectedBlockId={selectedBlockId}
        setSelectedBlockId={setSelectedBlockId}
        timestamp={timestamp}
        setTimestamp={setTimestamp}
        isLive={isLive}
        setIsLive={setIsLive}
        viewStartDate={viewStartDate!}
        setViewStartDate={setViewStartDate}
        viewEndDate={viewEndDate!}
        setViewEndDate={setViewEndDate}
        projectAvgSoc={socStats?.avg ?? null}
        socDelta={socStats?.spread ?? null}
        projectAvgSoh={sohStats?.avg ? sohStats.avg * 100 : null}
        sohDelta={sohStats?.spread ?? null}
        projectAvgCellTemp={cellTempStats?.avg ?? null}
        cellTempDelta={cellTempStats?.spread ?? null}
        isFetching={isTimeSeriesFetching}
        activePcsCount={activePcsCount}
        hideTitle={true}
      />
      <div style={{ flexGrow: 1, position: 'relative' }}>
        {projectDeviceId &&
          selectedBlockId &&
          selectedBlockId !== projectDeviceId && (
            <Tooltip label="Back to project" withArrow>
              <ActionIcon
                variant="default"
                style={{ position: 'absolute', top: 10, left: 10, zIndex: 10 }}
                onClick={() => setSelectedBlockId(projectDeviceId)}
                aria-label="Back to project"
              >
                <IconArrowBackUp size={18} />
              </ActionIcon>
            </Tooltip>
          )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={memoizedNodeTypes}
          edgeTypes={memoizedEdgeTypes}
          defaultEdgeOptions={{ style: { strokeWidth: 3, stroke: busColor } }}
          onNodeClick={onNodeClick}
          minZoom={0.1}
          maxZoom={4}
          className={isDarkMode ? 'dark' : ''}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  )
}

export default function SnapshotSLD() {
  useProjectFilter({
    projectTypes: [ProjectTypeId.BESS],
  })

  return (
    <ReactFlowProvider>
      <SnapshotSLDContent />
    </ReactFlowProvider>
  )
}

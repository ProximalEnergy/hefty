import { SensorTypeEnum } from '@/api/enumerations'
import { useGetUserSelf } from '@/api/v1/admin/users'
import {
  type SCADADataPoint,
  requestBatterySettlementAnalysis,
} from '@/api/v1/ai/battery_settlement_analysis'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import { useGetBatterySettlementDetails } from '@/api/v1/protected/web-application/projects/financial/battery_settlement'
import { PageError } from '@/components/Error'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useProjectDropdownToggle } from '@/hooks/custom'
import { useAuth } from '@clerk/clerk-react'
import {
  ActionIcon,
  Box,
  Button,
  Checkbox,
  Group,
  LoadingOverlay,
  MultiSelect,
  Paper,
  Stack,
  Tabs,
  Text,
  Textarea,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { IconSend, IconSparkles } from '@tabler/icons-react'
import DOMPurify from 'dompurify'
import {
  MRT_ColumnDef,
  MantineReactTable,
  useMantineReactTable,
} from 'mantine-react-table'
import MarkdownIt from 'markdown-it'
import { Data } from 'plotly.js/dist/plotly-custom.min.js'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router'
import { v4 as uuidv4 } from 'uuid'

const SABLE_POINT_COMPANY_ID = '38a8e696-dafa-44c0-b817-e3aee8cdfe8c'

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  createdAt: string
}

const Page = () => {
  const { projectId } = useParams()
  const project = useSelectProject(projectId || '-1')
  const [selectedColumns, setSelectedColumns] = useState<string[]>([])
  const [selectedCalculatedFields, setSelectedCalculatedFields] = useState<
    string[]
  >([])
  const [selectedSensorTypeIds, setSelectedSensorTypeIds] = useState<string[]>(
    [],
  )
  const [colorByTimeOfDay, setColorByTimeOfDay] = useState<boolean>(false)
  const [activeTab, setActiveTab] = useState<string>('table')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false)
  const [isStreaming] = useState<boolean>(false)
  const [inputValue, setInputValue] = useState<string>('')
  const [hasInitialAnalysis, setHasInitialAnalysis] = useState<boolean>(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const theme = useMantineTheme()
  const colorScheme = useComputedColorScheme()
  const markdown = useMemo(() => new MarkdownIt(), [])
  const { start, end } = useValidateDateRange({
    maxDays: 31,
  })
  const { getToken } = useAuth()
  useProjectDropdownToggle()

  // Loading placeholders (rotates while waiting for AI)
  const LOADING_MESSAGES = useMemo(
    () => [
      'Analyzing data.',
      'Analyzing data..',
      'Analyzing data...',
      'Calculating round-trip efficiency (RTE).',
      'Calculating round-trip efficiency (RTE)..',
      'Calculating round-trip efficiency (RTE)...',
      'Assessing RT-DA price spreads.',
      'Assessing RT-DA price spreads..',
      'Assessing RT-DA price spreads...',
      'Evaluating throughput and net positions.',
      'Evaluating throughput and net positions..',
      'Evaluating throughput and net positions...',
      'Estimating revenues and imbalances.',
      'Estimating revenues and imbalances..',
      'Estimating revenues and imbalances...',
      'Identifying anomalies and optimization opportunities.',
      'Identifying anomalies and optimization opportunities..',
      'Identifying anomalies and optimization opportunities...',
    ],
    [],
  )
  const [loadingIdx, setLoadingIdx] = useState<number>(0)
  const loadingTimerRef = useRef<number | null>(null)
  const typeTimerRef = useRef<number | null>(null)
  const [showLoading, setShowLoading] = useState<boolean>(false)

  let startRequest: string | undefined
  let endRequest: string | undefined
  if (project.data) {
    startRequest =
      (start && start.tz(project.data.time_zone, true).toISOString()) ||
      undefined
    endRequest =
      (end && end.tz(project.data.time_zone, true).toISOString()) || undefined
  }
  const sensorTypes = useGetSensorTypes({
    queryParams: {
      sensor_type_ids: project.data?.spec?.used_sensor_type_ids ?? [],
    },
    queryOptions: {
      enabled: !!project.data,
    },
  })
  const self = useGetUserSelf({})
  const batterySettlementDetails = useGetBatterySettlementDetails({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      start: startRequest || '',
      end: endRequest || '',
    },
    queryOptions: {
      enabled: !!projectId && !!startRequest && !!endRequest,
    },
  })
  const scadaData = useGetTimeSeries({
    pathParams: { project_id: projectId || '-1' },
    queryParams: {
      sensor_type_ids: selectedSensorTypeIds.map((id) => parseInt(id)),
      start: startRequest || '',
      end: endRequest || '',
    },
    queryOptions: {
      enabled:
        !!projectId &&
        !!startRequest &&
        !!endRequest &&
        !!selectedSensorTypeIds.length,
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 60 * 6, // 6 hours
    },
  })

  // Transform the data from API format to MRT format
  const tableData = useMemo(() => {
    if (
      !batterySettlementDetails.data?.qse_data?.data ||
      !batterySettlementDetails.data?.qse_data?.index
    ) {
      return []
    }

    const { data, index } = batterySettlementDetails.data.qse_data
    const columnNames = Object.keys(data)

    return index.map((time, rowIndex) => {
      const row: Record<string, string | number | null> = { time }
      columnNames.forEach((columnName) => {
        row[columnName] = data[columnName]?.[rowIndex] ?? null
      })
      return row
    })
  }, [batterySettlementDetails.data])

  // Get available raw data columns for MultiSelect
  const availableColumns = useMemo(() => {
    if (!batterySettlementDetails.data?.qse_data?.data) {
      return []
    }

    return Object.keys(batterySettlementDetails.data.qse_data.data).map(
      (key) => ({
        value: key,
        label: key,
      }),
    )
  }, [batterySettlementDetails.data])

  // Get available calculated fields for MultiSelect
  const availableCalculatedFields = useMemo(() => {
    if (!batterySettlementDetails.data?.calculated_data?.data) {
      return []
    }

    return Object.keys(batterySettlementDetails.data.calculated_data.data).map(
      (key) => ({
        value: key,
        label: key,
      }),
    )
  }, [batterySettlementDetails.data])

  // Group all data by units for dynamic axes
  const unitGroups = useMemo(() => {
    if (
      !tableData.length ||
      (!selectedColumns.length &&
        !selectedCalculatedFields.length &&
        !selectedSensorTypeIds.length)
    ) {
      return []
    }

    const units = batterySettlementDetails.data?.qse_data?.unit || {}
    const dataByUnit: Record<
      string,
      Array<{
        name: string
        x: (string | number | null)[]
        y: (string | number | null)[]
      }>
    > = {}

    // Add regular QSE data columns
    selectedColumns.forEach((column) => {
      const unit = units[column] || 'Unknown'
      const traceName = units[column] ? `${column} (${units[column]})` : column
      if (!dataByUnit[unit]) {
        dataByUnit[unit] = []
      }
      dataByUnit[unit].push({
        name: traceName,
        x: tableData.map((row) => row.time),
        y: tableData.map((row) => row[column] as number),
      })
    })

    // Add calculated fields from API
    const calculatedDataUnits =
      batterySettlementDetails.data?.calculated_data?.unit || {}
    const calculatedData =
      batterySettlementDetails.data?.calculated_data?.data || {}
    const calculatedIndex =
      batterySettlementDetails.data?.calculated_data?.index || []

    selectedCalculatedFields.forEach((fieldName) => {
      const unit = calculatedDataUnits[fieldName] || 'Unknown'
      const traceName = calculatedDataUnits[fieldName]
        ? `${fieldName} (${calculatedDataUnits[fieldName]})`
        : fieldName

      if (!dataByUnit[unit]) {
        dataByUnit[unit] = []
      }

      // Map the calculated data to match the table index
      const yData = calculatedIndex.map(
        (_, idx) => calculatedData[fieldName]?.[idx] ?? null,
      )

      dataByUnit[unit].push({
        name: traceName,
        x: calculatedIndex,
        y: yData,
      })
    })

    // Add SCADA data traces
    if (scadaData.data && selectedSensorTypeIds.length > 0) {
      selectedSensorTypeIds.forEach((sensorTypeId) => {
        const sensorType = sensorTypes.data?.find(
          (st) => st.sensor_type_id.toString() === sensorTypeId,
        )
        const sensorTypeName = sensorType?.name_long || `Sensor ${sensorTypeId}`
        const sensorTraceNameWithUnit = sensorType?.unit
          ? `${sensorTypeName} (${sensorType.unit})`
          : sensorTypeName

        const sensorData = scadaData.data.find(
          (data) => data.sensor_type_id.toString() === sensorTypeId,
        )

        if (sensorData && sensorData.x && sensorData.y) {
          const unit = sensorType?.unit || 'Unknown'
          if (!dataByUnit[unit]) {
            dataByUnit[unit] = []
          }
          dataByUnit[unit].push({
            name: sensorTraceNameWithUnit,
            x: sensorData.x,
            y: sensorData.y,
          })
        }
      })
    }

    // Convert to array - let Plotly assign unique colors to each trace
    const uniqueUnits = Object.keys(dataByUnit)
    return uniqueUnits.map((unit, index) => ({
      unit,
      data: dataByUnit[unit].map((item) => ({
        ...item,
        yaxis: `y${index + 1}`,
      })),
    }))
  }, [
    tableData,
    selectedColumns,
    selectedCalculatedFields,
    scadaData.data,
    selectedSensorTypeIds,
    sensorTypes.data,
    batterySettlementDetails.data,
  ])

  // Prepare plot data from unit groups
  const plotData = useMemo((): Data[] => {
    const isPercentUnit = (unit: string): boolean => {
      const lower = unit.toLowerCase()
      return unit.includes('%') || lower.includes('percent')
    }

    return unitGroups.flatMap((group) => {
      const percentHover = isPercentUnit(group.unit)
      return group.data.map((item) => ({
        x: item.x,
        y: item.y,
        type: 'scatter' as const,
        mode: 'lines' as const,
        name: item.name,
        yaxis: item.yaxis,
        hovertemplate: percentHover ? '(%{x}) %{y:.0%}' : undefined,
        hoverlabel: { namelength: -1 },
      }))
    })
  }, [unitGroups])

  // Create dynamic layout based on unique units
  const plotLayout = useMemo(() => {
    if (unitGroups.length === 0) {
      return {
        xaxis: { title: { text: 'Time' }, domain: [0.05, 0.95] },
        yaxis: { title: { text: 'Select data to plot' }, showgrid: false },
      }
    }

    const baseLayout: Record<string, unknown> = {
      xaxis: { title: { text: 'Time' }, domain: [0.05, 0.95] },
      yaxis: {
        title: { text: unitGroups[0].unit },
        showgrid: false,
      },
    }

    if (unitGroups.length > 1) {
      unitGroups.slice(1).forEach((group, idx) => {
        baseLayout[`yaxis${idx + 2}`] = {
          title: { text: group.unit },
          overlaying: 'y',
          side: idx % 2 === 0 ? 'right' : 'left',
          autoshift: true,
          anchor: 'free',
          showgrid: false,
        }
      })
    }

    return baseLayout
  }, [unitGroups])

  // Prepare insights scatter plot data
  const insightsPlotData = useMemo((): Data[] => {
    const calculatedData =
      batterySettlementDetails.data?.calculated_data?.data || {}
    const calculatedIndex =
      batterySettlementDetails.data?.calculated_data?.index || []

    // Check if both required fields exist
    const priceSpreadKey = Object.keys(calculatedData).find((key) =>
      key.includes('RT - DA Price Spread'),
    )
    const netProfitKey = Object.keys(calculatedData).find((key) =>
      key.includes('Net Profit'),
    )

    if (!priceSpreadKey || !netProfitKey) {
      return []
    }

    const priceSpreadData = calculatedData[priceSpreadKey] || []
    const netProfitData = calculatedData[netProfitKey] || []

    // Filter out null values and create paired data points
    const xData: number[] = []
    const yData: number[] = []
    const hoursData: number[] = []
    const timestampsData: string[] = []

    priceSpreadData.forEach((x, idx) => {
      const y = netProfitData[idx]
      if (x !== null && y !== null) {
        xData.push(x as number)
        yData.push(y as number)
        // Extract hour and timestamp
        const timestamp = calculatedIndex[idx]
        if (timestamp) {
          const date = new Date(timestamp)
          hoursData.push(date.getHours())
          timestampsData.push(timestamp)
        } else {
          hoursData.push(0)
          timestampsData.push('')
        }
      }
    })

    const trace: Data = {
      x: xData,
      y: yData,
      type: 'scatter',
      mode: 'markers',
      marker: { size: 8 },
      name: 'Price Spread vs Net Profit',
    }

    // Add color dimension if colorByTimeOfDay is enabled
    if (colorByTimeOfDay) {
      trace.marker = {
        size: 8,
        color: hoursData,
        colorscale: 'Viridis',
        showscale: true,
        colorbar: {
          tickmode: 'linear',
          tick0: 0,
          dtick: 4,
        },
      }
      trace.text = timestampsData.map((ts, idx) => {
        if (!ts) return `Hour: ${hoursData[idx]}:00`
        const date = new Date(ts)
        const dateStr = date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })
        const hour = hoursData[idx]
        return `${dateStr} ${hour}:00`
      })
      trace.hovertemplate =
        '%{text}<br>Price Spread: %{x}<br>Net Profit: %{y}<extra></extra>'
    }

    return [trace]
  }, [batterySettlementDetails.data, colorByTimeOfDay])

  const insightsPlotLayout = useMemo(() => {
    const calculatedData =
      batterySettlementDetails.data?.calculated_data?.data || {}
    const calculatedUnits =
      batterySettlementDetails.data?.calculated_data?.unit || {}

    const priceSpreadKey = Object.keys(calculatedData).find((key) =>
      key.includes('RT - DA Price Spread'),
    )
    const netProfitKey = Object.keys(calculatedData).find((key) =>
      key.includes('Net Profit'),
    )

    const xUnit = priceSpreadKey ? calculatedUnits[priceSpreadKey] || '' : ''
    const yUnit = netProfitKey ? calculatedUnits[netProfitKey] || '' : ''

    return {
      autosize: true,
      xaxis: {
        title: {
          text: xUnit
            ? `RT - DA Price Spread (${xUnit})`
            : 'RT - DA Price Spread',
        },
      },
      yaxis: {
        title: { text: yUnit ? `Net Profit (${yUnit})` : 'Net Profit' },
      },
    }
  }, [batterySettlementDetails.data])

  const columns = useMemo(() => {
    if (!batterySettlementDetails.data?.qse_data?.data) {
      return []
    }

    const units = batterySettlementDetails.data.qse_data.unit || {}

    return [
      {
        header: 'Time',
        accessorKey: 'time',
        size: 200,
      },
      ...Object.keys(batterySettlementDetails.data.qse_data.data).map(
        (key) => ({
          header: units[key] ? `${key} (${units[key]})` : key,
          accessorKey: key,
          size: 150,
        }),
      ),
    ]
  }, [batterySettlementDetails.data])

  const table = useMantineReactTable({
    columns: columns as MRT_ColumnDef<Record<string, string | number | null>>[],
    data: tableData,
    enableColumnDragging: false,
    enableColumnResizing: true,
    enableSorting: false,
    enableGlobalFilter: false,
    enablePagination: true,
    enableBottomToolbar: true,
    enableStickyHeader: true,
    mantineTableProps: {
      striped: true,
      highlightOnHover: true,
      stickyHeader: true,
    },
  })

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (viewportRef.current) {
      viewportRef.current.scrollTo({
        top: viewportRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages])

  // Cleanup on unmount
  useEffect(() => {
    return () => {}
  }, [])

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (loadingTimerRef.current) window.clearInterval(loadingTimerRef.current)
      if (typeTimerRef.current) window.clearInterval(typeTimerRef.current)
    }
  }, [])

  const renderMarkdown = (content: string) => {
    const renderedContent = markdown.render(content)
    const styledContent = renderedContent
      .replace(/<p>/g, '<p style="margin: 0">')
      .replace(
        /<code>/g,
        '<code style="color: white; font-size: 0.875em; background-color: #333333; padding: 2px 4px; border-radius: 4px;">',
      )
      .replace(
        /<pre>/g,
        '<pre style="color: white; font-size: 0.875em; background-color: #333333; padding: 10px; border-radius: 4px; overflow-x: auto;">',
      )
    const sanitizedContent = DOMPurify.sanitize(styledContent, {
      USE_PROFILES: { html: true },
    })
    return { __html: sanitizedContent }
  }

  const startAnalysis = async (userMessage?: string) => {
    if (!batterySettlementDetails.data || !startRequest || !endRequest) {
      notifications.show({
        title: 'No Data Available',
        message: 'Please wait for data to load before starting analysis.',
        color: 'yellow',
      })
      return
    }

    // Add user message if it's a follow-up
    if (userMessage) {
      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: 'user',
        content: userMessage,
        createdAt: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, userMsg])
      setInputValue('')
    }

    // Begin loading placeholders rotation
    if (loadingTimerRef.current) window.clearInterval(loadingTimerRef.current)
    setLoadingIdx(0)
    loadingTimerRef.current = window.setInterval(() => {
      setLoadingIdx((i) => (i + 1) % LOADING_MESSAGES.length)
    }, 1200)
    setShowLoading(true)

    setIsAnalyzing(true)

    // Create assistant message placeholder
    const assistantMsgId = uuidv4()
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, assistantMsg])

    // Prepare SCADA data
    const scadaDataPoints: SCADADataPoint[] | undefined = scadaData.data
      ? scadaData.data.map((sensor) => {
          const sensorType = sensorTypes.data?.find(
            (st) => st.sensor_type_id === sensor.sensor_type_id,
          )
          return {
            sensor_type_id: sensor.sensor_type_id,
            sensor_type_name: sensorType?.name_long,
            unit: sensorType?.unit ?? undefined,
            x: sensor.x,
            y: sensor.y,
          }
        })
      : undefined

    try {
      const token = await getToken({ template: 'default' })
      if (!token) {
        throw new Error('Authentication token not available')
      }

      const content = await requestBatterySettlementAnalysis(token, {
        project_id: projectId || '',
        project_name: project.data?.name_long,
        start: startRequest,
        end: endRequest,
        qse_data: batterySettlementDetails.data.qse_data,
        calculated_data: batterySettlementDetails.data.calculated_data,
        scada_data: scadaDataPoints,
        conversation_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        user_message: userMessage,
      })

      // Stop loading placeholders
      if (loadingTimerRef.current) window.clearInterval(loadingTimerRef.current)
      setShowLoading(false)

      // Simulate streaming via typewriter effect
      const full = content
      const step = 40 // characters per tick
      const delay = 20 // ms per tick
      let pos = 0

      if (typeTimerRef.current) window.clearInterval(typeTimerRef.current)
      typeTimerRef.current = window.setInterval(() => {
        pos = Math.min(full.length, pos + step)
        const nextChunk = full.slice(0, pos)
        setMessages((prev) => {
          const updated = [...prev]
          const lastMsg = updated[updated.length - 1]
          if (lastMsg && lastMsg.id === assistantMsgId) {
            lastMsg.content = nextChunk
          }
          return updated
        })
        if (pos >= full.length) {
          if (typeTimerRef.current) window.clearInterval(typeTimerRef.current)
          setIsAnalyzing(false)
          setHasInitialAnalysis(true)
        }
      }, delay)
    } catch (error) {
      console.error('Failed to run analysis:', error)
      notifications.show({
        title: 'Analysis Error',
        message: error instanceof Error ? error.message : 'Unknown error',
        color: 'red',
      })
      setIsAnalyzing(false)
      if (loadingTimerRef.current) window.clearInterval(loadingTimerRef.current)
      // Remove the empty assistant message
      setMessages((prev) => prev.filter((m) => m.id !== assistantMsgId))
      setShowLoading(false)
    }
  }

  const handleSendMessage = () => {
    if (!inputValue.trim() || isStreaming) return
    startAnalysis(inputValue)
  }

  const renderMessage = (message: ChatMessage) => {
    const isUserMessage = message.role === 'user'

    function determineTextColor(hexInput: string) {
      const hex = hexInput.replace(/^#/, '')
      const bigint = parseInt(hex, 16)
      const r = (bigint >> 16) & 255
      const g = (bigint >> 8) & 255
      const b = bigint & 255

      const linearize = (val: number): number => {
        const normalized = val / 255
        return normalized <= 0.03928
          ? normalized / 12.92
          : Math.pow((normalized + 0.055) / 1.055, 2.4)
      }

      const rLin = linearize(r)
      const gLin = linearize(g)
      const bLin = linearize(b)

      const luminance = 0.2126 * rLin + 0.7152 * gLin + 0.0722 * bLin
      return luminance > 0.179 ? 'black' : 'white'
    }

    const userTextColor = determineTextColor(
      theme.colors[theme.primaryColor][7],
    )

    return (
      <Group
        key={message.id}
        w="100%"
        justify={isUserMessage ? 'flex-end' : 'flex-start'}
      >
        <Paper
          p="xs"
          maw="80%"
          style={{
            backgroundColor: isUserMessage
              ? theme.colors[theme.primaryColor][7]
              : colorScheme === 'dark'
                ? theme.colors.dark[7]
                : theme.colors.gray[1],
          }}
        >
          <Text
            size="sm"
            c={
              isUserMessage
                ? userTextColor
                : colorScheme === 'dark'
                  ? theme.colors.dark[0]
                  : theme.colors.dark[7]
            }
            dangerouslySetInnerHTML={renderMarkdown(message.content)}
          />
        </Paper>
      </Group>
    )
  }

  if (self.isLoading) {
    return <PageLoader />
  }
  if (self.data?.company_id === SABLE_POINT_COMPANY_ID) {
    return (
      <PageError text="Please provide a Tenaska API key to see Battery Settlement Details" />
    )
  }

  return (
    <Stack p="md" w="100%" h="100%">
      <PageTitle>Battery Settlement Details</PageTitle>
      <AdvancedDatePicker
        defaultRange="yesterday"
        includeTodayInDateRange
        includeClearButton={false}
        maxDays={31}
      />
      <div
        style={{
          position: 'relative',
          height: '100%',
          width: '100%',
          overflow: 'hidden',
        }}
      >
        <LoadingOverlay
          visible={
            batterySettlementDetails.isPending ||
            sensorTypes.isPending ||
            (scadaData.isPending && selectedSensorTypeIds.length > 0)
          }
        />
        <Tabs
          defaultValue="table"
          h="100%"
          value={activeTab}
          onChange={(value) => setActiveTab(value || 'table')}
        >
          <Tabs.List>
            <Tabs.Tab value="table">Table</Tabs.Tab>
            <Tabs.Tab value="plot">Plot</Tabs.Tab>
            <Tabs.Tab value="insights">Insights</Tabs.Tab>
            <Tabs.Tab value="aria">Aria Summary</Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="table" h="calc(100% - 40px)">
            <Box h="100%" style={{ overflowY: 'auto' }}>
              <MantineReactTable table={table} />
            </Box>
          </Tabs.Panel>

          <Tabs.Panel value="plot" h="calc(100% - 40px)">
            <Stack h="100%" py="md">
              <Group grow>
                <MultiSelect
                  label="Select QSE Data to Plot"
                  placeholder="Choose raw data columns..."
                  data={availableColumns}
                  value={selectedColumns}
                  onChange={setSelectedColumns}
                  clearable
                  searchable
                />
                <MultiSelect
                  label="Select Calculated Fields to Plot"
                  placeholder="Choose calculated fields..."
                  data={availableCalculatedFields}
                  value={selectedCalculatedFields}
                  onChange={setSelectedCalculatedFields}
                  clearable
                  searchable
                />
                <MultiSelect
                  label="Select Proximal Data to Plot"
                  placeholder="Choose proximal data..."
                  data={sensorTypes.data
                    ?.filter(
                      (sensorType) =>
                        sensorType.sensor_type_id !==
                        SensorTypeEnum.GHOST_UNKNOWN,
                    )
                    .map((sensorType) => ({
                      value: sensorType.sensor_type_id.toString(),
                      label: sensorType.name_long,
                    }))}
                  value={selectedSensorTypeIds}
                  onChange={setSelectedSensorTypeIds}
                  clearable
                  searchable
                />
              </Group>
              <Box h="calc(100% - 60px)" style={{ overflow: 'auto' }}>
                {plotData.length > 0 ? (
                  <PlotlyPlot data={plotData} layout={plotLayout} />
                ) : (
                  <Box
                    h="100%"
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'var(--mantine-color-dimmed)',
                    }}
                  >
                    Select QSE Data or Calculated Fields to Plot
                  </Box>
                )}
              </Box>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="insights" h="calc(100% - 40px)">
            <Stack h="100%" py="md">
              <Group
                h="100%"
                gap="md"
                align="flex-start"
                style={{ height: 'calc(100% - 1rem)' }}
              >
                <Box style={{ flex: 1, height: '100%', overflowY: 'auto' }}>
                  {insightsPlotData.length > 0 && activeTab === 'insights' ? (
                    <PlotlyPlot
                      key={`insights-${insightsPlotData.length}-${colorByTimeOfDay}-${activeTab}`}
                      data={insightsPlotData}
                      layout={insightsPlotLayout}
                    />
                  ) : (
                    <Box
                      h="100%"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--mantine-color-dimmed)',
                      }}
                    >
                      No data available for insights
                    </Box>
                  )}
                </Box>
                <Paper withBorder p="md" style={{ width: '250px' }}>
                  <Stack gap="md">
                    <Text>Color by:</Text>
                    <Checkbox
                      label="Hour Beginning"
                      checked={colorByTimeOfDay}
                      onChange={(event) =>
                        setColorByTimeOfDay(event.currentTarget.checked)
                      }
                    />
                  </Stack>
                </Paper>
              </Group>
            </Stack>
          </Tabs.Panel>

          <Tabs.Panel value="aria" h="calc(100% - 40px)">
            <Stack h="100%" py="md" gap="md">
              {!hasInitialAnalysis && messages.length === 0 ? (
                <Stack align="center" justify="center" h="100%" gap="lg">
                  <IconSparkles size={48} stroke={1.5} />
                  <Text size="lg" fw={500}>
                    AI-Powered Battery Performance Analysis
                  </Text>
                  <Text size="sm" c="dimmed" ta="center" maw={500}>
                    Click the button below to have Aria analyze your battery
                    settlement data and provide comprehensive technical insights
                    about performance, market participation, and financial
                    outcomes.
                  </Text>
                  <Button
                    leftSection={<IconSparkles size={18} />}
                    onClick={() => startAnalysis()}
                    loading={isAnalyzing}
                    disabled={
                      isAnalyzing ||
                      !batterySettlementDetails.data ||
                      !startRequest ||
                      !endRequest
                    }
                    size="lg"
                  >
                    Start Analysis
                  </Button>
                </Stack>
              ) : (
                <Box
                  style={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                  }}
                >
                  <Box
                    ref={viewportRef}
                    style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}
                  >
                    <Stack gap="md" p="xs">
                      {messages.map(renderMessage)}
                      {showLoading && (
                        <Text size="sm" c="dimmed">
                          {LOADING_MESSAGES[loadingIdx]}
                        </Text>
                      )}
                    </Stack>
                  </Box>
                  <Stack gap="xs">
                    <Textarea
                      placeholder="Ask a follow-up question..."
                      value={inputValue}
                      onChange={(event) =>
                        setInputValue(event.currentTarget.value)
                      }
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' && !event.shiftKey) {
                          event.preventDefault()
                          handleSendMessage()
                        }
                      }}
                      minRows={2}
                      maxRows={4}
                      disabled={isAnalyzing}
                      rightSection={
                        <ActionIcon
                          disabled={!inputValue.trim() || isAnalyzing}
                          size="sm"
                          variant="transparent"
                          onClick={handleSendMessage}
                        >
                          <IconSend width="100%" />
                        </ActionIcon>
                      }
                    />
                  </Stack>
                </Box>
              )}
            </Stack>
          </Tabs.Panel>
        </Tabs>
      </div>
    </Stack>
  )
}

export default Page

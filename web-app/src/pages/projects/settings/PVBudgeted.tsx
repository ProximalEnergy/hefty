import { useGetUserSelf } from '@/api/admin'
import {
  useDeletePVBudgetedSeries,
  useGetPVBudgetedSeries,
} from '@/api/v1/operational/project/pv_budgeted_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import ConfirmationModal from '@/components/modals/ConfirmationModal'
import { baseURL } from '@/urlConfig'
import { useAuth } from '@clerk/clerk-react'
import {
  ActionIcon,
  Button,
  Card,
  Group,
  NumberInput,
  Radio,
  ScrollArea,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
  Tooltip,
  useMantineTheme,
} from '@mantine/core'
import { IconEdit, IconTrash } from '@tabler/icons-react'
import { useQueryClient } from '@tanstack/react-query'
import axios from 'axios'
import dayjs from 'dayjs'
import timezone from 'dayjs/plugin/timezone'
import utc from 'dayjs/plugin/utc'
import { useRef, useState } from 'react'

dayjs.extend(utc)
dayjs.extend(timezone)

type GridRow = {
  time_stamp?: string
  poi_ac_power?: number
  ghi?: number
  poa?: number
  temperature?: number
  soiling_percentage?: number
}

const COLUMN_HEADERS = [
  'Timestamp',
  'POI AC power',
  'POA',
  'Soiling percentage',
  'Temperature',
  'GHI',
] as const

const getVisibleColumns = (
  soilingMode: string | null,
  hasData: boolean = false,
): readonly string[] => {
  let columns = [...COLUMN_HEADERS]

  // Hide timestamp column if no data has been pasted yet
  if (!hasData) {
    columns = columns.filter((header) => header !== 'Timestamp')
  }

  // Hide soiling percentage column if not in per_timestamp mode
  if (soilingMode !== 'per_timestamp' && soilingMode !== 'PER_TIMESTAMP') {
    columns = columns.filter((header) => header !== 'Soiling percentage')
  }

  return columns
}

const getVisibleColumnKeys = (
  soilingMode: string | null,
  hasData: boolean = false,
): (keyof GridRow)[] => {
  const keys: (keyof GridRow)[] = []

  // Add timestamp column only if data has been pasted
  if (hasData) {
    keys.push('time_stamp')
  }

  // Keep order in sync with headers: POI, POA, Soiling %, Temperature, GHI
  keys.push('poi_ac_power')
  keys.push('poa')
  if (soilingMode === 'per_timestamp' || soilingMode === 'PER_TIMESTAMP') {
    keys.push('soiling_percentage')
  }
  keys.push('temperature')
  keys.push('ghi')

  return keys
}

const VISIBLE_LIMIT = 20

function parseLine(line: string, soilingMode: string | null): GridRow {
  const cells = line.split(/[\t,]/)
  const [p, a, s, t, g] = cells
  const result: GridRow = {
    // time_stamp is generated separately on paste
    poi_ac_power: toNum(p),
    poa: toNum(a),
    temperature: toNum(t),
    ghi: toNum(g),
  }

  if (soilingMode === 'per_timestamp' || soilingMode === 'PER_TIMESTAMP') {
    result.soiling_percentage = toNum(s)
  }

  return result
}

function generateTimestamps(
  count: number,
  projectTimezone: string | undefined,
): string[] {
  const tz = projectTimezone || 'UTC' // Fallback to UTC if not provided
  const timestamps: string[] = []
  let startLocal: dayjs.Dayjs

  if (count === 8760) {
    // Start at 2019-01-01 00:00:00 in the project's timezone
    startLocal = dayjs.tz('2019-01-01T00:00:00', tz)
  } else {
    // For non-8760, start at the beginning of today in the project's timezone
    startLocal = dayjs().tz(tz).startOf('day')
  }

  for (let i = 0; i < count; i++) {
    const d = startLocal.add(i, 'hour')
    timestamps.push(d.toISOString()) // convert to UTC for backend
  }
  return timestamps
}

function splitNonEmptyLines(text: string): string[] {
  return text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
}

function toNum(value?: string) {
  if (value === undefined || value === null) return undefined
  try {
    const cleaned = String(value)
      .trim()
      .replace(/,/g, '') // remove thousand separators
      .replace(/\s+/g, '') // remove spaces
      .replace(/(mw|kw|w)$/i, '') // drop trailing unit text
    const n = Number(cleaned)
    return Number.isFinite(n) ? n : undefined
  } catch {
    return undefined
  }
}

function detectUnitsAndConvert(
  rows: GridRow[],
  pvCapacityMW: number,
): { rows: GridRow[]; label: string | null } {
  if (rows.length === 0) return { rows, label: null }

  const poiValues = rows
    .map((row) => row.poi_ac_power)
    .filter((val): val is number => val !== undefined)

  if (poiValues.length === 0) return { rows, label: null }

  const maxValue = Math.max(...poiValues)
  const ratio =
    Number.isFinite(pvCapacityMW) && pvCapacityMW > 0
      ? maxValue / pvCapacityMW
      : Number.NaN

  let conversionFactor = 1
  let detectedUnit = 'MW'

  // Primary: capacity-relative detection when capacity is available
  if (Number.isFinite(ratio)) {
    if (ratio > 500 && ratio < 2000) {
      conversionFactor = 1000
      detectedUnit = 'kW'
    } else if (ratio > 500000 && ratio < 2000000) {
      conversionFactor = 1000000
      detectedUnit = 'W'
    } else if (ratio > 0.5 && ratio < 2) {
      conversionFactor = 1
      detectedUnit = 'MW'
    }
  }

  // Fallback: absolute magnitude detection (handles missing/wrong capacity)
  if (conversionFactor === 1) {
    if (maxValue >= 200000) {
      conversionFactor = 1000000
      detectedUnit = 'W'
    } else if (maxValue >= 200) {
      conversionFactor = 1000
      detectedUnit = 'kW'
    }
  }

  if (conversionFactor !== 1) {
    return {
      rows: rows.map((row) => ({
        ...row,
        poi_ac_power:
          typeof row.poi_ac_power === 'number'
            ? row.poi_ac_power / conversionFactor
            : undefined,
      })),
      label: `Detected: ${detectedUnit}, converted to MW`,
    }
  }

  return { rows, label: null }
}

export default function PVBudgeted({ projectId }: { projectId: string }) {
  const { getToken } = useAuth()
  const queryClient = useQueryClient()
  const userSelf = useGetUserSelf({})
  const project = useSelectProject(projectId!)
  const existingSeries = useGetPVBudgetedSeries({
    pathParams: { projectId },
  })

  const deleteSeriesMutation = useDeletePVBudgetedSeries()

  // Get actual PV capacity from project data
  const pvCapacityMW = project.data?.capacity_ac || 100
  const [visibleRows, setVisibleRows] = useState<GridRow[]>([])
  const allRowsRef = useRef<GridRow[]>([])
  const [totalRows, setTotalRows] = useState(0)
  const [, setParsedCount] = useState(0)
  const [, setIsParsing] = useState(false)
  const focusedCellRef = useRef<{ rowIndex: number; colIndex: number } | null>(
    null,
  )
  const [seriesMeta, setSeriesMeta] = useState({
    p_value: '',
    p_value_other: '',
    frequency: '',
    soiling_mode: null as string | null,
    soiling_fixed_percentage: undefined as number | undefined,
    tmy_source: '',
    model_version: '',
    filename: '',
  })
  const [deleteModalOpened, setDeleteModalOpened] = useState(false)
  const [seriesToDelete, setSeriesToDelete] = useState<number | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [, setIsLoadingSeriesData] = useState(false)
  const [editingSeriesId, setEditingSeriesId] = useState<number | null>(null)
  const [editingSeries, setEditingSeries] = useState<any | null>(null)
  const [poiUnitNote, setPoiUnitNote] = useState<string | null>(null)

  const theme = useMantineTheme()

  const hasData = totalRows > 0

  const handleDeleteClick = (seriesId: number) => {
    setSeriesToDelete(seriesId)
    setDeleteModalOpened(true)
  }

  const normalizeSoilingMode = (mode: string | null) => {
    if (!mode) return null
    if (mode.toLowerCase() === 'per_timestamp') return 'per_timestamp'
    if (mode.toLowerCase() === 'fixed') return 'fixed'
    return mode
  }

  const handleEditClick = async (series: any) => {
    setEditingSeries(series)
    try {
      setIsLoadingSeriesData(true)
      setEditingSeriesId(series.pv_budgeted_series_id)

      // Load metadata into form
      setSeriesMeta({
        p_value: (series.p_value || '').toLowerCase(),
        p_value_other: '',
        frequency: series.frequency || '',
        soiling_mode: normalizeSoilingMode(series.soiling_mode || null),
        soiling_fixed_percentage: series.soiling_fixed_percentage ?? undefined,
        tmy_source: series.tmy_source || '',
        model_version: series.model_version || '',
        filename: series.filename || '',
      })
      setPoiUnitNote(null)

      // Fetch rows for this series
      const token = await getToken()
      const resp = await axios.get(
        `${baseURL}/v1/operational/projects/${projectId}/pv-budgeted/data`,
        {
          headers: { Authorization: `Bearer ${token}` },
          params: { pv_budgeted_series_id: series.pv_budgeted_series_id },
        },
      )
      const rows: Array<{
        time_stamp: string
        poi_ac_power: number
        ghi: number
        poa: number
        temperature: number
        soiling_percentage: number
      }> = resp.data || []

      // Map into GridRow format
      const mapped: GridRow[] = rows.map((r) => ({
        time_stamp: r.time_stamp,
        poi_ac_power: r.poi_ac_power,
        ghi: r.ghi,
        poa: r.poa,
        temperature: r.temperature,
        soiling_percentage: r.soiling_percentage,
      }))

      // Populate grid state
      allRowsRef.current = mapped
      setTotalRows(mapped.length)
      setParsedCount(Math.min(mapped.length, VISIBLE_LIMIT))
      setIsParsing(false)
      setVisibleRows(mapped.slice(0, VISIBLE_LIMIT))
    } catch (e) {
      console.error('Failed to load series data', e)
    } finally {
      setIsLoadingSeriesData(false)
    }
  }

  const handleConfirmDelete = async () => {
    if (!seriesToDelete) return

    try {
      setIsDeleting(true)
      await deleteSeriesMutation.mutateAsync({
        projectId,
        seriesId: seriesToDelete,
      })

      // Refresh the series list
      queryClient.invalidateQueries({
        queryKey: ['pvBudgetedSeries', { projectId }],
      })

      setDeleteModalOpened(false)
      setSeriesToDelete(null)
    } catch (error) {
      console.error('Error deleting series:', error)
      // Keep modal open on error so user can try again
    } finally {
      setIsDeleting(false)
    }
  }

  const handleSave = async () => {
    if (!hasData) return

    try {
      setIsSaving(true)
      // Get all data from both visible rows and background processing
      const allData =
        allRowsRef.current.length > 0 ? allRowsRef.current : visibleRows

      // Filter out empty rows and validate required fields
      const validRows = allData.filter((row) => {
        const hasRequiredFields =
          row.poi_ac_power !== undefined &&
          row.poa !== undefined &&
          row.poi_ac_power !== null &&
          row.poa !== null

        // If soiling mode is per_timestamp, also require soiling_percentage
        if (
          seriesMeta.soiling_mode === 'per_timestamp' ||
          seriesMeta.soiling_mode === 'PER_TIMESTAMP'
        ) {
          return (
            hasRequiredFields &&
            row.soiling_percentage !== undefined &&
            row.soiling_percentage !== null
          )
        }

        return hasRequiredFields
      })

      if (validRows.length === 0) {
        const requiredFields =
          seriesMeta.soiling_mode === 'per_timestamp' ||
          seriesMeta.soiling_mode === 'PER_TIMESTAMP'
            ? 'POI AC power, POA, and Soiling percentage'
            : 'POI AC power and POA'
        alert(`Please provide data for at least ${requiredFields} columns`)
        return
      }

      // Use generated timestamps from the grid; fallback to hourly from now
      const now = new Date()
      const rowsWithTimestamps = validRows.map((row, index) => ({
        time_stamp:
          row.time_stamp ||
          new Date(now.getTime() + index * 60 * 60 * 1000).toISOString(),
        poi_ac_power: row.poi_ac_power!,
        ghi: row.ghi ?? null,
        poa: row.poa!,
        temperature: row.temperature ?? null,
        soiling_percentage:
          seriesMeta.soiling_mode === 'per_timestamp' ||
          seriesMeta.soiling_mode === 'PER_TIMESTAMP'
            ? (row.soiling_percentage ?? null)
            : null,
      }))

      // Prepare series metadata
      const seriesData = {
        p_value:
          seriesMeta.p_value === 'other'
            ? `P${seriesMeta.p_value_other}`
            : seriesMeta.p_value,
        frequency: seriesMeta.frequency || '1H', // Default to hourly if not detected
        soiling_mode:
          seriesMeta.soiling_mode === '' ? null : seriesMeta.soiling_mode,
        soiling_fixed_percentage: seriesMeta.soiling_fixed_percentage,
        tmy_source: seriesMeta.tmy_source,
        model_version: seriesMeta.model_version,
        filename: seriesMeta.filename,
      }

      // Get company ID from user context (optional)
      const companyId = userSelf.data?.company_id || null

      // Prepare the bulk upsert request
      const payload = {
        pv_budgeted_series_id: editingSeriesId, // update when editing, create when null
        series: seriesData,
        rows: rowsWithTimestamps,
        company_id_provider: companyId,
        company_id_counter: companyId,
        execution_date: new Date().toISOString().split('T')[0],
      }

      // Make API call to save the data
      const token = await getToken()
      await axios.post(
        `${baseURL}/v1/operational/projects/${projectId}/pv-budgeted/data/bulk-upsert`,
        payload,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        },
      )

      // Refresh the existing series list
      queryClient.invalidateQueries({
        queryKey: ['pvBudgetedSeries', { projectId }],
      })

      // Clear the form after successful save
      clearAll()
      setEditingSeriesId(null)
    } catch (error) {
      console.error('Error saving PV budgeted data:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handlePaste: React.ClipboardEventHandler<HTMLDivElement> = (e) => {
    const text = e.clipboardData?.getData('text') || ''
    if (!text) return
    e.preventDefault()

    const focus = focusedCellRef.current
    const lines = splitNonEmptyLines(text)
    if (lines.length === 0) return

    // Column-aware paste when a cell is focused
    if (focus) {
      const values = lines.map((l) => l.split(/[\t,]/))

      // Ensure frequency is set to hourly when pasting time-series
      setSeriesMeta((prev) => ({ ...prev, frequency: '1H' }))

      // Update only the visible portion (first VISIBLE_LIMIT rows)
      setVisibleRows((prev) => {
        const nextLength = Math.max(prev.length, VISIBLE_LIMIT)
        const next = [...prev]
        while (next.length < nextLength) next.push({})
        // Generate timestamps for the affected range if not already present
        const ts = generateTimestamps(values.length, project.data?.time_zone)
        for (let i = 0; i < values.length; i++) {
          const rowIdx = focus.rowIndex + i
          if (rowIdx >= VISIBLE_LIMIT) break
          const row = { ...next[rowIdx] }
          if (!row.time_stamp) {
            row.time_stamp = ts[i]
          }
          for (let j = 0; j < values[i].length; j++) {
            const colIdx = focus.colIndex + j
            const columnKeys = getVisibleColumnKeys(
              seriesMeta.soiling_mode,
              hasData,
            )
            if (colIdx >= columnKeys.length) break
            const key = columnKeys[colIdx]
            if (key === 'time_stamp') {
              // Do not allow overwriting timestamps through paste
              continue
            }
            const n = toNum(values[i][j])
            row[key] = typeof n === 'number' ? n : undefined
          }
          next[rowIdx] = row
        }

        // Apply unit detection if we pasted into POI AC power column
        const columnKeys = getVisibleColumnKeys(
          seriesMeta.soiling_mode,
          hasData,
        )
        if (columnKeys[focus.colIndex] === 'poi_ac_power') {
          const result = detectUnitsAndConvert(next, pvCapacityMW)
          setPoiUnitNote(result.label)
          return result.rows
        }
        return next
      })

      // Mirror into full dataset
      const neededAll = focus.rowIndex + values.length
      while (allRowsRef.current.length < neededAll) {
        allRowsRef.current.push({})
      }
      const ts = generateTimestamps(values.length, project.data?.time_zone)
      for (let i = 0; i < values.length; i++) {
        const rowIdx = focus.rowIndex + i
        const row = { ...allRowsRef.current[rowIdx] }
        if (!row.time_stamp) {
          row.time_stamp = ts[i]
        }
        for (let j = 0; j < values[i].length; j++) {
          const colIdx = focus.colIndex + j
          const columnKeys = getVisibleColumnKeys(
            seriesMeta.soiling_mode,
            hasData,
          )
          if (colIdx >= columnKeys.length) break
          const key = columnKeys[colIdx]
          if (key === 'time_stamp') {
            continue
          }
          const n = toNum(values[i][j])
          row[key] = typeof n === 'number' ? n : undefined
        }
        allRowsRef.current[rowIdx] = row
      }

      // Apply unit detection to full dataset if we pasted into POI AC power column
      const columnKeys = getVisibleColumnKeys(seriesMeta.soiling_mode, hasData)
      if (columnKeys[focus.colIndex] === 'poi_ac_power') {
        const resultAll = detectUnitsAndConvert(
          allRowsRef.current,
          pvCapacityMW,
        )
        allRowsRef.current = resultAll.rows
        setPoiUnitNote(resultAll.label)
      }

      // Update counters
      const newTotal = Math.max(totalRows, neededAll)
      setTotalRows(newTotal)
      setParsedCount(Math.min(newTotal, VISIBLE_LIMIT))
      setIsParsing(false)
      return
    }

    // Fallback: treat as full-grid paste starting at column 0
    setIsParsing(true)
    setTotalRows(lines.length)

    const FIRST_CHUNK = VISIBLE_LIMIT
    const head = lines.slice(0, FIRST_CHUNK)
    const headRows = head.map((line) =>
      parseLine(line, seriesMeta.soiling_mode),
    )

    // Ensure frequency is set to hourly when pasting time-series
    setSeriesMeta((prev) => ({ ...prev, frequency: '1H' }))

    // Generate timestamps for the entire paste and assign to first chunk
    const allTimestamps = generateTimestamps(
      lines.length,
      project.data?.time_zone,
    )
    const headResult = detectUnitsAndConvert(headRows, pvCapacityMW)
    setPoiUnitNote(headResult.label)
    const convertedHeadRows = headResult.rows.map((r, i) => ({
      ...r,
      time_stamp: allTimestamps[i],
    }))
    setVisibleRows(convertedHeadRows)
    setParsedCount(Math.min(FIRST_CHUNK, lines.length))

    const rest = lines.slice(FIRST_CHUNK)
    allRowsRef.current = []
    allRowsRef.current.push(...convertedHeadRows)

    let index = 0
    const CHUNK_SIZE = 1000
    const processChunk = () => {
      const chunk = rest.slice(index, index + CHUNK_SIZE)
      const chunkRows = chunk.map((line) =>
        parseLine(line, seriesMeta.soiling_mode),
      )
      const chunkResult = detectUnitsAndConvert(chunkRows, pvCapacityMW)
      if (chunkResult.label) setPoiUnitNote(chunkResult.label)
      const convertedChunkRows = chunkResult.rows.map((r, i) => ({
        ...r,
        time_stamp: allTimestamps[FIRST_CHUNK + index + i],
      }))
      allRowsRef.current.push(...convertedChunkRows)
      index += CHUNK_SIZE
      setParsedCount(FIRST_CHUNK + Math.min(index, rest.length))
      if (index < rest.length) setTimeout(processChunk, 0)
      else setIsParsing(false)
    }

    if (rest.length > 0) setTimeout(processChunk, 0)
    else setIsParsing(false)
  }

  const updateCell = (
    rowIndex: number,
    key: keyof GridRow,
    value: number | string | null,
  ) => {
    if (key === 'time_stamp') return
    const n = typeof value === 'number' ? value : Number(value)
    const safe = Number.isFinite(n) ? (n as number) : undefined
    setVisibleRows((prev) => {
      const next = [...prev]
      next[rowIndex] = { ...next[rowIndex], [key]: safe }
      return next
    })
    // Mirror into full data if available
    if (allRowsRef.current[rowIndex]) {
      allRowsRef.current[rowIndex] = {
        ...allRowsRef.current[rowIndex],
        [key]: safe,
      }
    }
  }

  const clearAll = () => {
    setVisibleRows([])
    allRowsRef.current = []
    setTotalRows(0)
    setParsedCount(0)
    setIsParsing(false)
    setPoiUnitNote(null)
    setEditingSeriesId(null)
    setEditingSeries(null)
    setSeriesMeta({
      p_value: '',
      p_value_other: '',
      frequency: '',
      soiling_mode: null,
      soiling_fixed_percentage: undefined,
      tmy_source: '',
      model_version: '',
      filename: '',
    })
  }

  return (
    <Stack gap="md" mt="md" h="100%">
      <Title order={3}>PV Budgeted Performance</Title>

      <Group align="start" gap="md" flex={1}>
        {/* Left Pane - Existing Series */}
        <Card withBorder w="500px" h="100%">
          <Stack gap="md">
            <Title order={4}>Existing Series</Title>
            <Text size="sm" c="dimmed">
              PV Budgeted Series in the database for this project
            </Text>
            <ScrollArea h={400}>
              {(() => {
                if (existingSeries.isLoading) {
                  return (
                    <Text size="sm" c="dimmed" ta="center" py="xl">
                      Loading series...
                    </Text>
                  )
                } else if (existingSeries.error) {
                  return (
                    <Text size="sm" c="red" ta="center" py="xl">
                      Error loading series: {existingSeries.error.message}
                    </Text>
                  )
                } else if (
                  existingSeries.data &&
                  existingSeries.data.length > 0
                ) {
                  return (
                    <Table>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>P-value</Table.Th>
                          <Table.Th>Filename</Table.Th>
                          <Table.Th>Actions</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {existingSeries.data?.map((series: any) => (
                          <Table.Tr
                            key={series.pv_budgeted_series_id}
                            bg={
                              editingSeriesId === series.pv_budgeted_series_id
                                ? theme.colors.blue[0]
                                : undefined
                            }
                          >
                            <Table.Td>{series.p_value}</Table.Td>
                            <Table.Td>{series.filename || 'N/A'}</Table.Td>
                            <Table.Td>
                              <Group gap="xs">
                                <Tooltip label="Edit Series" withArrow>
                                  <ActionIcon
                                    size="sm"
                                    variant="light"
                                    color="blue"
                                    onClick={() => handleEditClick(series)}
                                  >
                                    <IconEdit size={14} />
                                  </ActionIcon>
                                </Tooltip>
                                <Tooltip label="Delete Series..." withArrow>
                                  <ActionIcon
                                    size="sm"
                                    variant="light"
                                    color="red"
                                    onClick={() =>
                                      handleDeleteClick(
                                        series.pv_budgeted_series_id,
                                      )
                                    }
                                  >
                                    <IconTrash size={14} />
                                  </ActionIcon>
                                </Tooltip>
                              </Group>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  )
                } else {
                  return (
                    <Text size="sm" c="dimmed" ta="center" py="xl">
                      No existing series found
                    </Text>
                  )
                }
              })()}
            </ScrollArea>
          </Stack>
        </Card>

        {/* Right Pane - Create New Series */}
        <Card withBorder style={{ flex: 1, height: '100%' }}>
          <Stack gap="md" h="100%">
            <Title order={4}>
              {editingSeries
                ? `Edit Existing Series: ${
                    editingSeries.filename || editingSeries.p_value
                  }`
                : 'Create New Series'}
            </Title>
            <Text size="sm" c="dimmed">
              Paste from Excel/CSV directly into the grid below. Expected column
              order: POI AC power, POA, Temperature, GHI, Soiling percentage.
            </Text>

            <Stack gap="xs">
              <Title order={5} style={{ margin: 0 }}>
                Series Metadata
              </Title>
              <Group grow>
                <Stack gap="xs">
                  <Text size="xs" fw={500}>
                    P-value
                  </Text>
                  <Radio.Group
                    value={seriesMeta.p_value}
                    onChange={(value) =>
                      setSeriesMeta((prev) => ({ ...prev, p_value: value }))
                    }
                  >
                    <Stack gap="xs">
                      <Radio value="p50" label="P50" size="xs" />
                      <Radio value="p90" label="P90" size="xs" />
                      <Radio value="p95" label="P95" size="xs" />
                      <Radio value="other" label="Other" size="xs" />
                      {seriesMeta.p_value === 'other' && (
                        <TextInput
                          size="xs"
                          placeholder="Enter number (e.g., 75)"
                          value={seriesMeta.p_value_other}
                          onChange={(e) =>
                            setSeriesMeta((prev) => ({
                              ...prev,
                              p_value_other: e.target.value,
                            }))
                          }
                          leftSection="P"
                          styles={{ input: { marginLeft: 20 } }}
                        />
                      )}
                    </Stack>
                  </Radio.Group>
                </Stack>
                <TextInput
                  size="xs"
                  label="Frequency"
                  placeholder="Auto-detected from data"
                  value={seriesMeta.frequency}
                  disabled
                  styles={{
                    input: {
                      backgroundColor: 'var(--mantine-color-gray-1)',
                      cursor: 'not-allowed',
                    },
                  }}
                />
                <Select
                  size="xs"
                  label="Soiling Mode"
                  placeholder="Select mode"
                  data={[
                    { value: 'fixed', label: 'Fixed' },
                    { value: 'per_timestamp', label: 'Per Timestamp' },
                    { value: '', label: 'None' },
                  ]}
                  value={seriesMeta.soiling_mode}
                  onChange={(value) =>
                    setSeriesMeta((prev) => ({
                      ...prev,
                      soiling_mode: value,
                      soiling_fixed_percentage:
                        value === '' ? 0 : prev.soiling_fixed_percentage,
                    }))
                  }
                />
              </Group>
              <Group grow>
                <NumberInput
                  size="xs"
                  label="Fixed Soiling %"
                  placeholder="e.g., 2.5"
                  decimalScale={2}
                  value={seriesMeta.soiling_fixed_percentage}
                  onChange={(value) =>
                    setSeriesMeta((prev) => ({
                      ...prev,
                      soiling_fixed_percentage:
                        typeof value === 'number' ? value : undefined,
                    }))
                  }
                  disabled={
                    seriesMeta.soiling_mode !== 'fixed' &&
                    seriesMeta.soiling_mode !== 'FIXED'
                  }
                />
                <TextInput
                  size="xs"
                  label="TMY Source"
                  placeholder="e.g., TMY NSRDB 1999"
                  value={seriesMeta.tmy_source}
                  onChange={(e) =>
                    setSeriesMeta((prev) => ({
                      ...prev,
                      tmy_source: e.target.value,
                    }))
                  }
                />
                <TextInput
                  size="xs"
                  label="Model Version"
                  placeholder="e.g., PVSyst 7.4.7"
                  value={seriesMeta.model_version}
                  onChange={(e) =>
                    setSeriesMeta((prev) => ({
                      ...prev,
                      model_version: e.target.value,
                    }))
                  }
                />
              </Group>
              <TextInput
                size="xs"
                label="Filename"
                placeholder="e.g., SunCreekSolar_p50_res0.xlsx"
                value={seriesMeta.filename}
                onChange={(e) =>
                  setSeriesMeta((prev) => ({
                    ...prev,
                    filename: e.target.value,
                  }))
                }
              />
            </Stack>

            <Group justify="flex-start" gap={6}>
              <Button
                size="xs"
                variant="default"
                onClick={clearAll}
                disabled={!hasData}
              >
                Clear
              </Button>
            </Group>

            <Stack gap="xs">
              <Title order={5}>Provide the 8760s for Year 1</Title>
              <Text c="dimmed" size="sm">
                Copy-paste your 8760s into the respective columns based on
                Standard Time. The timestamps will be automatically generated as
                Standard Time at the site's local timezone for the year 2019. A
                preview of the top rows will be shown below. The remaining rows
                are hidden but will be saved to the database.
              </Text>
            </Stack>

            <ScrollArea h={420} onPaste={handlePaste} type="auto">
              {(() => {
                const displayRows: GridRow[] = visibleRows.length
                  ? visibleRows
                  : Array.from({ length: 10 }, () => ({}) as GridRow)
                return (
                  <Table
                    highlightOnHover
                    withRowBorders={false}
                    stickyHeader
                    stickyHeaderOffset={0}
                    miw={800}
                    fz="xs"
                    horizontalSpacing={4}
                    verticalSpacing={2}
                  >
                    <Table.Thead>
                      <Table.Tr>
                        {getVisibleColumns(
                          seriesMeta.soiling_mode,
                          hasData,
                        ).map((h) => (
                          <Table.Th
                            key={h}
                            style={{ paddingTop: 2, paddingBottom: 2 }}
                          >
                            {h === 'Timestamp' ? (
                              `Timestamp (${
                                project.data?.time_zone?.replace(/_/g, ' ') ||
                                'UTC'
                              })`
                            ) : h === 'POI AC power' ? (
                              <>
                                POI AC power
                                <Text component="span" c="red" inherit>
                                  {' '}
                                  *
                                </Text>
                                {poiUnitNote && (
                                  <Text
                                    component="span"
                                    size="10"
                                    c="dimmed"
                                    style={{
                                      marginLeft: 6,
                                      lineHeight: 1,
                                      display: 'inline-block',
                                    }}
                                  >
                                    {poiUnitNote}
                                  </Text>
                                )}
                              </>
                            ) : h === 'POA' ||
                              (h === 'Soiling percentage' &&
                                (seriesMeta.soiling_mode === 'per_timestamp' ||
                                  seriesMeta.soiling_mode ===
                                    'PER_TIMESTAMP')) ? (
                              <>
                                {h}
                                <Text component="span" c="red" inherit>
                                  {' '}
                                  *
                                </Text>
                              </>
                            ) : (
                              h
                            )}
                          </Table.Th>
                        ))}
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {displayRows.map((row, rIdx) => (
                        <Table.Tr key={rIdx}>
                          {getVisibleColumnKeys(
                            seriesMeta.soiling_mode,
                            hasData,
                          ).map((key, colIdx) => {
                            const getPlaceholder = (
                              key: keyof GridRow,
                              rIdx: number,
                            ) => {
                              if (rIdx === 0) {
                                const columnNames: Record<
                                  keyof GridRow,
                                  string
                                > = {
                                  time_stamp: 'Timestamp',
                                  poi_ac_power: 'POI AC Power',
                                  poa: 'POA',
                                  temperature: 'Temperature',
                                  ghi: 'GHI',
                                  soiling_percentage: 'Soiling percentage',
                                }
                                return `Paste your entire [${columnNames[key]}] column here.`
                              }
                              const units: Record<keyof GridRow, string> = {
                                time_stamp: '',
                                poi_ac_power: 'MW',
                                poa: 'W/m²',
                                temperature: '°C',
                                ghi: 'W/m²',
                                soiling_percentage: '%',
                              }
                              return units[key]
                            }

                            const getDecimalScale = (key: keyof GridRow) => {
                              const scales: Record<keyof GridRow, number> = {
                                time_stamp: 0,
                                poi_ac_power: 3,
                                poa: 1,
                                temperature: 1,
                                ghi: 1,
                                soiling_percentage: 2,
                              }
                              return scales[key]
                            }

                            return (
                              <Table.Td key={key}>
                                {key === 'time_stamp' ? (
                                  <TextInput
                                    size="xs"
                                    value={
                                      row.time_stamp
                                        ? dayjs(row.time_stamp)
                                            .tz(
                                              project.data?.time_zone || 'UTC',
                                            )
                                            .format('YYYY-MM-DD HH:mm')
                                        : ''
                                    }
                                    readOnly
                                    styles={{
                                      input: {
                                        paddingTop: 0,
                                        paddingBottom: 0,
                                        height: 24,
                                      },
                                    }}
                                    onFocus={() =>
                                      (focusedCellRef.current = {
                                        rowIndex: rIdx,
                                        colIndex: colIdx,
                                      })
                                    }
                                  />
                                ) : (
                                  <NumberInput
                                    size="xs"
                                    placeholder={getPlaceholder(key, rIdx)}
                                    decimalScale={getDecimalScale(key)}
                                    hideControls
                                    styles={{
                                      input: {
                                        paddingTop: 0,
                                        paddingBottom: 0,
                                        height: 24,
                                      },
                                    }}
                                    required={key === 'poi_ac_power'}
                                    value={row[key] ?? undefined}
                                    onChange={(v) => updateCell(rIdx, key, v)}
                                    onFocus={() =>
                                      (focusedCellRef.current = {
                                        rowIndex: rIdx,
                                        colIndex: colIdx,
                                      })
                                    }
                                  />
                                )}
                              </Table.Td>
                            )
                          })}
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )
              })()}
            </ScrollArea>

            {totalRows > visibleRows.length && (
              <Text size="xs" c="dimmed" ta="center" mt="xs">
                ... and {totalRows - visibleRows.length} more rows are hidden.
              </Text>
            )}

            <Group justify="flex-start" gap={6}>
              <Button
                size="xs"
                variant="default"
                onClick={clearAll}
                disabled={!hasData}
              >
                Cancel
              </Button>
              <Button
                size="xs"
                disabled={!hasData || isSaving}
                onClick={handleSave}
                loading={isSaving}
              >
                Save
              </Button>
            </Group>
          </Stack>
        </Card>
      </Group>

      <ConfirmationModal
        opened={deleteModalOpened}
        onClose={() => {
          if (isDeleting) return
          setDeleteModalOpened(false)
          setSeriesToDelete(null)
        }}
        onConfirm={handleConfirmDelete}
        title="Delete PV Budgeted Series"
        message="Are you sure you want to delete this series? This action cannot be undone and will permanently remove all associated data."
        confirmLoading={isDeleting}
      />
    </Stack>
  )
}

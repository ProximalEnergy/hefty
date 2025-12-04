import { DeviceTypeEnum, SensorTypeEnum } from '@/api/enumerations'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useGetDataTimeSeriesV3 } from '@/api/v1/operational/project/project_data'
import { useGetPvExpected } from '@/api/v1/operational/project/project_pv_expected'
import { useGetTagsByRegex } from '@/api/v1/operational/project/project_tags'
import { useSelectProject } from '@/api/v1/operational/projects'
import {
  SensorType,
  useGetSensorTypes,
} from '@/api/v1/operational/sensor_types'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useGetTags } from '@/hooks/api'
import { useGetDevicesV2 } from '@/hooks/api'
import { Tag } from '@/hooks/types'
import {
  Box,
  Button,
  Checkbox,
  Group,
  Paper,
  ScrollArea,
  SegmentedControl,
  Select,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from '@mantine/core'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

import AllTags from './AllTags'
import ByDevice from './ByDevice'
import BySensor from './BySensor'
import PlotWithUnits from './PlotWithUnits'
import UniquePatterns from './UniquePatterns'

const DataBrowsing = () => {
  const { projectId } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | null>(
    null,
  )
  const [selectedTags, setSelectedTags] = useState<Tag[]>([])
  const [expandedDevices, setExpandedDevices] = useState<Set<number>>(new Set())
  const [expandedSensorTypes, setExpandedSensorTypes] = useState<
    Set<number | null>
  >(new Set())
  const [displayMode, setDisplayMode] = useState<'by_device' | 'by_sensor'>(
    'by_device',
  )
  const [interval, setInterval] = useState<string>('5min')
  const [showTags, setShowTags] = useState<
    'curated_tags' | 'unique_patterns' | 'all_tags'
  >('curated_tags')
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearchTerm, setDebouncedSearchTerm] = useState<string>('')
  const [hasLoadedTagsFromUrl, setHasLoadedTagsFromUrl] = useState(false)
  const intervalOptions = {
    '1min': '1 minute',
    '5min': '5 minutes',
    '15min': '15 minutes',
    '30min': '30 minutes',
    '1hr': '1 hour',
  }
  const { start, end } = useValidateDateRange({})
  const project = useSelectProject(projectId!)
  const previousProjectIdRef = useRef(projectId)

  useEffect(() => {
    if (!projectId) {
      previousProjectIdRef.current = projectId
      return
    }

    if (
      previousProjectIdRef.current &&
      previousProjectIdRef.current !== projectId
    ) {
      queueMicrotask(() => {
        setSelectedTags([])
        setHasLoadedTagsFromUrl(false)
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev)
          next.delete('tagIds')
          return next
        })
      })
    }

    previousProjectIdRef.current = projectId
  }, [projectId, setSearchParams])

  // Parse tagIds from URL
  const tagIdsFromUrl = useMemo(() => {
    const tagIdsParam = searchParams.get('tagIds')
    if (!tagIdsParam) return []
    return tagIdsParam
      .split(',')
      .map((id) => parseInt(id.trim(), 10))
      .filter((id) => !isNaN(id))
  }, [searchParams])

  // Split into positive and negative tag IDs
  const { positiveTagIds, negativeTagIds } = useMemo(() => {
    const positive: number[] = []
    const negative: number[] = []
    tagIdsFromUrl.forEach((id) => {
      if (id > 0) {
        positive.push(id)
      } else if (id < 0) {
        negative.push(-id) // Convert to positive device_id
      }
    })
    return { positiveTagIds: positive, negativeTagIds: negative }
  }, [tagIdsFromUrl])

  // Fetch positive tags from URL
  const urlTagsQuery = useGetTags({
    pathParams: { projectId: projectId! },
    queryParams: {
      tag_ids: positiveTagIds,
      deep: true,
      include_ghost_tags: true, // Include un-mapped tags (device_id=0 or sensor_type_id=GHOST_UNKNOWN)
    },
    queryOptions: {
      enabled:
        positiveTagIds.length > 0 &&
        !hasLoadedTagsFromUrl &&
        selectedTags.length === 0 &&
        !!project.data,
      staleTime: Infinity,
    },
  })

  // Fetch devices for negative tag IDs (expected power tags)
  const urlDevicesQuery = useGetDevicesV2({
    pathParams: { projectId: projectId! },
    filters: {
      device_ids: negativeTagIds,
      with_tags: false,
    },
    queryOptions: {
      enabled:
        negativeTagIds.length > 0 &&
        project.data?.has_expected_energy_integration &&
        !hasLoadedTagsFromUrl &&
        selectedTags.length === 0 &&
        !!project.data,
      staleTime: Infinity,
    },
  })

  // Construct expected power tags from devices
  const urlExpectedPowerTags = useMemo(() => {
    if (
      !urlDevicesQuery.data ||
      !project.data?.has_expected_energy_integration
    ) {
      return []
    }

    const supportedEEMDeviceTypes = [5, 2, 9]

    const expectedPowerSensorTypes = {
      2: {
        sensor_type_id: -2,
        name_long: 'PV PCS Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
      5: {
        sensor_type_id: -5,
        name_long: 'Meter Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
      9: {
        sensor_type_id: -9,
        name_long: 'PV DC Combiner Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
    }

    // Filter devices to only those with supported device types
    const supportedDevices = urlDevicesQuery.data.filter(
      (device) =>
        device.device_type_id &&
        supportedEEMDeviceTypes.includes(device.device_type_id),
    )

    // Create Tag objects with tag_id = -device_id
    const expectedTags: Tag[] = supportedDevices.map((device) => ({
      tag_id: -device.device_id,
      device: device,
      device_id: device.device_id,
      sensor_type:
        expectedPowerSensorTypes[
          device.device_type_id as keyof typeof expectedPowerSensorTypes
        ],
      data_type: null,
      name_short: null,
      name_long: null,
      name_scada: '',
      scada_id: null,
      scada_type: null,
      unit_scada: null,
      unit_offset: null,
      unit_scale: null,
      point: null,
      polygon: null,
      sensor_type_id: null,
    }))

    return expectedTags
  }, [urlDevicesQuery.data, project.data])

  // Combine positive tags and expected power tags from URL
  const urlLoadedTags = useMemo(() => {
    const positiveTags = urlTagsQuery.data ?? []
    const expectedTags = urlExpectedPowerTags
    return [...positiveTags, ...expectedTags]
  }, [urlTagsQuery.data, urlExpectedPowerTags])

  // Load tags from URL into selectedTags (only once on initial load)
  useEffect(() => {
    if (
      !hasLoadedTagsFromUrl &&
      tagIdsFromUrl.length > 0 &&
      selectedTags.length === 0 &&
      urlLoadedTags.length > 0
    ) {
      // Check if all queries are complete
      const positiveTagsReady =
        positiveTagIds.length === 0 || urlTagsQuery.isSuccess
      const expectedTagsReady =
        negativeTagIds.length === 0 ||
        !project.data?.has_expected_energy_integration ||
        urlDevicesQuery.isSuccess

      if (positiveTagsReady && expectedTagsReady) {
        queueMicrotask(() => {
          setHasLoadedTagsFromUrl(true)
          setSelectedTags(urlLoadedTags)
        })
      }
    }
  }, [
    hasLoadedTagsFromUrl,
    tagIdsFromUrl.length,
    positiveTagIds.length,
    negativeTagIds.length,
    selectedTags.length,
    urlLoadedTags,
    urlTagsQuery.isSuccess,
    urlDevicesQuery.isSuccess,
    project.data,
  ])

  const sensorTypes = useGetSensorTypes({
    queryParams: {
      sensor_type_ids: project.data?.spec.used_sensor_type_ids ?? [],
    },
    queryOptions: { enabled: !!project.data },
  })
  const usedDeviceTypeIds = Array.from(
    new Set(
      sensorTypes.data?.map((sensorType) => sensorType.device_type_id) ?? [],
    ),
  )

  const deviceTypes = useGetDeviceTypes({
    queryParams: {
      device_type_ids: usedDeviceTypeIds,
    },
    queryOptions: { enabled: !!project.data && usedDeviceTypeIds.length > 0 },
  })
  const deviceTypeData = deviceTypes.data
    ?.filter((deviceType) => deviceType.device_type_id !== DeviceTypeEnum.GHOST)
    .sort((a, b) => (a.name_long ?? '').localeCompare(b.name_long ?? ''))

  const tags = useGetTags({
    pathParams: { projectId: projectId! },
    queryParams: {
      device_type_ids: [selectedDeviceType],
      deep: true,
    },
    queryOptions: { enabled: !!selectedDeviceType },
  })
  const uniqueDeviceIds = useMemo(() => {
    return Array.from(
      new Set(
        tags.data
          ?.map((tag) => tag.device_id)
          .filter((id): id is number => id !== null) ?? [],
      ),
    ).sort((a, b) => a - b)
  }, [tags.data])

  // Build expected power tags - one per device with supported device type
  const expectedPowerTags = useMemo(() => {
    if (!tags.data) return []

    const supportedEEMDeviceTypes = [5, 2, 9]

    // Get unique devices that have device_type_id in supportedEEMDeviceTypes
    const deviceMap = new Map<number, Tag['device']>()
    tags.data.forEach((tag) => {
      if (
        tag.device_id &&
        tag.device?.device_type_id &&
        supportedEEMDeviceTypes.includes(tag.device.device_type_id) &&
        !deviceMap.has(tag.device_id)
      ) {
        deviceMap.set(tag.device_id, tag.device)
      }
    })

    const expectedPowerSensorTypes = {
      2: {
        sensor_type_id: -2,
        name_long: 'PV PCS Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
      5: {
        sensor_type_id: -5,
        name_long: 'Meter Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
      9: {
        sensor_type_id: -9,
        name_long: 'PV DC Combiner Expected Power',
        unit: 'MW',
      } as unknown as SensorType,
    }

    // Create Tag objects with tag_id = -device_id
    const expectedTags: Tag[] = Array.from(deviceMap.entries()).map(
      ([deviceId, device]) => ({
        tag_id: -deviceId,
        device: device,
        device_id: deviceId,
        sensor_type:
          expectedPowerSensorTypes[
            device.device_type_id as keyof typeof expectedPowerSensorTypes
          ],
        data_type: null, // TODO: Fill in later
        name_short: null, // TODO: Fill in later
        name_long: null, // TODO: Fill in later
        name_scada: '', // TODO: Fill in later
        scada_id: null, // TODO: Fill in later
        scada_type: null, // TODO: Fill in later
        unit_scada: null, // TODO: Fill in later
        unit_offset: null, // TODO: Fill in later
        unit_scale: null, // TODO: Fill in later
        point: null, // TODO: Fill in later
        polygon: null, // TODO: Fill in later
        sensor_type_id: null, // TODO: Fill in later
      }),
    )

    return expectedTags
  }, [tags.data])

  const enrichedTags = useMemo(() => {
    if (!project.data || !tags.data) return []
    if (!project.data.has_expected_energy_integration) return tags.data
    return [...(tags.data ?? []), ...(expectedPowerTags ?? [])]
  }, [tags.data, project.data, expectedPowerTags])

  const enrichedUniqueSensorTypeIds = useMemo(() => {
    return Array.from(
      new Set(enrichedTags.map((tag) => tag.sensor_type_id) ?? []),
    ).sort((a, b) => {
      if (a === null && b === null) return 0
      if (a === null) return 1
      if (b === null) return -1
      return a - b
    })
  }, [enrichedTags])

  const allTags = useGetTagsByRegex({
    pathParams: { projectId: projectId! },
    queryParams: {
      regex: debouncedSearchTerm,
      limit: 200,
    },
    queryOptions: {
      enabled: showTags === 'all_tags' && debouncedSearchTerm.length >= 3,
    },
  })

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined

  if (project.data) {
    if (start) {
      startQuery = start.tz(project.data.time_zone, true).toISOString()
    }
    if (end) {
      endQuery = end.tz(project.data.time_zone, true).toISOString()
    }
  }

  const layout = useMemo(() => {
    const range =
      start?.tz('UTC', true).toISOString() && end?.tz('UTC', true).toISOString()
        ? [
            start?.tz('UTC', true).toISOString(),
            end?.tz('UTC', true).toISOString(),
          ]
        : undefined
    return {
      xaxis: {
        title: { text: 'Time' },
        range: range
          ? [
              start?.tz('UTC', true).toISOString(),
              end?.tz('UTC', true).toISOString(),
            ]
          : undefined,
        autorange: range ? false : undefined,
      },
    }
  }, [start, end])

  const timeseriesData = useGetDataTimeSeriesV3({
    pathParams: { projectId: projectId! },
    queryParams: {
      tag_ids: selectedTags
        .map((tag) => tag.tag_id)
        .filter((tagId) => tagId > 0),
      start: startQuery,
      end: endQuery,
      ensure_full_range: true,
      interval: interval,
      cutoff_now: true,
    },
    queryOptions: {
      enabled: false,
    },
  })
  const expectedPowerTimeseriesData = useGetPvExpected({
    pathParams: { projectId: projectId! },
    queryParams: {
      start: startQuery || '',
      end: endQuery || '',
      device_ids: selectedTags
        .filter((tag) => tag.tag_id < 0)
        .map((tag) => -tag.tag_id),
      highest_priority_only: true,
      cutoff_now: true,
    },
    queryOptions: {
      enabled: false,
    },
  })
  const fullTimeseriesData = useMemo(() => {
    const regularData = timeseriesData.data ?? []
    const expectedData = expectedPowerTimeseriesData.data ?? []
    return [...regularData, ...expectedData]
  }, [timeseriesData.data, expectedPowerTimeseriesData.data])

  const displayedTags = useMemo(() => {
    if (showTags === 'all_tags') {
      return allTags.data ?? []
    }
    if (showTags === 'curated_tags' && enrichedTags) {
      const matchesSearch = (tag: Tag): boolean => {
        if (!debouncedSearchTerm.trim()) return true
        try {
          const regex = new RegExp(debouncedSearchTerm, 'i')
          const displayedNameByDevice =
            tag.sensor_type?.name_long + ' ' + (tag.device?.name_long ?? '')
          const displayedNameBySensor =
            tag.device?.device_type?.name_long +
            ' ' +
            (tag.device?.name_long ?? '')
          return (
            regex.test(displayedNameByDevice) ||
            regex.test(displayedNameBySensor) ||
            regex.test(tag.name_scada)
          )
        } catch {
          return false
        }
      }
      return enrichedTags.filter(matchesSearch)
    }
    return []
  }, [showTags, enrichedTags, allTags.data, debouncedSearchTerm])

  const handleSelectAll = () => {
    setSelectedTags((prev) => {
      const existingTagIds = new Set(prev.map((tag) => tag.tag_id))
      const newTags = displayedTags.filter(
        (tag) => !existingTagIds.has(tag.tag_id),
      )
      return [...prev, ...newTags]
    })
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTerm(searchTerm)
    }, 500)

    return () => clearTimeout(timer)
  }, [searchTerm])

  // Update URL parameter when selectedTags changes
  // Skip this during initial load when tags are being loaded from URL
  useEffect(() => {
    // Don't update URL if we're still loading tags from URL or if tags were just loaded
    if (!hasLoadedTagsFromUrl && tagIdsFromUrl.length > 0) {
      return
    }

    const tagIds = selectedTags.map((tag) => tag.tag_id)
    const nextParams = new URLSearchParams(searchParams)
    if (tagIds.length > 0) {
      nextParams.set('tagIds', tagIds.join(','))
    } else {
      nextParams.delete('tagIds')
    }
    setSearchParams(nextParams, { replace: true })
  }, [
    selectedTags,
    searchParams,
    setSearchParams,
    hasLoadedTagsFromUrl,
    tagIdsFromUrl.length,
  ])

  const isLoading =
    project.isFetching || deviceTypes.isFetching || sensorTypes.isFetching
  if (isLoading) {
    return <PageLoader />
  }

  const expandAllDevices = () => {
    setExpandedDevices(new Set(uniqueDeviceIds))
  }

  const collapseAllDevices = () => {
    setExpandedDevices(new Set())
  }

  const expandAllSensorTypes = () => {
    setExpandedSensorTypes(new Set(enrichedUniqueSensorTypeIds))
  }

  const collapseAllSensorTypes = () => {
    setExpandedSensorTypes(new Set())
  }

  const handleDownloadCSV = () => {
    if (!fullTimeseriesData || fullTimeseriesData.length === 0) {
      return
    }

    // Normalize timestamp function - converts to ISO string for consistent comparison
    const normalizeTimestamp = (timestamp: string): string => {
      try {
        const date = new Date(timestamp)
        // Return ISO string, which is consistent format
        return date.toISOString()
      } catch {
        // If parsing fails, return original
        return timestamp
      }
    }

    // Collect all unique timestamps, normalized to ISO format
    const allNormalizedTimestamps = new Set<string>()

    fullTimeseriesData.forEach((trace) => {
      trace.x.forEach((timestamp) => {
        const normalized = normalizeTimestamp(timestamp)
        allNormalizedTimestamps.add(normalized)
      })
    })

    // Sort normalized timestamps
    const sortedNormalizedTimestamps = Array.from(
      allNormalizedTimestamps,
    ).sort()

    // Create a matrix: rows are timestamps, columns are traces
    // Initialize with empty strings
    const matrix: (string | number)[][] = sortedNormalizedTimestamps.map(() =>
      new Array(fullTimeseriesData.length + 1).fill(''),
    )

    // Fill in timestamps in first column (use normalized ISO format for consistency)
    sortedNormalizedTimestamps.forEach((normalizedTs, rowIdx) => {
      matrix[rowIdx][0] = normalizedTs
    })

    // Fill in y-values for each trace
    fullTimeseriesData.forEach((trace, traceIdx) => {
      const columnIdx = traceIdx + 1

      // Create a map from normalized timestamp to y-value for this trace
      const normalizedTimestampToValue = new Map<string, number | null>()
      trace.x.forEach((ts, idx) => {
        const normalized = normalizeTimestamp(ts)
        normalizedTimestampToValue.set(normalized, trace.y[idx] ?? null)
      })

      // Fill in values for each normalized timestamp
      sortedNormalizedTimestamps.forEach((normalizedTs, rowIdx) => {
        const value = normalizedTimestampToValue.get(normalizedTs)
        matrix[rowIdx][columnIdx] =
          value !== null && value !== undefined ? value : ''
      })
    })

    // Build CSV content
    const headers = [
      'Time',
      ...fullTimeseriesData.map(
        (trace) => trace.tag_name_scada || trace.name || '',
      ),
    ]
    const csvRows = [
      headers.join(','),
      ...matrix.map((row) =>
        row
          .map((cell) => {
            // Escape commas and quotes in cell values
            if (typeof cell === 'string') {
              const escaped = cell.replace(/"/g, '""')
              return cell.includes(',') ||
                cell.includes('"') ||
                cell.includes('\n')
                ? `"${escaped}"`
                : escaped
            }
            return cell
          })
          .join(','),
      ),
    ]

    const csvContent = csvRows.join('\n')

    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute(
      'download',
      `data-browsing-${new Date().toISOString().split('T')[0]}.csv`,
    )
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  return (
    <Stack p="md" h="100%">
      <Group h="100%" w="100%">
        <Stack h="100%" flex={1}>
          <PageTitle
            info={
              <div>
                <Text size="sm" fw={500} mb="xs">
                  Data Browsing Capabilities
                </Text>
                <Text size="xs" mb="xs">
                  Browse and visualize timeseries data from your project. Select
                  tags (data points) from devices and sensors, then fetch and
                  plot the data over your chosen date range.
                </Text>
                <Text size="xs" fw={500} mb="xs" mt="md">
                  Key Features:
                </Text>
                <Text
                  size="xs"
                  component="ul"
                  style={{ margin: 0, paddingLeft: '1rem' }}
                >
                  <li>
                    <strong>Tag Selection:</strong> Browse tags by device type,
                    device, or sensor type. Use &quot;Curated Tags&quot; for
                    organized views, &quot;Unique Patterns&quot; to discover and
                    search tag patterns, or &quot;All Tags&quot; for regex
                    search.
                  </li>
                  <li>
                    <strong>Display Modes:</strong> Organize tags &quot;By
                    Device&quot; (grouped by physical devices) or &quot;By
                    Sensor&quot; (grouped by sensor types).
                  </li>
                  <li>
                    <strong>Data Visualization:</strong> Plot selected tags with
                    automatic unit handling and multiple y-axes for different
                    measurement units.
                  </li>
                  <li>
                    <strong>Data Export:</strong> Download timeseries data as
                    CSV for analysis.
                  </li>
                  <li>
                    <strong>Expected Power:</strong> For projects with expected
                    energy integration, view expected power alongside actual
                    measurements.
                  </li>
                </Text>
              </div>
            }
          >
            Data Browsing
          </PageTitle>
          <Group align="center">
            <Tooltip
              openDelay={250}
              label={
                <div>
                  <Text size="xs" fw={500} mb={4}>
                    Curated Tags:
                  </Text>
                  <Text size="xs" mb={8}>
                    Browse tags organized by device type. Select a device type
                    to see all available tags for that type, organized by device
                    or sensor type. Best for exploring structured data.
                  </Text>
                  <Text size="xs" fw={500} mb={4}>
                    Unique Patterns:
                  </Text>
                  <Text size="xs" mb={8}>
                    Discover unique tag naming patterns in your project. Click
                    any pattern to automatically convert it to a regex search
                    (replacing [INT] with digit matching) and switch to All Tags
                    view. Patterns are sorted alphabetically with [INT] segments
                    highlighted.
                  </Text>
                  <Text size="xs" fw={500} mb={4}>
                    All Tags:
                  </Text>
                  <Text size="xs">
                    Search all tags using regex patterns (minimum 3 characters).
                    Useful for finding specific tags by name or pattern across
                    the entire project.
                  </Text>
                </div>
              }
              multiline
              w={300}
              withArrow
            >
              <SegmentedControl
                data={[
                  { label: 'Curated Tags', value: 'curated_tags' },
                  { label: 'Unique Patterns', value: 'unique_patterns' },
                  { label: 'All Tags', value: 'all_tags' },
                ]}
                value={showTags}
                onChange={(value) =>
                  setShowTags(
                    value as 'curated_tags' | 'unique_patterns' | 'all_tags',
                  )
                }
                flex={1}
              />
            </Tooltip>
          </Group>
          {showTags === 'curated_tags' && (
            <>
              <Select
                data={deviceTypeData?.map((deviceType) => ({
                  label: deviceType.name_long ?? '',
                  value: deviceType.device_type_id.toString(),
                }))}
                value={selectedDeviceType}
                onChange={setSelectedDeviceType}
                placeholder="Select Device Type..."
                clearable
                searchable
              />

              <Group align="center">
                <Text>Display Mode</Text>
                <Tooltip
                  openDelay={250}
                  label={
                    <div>
                      <Text size="xs" fw={500} mb={4}>
                        By Device:
                      </Text>
                      <Text size="xs" mb={8}>
                        Organize tags by physical device. Expand devices to see
                        all sensor types and tags associated with each device.
                        Best for exploring data from specific equipment.
                      </Text>
                      <Text size="xs" fw={500} mb={4}>
                        By Sensor:
                      </Text>
                      <Text size="xs">
                        Organize tags by sensor type. Expand sensor types to see
                        all devices that have that sensor type. Best for
                        comparing the same measurement type across multiple
                        devices.
                      </Text>
                    </div>
                  }
                  multiline
                  w={300}
                  withArrow
                >
                  <div style={{ flex: 1 }}>
                    <SegmentedControl
                      data={[
                        { label: 'By Device', value: 'by_device' },
                        { label: 'By Sensor', value: 'by_sensor' },
                      ]}
                      value={displayMode}
                      onChange={(value) =>
                        setDisplayMode(value as 'by_device' | 'by_sensor')
                      }
                      flex={1}
                    />
                  </div>
                </Tooltip>
              </Group>
            </>
          )}
          <TextInput
            placeholder="Search tags..."
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.currentTarget.value)}
          />
          <Paper withBorder h="10%" flex={1}>
            {showTags === 'curated_tags' ? (
              displayMode === 'by_device' ? (
                <ByDevice
                  tags={enrichedTags}
                  uniqueDeviceIds={uniqueDeviceIds}
                  selectedTags={selectedTags}
                  setSelectedTags={setSelectedTags}
                  expandedDevices={expandedDevices}
                  setExpandedDevices={setExpandedDevices}
                  isFetching={tags.isFetching}
                  searchTerm={debouncedSearchTerm}
                />
              ) : (
                <BySensor
                  tags={enrichedTags}
                  uniqueSensorTypeIds={enrichedUniqueSensorTypeIds}
                  selectedTags={selectedTags}
                  setSelectedTags={setSelectedTags}
                  expandedSensorTypes={expandedSensorTypes}
                  setExpandedSensorTypes={setExpandedSensorTypes}
                  isFetching={tags.isFetching}
                  searchTerm={debouncedSearchTerm}
                />
              )
            ) : showTags === 'unique_patterns' ? (
              <UniquePatterns
                setSearchTerm={setSearchTerm}
                setShowTags={setShowTags}
                searchTerm={debouncedSearchTerm}
              />
            ) : (
              <AllTags
                projectId={projectId!}
                selectedTags={selectedTags}
                setSelectedTags={setSelectedTags}
                searchTerm={debouncedSearchTerm}
              />
            )}
          </Paper>
          <Group grow>
            <Button
              size="compact-xs"
              onClick={
                displayMode === 'by_device'
                  ? expandAllDevices
                  : expandAllSensorTypes
              }
            >
              Expand All
            </Button>
            <Button
              size="compact-xs"
              onClick={
                displayMode === 'by_device'
                  ? collapseAllDevices
                  : collapseAllSensorTypes
              }
            >
              Collapse All
            </Button>
          </Group>
          <Button
            size="compact-xs"
            disabled={
              (showTags === 'curated_tags' && tags.isFetching) ||
              (showTags === 'all_tags' && allTags.isFetching) ||
              displayedTags.length === 0 ||
              displayedTags.length > 200
            }
            onClick={handleSelectAll}
          >
            Select All ({displayedTags.length} tags)
          </Button>
          <Paper withBorder h="10%" flex={1}>
            <ScrollArea h="100%" style={{ height: '100%', overflowY: 'auto' }}>
              <Stack p="md" h="100%" gap={3}>
                {selectedTags.map((tag) => {
                  // Use name_scada fallback for un-mapped tags (sensor_type_id=GHOST_UNKNOWN or device_id=0)
                  const isUnmappedTag =
                    tag.sensor_type_id === SensorTypeEnum.GHOST_UNKNOWN ||
                    tag.device_id === 0
                  const tagName = isUnmappedTag
                    ? tag.name_scada
                    : tag.sensor_type?.name_long
                      ? tag.sensor_type.name_long +
                        ' ' +
                        (tag.device?.name_long ?? '')
                      : tag.name_scada
                  return (
                    <Checkbox
                      key={tag.tag_id}
                      label={tagName}
                      checked={true}
                      onChange={() => {
                        setSelectedTags((prev) => {
                          return prev.filter(
                            (selectedTag) => selectedTag.tag_id !== tag.tag_id,
                          )
                        })
                      }}
                    />
                  )
                })}
              </Stack>
            </ScrollArea>
          </Paper>
          <Button size="compact-xs" onClick={() => setSelectedTags([])}>
            Clear All
          </Button>
          <Group align="center">
            <Text>Data Granularity</Text>
            <Select
              data={Object.entries(intervalOptions).map(([key, value]) => ({
                label: value,
                value: key,
              }))}
              value={interval}
              onChange={(value) => setInterval(value || '5min')}
              flex={1}
            />
          </Group>
          <AdvancedDatePicker
            width="100%"
            includeTodayInDateRange
            maxDays={7}
          />
          <Button
            size="compact-xs"
            disabled={selectedTags.length === 0}
            onClick={() => {
              timeseriesData.refetch()
              expectedPowerTimeseriesData.refetch()
            }}
          >
            Fetch Data
          </Button>
        </Stack>
        <Stack h="100%" flex={5}>
          <Box h="100%" w="100%">
            <PlotWithUnits
              data={fullTimeseriesData}
              tags={selectedTags}
              layout={layout}
              isLoading={
                timeseriesData.isFetching ||
                expectedPowerTimeseriesData.isFetching
              }
              error={timeseriesData.error || expectedPowerTimeseriesData.error}
              allowPinning={true}
            />
          </Box>
          <Button
            size="compact-xs"
            disabled={fullTimeseriesData.length === 0}
            onClick={handleDownloadCSV}
          >
            Download Data
          </Button>
        </Stack>
      </Group>
    </Stack>
  )
}

export default DataBrowsing

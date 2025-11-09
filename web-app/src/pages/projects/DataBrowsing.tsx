// TODO:
// - Add virtualization to lowest ScrollArea
// - Add units display to lower ScrollArea
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetSensorTypes } from '@/api/v1/operational/sensor_types'
import CustomCard from '@/components/CustomCard'
import { PageLoader } from '@/components/Loading'
import { PageTitle } from '@/components/PageTitle'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetDevicesV2, useGetTags } from '@/hooks/api'
import { DataTimeSeries } from '@/hooks/types'
import {
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
import { useDebouncedValue } from '@mantine/hooks'
import { IconChevronDown, IconTag } from '@tabler/icons-react'
import { useVirtualizer } from '@tanstack/react-virtual'
import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router'

interface Parent {
  id: number
  name_long: string | null
}

interface TagChild {
  id: number
  parent_id: number
  name_long: string | null
  device_id: number | null
  sensor_type_id: number | null
  name_scada: string | null
  unit: string | null
}

interface BaseLayout {
  xaxis: { domain: [number, number] }
  yaxis: {
    title: { text: string }
    linecolor: string | undefined
    showgrid: boolean
    tickfont: { color: string | undefined }
    titlefont: { color: string | undefined }
  }
}

interface AdditionalAxes {
  [key: string]: {
    title: { text: string }
    overlaying: string
    side: string
    autoshift: boolean
    anchor: string
    showgrid: boolean
    tickfont: { color: string | undefined }
    titlefont: { color: string | undefined }
  }
}

function dataToCSV(data: DataTimeSeries[]) {
  if (data.length === 0) return ''

  const timestamps = data[0].x
  const headers = ['Timestamp', ...data.map((sensor) => sensor.tag_name_scada)]
  const csvRows = [headers.join(',')]

  timestamps.forEach((timestamp, index) => {
    const row = [timestamp]
    data.forEach((sensor) => {
      const value = sensor.y[index]
      if (typeof value === 'number') {
        row.push(value?.toFixed(4) || '')
      } else if (value !== null) {
        row.push(value)
      } else {
        row.push('')
      }
    })
    csvRows.push(row.join(','))
  })

  return csvRows.join('\n')
}

function downloadCSV(csv: string, filename: string) {
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.setAttribute('hidden', '')
  a.setAttribute('href', url)
  a.setAttribute('download', filename)
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function handleDownload(data: DataTimeSeries[]) {
  const csvData = dataToCSV(data)
  if (csvData) {
    downloadCSV(csvData, 'sensor-data.csv')
  }
}

const ParentItem = React.memo(
  ({
    parent,
    childrenTags,
    isExpanded,
    onToggleExpand,
    onParentCheck,
    onChildCheck,
    checkedChildren,
    tagDisplay,
  }: {
    parent: Parent
    childrenTags: TagChild[]
    isExpanded: boolean
    onToggleExpand: (id: number) => void
    onParentCheck: (id: number) => void
    onChildCheck: (id: number) => void
    checkedChildren: Record<number, boolean>
    tagDisplay: string
  }) => {
    const checkedCount = childrenTags.filter(
      (child) => checkedChildren[child.id],
    ).length
    const isIndeterminate =
      checkedCount > 0 && checkedCount < childrenTags.length
    const isParentChecked = checkedCount === childrenTags.length

    return (
      <Stack key={parent.id} gap={0}>
        <Group gap={2}>
          <Checkbox
            checked={isParentChecked}
            indeterminate={isIndeterminate}
            onChange={() => onParentCheck(parent.id)}
          />
          <Group
            onClick={() => onToggleExpand(parent.id)}
            gap={2}
            style={{ cursor: 'pointer' }}
          >
            <Text size="sm">{parent.name_long}</Text>
            <IconChevronDown
              size={14}
              style={{
                transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 0.3s',
              }}
            />
          </Group>
        </Group>

        {isExpanded && (
          <Stack style={{ paddingLeft: '18px' }} gap={0}>
            {childrenTags.map((tag) => (
              <Group gap={2} key={tag.id}>
                <Checkbox
                  checked={checkedChildren[tag.id] || false}
                  onChange={() => onChildCheck(tag.id)}
                />
                <IconTag size={14} />
                <Tooltip
                  label={
                    tagDisplay === 'device_name'
                      ? tag.name_long
                      : tag.name_scada
                  }
                  disabled={!tag.name_long || tag.name_long.length < 40}
                  position="right"
                >
                  <Text
                    size="sm"
                    style={{
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '100%',
                    }}
                  >
                    {tagDisplay === 'device_name'
                      ? tag.name_long
                      : tag.name_scada}
                  </Text>
                </Tooltip>
              </Group>
            ))}
          </Stack>
        )}
      </Stack>
    )
  },
)

const SelectedTagsList = React.memo(
  ({
    selectedTags,
    checkedChildren,
    onChildCheck,
    tagDisplay,
  }: {
    selectedTags: TagChild[]
    checkedChildren: Record<number, boolean>
    onChildCheck: (id: number) => void
    tagDisplay: string
  }) => (
    <ScrollArea style={{ height: '100%', overflowY: 'auto' }}>
      {selectedTags.map((tag) => (
        <Group gap={2} key={tag.id}>
          <Checkbox
            checked={checkedChildren[tag.id] || false}
            onChange={() => onChildCheck(tag.id)}
          />
          <Tooltip
            label={
              tagDisplay === 'device_name' ? tag.name_long : tag.name_scada
            }
            disabled={!tag.name_long || tag.name_long.length < 40}
            position="right"
          >
            <Text
              size="sm"
              style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '100%',
              }}
            >
              {tagDisplay === 'device_name' ? tag.name_long : tag.name_scada}
            </Text>
          </Tooltip>
        </Group>
      ))}
    </ScrollArea>
  ),
)

const Page = () => {
  const { projectId = '-1' } = useParams()
  const intervalOptions = {
    '1min': '1 minute',
    '5min': '5 minutes',
    '15min': '15 minutes',
    '30min': '30 minutes',
    '1hr': '1 hour',
  }
  const [interval, setInterval] = useState<string>('5min')

  // Retrieve parameters from the URL
  const params = useMemo(() => new URLSearchParams(window.location.search), [])

  useEffect(() => {
    setCheckedParents({})
    setCheckedChildren({})
    params.delete('selectedTagIds')
  }, [projectId, params])

  const [expandedIds, setExpandedIds] = useState<number[]>([])
  const [checkedParents, setCheckedParents] = useState<Record<number, boolean>>(
    {},
  )
  const [checkedChildren, setCheckedChildren] = useState<
    Record<number, boolean>
  >({})
  const [searchTerm, setSearchTerm] = useState<string>('')
  const [debouncedSearchTerm] = useDebouncedValue(searchTerm, 300)
  const [isInitialLoad, setIsInitialLoad] = useState<boolean>(true)
  const urlTagDisplay = params.get('tagDisplay')
  const urlParentType = params.get('parentType')
  const urlSelectedDeviceType = params.get('selectedDeviceType')
  const urlSelectedTagIds = params.get('selectedTagIds')
  const urlShowAllTags = params.get('showAllTags')

  // Initialize state with URL parameters or default values
  const [tagDisplay, setTagDisplay] = useState<string>(
    urlTagDisplay || 'device_name',
  )
  const [parentType, setParentType] = useState<string>(
    urlParentType || 'device',
  )
  const [selectedDeviceType, setSelectedDeviceType] = useState<string | null>(
    urlSelectedDeviceType || null,
  )
  const [showAllTags, setShowAllTags] = useState<boolean>(
    urlShowAllTags === 'true',
  )

  const [initialSelectedTagIds, setInitialSelectedTagIds] = useState<number[]>(
    [],
  )

  useEffect(() => {
    if (isInitialLoad) {
      if (urlSelectedTagIds) {
        setInitialSelectedTagIds(urlSelectedTagIds.split(',').map(Number))
      } else {
        setInitialSelectedTagIds([])
      }
    }
  }, [isInitialLoad, urlSelectedTagIds])

  useEffect(() => {
    if (initialSelectedTagIds.length > 0) {
      const initialCheckedChildren = initialSelectedTagIds.reduce(
        (acc, id) => ({ ...acc, [id]: true }),
        {},
      )
      setCheckedChildren(initialCheckedChildren)
    }
  }, [initialSelectedTagIds])

  const { start, end } = useValidateDateRange({})

  // API Data
  const project = useSelectProject(projectId!)

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

  const { data: deviceTypes, isLoading: isDeviceTypesLoading } =
    useGetDeviceTypes({})
  const { data: sensorTypes, isLoading: isSensorTypesLoading } =
    useGetSensorTypes({
      queryParams: { project_id: projectId },
    })
  const { data: devices, isLoading: isDevicesLoading } = useGetDevicesV2({
    pathParams: { projectId },
    filters: {
      with_tags: true,
    },
  })

  const isLoading =
    !project.data ||
    isDeviceTypesLoading ||
    isDevicesLoading ||
    isSensorTypesLoading

  const { data: tags, isLoading: isTagsLoading } = useGetTags({
    pathParams: { projectId },
    queryParams: {
      in_tsdb: true,
      include_ghost_tags: showAllTags,
    },
    queryOptions: { enabled: !isLoading },
  })

  // Update URL params whenever these dependencies change
  useEffect(() => {
    const updateParams = new URLSearchParams(window.location.search)
    updateParams.set('tagDisplay', tagDisplay)
    updateParams.set('parentType', parentType)
    updateParams.set('showAllTags', showAllTags.toString())
    if (selectedDeviceType) {
      updateParams.set('selectedDeviceType', selectedDeviceType)
    } else {
      updateParams.delete('selectedDeviceType')
    }

    if (tags) {
      const selectedTagIds = Object.keys(checkedChildren)
        .filter((key) => checkedChildren[Number(key)])
        .map(Number)
      if (selectedTagIds.length > 0) {
        updateParams.set('selectedTagIds', selectedTagIds.join(','))
      } else {
        updateParams.delete('selectedTagIds')
      }
    }

    window.history.replaceState(
      {},
      '',
      `${window.location.pathname}?${updateParams}`,
    )
  }, [
    tagDisplay,
    parentType,
    selectedDeviceType,
    checkedChildren,
    start,
    end,
    showAllTags,
    tags,
  ])

  const filteredDeviceTypes = useMemo(
    () =>
      deviceTypes?.filter((d) => {
        // Filter out device types with no devices or no associated tags
        const devicesWithThisType = devices?.filter(
          (device) => device.device_type_id === d.device_type_id,
        )

        return d.device_type_id !== 0 && (devicesWithThisType?.length ?? 0) > 0
      }) || [],
    [deviceTypes, devices],
  )

  // All tags mapped to TagChild structure
  const tagChildren: TagChild[] = useMemo(() => {
    if (!tags || !sensorTypes || !devices) return []
    return tags.map((tag) => {
      const sensorType = sensorTypes.find(
        (s) => s.sensor_type_id === tag.sensor_type_id,
      )
      const device = devices.find((d) => d.device_id === tag.device_id)
      const nameLong =
        tag.sensor_type_id === 24 || tag.sensor_type_id === 25
          ? tag.name_long
          : `${sensorType?.name_long || ''} ${device?.name_long || ''}`.trim()

      const parentId =
        parentType === 'device'
          ? (tag.device_id ?? -1)
          : (tag.sensor_type_id ?? -1)

      return {
        id: tag.tag_id,
        parent_id: parentId,
        name_long: nameLong || null,
        device_id: tag.device_id || null,
        sensor_type_id: tag.sensor_type_id || null,
        name_scada: tag.name_scada || null,
        unit: sensorType?.unit || null,
      }
    })
  }, [tags, sensorTypes, devices, parentType])

  // Filtered tags based on selectedDeviceType and search
  const filteredTags: TagChild[] = useMemo(() => {
    if (!selectedDeviceType || !devices || !tags || !sensorTypes) return []

    const relevantDevices = devices.filter(
      (device) => device.device_type_id.toString() === selectedDeviceType,
    )
    const deviceIds = relevantDevices.map((d) => d.device_id)

    const baseTags = tags.filter(
      (tag) =>
        tag.sensor_type_id &&
        tag.device_id &&
        deviceIds.includes(tag.device_id),
    )

    const mappedTags = baseTags.map((tag) => {
      const sensorType = sensorTypes.find(
        (s) => s.sensor_type_id === tag.sensor_type_id,
      )
      const device = devices.find((d) => d.device_id === tag.device_id)
      const nameLong =
        device?.device_type_id === 10
          ? tag.name_long + ' ' + sensorType?.name_long
          : `${sensorType?.name_long || ''} ${device?.name_long || ''}`.trim()
      const parentId =
        parentType === 'device' ? tag.device_id! : tag.sensor_type_id!

      return {
        id: tag.tag_id,
        parent_id: parentId,
        name_long: nameLong || 'none',
        device_id: tag.device_id,
        sensor_type_id: tag.sensor_type_id,
        name_scada: tag.name_scada,
        unit: sensorType?.unit || null,
      }
    })

    if (!debouncedSearchTerm) return mappedTags

    try {
      const regex = new RegExp(debouncedSearchTerm, 'i')
      if (tagDisplay === 'device_name') {
        return mappedTags.filter((tag) => regex.test(tag.name_long || ''))
      } else {
        return mappedTags.filter((tag) => regex.test(tag.name_scada || ''))
      }
    } catch (e) {
      console.error('Invalid regular expression:', e)
      return []
    }
  }, [
    tags,
    sensorTypes,
    devices,
    debouncedSearchTerm,
    parentType,
    selectedDeviceType,
    tagDisplay,
  ])

  const rawTags = useMemo(() => {
    if (!tags || !sensorTypes || !devices) return []
    if (!debouncedSearchTerm)
      return tags.sort((a, b) => a.name_scada.localeCompare(b.name_scada))

    try {
      const regex = new RegExp(debouncedSearchTerm, 'i')
      const filteredTags = tags.filter(
        (tag) =>
          regex.test(tag.name_long || '') || regex.test(tag.name_scada || ''),
      )

      // Sort the filtered tags alphabetically based on the 'name_long' or 'name_scada' field
      return filteredTags.sort((a, b) => {
        const nameA = (a.name_scada || '').toLowerCase()
        const nameB = (b.name_scada || '').toLowerCase()
        return nameA.localeCompare(nameB) // Alphabetical comparison
      })
    } catch (e) {
      console.error('Invalid regular expression:', e)
      return []
    }
  }, [tags, sensorTypes, devices, debouncedSearchTerm])

  const selectedTagIds = useMemo(
    () =>
      Object.keys(checkedChildren)
        .filter((key) => checkedChildren[Number(key)])
        .map(Number),
    [checkedChildren],
  )

  const selectedTags = useMemo(() => {
    const filtered = tagChildren.filter((t) => selectedTagIds.includes(t.id))
    return filtered.sort((a, b) =>
      (a.name_long || '').localeCompare(b.name_long || ''),
    )
  }, [tagChildren, selectedTagIds])

  const filteredParents: Parent[] = useMemo(() => {
    if (!selectedDeviceType || !devices || !tags || !sensorTypes) return []

    const relevantDevices = devices.filter(
      (device) => device.device_type_id.toString() === selectedDeviceType,
    )
    const deviceIds = relevantDevices.map((d) => d.device_id)

    if (parentType === 'device') {
      const parents = relevantDevices
        .filter((device) =>
          filteredTags.some((tag) => tag.parent_id === device.device_id),
        )
        .map((device) => ({
          id: device.device_id,
          name_long: device.name_full || '',
        }))
      return parents
    } else {
      // parentType === "sensor"
      const tagsForDevices = tags.filter(
        (tag) =>
          tag.sensor_type_id &&
          tag.device_id &&
          deviceIds.includes(tag.device_id),
      )

      const sensorTypeIds = Array.from(
        new Set(
          tagsForDevices
            .map((t) => t.sensor_type_id)
            .filter((id) => id !== null),
        ),
      ) as number[]

      const parents = sensorTypes
        .filter((sensorType) =>
          sensorTypeIds.includes(sensorType.sensor_type_id),
        )
        .map((sensorType) => ({
          id: sensorType.sensor_type_id,
          name_long: sensorType.name_long || '',
        }))
      return parents
    }
  }, [devices, sensorTypes, selectedDeviceType, filteredTags, parentType, tags])

  const {
    data: timeSeriesData,
    isLoading: timeSeriesIsLoading,
    refetch,
  } = useGetTimeSeries({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      tag_ids: selectedTags?.map((tag) => tag.id),
      start: startQuery,
      end: endQuery,
      include_ghost_tags: showAllTags,
      interval: interval,
    },
    queryOptions: { enabled: false },
  })

  // Handlers
  const handleParentCheckboxChange = useCallback(
    (parentId: number) => {
      const newCheckedState = !checkedParents[parentId]
      setCheckedParents((prev) => ({ ...prev, [parentId]: newCheckedState }))

      const children = filteredTags.filter((tag) => tag.parent_id === parentId)
      const newCheckedChildren = { ...checkedChildren }
      children.forEach((child) => {
        newCheckedChildren[child.id] = newCheckedState
      })
      setCheckedChildren(newCheckedChildren)
    },
    [checkedParents, checkedChildren, filteredTags],
  )

  const handleChildCheckboxChange = useCallback(
    (childId: number) => {
      const isChecked = !checkedChildren[childId]
      setCheckedChildren((prev) => ({ ...prev, [childId]: isChecked }))

      if (isChecked) {
        // Add to selectedTags if necessary
        const selectedTag = rawTags.find((tag) => tag.tag_id === childId)
        if (selectedTag) {
          setCheckedChildren((prev: Record<number, boolean>) => ({
            ...prev,
            [childId]: true,
          }))
        }
      } else {
        // Remove from selectedTags if necessary
        setCheckedChildren((prev: Record<number, boolean>) => {
          const newState = { ...prev }
          delete newState[childId]
          return newState
        })
      }
    },
    [checkedChildren, rawTags],
  )

  const toggleParentExpansion = useCallback((parentId: number) => {
    setExpandedIds((prev) =>
      prev.includes(parentId)
        ? prev.filter((id) => id !== parentId)
        : [...prev, parentId],
    )
  }, [])

  const handleSearchChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setSearchTerm(event.target.value)
    },
    [],
  )

  const handleSelectAll = useCallback(() => {
    if (!showAllTags) {
      const newCheckedParents: Record<number, boolean> = {}
      const newCheckedChildren: Record<number, boolean> = {}
      filteredParents.forEach((parent) => {
        newCheckedParents[parent.id] = true
        const children = filteredTags.filter(
          (tag) => tag.parent_id === parent.id,
        )
        children.forEach((child) => {
          newCheckedChildren[child.id] = true
        })
      })
      setCheckedParents((prev) => ({ ...prev, ...newCheckedParents }))
      setCheckedChildren((prev) => ({ ...prev, ...newCheckedChildren }))
    } else {
      const newCheckedParents: Record<number, boolean> = {}
      const newCheckedChildren: Record<number, boolean> = {}
      rawTags.forEach((tag) => {
        newCheckedChildren[tag.tag_id] = true
      })
      setCheckedParents((prev) => ({ ...prev, ...newCheckedParents }))
      setCheckedChildren((prev) => ({ ...prev, ...newCheckedChildren }))
    }
  }, [filteredParents, filteredTags, rawTags, showAllTags])

  const handleClearAll = useCallback(() => {
    setCheckedParents({})
    setCheckedChildren({})
  }, [])

  const handleExpandAll = useCallback(() => {
    setExpandedIds(filteredParents.map((parent) => parent.id))
  }, [filteredParents])

  const handleCollapseAll = useCallback(() => {
    setExpandedIds([])
  }, [])

  const uniqueUnits = useMemo(() => {
    return Array.from(new Set(selectedTags.map((item) => item.unit)))
  }, [selectedTags])

  const unitGroups = useMemo(() => {
    if (!uniqueUnits || uniqueUnits.length === 0) return []

    const colors = [
      '#1f77b4',
      '#ff7f0e',
      '#2ca02c',
      '#d62728',
      '#9467bd',
      '#8c564b',
      '#e377c2',
      '#7f7f7f',
      '#bcbd22',
      '#17becf',
    ]

    return uniqueUnits.map((unit, index) => {
      const itemsWithUnit = selectedTags.filter((item) => item.unit === unit)
      return {
        unit: unit || '',
        color:
          uniqueUnits.length > 1 ? colors[index % colors.length] : undefined,
        data: itemsWithUnit.map((item) => {
          const foundSeries = timeSeriesData?.find(
            (d) => d.tag_name_scada === item.name_scada,
          )
          return {
            x: foundSeries?.x || [],
            y: foundSeries?.y || [],
            name: item.name_scada,
            hoverlabel: { namelength: -1 },
            yaxis: `y${index + 1}`,
            line: {
              color:
                uniqueUnits.length > 1
                  ? colors[index % colors.length]
                  : undefined,
            },
          }
        }),
      }
    })
  }, [selectedTags, timeSeriesData, uniqueUnits])

  const layout = useMemo(() => {
    if (!uniqueUnits || uniqueUnits.length === 0 || !unitGroups) {
      return {
        xaxis: { domain: [0.05, 0.95] },
        yaxis: { title: { text: 'Add Data!' }, showgrid: false },
      }
    }

    const baseLayout: BaseLayout = {
      xaxis: { domain: [0.05, 0.95] },
      yaxis: {
        title: { text: uniqueUnits[0] || 'Add Data!' },
        linecolor: unitGroups[0]?.color,
        showgrid: false,
        tickfont: { color: unitGroups[0]?.color },
        titlefont: { color: unitGroups[0]?.color },
      },
    }

    if (unitGroups.length > 1) {
      const additionalAxes = unitGroups.slice(1).reduce((acc, group, idx) => {
        acc[`yaxis${idx + 2}`] = {
          title: { text: group.unit },
          overlaying: 'y',
          side: idx % 2 === 0 ? 'right' : 'left',
          autoshift: true,
          anchor: 'free',
          showgrid: false,
          tickfont: { color: group.color },
          titlefont: { color: group.color },
        }
        return acc
      }, {} as AdditionalAxes)
      return { ...baseLayout, ...additionalAxes }
    }

    return baseLayout
  }, [unitGroups, uniqueUnits])

  useEffect(() => {
    if (
      urlTagDisplay &&
      urlParentType &&
      urlSelectedDeviceType &&
      urlSelectedTagIds &&
      start &&
      end &&
      !isLoading &&
      !isTagsLoading &&
      isInitialLoad
    ) {
      if (selectedTags.length > 0) {
        refetch()
      }
      setIsInitialLoad(false)
    } else if (!isLoading && !isTagsLoading && isInitialLoad) {
      setIsInitialLoad(false)
    }
  }, [
    urlTagDisplay,
    urlParentType,
    urlSelectedDeviceType,
    urlSelectedTagIds,
    start,
    end,
    isLoading,
    isTagsLoading,
    isInitialLoad,
    selectedTags,
    refetch,
    checkedParents,
  ])

  useEffect(() => {
    if (showAllTags) {
      setSearchTerm('')
      setTagDisplay('scada_name')
    }
    if (!showAllTags) {
      setSearchTerm('')
      setCheckedChildren({})
    }
  }, [showAllTags])

  // The scrollable element for your list
  const parentRef = React.useRef(null)

  // rawTags virtualizer
  /* eslint-disable react-hooks/incompatible-library */
  const rawRowVirtualizer = useVirtualizer({
    count: rawTags.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,
  })
  // filteredTags virtualizer
  const filteredRowVirtualizer = useVirtualizer({
    count: filteredParents.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35,
  })

  if (isLoading) {
    return <PageLoader />
  }

  return (
    <Stack h="100%">
      <Group h="100%" w="100%">
        <Paper withBorder h="100%">
          <Stack p="md" h="100%">
            <PageTitle
              info={
                <Text>
                  This page allows for detailed exploration of project data.
                  Select tags and time ranges to visualize and download
                  time-series data.
                </Text>
              }
            >
              Data Browsing
            </PageTitle>
            <TextInput
              label="Search"
              description="*Supports regular expressions"
              value={searchTerm}
              onChange={handleSearchChange}
            />
            <Checkbox
              label="Show All Tags"
              checked={showAllTags}
              onChange={() => setShowAllTags(!showAllTags)}
            />
            <SegmentedControl
              data={[
                { label: 'Device Name', value: 'device_name' },
                { label: 'SCADA Name', value: 'scada_name' },
              ]}
              value={tagDisplay}
              onChange={setTagDisplay}
              disabled={showAllTags}
            />
            <Group grow>
              <Select
                data={filteredDeviceTypes.map((device) => ({
                  label: device.name_long || '',
                  value: device.device_type_id.toString(),
                }))}
                placeholder="Select Device Type..."
                clearable
                value={selectedDeviceType}
                onChange={setSelectedDeviceType}
                searchable
                disabled={showAllTags}
              />
              <SegmentedControl
                data={[
                  { label: 'Device', value: 'device' },
                  { label: 'Sensor', value: 'sensor' },
                ]}
                value={parentType}
                onChange={setParentType}
                disabled={showAllTags}
              />
            </Group>
            <Paper
              p="md"
              withBorder
              style={{
                flex: 1,
                overflow: 'hidden',
              }}
            >
              {isTagsLoading && (selectedDeviceType || showAllTags) ? (
                <div style={{ width: '100%', height: '100%' }}>
                  <PageLoader />
                </div>
              ) : showAllTags ? (
                <div
                  ref={parentRef}
                  style={{
                    height: '100%',
                    overflowY: 'scroll',
                    overflowX: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: `${rawRowVirtualizer.getTotalSize()}px`,
                      width: '100%',
                      position: 'relative',
                    }}
                  >
                    {rawRowVirtualizer.getVirtualItems().map((virtualRow) => {
                      const tag = rawTags[virtualRow.index]

                      return (
                        <div
                          key={tag.tag_id}
                          data-index={virtualRow.index}
                          ref={rawRowVirtualizer.measureElement}
                          style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            width: '100%',
                            transform: `translateY(${virtualRow.start}px)`,
                          }}
                        >
                          <Group gap={2} key={tag.tag_id}>
                            <Checkbox
                              checked={checkedChildren[tag.tag_id] || false}
                              onChange={() =>
                                handleChildCheckboxChange(tag.tag_id)
                              }
                            />
                            <Tooltip
                              label={
                                tagDisplay === 'device_name'
                                  ? tag.name_long
                                  : tag.name_scada
                              }
                              disabled={
                                !tag.name_long || tag.name_long.length < 40
                              }
                              position="right"
                            >
                              <Text
                                size="sm"
                                style={{
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  maxWidth: '100%',
                                }}
                              >
                                {tagDisplay === 'device_name'
                                  ? tag.name_long
                                  : tag.name_scada}
                              </Text>
                            </Tooltip>
                          </Group>
                        </div>
                      )
                    })}
                  </div>
                </div>
              ) : (
                <div
                  ref={parentRef}
                  style={{
                    height: '100%',
                    overflowY: 'scroll',
                    overflowX: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: `${filteredRowVirtualizer.getTotalSize()}px`,
                      width: '100%',
                      position: 'relative',
                    }}
                  >
                    {filteredRowVirtualizer
                      .getVirtualItems()
                      .map((virtualRow) => {
                        const parent = filteredParents[virtualRow.index]
                        if (!parent) return null
                        const childrenTags = filteredTags.filter(
                          (tag) => tag.parent_id === parent.id,
                        )

                        return (
                          <div
                            key={parent.id}
                            data-index={virtualRow.index}
                            ref={filteredRowVirtualizer.measureElement}
                            style={{
                              position: 'absolute',
                              top: 0,
                              left: 0,
                              width: '100%',
                              transform: `translateY(${virtualRow.start}px)`,
                            }}
                          >
                            {' '}
                            <ParentItem
                              key={parent.id}
                              parent={parent}
                              childrenTags={childrenTags}
                              isExpanded={expandedIds.includes(parent.id)}
                              onToggleExpand={toggleParentExpansion}
                              onParentCheck={handleParentCheckboxChange}
                              onChildCheck={handleChildCheckboxChange}
                              checkedChildren={checkedChildren}
                              tagDisplay={tagDisplay}
                            />
                          </div>
                        )
                      })}
                  </div>
                </div>
              )}
            </Paper>

            <Group gap="sm" grow>
              <Button
                size="compact-xs"
                onClick={handleExpandAll}
                disabled={showAllTags}
              >
                Expand All
              </Button>
              <Button
                size="compact-xs"
                onClick={handleCollapseAll}
                disabled={showAllTags}
              >
                Collapse All
              </Button>
            </Group>
            <Button
              size="compact-xs"
              onClick={handleSelectAll}
              disabled={
                showAllTags ? rawTags.length > 200 : filteredTags.length > 200
              }
            >
              Select All ({showAllTags ? rawTags.length : filteredTags.length}{' '}
              tags)
            </Button>
            <Paper
              p="md"
              withBorder
              style={{
                maxHeight: '25%',
                minHeight: '10%',
                overflowY: 'scroll',
                overflowX: 'hidden',
              }}
            >
              <SelectedTagsList
                selectedTags={selectedTags}
                checkedChildren={checkedChildren}
                onChildCheck={handleChildCheckboxChange}
                tagDisplay={tagDisplay}
              />
            </Paper>
            <Button size="compact-xs" onClick={handleClearAll}>
              Clear All
            </Button>
            <Group preventGrowOverflow grow>
              <Text>Data Granularity</Text>
              <Select
                data={Object.entries(intervalOptions).map(([key, value]) => ({
                  label: value,
                  value: key,
                }))}
                value={interval}
                onChange={(value) => setInterval(value || '5min')}
              />
            </Group>
            <AdvancedDatePicker
              includeClearButton={false}
              includeTodayInDateRange
              disableQuickActions
              maxDays={7}
              width="100%"
            />
            <Button
              size="compact-xs"
              onClick={() => refetch()}
              disabled={selectedTags.length === 0}
            >
              Fetch Data
            </Button>
          </Stack>
        </Paper>
        <Stack p="md" h="100%" flex={3}>
          <CustomCard style={{ height: '100%' }}>
            <PlotlyPlot
              data={unitGroups.flatMap(
                (group) =>
                  group.data?.map((item) => ({
                    ...item,
                    name: item.name || 'Unnamed',
                  })) || [],
              )}
              layout={layout}
              isLoading={timeSeriesIsLoading}
              allowPinning
            />
          </CustomCard>
          <Button
            size="compact-xs"
            onClick={() => handleDownload(timeSeriesData || [])}
            disabled={!timeSeriesData}
          >
            Download Data
          </Button>
        </Stack>
      </Group>
    </Stack>
  )
}

export default React.memo(Page)

import { SensorTypeEnum } from '@/api/enumerations'
import { EnrichedTag } from '@/pages/projects/data_browsing/DataBrowsing'
import { Checkbox, Group, LoadingOverlay, useMantineTheme } from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useCallback, useMemo, useRef } from 'react'

interface ByDeviceProps {
  tags: EnrichedTag[] | undefined
  uniqueDeviceIds: number[]
  selectedTags: EnrichedTag[]
  setSelectedTags: React.Dispatch<React.SetStateAction<EnrichedTag[]>>
  expandedDevices: Set<number>
  setExpandedDevices: React.Dispatch<React.SetStateAction<Set<number>>>
  isFetching: boolean
  searchTerm: string
  tagNameMode: 'name_full' | 'name_scada'
}

const ByDevice = ({
  tags,
  uniqueDeviceIds,
  selectedTags,
  setSelectedTags,
  expandedDevices,
  setExpandedDevices,
  isFetching,
  searchTerm,
  tagNameMode,
}: ByDeviceProps) => {
  const theme = useMantineTheme()
  const parentRef = useRef<HTMLDivElement>(null)

  // Helper function to check if a tag matches the search term
  const matchesSearch = useCallback(
    (tag: EnrichedTag): boolean => {
      if (!searchTerm.trim()) return true
      try {
        const regex = new RegExp(searchTerm, 'i')
        return regex.test(tag.name_full) || regex.test(tag.name_scada)
      } catch {
        return false
      }
    },
    [searchTerm],
  )

  // Flatten devices and their tags into a single array for virtualization
  const flattenedItems = useMemo(() => {
    if (!tags || !uniqueDeviceIds) return []

    const items: Array<{
      type: 'device' | 'tag'
      deviceId?: number
      tag?: EnrichedTag
      index: number
    }> = []
    let index = 0

    uniqueDeviceIds.forEach((deviceId) => {
      const deviceTags = tags.filter((tag) => tag.device_id === deviceId)
      const matchingDeviceTags = deviceTags.filter(matchesSearch)

      if (!matchingDeviceTags || matchingDeviceTags.length === 0) {
        return
      }

      // Add device header
      items.push({
        type: 'device',
        deviceId,
        index: index++,
      })

      // Add tags if device is expanded
      if (expandedDevices.has(deviceId)) {
        const sortedTags = matchingDeviceTags.slice().sort((a, b) => {
          return (a.name_full || a.name_scada).localeCompare(
            b.name_full || b.name_scada,
          )
        })

        sortedTags.forEach((tag) => {
          items.push({
            type: 'tag',
            deviceId,
            tag,
            index: index++,
          })
        })
      }
    })

    return items
  }, [tags, uniqueDeviceIds, expandedDevices, matchesSearch])

  const getDeviceCheckboxState = (
    deviceId: number,
    deviceTags: EnrichedTag[] | undefined,
  ) => {
    if (!deviceTags || deviceTags.length === 0) {
      return { checked: false, indeterminate: false }
    }
    // Filter tags by device ID and search term
    const deviceTagObjects = deviceTags
      .filter((tag) => tag.device_id === deviceId)
      .filter(matchesSearch)
    if (deviceTagObjects.length === 0) {
      return { checked: false, indeterminate: false }
    }
    const selectedTagIds = new Set(selectedTags.map((tag) => tag.tag_id))
    const selectedCount = deviceTagObjects.filter((tag) =>
      selectedTagIds.has(tag.tag_id),
    ).length
    const totalCount = deviceTagObjects.length
    const checked = selectedCount === totalCount && totalCount > 0
    const indeterminate = selectedCount > 0 && selectedCount < totalCount
    return { checked, indeterminate }
  }

  const toggleDeviceExpansion = (deviceId: number) => {
    setExpandedDevices((prev) => {
      const next = new Set(prev)
      if (next.has(deviceId)) {
        next.delete(deviceId)
      } else {
        next.add(deviceId)
      }
      return next
    })
  }

  const handleDeviceCheckboxChange = (
    deviceId: number,
    deviceTags: EnrichedTag[] | undefined,
  ) => {
    if (!deviceTags) return
    // Filter tags by device ID and search term
    const deviceTagObjects = deviceTags
      .filter((tag) => tag.device_id === deviceId)
      .filter(matchesSearch)
    const deviceCheckboxState = getDeviceCheckboxState(deviceId, deviceTags)
    setSelectedTags((prev) => {
      const deviceTagIds = new Set(deviceTagObjects.map((tag) => tag.tag_id))
      if (deviceCheckboxState.checked) {
        return prev.filter((tag) => !deviceTagIds.has(tag.tag_id))
      } else {
        return [
          ...prev.filter((tag) => !deviceTagIds.has(tag.tag_id)),
          ...deviceTagObjects,
        ]
      }
    })
  }

  const rowVirtualizer = useVirtualizer({
    count: flattenedItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      const item = flattenedItems[index]
      return item?.type === 'device' ? 35 : 35
    },
    overscan: 5,
  })

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <LoadingOverlay visible={isFetching} />
      <div
        ref={parentRef}
        style={{
          height: '100%',
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: theme.spacing.md,
        }}
      >
        <div
          style={{
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
            padding: '16px',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const item = flattenedItems[virtualRow.index]
            if (!item) return null

            if (item.type === 'device') {
              const deviceId = item.deviceId!
              const tagWithDevice = tags?.find(
                (tag) =>
                  tag.device_id === deviceId ||
                  tag.device?.device_id === deviceId,
              )
              const device = tagWithDevice?.device
              const deviceTags = tags?.filter(
                (tag) =>
                  tag.device_id === deviceId ||
                  tag.device?.device_id === deviceId,
              )

              const deviceTypeName =
                device?.device_type?.name_long ??
                tagWithDevice?.device_type_name_long ??
                ''
              const deviceNameShort =
                device?.name_long ?? tagWithDevice?.device_name_long ?? ''
              const deviceName = `${deviceTypeName} ${deviceNameShort}`.trim()

              const isExpanded = expandedDevices.has(deviceId)
              const deviceCheckboxState = getDeviceCheckboxState(
                deviceId,
                deviceTags,
              )

              return (
                <div
                  key={`device-${deviceId}`}
                  data-index={virtualRow.index}
                  ref={rowVirtualizer.measureElement}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${virtualRow.start}px)`,
                  }}
                >
                  <Group>
                    <Checkbox
                      label={deviceName}
                      checked={deviceCheckboxState.checked}
                      indeterminate={deviceCheckboxState.indeterminate}
                      onChange={() =>
                        handleDeviceCheckboxChange(deviceId, deviceTags)
                      }
                    />
                    {isExpanded ? (
                      <IconChevronDown
                        size={14}
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleDeviceExpansion(deviceId)}
                      />
                    ) : (
                      <IconChevronRight
                        size={14}
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleDeviceExpansion(deviceId)}
                      />
                    )}
                  </Group>
                </div>
              )
            } else {
              // It's a tag
              const tag = item.tag!
              // Expected power tags (tag_id < 0) don't have name_scada, always use name_full
              const isExpectedPowerTag = tag.tag_id < 0
              let tagName: string
              if (isExpectedPowerTag) {
                tagName = tag.name_full || ''
              } else if (tagNameMode === 'name_scada') {
                tagName = tag.name_scada || ''
              } else {
                // name_full mode: Use name_scada fallback for un-mapped tags
                const isUnmappedTag =
                  tag.sensor_type_id === SensorTypeEnum.GHOST_UNKNOWN ||
                  tag.device_id === 0
                tagName = isUnmappedTag
                  ? tag.name_scada
                  : tag.name_full || tag.name_scada
              }
              const isTagChecked = selectedTags.some(
                (selectedTag) => selectedTag.tag_id === tag.tag_id,
              )

              return (
                <div
                  key={tag.tag_id}
                  data-index={virtualRow.index}
                  ref={rowVirtualizer.measureElement}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${virtualRow.start}px)`,
                    paddingLeft: '32px',
                  }}
                >
                  <Checkbox
                    label={tagName}
                    onChange={() => {
                      setSelectedTags((prev) => {
                        const wasChecked = prev.some(
                          (selectedTag) => selectedTag.tag_id === tag.tag_id,
                        )
                        if (wasChecked) {
                          return prev.filter(
                            (selectedTag) => selectedTag.tag_id !== tag.tag_id,
                          )
                        } else {
                          return [...prev, tag]
                        }
                      })
                    }}
                    checked={isTagChecked}
                  />
                </div>
              )
            }
          })}
        </div>
      </div>
    </div>
  )
}

export default ByDevice

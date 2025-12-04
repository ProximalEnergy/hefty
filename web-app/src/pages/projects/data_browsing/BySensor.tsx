import { SensorTypeEnum } from '@/api/enumerations'
import { Tag } from '@/hooks/types'
import { Checkbox, Group, LoadingOverlay, useMantineTheme } from '@mantine/core'
import { IconChevronDown, IconChevronRight } from '@tabler/icons-react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useCallback, useMemo, useRef } from 'react'

interface BySensorProps {
  tags: Tag[] | undefined
  uniqueSensorTypeIds: (number | null)[]
  selectedTags: Tag[]
  setSelectedTags: React.Dispatch<React.SetStateAction<Tag[]>>
  expandedSensorTypes: Set<number | null>
  setExpandedSensorTypes: React.Dispatch<
    React.SetStateAction<Set<number | null>>
  >
  isFetching: boolean
  searchTerm: string
}

const BySensor = ({
  tags,
  uniqueSensorTypeIds,
  selectedTags,
  setSelectedTags,
  expandedSensorTypes,
  setExpandedSensorTypes,
  isFetching,
  searchTerm,
}: BySensorProps) => {
  const theme = useMantineTheme()
  const parentRef = useRef<HTMLDivElement>(null)

  // Helper function to check if a tag matches the search term
  const matchesSearch = useCallback(
    (tag: Tag): boolean => {
      if (!searchTerm.trim()) return true
      try {
        const regex = new RegExp(searchTerm, 'i')
        const displayedName =
          tag.device?.device_type?.name_long +
          ' ' +
          (tag.device?.name_long ?? '')
        return regex.test(displayedName) || regex.test(tag.name_scada)
      } catch {
        return false
      }
    },
    [searchTerm],
  )

  // Flatten sensor types and their tags into a single array for virtualization
  const flattenedItems = useMemo(() => {
    if (!tags || !uniqueSensorTypeIds) return []

    const items: Array<{
      type: 'sensorType' | 'tag'
      sensorTypeId?: number | null
      tag?: Tag
      index: number
    }> = []
    let index = 0

    uniqueSensorTypeIds.forEach((sensorTypeId) => {
      const sensorTypeTags = tags.filter(
        (tag) => tag.sensor_type_id === sensorTypeId,
      )
      const matchingSensorTypeTags = sensorTypeTags.filter(matchesSearch)

      if (!matchingSensorTypeTags || matchingSensorTypeTags.length === 0) {
        return
      }

      // Add sensor type header
      items.push({
        type: 'sensorType',
        sensorTypeId,
        index: index++,
      })

      // Add tags if sensor type is expanded
      if (expandedSensorTypes.has(sensorTypeId)) {
        const sortedTags = matchingSensorTypeTags.slice().sort((a, b) => {
          const nameA =
            a.device?.device_type?.name_long +
            ' ' +
            (a.device?.name_long ?? 'Unknown Device')
          const nameB =
            b.device?.device_type?.name_long +
            ' ' +
            (b.device?.name_long ?? 'Unknown Device')
          return nameA.localeCompare(nameB)
        })

        sortedTags.forEach((tag) => {
          items.push({
            type: 'tag',
            sensorTypeId,
            tag,
            index: index++,
          })
        })
      }
    })

    return items
  }, [tags, uniqueSensorTypeIds, expandedSensorTypes, matchesSearch])

  const getSensorTypeCheckboxState = (
    sensorTypeId: number | null,
    sensorTypeTags: Tag[] | undefined,
  ) => {
    if (!sensorTypeTags || sensorTypeTags.length === 0) {
      return { checked: false, indeterminate: false }
    }
    // Filter tags by sensor type ID and search term
    const sensorTypeTagObjects = sensorTypeTags
      .filter((tag) => tag.sensor_type_id === sensorTypeId)
      .filter(matchesSearch)
    if (sensorTypeTagObjects.length === 0) {
      return { checked: false, indeterminate: false }
    }
    const selectedTagIds = new Set(selectedTags.map((tag) => tag.tag_id))
    const selectedCount = sensorTypeTagObjects.filter((tag) =>
      selectedTagIds.has(tag.tag_id),
    ).length
    const totalCount = sensorTypeTagObjects.length
    const checked = selectedCount === totalCount && totalCount > 0
    const indeterminate = selectedCount > 0 && selectedCount < totalCount
    return { checked, indeterminate }
  }

  const toggleSensorTypeExpansion = (sensorTypeId: number | null) => {
    setExpandedSensorTypes((prev) => {
      const next = new Set(prev)
      if (next.has(sensorTypeId)) {
        next.delete(sensorTypeId)
      } else {
        next.add(sensorTypeId)
      }
      return next
    })
  }

  const handleSensorTypeCheckboxChange = (
    sensorTypeId: number | null,
    sensorTypeTags: Tag[] | undefined,
  ) => {
    if (!sensorTypeTags) return
    // Filter tags by sensor type ID and search term
    const sensorTypeTagObjects = sensorTypeTags
      .filter((tag) => tag.sensor_type_id === sensorTypeId)
      .filter(matchesSearch)
    const sensorTypeCheckboxState = getSensorTypeCheckboxState(
      sensorTypeId,
      sensorTypeTags,
    )
    setSelectedTags((prev) => {
      const sensorTypeTagIds = new Set(
        sensorTypeTagObjects.map((tag) => tag.tag_id),
      )
      if (sensorTypeCheckboxState.checked) {
        return prev.filter((tag) => !sensorTypeTagIds.has(tag.tag_id))
      } else {
        return [
          ...prev.filter((tag) => !sensorTypeTagIds.has(tag.tag_id)),
          ...sensorTypeTagObjects,
        ]
      }
    })
  }

  const rowVirtualizer = useVirtualizer({
    count: flattenedItems.length,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => {
      const item = flattenedItems[index]
      return item?.type === 'sensorType' ? 35 : 35
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

            if (item.type === 'sensorType') {
              const sensorTypeId = item.sensorTypeId!
              const sensorType = tags?.find(
                (tag) => tag.sensor_type_id === sensorTypeId,
              )?.sensor_type
              const sensorTypeTags = tags?.filter(
                (tag) => tag.sensor_type_id === sensorTypeId,
              )
              const sensorTypeName = sensorType?.name_long ?? 'Unknown Sensor'
              const isExpanded = expandedSensorTypes.has(sensorTypeId)
              const sensorTypeCheckboxState = getSensorTypeCheckboxState(
                sensorTypeId,
                sensorTypeTags,
              )

              return (
                <div
                  key={`sensorType-${sensorTypeId ?? 'null'}`}
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
                      label={sensorTypeName}
                      checked={sensorTypeCheckboxState.checked}
                      indeterminate={sensorTypeCheckboxState.indeterminate}
                      onChange={() =>
                        handleSensorTypeCheckboxChange(
                          sensorTypeId,
                          sensorTypeTags,
                        )
                      }
                    />
                    {isExpanded ? (
                      <IconChevronDown
                        size={14}
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleSensorTypeExpansion(sensorTypeId)}
                      />
                    ) : (
                      <IconChevronRight
                        size={14}
                        style={{ cursor: 'pointer' }}
                        onClick={() => toggleSensorTypeExpansion(sensorTypeId)}
                      />
                    )}
                  </Group>
                </div>
              )
            } else {
              // It's a tag
              const tag = item.tag!
              // Use name_scada fallback for un-mapped tags (sensor_type_id=GHOST_UNKNOWN or device_id=0)
              const isUnmappedTag =
                tag.sensor_type_id === SensorTypeEnum.GHOST_UNKNOWN ||
                tag.device_id === 0
              const tagName = isUnmappedTag
                ? tag.name_scada
                : tag.device?.device_type?.name_long
                  ? tag.device.device_type.name_long +
                    ' ' +
                    (tag.device?.name_long ?? '')
                  : tag.name_scada
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

export default BySensor

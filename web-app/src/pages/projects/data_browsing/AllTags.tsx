import { useGetTagsByRegex } from '@/api/v1/operational/project/project_tags'
import { EnrichedTag } from '@/pages/projects/data_browsing/DataBrowsing'
import {
  Checkbox,
  LoadingOverlay,
  Stack,
  Text,
  useMantineTheme,
} from '@mantine/core'
import { IconAlertTriangle } from '@tabler/icons-react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useCallback, useRef } from 'react'

interface AllTagsProps {
  projectId: string
  selectedTags: EnrichedTag[]
  setSelectedTags: React.Dispatch<React.SetStateAction<EnrichedTag[]>>
  searchTerm: string
}

const AllTags = ({
  projectId,
  selectedTags,
  setSelectedTags,
  searchTerm,
}: AllTagsProps) => {
  const theme = useMantineTheme()
  const parentRef = useRef<HTMLDivElement>(null)

  const tags = useGetTagsByRegex({
    pathParams: { projectId },
    queryParams: {
      regex: searchTerm,
      limit: 200,
      deep: false,
    },
    queryOptions: {
      enabled: searchTerm.length >= 3,
    },
  })

  const tagList = tags.data ?? []

  const getScrollElement = useCallback(() => parentRef.current, [])
  const estimateSize = useCallback(() => 35, [])

  // TanStack Virtual's useVirtualizer returns non-memoizable functions by design.
  // This is expected behavior, so we use a ref to keep the measureElement function stable.
  const rowVirtualizer = useVirtualizer({
    count: tagList.length,
    getScrollElement,
    estimateSize,
    overscan: 5,
  })

  // Store measureElement in a ref to keep it stable across renders
  const measureElementRef = useRef(rowVirtualizer.measureElement)
  measureElementRef.current = rowVirtualizer.measureElement

  // Create stable callback that uses the ref
  const measureElement = useCallback((node: Element | null) => {
    if (node) {
      measureElementRef.current(node)
    }
  }, [])

  // Extract virtualizer values - these will update on each render which is expected
  const virtualItems = rowVirtualizer.getVirtualItems()
  const totalSize = rowVirtualizer.getTotalSize()

  if (searchTerm.length < 3) {
    return (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <Stack p="md" align="center" justify="center" h="100%">
          <Text>Type at least 3 characters to search</Text>
        </Stack>
      </div>
    )
  }

  if (
    searchTerm.length >= 3 &&
    !tags.isFetching &&
    (!tags.data || tags.data.length === 0)
  ) {
    if (tags.error) {
      return (
        <div style={{ position: 'relative', height: '100%', width: '100%' }}>
          <Stack p="md" align="center" justify="center" h="100%">
            <IconAlertTriangle size={48} />
            <Text ta="center">{tags.error.response?.data?.detail}</Text>
          </Stack>
        </div>
      )
    }
    return (
      <div style={{ position: 'relative', height: '100%', width: '100%' }}>
        <Stack p="md" align="center" justify="center" h="100%">
          <Text>No tags found</Text>
        </Stack>
      </div>
    )
  }

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <LoadingOverlay visible={tags.isFetching} />
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
            height: `${totalSize}px`,
            width: '100%',
            position: 'relative',
            padding: '16px',
          }}
        >
          {virtualItems.map((virtualRow) => {
            const tag = tagList[virtualRow.index]
            if (!tag) return null

            const isTagChecked = selectedTags.some(
              (selectedTag) => selectedTag.tag_id === tag.tag_id,
            )

            return (
              <div
                key={tag.tag_id}
                data-index={virtualRow.index}
                ref={measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <Checkbox
                  label={(tag as EnrichedTag).name_full || tag.name_scada}
                  checked={isTagChecked}
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
                        // Create enriched tag if it doesn't have name_full
                        const enrichedTag: EnrichedTag = {
                          ...tag,
                          name_full:
                            (tag.device?.device_type?.name_long ?? '') +
                            ' ' +
                            (tag.device?.name_long ?? '') +
                            ' ' +
                            (tag.sensor_type?.name_metric ?? ''),
                        }
                        return [...prev, enrichedTag]
                      }
                    })
                  }}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default AllTags

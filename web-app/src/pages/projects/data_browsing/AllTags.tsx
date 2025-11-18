import { useGetTagsByRegex } from '@/api/v1/operational/project/project_tags'
import { Tag } from '@/hooks/types'
import {
  Checkbox,
  LoadingOverlay,
  Stack,
  Text,
  useMantineTheme,
} from '@mantine/core'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useRef } from 'react'

interface AllTagsProps {
  projectId: string
  selectedTags: Tag[]
  setSelectedTags: React.Dispatch<React.SetStateAction<Tag[]>>
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

  const rowVirtualizer = useVirtualizer({
    count: tagList.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 35,
    overscan: 5,
  })

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
            height: `${rowVirtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
            padding: '16px',
          }}
        >
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const tag = tagList[virtualRow.index]
            if (!tag) return null

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
                }}
              >
                <Checkbox
                  label={tag.name_scada}
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
                        return [...prev, tag]
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

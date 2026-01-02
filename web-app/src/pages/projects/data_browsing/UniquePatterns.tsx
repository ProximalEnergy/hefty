import {
  useGetUniqueTagTypes,
  usePutUniqueTagPatterns,
} from '@/api/v1/protected/web-application/projects/project-tag-explorer'
import {
  Button,
  LoadingOverlay,
  Stack,
  Text,
  useComputedColorScheme,
  useMantineTheme,
} from '@mantine/core'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useCallback, useMemo, useRef } from 'react'
import { useParams } from 'react-router'

interface UniquePatternsProps {
  setSearchTerm: (value: string) => void
  setShowTags: (value: 'curated_tags' | 'unique_patterns' | 'all_tags') => void
  searchTerm: string
}

const UniquePatterns = ({
  setSearchTerm,
  setShowTags,
  searchTerm,
}: UniquePatternsProps) => {
  const { projectId } = useParams()
  const theme = useMantineTheme()
  const computedColorScheme = useComputedColorScheme('light')
  const parentRef = useRef<HTMLDivElement>(null)

  const uniqueTagTypes = useGetUniqueTagTypes({
    pathParams: { projectId: projectId || '-1' },
  })

  const putUniqueTagPatterns = usePutUniqueTagPatterns()

  // Helper function to check if a pattern matches the search term
  const matchesSearch = useCallback(
    (pattern: string): boolean => {
      if (!searchTerm.trim()) return true
      try {
        const regex = new RegExp(searchTerm, 'i')
        return regex.test(pattern)
      } catch {
        return false
      }
    },
    [searchTerm],
  )

  const tagPatterns = useMemo(() => {
    if (!uniqueTagTypes.data) return []
    return uniqueTagTypes.data
      .map((tagType) => tagType.tag_pattern)
      .filter(matchesSearch)
      .sort((a, b) => a.localeCompare(b))
  }, [uniqueTagTypes.data, matchesSearch])

  const hasResolved =
    !uniqueTagTypes.isFetching && uniqueTagTypes.data !== undefined
  const allPatterns = useMemo(() => {
    if (!uniqueTagTypes.data) return []
    return uniqueTagTypes.data.map((tagType) => tagType.tag_pattern)
  }, [uniqueTagTypes.data])
  const isEmpty = hasResolved && allPatterns.length === 0
  const hasNoMatches =
    hasResolved && allPatterns.length > 0 && tagPatterns.length === 0

  const convertPatternToSearch = (pattern: string): string => {
    // Replace [INT] with regex pattern for integers with optional zero-padding
    return pattern.replace(/\[INT\]/g, '\\d+')
  }

  const handlePatternClick = (pattern: string) => {
    const searchPattern = convertPatternToSearch(pattern)
    setSearchTerm(searchPattern)
    setShowTags('all_tags')
  }

  const handleAssignPatterns = () => {
    if (projectId) {
      putUniqueTagPatterns.mutate({ projectId })
    }
  }

  const renderColoredPattern = (pattern: string) => {
    const parts: Array<{ text: string; isInt: boolean }> = []
    const regex = /(\[INT\])/g
    let lastIndex = 0
    let match

    while ((match = regex.exec(pattern)) !== null) {
      // Add text before [INT]
      if (match.index > lastIndex) {
        parts.push({
          text: pattern.substring(lastIndex, match.index),
          isInt: false,
        })
      }
      // Add [INT] part
      parts.push({ text: match[0], isInt: true })
      lastIndex = regex.lastIndex
    }
    // Add remaining text
    if (lastIndex < pattern.length) {
      parts.push({ text: pattern.substring(lastIndex), isInt: false })
    }

    // If no [INT] found, return the whole pattern as default text
    if (parts.length === 0) {
      parts.push({ text: pattern, isInt: false })
    }

    const defaultTextColor =
      computedColorScheme === 'dark'
        ? theme.colors.dark[0]
        : theme.colors.dark[9]

    return (
      <>
        {parts.map((part, index) => (
          <span
            key={index}
            style={{
              color: part.isInt
                ? theme.colors[theme.primaryColor][6]
                : defaultTextColor,
              fontWeight: part.isInt ? 'bold' : 'normal',
            }}
          >
            {part.text}
          </span>
        ))}
      </>
    )
  }

  const getScrollElement = useCallback(() => parentRef.current, [])
  const estimateSize = useCallback(() => 35, [])

  // TanStack Virtual's useVirtualizer returns non-memoizable functions by design.
  // This is expected behavior, so we use a ref to keep the measureElement function stable.
  // eslint-disable-next-line react-hooks/incompatible-library
  const rowVirtualizer = useVirtualizer({
    count: tagPatterns.length,
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

  return (
    <div style={{ position: 'relative', height: '100%', width: '100%' }}>
      <LoadingOverlay visible={uniqueTagTypes.isFetching} />
      {isEmpty ? (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: theme.spacing.md,
          }}
        >
          <Stack align="center" gap="md">
            <Text size="sm" c="dimmed">
              Unique tag patterns have not been assigned for this project yet.
            </Text>
            <Button
              onClick={handleAssignPatterns}
              loading={putUniqueTagPatterns.isPending}
            >
              Assign Unique Patterns
            </Button>
          </Stack>
        </div>
      ) : hasNoMatches ? (
        <div
          style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: theme.spacing.md,
          }}
        >
          <Text size="sm" c="dimmed">
            No patterns match your search.
          </Text>
        </div>
      ) : (
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
              const tagPattern = tagPatterns[virtualRow.index]
              if (!tagPattern) return null

              return (
                <div
                  key={virtualRow.index}
                  data-index={virtualRow.index}
                  ref={measureElement}
                  onClick={() => handlePatternClick(tagPattern)}
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${virtualRow.start}px)`,
                    cursor: 'pointer',
                  }}
                >
                  {renderColoredPattern(tagPattern)}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default UniquePatterns

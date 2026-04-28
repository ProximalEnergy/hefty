import { useGetUserFavoriteKPITypes } from '@/api/v1/admin/user_kpi_types'
import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import KPICard, { EmptyKPICard } from '@/components/KPICard'
import { QUERY_TIME } from '@/utils/queryTiming'
import { Group, Skeleton } from '@mantine/core'
import { useElementSize } from '@mantine/hooks'
import dayjs from 'dayjs'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router'

export const KPICards = () => {
  const { projectId } = useParams()
  const { ref: containerRef, width: containerWidth } = useElementSize()
  const { ref: contentRef, width: contentWidth } = useElementSize()
  const [rotationOffset, setRotationOffset] = useState(0)
  const [isHovered, setIsHovered] = useState(false)
  const [queryDate, setQueryDate] = useState(dayjs().format('YYYY-MM-DD'))

  const project = useSelectProject(projectId!)
  const projectKPIInstances = useGetKPIInstances({
    queryParams: {
      project_ids: [projectId || '-1'],
      deep: true,
    },
    queryOptions: {
      enabled: !!projectId,
    },
  })
  const projectKPITypeIds = projectKPIInstances.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const favoritedKPITypes = useGetUserFavoriteKPITypes({})

  const kpiTypeIds = favoritedKPITypes.data?.map(
    (kpiInstance) => kpiInstance.kpi_type_id,
  )

  const selectedKPITypeIds = (projectKPITypeIds || []).filter((id) =>
    (kpiTypeIds || []).includes(id),
  )

  const data = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '-1' },
    queryParams: {
      kpi_type_ids: selectedKPITypeIds,
      date: queryDate,
    },
    queryOptions: {
      enabled:
        !!projectId && !!favoritedKPITypes.data && !!projectKPIInstances.data,
      refetchInterval: QUERY_TIME.ONE_MINUTE, // Refetch every 60 seconds
      staleTime: QUERY_TIME.THIRTY_SECONDS, // Consider data stale after 30 seconds
    },
  })

  // Update queryDate when we detect today has no data (defer to avoid cascading renders)
  useEffect(() => {
    const today = dayjs().format('YYYY-MM-DD')
    if (
      data.isSuccess &&
      data.data &&
      data.data.length === 0 &&
      queryDate === today
    ) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setQueryDate(dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
      })
    }
  }, [data.isSuccess, data.data, queryDate])

  const contentIsGreaterThanContainer = contentWidth > containerWidth

  const filteredData = data.data?.filter(
    (kpi) => kpi.value !== null && kpi.value !== undefined,
  )

  const items = filteredData

  // Derive rotation offset: reset to 0 when content fits in container
  const effectiveRotationOffset = contentIsGreaterThanContainer
    ? rotationOffset
    : 0

  const rotatedItems = items
    ? items.slice(effectiveRotationOffset).concat(items.slice(0, effectiveRotationOffset))
    : []

  // Rotate items every 4 seconds when content is greater than container and not hovered
  useEffect(() => {
    if (!contentIsGreaterThanContainer || isHovered || !items?.length) return

    const interval = setInterval(() => {
      setRotationOffset((prev) => (prev + 1) % items.length)
    }, 4000)

    return () => {
      clearInterval(interval)
    }
  }, [contentIsGreaterThanContainer, items?.length, isHovered])

  // Reset rotation offset state when content is no longer greater than container
  useEffect(() => {
    if (!contentIsGreaterThanContainer && rotationOffset !== 0) {
      // Defer state update to avoid cascading renders
      queueMicrotask(() => {
        setRotationOffset(0)
      })
    }
  }, [contentIsGreaterThanContainer, rotationOffset])

  if (
    project.isLoading ||
    favoritedKPITypes.isLoading ||
    data.isLoading ||
    projectKPIInstances.isLoading
  ) {
    return (
      <Skeleton radius="md">
        <EmptyKPICard />
      </Skeleton>
    )
  }

  return (
    <Group
      ref={containerRef}
      style={{ overflow: 'hidden' }}
      w="100%"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <Group wrap="nowrap" ref={contentRef}>
        {rotatedItems?.map((kpi) => (
          <KPICard
            key={kpi.kpi_type_id}
            {...kpi}
            link={`kpis/type/${kpi.kpi_type_id}`}
          />
        ))}
      </Group>
    </Group>
  )
}

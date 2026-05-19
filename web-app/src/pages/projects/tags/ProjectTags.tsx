import { ProjectTypeEnum } from '@/api/enumerations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetTags } from '@/hooks/api'
import { ProjectTagsTable } from '@/pages/projects/tags/ProjectTagsTable'
import { Group, Select, Stack } from '@mantine/core'
import { type ColumnFiltersState } from '@tanstack/react-table'
import { useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router'

const SELECT_DATA = Array.from({ length: 100 }, (_, i) => ({
  value: (i + 1).toString(),
  label: (i + 1).toString(),
}))

export default function ProjectTags() {
  // Local State
  const [deviceId, setDeviceId] = useState<string | null>('')

  // URL State
  const { projectId } = useParams<{ projectId: string }>()
  const [searchParams, setSearchParams] = useSearchParams()

  // Data Fetching
  const project = useSelectProject(projectId)
  const tags = useGetTags({
    pathParams: { projectId: projectId || '' },
  })

  // Handle Sensor Type Change (null when clearable Select is cleared)
  const handleSensorTypeChange = (value: string | null) => {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value == null) {
        next.delete('sensorType')
      } else {
        next.set('sensorType', value)
      }
      return next
    })
  }

  const sensorTypeFromUrl = searchParams.get('sensorType')

  const columnFilters = useMemo((): ColumnFiltersState => {
    const filters: ColumnFiltersState = []
    if (deviceId) {
      filters.push({ id: 'device_id', value: deviceId })
    }
    if (sensorTypeFromUrl) {
      filters.push({ id: 'sensor_type_id', value: sensorTypeFromUrl })
    }
    return filters
  }, [deviceId, sensorTypeFromUrl])

  return (
    <Stack p="md" h="100%">
      <Group>
        {project.isLoading ? (
          <div>Project Loading...</div>
        ) : (
          <div>Project Loaded</div>
        )}
        {' | '}
        {tags.isLoading ? <div>Tags Loading...</div> : <div>Tags Loaded</div>}
      </Group>

      {tags.data && (
        <>
          <Select
            label="Device ID (useState)"
            data={SELECT_DATA}
            value={deviceId}
            onChange={setDeviceId}
            clearable
          />
          <Select
            label="Sensor Type ID (useSearchParams)"
            data={SELECT_DATA}
            value={searchParams.get('sensorType')}
            onChange={handleSensorTypeChange}
            clearable
          />
          <div>*Tag ID will only be visible for PV projects.</div>
        </>
      )}
      {project.data && tags.data && (
        <>
          <div>{tags.data.length} tags found</div>
          <ProjectTagsTable
            data={tags.data}
            columnFilters={columnFilters}
            columnVisibility={{
              tag_id:
                project.data.project_type_id === ProjectTypeEnum.PV
                  ? true
                  : false,
            }}
          />
        </>
      )}
    </Stack>
  )
}

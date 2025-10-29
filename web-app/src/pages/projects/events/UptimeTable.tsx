import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import { useSelectProject } from '@/api/v1/operational/projects'
import { PageLoader } from '@/components/Loading'
import UptimeGIS from '@/components/UptimeGIS'
import { AdvancedDatePicker } from '@/components/datepicker/AdvancedDatePickerInput'
import { useValidateDateRange } from '@/components/datepicker/utils'
import { useGetTags, useGetUptimeTable } from '@/hooks/api'
import { useProjectFilter } from '@/hooks/custom'
import { Tag } from '@/hooks/types'
import { Button, Group, Stack, Tabs, Text, Title } from '@mantine/core'
import { IconArrowRight } from '@tabler/icons-react'
import { MantineReactTable } from 'mantine-react-table'
import { useEffect, useRef, useState } from 'react'
import { MapRef } from 'react-map-gl/mapbox'
import { useParams } from 'react-router'

function ViewDataButton({
  deviceId,
  deviceTypeId,
  startQuery,
  endQuery,
  tags,
}: {
  deviceId: number
  deviceTypeId: number
  startQuery: string
  endQuery: string
  tags: Tag[]
}) {
  const { projectId } = useParams<{ projectId: string }>()
  const filteredTags = tags
    .filter((tag) => tag.device_id === deviceId)
    .filter((tag) => tag.sensor_type_id != 0)
  const tagString = filteredTags.map((tag) => tag.tag_id).join('%2C')

  const onClick = () => {
    if (filteredTags.length > 0) {
      const link = `/projects/${projectId}/data-browsing?start=${
        startQuery.split('T')[0]
      }&end=${
        endQuery.split('T')[0]
      }&selectedDeviceType=${deviceTypeId}&selectedTagIds=${tagString}`
      window.open(link, '_blank')
    }
  }

  return (
    <Stack>
      <Button rightSection={<IconArrowRight />} onClick={onClick}>
        View Data
      </Button>
    </Stack>
  )
}

const UptimeTable = () => {
  useProjectFilter({
    hasEventIntegration: true,
  })

  const { projectId } = useParams<{ projectId: string }>()
  const pcsRef = useRef<MapRef>(null)
  const blockRef = useRef<MapRef>(null)
  const pcsModuleRef = useRef<MapRef>(null)
  const combinerRef = useRef<MapRef>(null)

  const [selectedGIS, setSelectedGIS] = useState<string | null>(null)
  const [selectedTab, setSelectedTab] = useState<string | null>(null)
  const [pcsBounds, setPcsBounds] = useState<any>(null)
  const [blockBounds, setBlockBounds] = useState<any>(null)
  const [combinerBounds, setCombinerBounds] = useState<any>(null)

  const { data: project } = useSelectProject(projectId!)

  let startQuery: string | undefined = undefined
  let endQuery: string | undefined = undefined
  const { start, end } = useValidateDateRange({})

  if (project) {
    if (start) {
      startQuery = start.tz(project.time_zone, true).toISOString()
    }
    if (end) {
      endQuery = end.tz(project.time_zone, true).toISOString()
    }
  }

  const { data: deviceTypes, isLoading: isDeviceTypesLoading } =
    useGetDeviceTypes({
      queryOptions: {
        enabled: !!projectId,
      },
    })

  const { data: uptimeData, isLoading: isUptimeDataLoading } =
    useGetUptimeTable({
      pathParams: { projectId: projectId || '' },
      queryParams: {
        start: startQuery || '',
        end: endQuery || '',
        project_id: projectId || '',
      },
      queryOptions: {
        enabled: !!projectId && !!startQuery && !!endQuery,
      },
    })
  const uniqueDeviceIds = Array.from(
    new Set(uptimeData?.map((data) => data.device_id)),
  )

  const { data: tags, isLoading: isTagsLoading } = useGetTags({
    pathParams: { projectId: projectId || '' },
    queryParams: { device_ids: uniqueDeviceIds, in_tsdb: true },
    queryOptions: {
      enabled: !!projectId,
    },
  })

  useEffect(() => {
    pcsRef.current?.resize()
    blockRef.current?.resize()
    pcsModuleRef.current?.resize()
    combinerRef.current?.resize()
    if (pcsBounds) {
      pcsRef.current?.fitBounds(pcsBounds, { duration: 0 })
    }
    if (blockBounds) {
      blockRef.current?.fitBounds(blockBounds, { duration: 0 })
    }
    if (combinerBounds) {
      combinerRef.current?.fitBounds(combinerBounds, { duration: 0 })
    }
  }, [selectedGIS, selectedTab, uptimeData])

  if (isUptimeDataLoading || isDeviceTypesLoading || isTagsLoading) {
    return <PageLoader />
  }

  let maxUptime: number = 0
  if (uptimeData && uptimeData.length > 0) {
    maxUptime =
      uptimeData?.[0]?.downtime_hours / uptimeData?.[0]?.downtime_percentage
  }

  return (
    <Stack h="100%" w="100%" p="sm">
      <Title order={1}>Uptime Table</Title>
      <Group justify="space-between">
        <AdvancedDatePicker defaultRange="today" includeClearButton={false} />
        <Text>Maximum Uptime: {maxUptime.toFixed(1)} hours</Text>
      </Group>
      <Tabs
        defaultValue="table"
        flex={1}
        display="flex"
        onChange={(value) => setSelectedTab(value)}
        style={{ flexDirection: 'column' }}
      >
        <Tabs.List>
          <Tabs.Tab value="table">Table</Tabs.Tab>
          <Tabs.Tab value="gis">GIS</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="table">
          <MantineReactTable
            data={uptimeData || []}
            enableDensityToggle={false}
            initialState={{ density: 'xs' }}
            columns={[
              {
                accessorFn: (row) =>
                  deviceTypes?.find(
                    (type) => type.device_type_id === row.device_type_id,
                  )?.name_long,
                header: 'Device Type',
              },
              {
                accessorFn: (row) => row.device_name_full,
                header: 'Device Name',
              },
              {
                accessorFn: (row) =>
                  (maxUptime - row.downtime_hours).toFixed(1),
                header: 'Uptime Hours',
              },
              {
                accessorFn: (row) =>
                  ((1 - row.downtime_percentage) * 100).toFixed(1) + '%',
                header: 'Uptime Percentage',
              },

              {
                accessorFn: (row) => row.downtime_hours.toFixed(1),
                header: 'Downtime Hours',
              },
              {
                accessorFn: (row) =>
                  (row.downtime_percentage * 100).toFixed(1) + '%',
                header: 'Downtime Percentage',
              },
              { accessorFn: (row) => row.events, header: 'Events' },
              {
                accessorFn: (row) => (
                  <ViewDataButton
                    deviceId={row.device_id}
                    deviceTypeId={row.device_type_id}
                    startQuery={startQuery || ''}
                    endQuery={endQuery || ''}
                    tags={tags || []}
                  />
                ),
                header: 'Data Browsing',
              },
            ]}
          />
        </Tabs.Panel>
        <Tabs.Panel value="gis" h="100%">
          <Tabs
            defaultValue={selectedGIS || 'pcs'}
            flex={1}
            h="100%"
            display="flex"
            onChange={(value) => setSelectedGIS(value)}
            style={{ flexDirection: 'column' }}
          >
            <Tabs.List>
              <Tabs.Tab value="block">Block</Tabs.Tab>
              <Tabs.Tab value="pcs">PCS</Tabs.Tab>
              <Tabs.Tab value="combiner">Combiner</Tabs.Tab>
            </Tabs.List>
            <Tabs.Panel value="block" h="100%">
              <UptimeGIS
                deviceTypeId={6}
                uptimeData={uptimeData || []}
                mapRef={blockRef}
                deviceTypeName="Block"
                onBoundsChange={(bounds) => setBlockBounds(bounds)}
              />
            </Tabs.Panel>
            <Tabs.Panel value="pcs" h="100%">
              <UptimeGIS
                deviceTypeId={2}
                uptimeData={uptimeData || []}
                mapRef={pcsRef}
                deviceTypeName="PCS"
                onBoundsChange={(bounds) => setPcsBounds(bounds)}
              />
            </Tabs.Panel>
            <Tabs.Panel value="combiner" h="100%">
              <UptimeGIS
                deviceTypeId={9}
                uptimeData={uptimeData || []}
                mapRef={combinerRef}
                deviceTypeName="Combiner"
                onBoundsChange={(bounds) => setCombinerBounds(bounds)}
              />
            </Tabs.Panel>
          </Tabs>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  )
}

export default UptimeTable

import { useGetKPIInstances } from '@/api/v1/operational/kpi_instances'
import { useGetKPISummaryCards } from '@/api/v1/operational/project/kpi_data'
import { useGetTimeSeries } from '@/api/v1/operational/project/project_data'
import { useSelectProject } from '@/api/v1/operational/projects'
import KPICard from '@/components/KPICard'
import PlotlyPlot from '@/components/plots/PlotlyPlot'
import { useGetTags } from '@/hooks/api'
import {
  Button,
  Group,
  LoadingOverlay,
  MultiSelect,
  Paper,
  Select,
  Stack,
  Text,
  TextInput,
  useMantineTheme,
} from '@mantine/core'
import { useRef, useState } from 'react'
import { Responsive, WidthProvider } from 'react-grid-layout'
import { useParams } from 'react-router'

type Item = {
  key: string
  type: string
  text?: string
  title?: string
  minHeight?: number
  minWidth?: number
  x?: number
  y?: number
  w?: number
  h?: number
  selectedTags?: string[]
  selectedKpi?: string | null
}

const ResponsiveGridLayout = WidthProvider(Responsive)

const MyFirstGrid = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const theme = useMantineTheme()
  const [items, setItems] = useState<Item[]>([])
  const [editing, setEditing] = useState(false)
  const [previousLayout, setPreviousLayout] = useState<Item[]>([])
  const nextKeyRef = useRef(0)

  const { data: project } = useSelectProject(projectId!)

  const { data: tags, isLoading: isTagsLoading } = useGetTags({
    pathParams: { projectId: projectId || '' },
    queryParams: {
      sensor_type_ids: [1, 2],
    },
    queryOptions: { enabled: !!projectId },
  })

  const { data: kpiInstances, isLoading: isKpiInstancesLoading } =
    useGetKPIInstances({
      queryParams: {
        project_ids: [projectId ?? '-1'],
        deep: true,
      },
      queryOptions: {
        enabled: !!projectId,
      },
    })

  const addItem = () => {
    const newKey = nextKeyRef.current.toString()
    nextKeyRef.current += 1
    const newItem: Item = {
      key: newKey,
      type: 'text',
      x: 0,
      y: items.length,
      w: 2,
      h: 2,
      minHeight: 2,
      minWidth: 2,
    }
    setItems([...items, newItem])
  }

  const addTitleItem = () => {
    const newKey = nextKeyRef.current.toString()
    nextKeyRef.current += 1
    const newItem: Item = {
      key: newKey,
      type: 'title',
      title: project?.name_long,
      x: 0,
      y: 0,
      w: 2,
      h: 2,
      minHeight: 2,
      minWidth: 2,
    }
    setItems([...items, newItem])
  }

  const addPlotItem = () => {
    const newKey = nextKeyRef.current.toString()
    nextKeyRef.current += 1
    const newItem: Item = {
      key: newKey,
      type: 'plot',
      x: 0,
      y: 0,
      w: 12,
      h: 10,
      selectedTags: [],
    }
    setItems([...items, newItem])
  }

  const addKpiItem = () => {
    const newKey = nextKeyRef.current.toString()
    nextKeyRef.current += 1
    const newItem: Item = {
      key: newKey,
      type: 'kpi',
      x: 0,
      y: 0,
      w: 3,
      h: 4,
      minHeight: 4,
    }
    setItems([...items, newItem])
  }

  const onLayoutChange = (layout: any) => {
    const updatedItems = items.map((item) => {
      const layoutItem = layout.find((l: any) => l.i === item.key)
      if (layoutItem) {
        return {
          ...item,
          x: layoutItem.x,
          y: layoutItem.y,
          w: layoutItem.w,
          h: layoutItem.h,
        }
      }
      return item
    })
    setItems(updatedItems)
  }

  const handleEditClick = () => {
    if (!editing) {
      setPreviousLayout(items)
    }
    setEditing(!editing)
  }

  const handleCancelClick = () => {
    setItems(previousLayout)
    setEditing(false)
  }

  if (isTagsLoading || isKpiInstancesLoading) {
    return <LoadingOverlay visible={true} />
  }

  return (
    <Stack p="sm">
      {!editing && (
        <Group justify="flex-end">
          <Button onClick={handleEditClick}>Edit</Button>
        </Group>
      )}

      {editing && (
        <Group justify="space-between">
          <Group justify="flex-start">
            <Button onClick={addItem}>Add text component</Button>
            <Button onClick={addTitleItem}>Add title component</Button>
            <Button onClick={addPlotItem}>Add plot component</Button>
            <Button onClick={addKpiItem}>Add kpi component</Button>
          </Group>
          <Group justify="flex-end">
            <Button onClick={() => setEditing(false)}>Save</Button>
            <Button variant="default" onClick={handleCancelClick}>
              Cancel
            </Button>
          </Group>
        </Group>
      )}

      <ResponsiveGridLayout
        className="layout"
        cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
        rowHeight={30}
        isDraggable={editing}
        isResizable={editing}
        onLayoutChange={onLayoutChange}
      >
        {items.map((item, index) => (
          <div
            key={item.key}
            data-grid={{
              x: item.x || 0,
              y: item.y || index,
              w: item.w || item.minWidth || 1,
              h: item.h || item.minHeight || 1,
              minHeight: item.minHeight || 1,
              minWidth: item.minWidth || 1,
            }}
          >
            <Paper
              p="sm"
              withBorder
              h="100%"
              w="100%"
              style={{
                border: 'none',
                backgroundColor: theme.colors.dark[5],
                borderWidth: editing ? '2px' : '0px',
                borderStyle: editing ? 'solid' : 'none',
                overflow: 'hidden',
              }}
            >
              <Stack h="100%">
                {item.type === 'text' && editing && (
                  <TextInput
                    onChange={(e) => {
                      const updatedItems = items.map((i) =>
                        i.key === item.key ? { ...i, text: e.target.value } : i,
                      )
                      setItems(updatedItems)
                    }}
                    defaultValue={item.text}
                  />
                )}
                {item.type === 'text' && !editing && <Text>{item.text}</Text>}
                {item.type === 'title' && <Text>{item.title}</Text>}
                {item.type === 'plot' && (
                  <Stack h="100%">
                    {editing && (
                      <MultiSelect
                        data={
                          tags?.map((tag) => ({
                            value: tag.tag_id.toString(),
                            label: tag.name_scada,
                          })) || []
                        }
                        placeholder={
                          item.selectedTags?.length &&
                          item.selectedTags?.length > 0
                            ? ''
                            : 'Select one or more traces...'
                        }
                        searchable
                        value={item.selectedTags || []}
                        onChange={(value) => {
                          const updatedItems = items.map((i) =>
                            i.key === item.key
                              ? { ...i, selectedTags: value }
                              : i,
                          )
                          setItems(updatedItems)
                        }}
                      />
                    )}
                    {!editing &&
                      item.selectedTags &&
                      item.selectedTags.length > 0 && (
                        <Text>
                          {item.selectedTags
                            .map(
                              (selectedTag) =>
                                tags?.find(
                                  (tag) => tag.tag_id === Number(selectedTag),
                                )?.name_scada,
                            )
                            .join(', ')}
                        </Text>
                      )}
                    {item.selectedTags && item.selectedTags.length > 0 && (
                      <PlotComponent
                        projectId={projectId || ''}
                        selectedTags={item.selectedTags}
                      />
                    )}
                  </Stack>
                )}
                {item.type === 'kpi' && editing && (
                  <Stack>
                    <Select
                      data={kpiInstances
                        ?.filter((kpi) => kpi.is_visible)
                        .map((kpi) => ({
                          value: kpi.kpi_type_id.toString(),
                          label: kpi.kpi_type?.name_long || '',
                        }))}
                      searchable
                      value={item.selectedKpi}
                      onChange={(value) => {
                        const updatedItems = items.map((i) =>
                          i.key === item.key ? { ...i, selectedKpi: value } : i,
                        )
                        setItems(updatedItems)
                      }}
                      placeholder="Select a KPI..."
                    />
                  </Stack>
                )}
                {item.type === 'kpi' && !editing && (
                  <KPICardComponent
                    projectId={projectId || ''}
                    kpiTypeId={item.selectedKpi}
                  />
                )}
              </Stack>
            </Paper>
          </div>
        ))}
      </ResponsiveGridLayout>
    </Stack>
  )
}

const PlotComponent = ({
  projectId,
  selectedTags,
}: {
  projectId: string
  selectedTags: string[]
}) => {
  const { data: timeSeriesData, isLoading: timeSeriesIsLoading } =
    useGetTimeSeries({
      pathParams: { projectId: projectId || '' },
      queryParams: {
        tag_ids: selectedTags.map(Number),
      },
      queryOptions: { enabled: !!projectId && selectedTags.length > 0 },
    })

  return <PlotlyPlot data={timeSeriesData} isLoading={timeSeriesIsLoading} />
}

const KPICardComponent = ({
  projectId,
  kpiTypeId,
}: {
  projectId: string
  kpiTypeId: string | undefined | null
}) => {
  const { data: kpiData, isLoading: kpiIsLoading } = useGetKPISummaryCards({
    pathParams: { projectId: projectId || '' },
    queryParams: { kpi_type_ids: [Number(kpiTypeId)] },
    queryOptions: { enabled: !!kpiTypeId },
  })
  if (kpiIsLoading) {
    return <LoadingOverlay visible={true} />
  }
  return (
    <KPICard
      kpi_type_id={kpiData?.[0]?.kpi_type_id || 0}
      contract_id={kpiData?.[0]?.contract_id || 0}
      title={kpiData?.[0]?.title || ''}
      info={kpiData?.[0]?.info || ''}
      value={kpiData?.[0]?.value || 0}
      prefix={kpiData?.[0]?.prefix || ''}
      unit={kpiData?.[0]?.unit || ''}
      change={kpiData?.[0]?.change || 0}
      link={kpiData?.[0]?.link || ''}
      valColor={kpiData?.[0]?.valColor || ''}
      is_visible={kpiData?.[0]?.is_visible || false}
    />
  )
}

const CustomReport = () => {
  return <MyFirstGrid />
}

export default CustomReport

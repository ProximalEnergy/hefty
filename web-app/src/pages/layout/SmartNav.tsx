import { useGetDevicesV2 } from '@/hooks/api'
import {
  ActionIcon,
  Affix,
  Box,
  Button,
  Drawer,
  Group,
  LoadingOverlay,
  Stack,
  useMantineTheme,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import {
  IconCornerDownRight,
  IconExternalLink,
  IconMap,
} from '@tabler/icons-react'
import { useEffect, useState } from 'react'
import {
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from 'react-router-dom'

interface Buttons {
  label: string
  link: string
  blockSpecific?: boolean
}

const SmartNav = () => {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [opened, { open, close }] = useDisclosure(false)
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [blockId, setBlockId] = useState<string | null>(null)
  const [blockName, setBlockName] = useState<string | null>(null)
  const theme = useMantineTheme()
  const start = searchParams.get('start') || ''
  const end = searchParams.get('end') || ''

  const { data: blockDevices, isLoading: isBlockDevicesLoading } =
    useGetDevicesV2({
      pathParams: { projectId: projectId || '' },
      filters: { device_type_ids: [6] },
      queryOptions: {
        enabled: !!projectId,
      },
    })
  const locationFullPath = location.pathname + location.search

  useEffect(() => {
    if (
      location.pathname.startsWith(`/projects/${projectId}/gis/pv-dc-combiner/`)
    ) {
      setBlockId(location.pathname.split('/').pop() || null)
    } else if (
      locationFullPath.includes(
        `/projects/${projectId}/equipment-analysis/pv-dc-combiner/block?deviceId=`,
      )
    ) {
      const params = new URLSearchParams(location.search)
      setBlockId(params.get('deviceId'))
    } else if (
      location.pathname.startsWith(`/projects/${projectId}/gis/tracker/`)
    ) {
      setBlockId(location.pathname.split('/').pop() || null)
    } else if (
      locationFullPath.includes(
        `/projects/${projectId}/equipment-analysis/tracker?deviceId=`,
      )
    ) {
      const params = new URLSearchParams(location.search)
      setBlockId(params.get('deviceId'))
    } else {
      setBlockId(searchParams.get('deviceId'))
    }
  }, [locationFullPath, searchParams])

  useEffect(() => {
    setBlockName(
      blockDevices?.find(
        (device) => device.device_id === parseInt(blockId || ''),
      )?.name_long || null,
    )
  }, [blockId])

  const PCSGroup: Buttons[] = [
    {
      label: 'PV PCS GIS',
      link: `/projects/${projectId}/gis/pv-pcs`,
      blockSpecific: false,
    },
    {
      label: 'All PCS KPIs',
      link: `/projects/${projectId}/kpis?deviceTypeId=2`,
      blockSpecific: false,
    },
    {
      label: 'PCS Current Day',
      link: `/projects/${projectId}/equipment-analysis/pv-pcs`,
      blockSpecific: false,
    },
    {
      label: 'PCS Events',
      link: `/projects/${projectId}/events?deviceTypeIds=2`,
      blockSpecific: false,
    },
  ]

  const combinerGroup: Buttons[] = [
    {
      label: 'DC Combiner GIS',
      link: `/projects/${projectId}/gis/pv-dc-combiner`,
      blockSpecific: false,
    },
    {
      label: `Block ${blockName}`,
      link: `/projects/${projectId}/gis/pv-dc-combiner/${blockId}`,
      blockSpecific: true,
    },
    {
      label: 'All DC Combiner KPIs',
      link: `/projects/${projectId}/kpis?deviceTypeId=9`,
      blockSpecific: false,
    },
    {
      label: 'DC Combiner Current Day',
      link: `/projects/${projectId}/equipment-analysis/pv-dc-combiner`,
      blockSpecific: false,
    },
    {
      label: `Block ${blockName}`,
      link: `/projects/${projectId}/equipment-analysis/pv-dc-combiner/block?deviceId=${blockId}`,
      blockSpecific: true,
    },
    {
      label: 'DC Combiner Events',
      link: `/projects/${projectId}/events?deviceTypeIds=9`,
      blockSpecific: false,
    },
  ]

  const trackerGroup: Buttons[] = [
    {
      label: 'Tracker GIS',
      link: `/projects/${projectId}/gis/tracker?start=${start}&end=${end}`,
      blockSpecific: false,
    },
    {
      label: `Block ${blockName}`,
      link: `/projects/${projectId}/gis/tracker/${blockId}?start=${start}&end=${end}`,
      blockSpecific: true,
    },
    {
      label: 'All Tracker KPIs',
      link: `/projects/${projectId}/kpis?deviceTypeId=10`,
      blockSpecific: false,
    },
    {
      label: 'Tracker Current Day',
      link: `/projects/${projectId}/equipment-analysis/tracker?start=${start}&end=${end}`,
      blockSpecific: false,
    },
    {
      label: `Block ${blockName}`,
      link: `/projects/${projectId}/equipment-analysis/tracker/block?deviceId=${blockId}&start=${start}&end=${end}`,
      blockSpecific: true,
    },
    {
      label: 'Tracker Events',
      link: `/projects/${projectId}/events?deviceTypeIds=10`,
      blockSpecific: false,
    },
  ]

  const isOnPCSPage = PCSGroup.some((button) =>
    locationFullPath.startsWith(button.link),
  )
  const isOnCombinerPage = combinerGroup.some((button) =>
    locationFullPath.startsWith(button.link),
  )
  const isOnTrackerPage = trackerGroup.some((button) =>
    locationFullPath.startsWith(button.link),
  )
  const isOnAnyPage = isOnPCSPage || isOnCombinerPage || isOnTrackerPage

  if (isBlockDevicesLoading)
    return (
      <Box pos="relative">
        <LoadingOverlay />
      </Box>
    )

  return (
    <Group>
      <Drawer
        opened={opened}
        position="right"
        onClose={close}
        title="Suggested Pages"
        size="xs"
      >
        {isOnPCSPage && (
          <Stack>
            {PCSGroup.map(
              (button, index) =>
                !locationFullPath.startsWith(button.link) && (
                  <Button
                    key={index}
                    rightSection={<IconExternalLink size={14} />}
                    onClick={() => {
                      navigate(button.link)
                      close()
                    }}
                  >
                    {button.label}
                  </Button>
                ),
            )}
          </Stack>
        )}
        {isOnCombinerPage && (
          <Stack>
            {combinerGroup
              .filter(
                (button) =>
                  !button.blockSpecific ||
                  (button.blockSpecific &&
                    combinerGroup.some(
                      (b) =>
                        b.blockSpecific && locationFullPath.startsWith(b.link),
                    )),
              )
              .map(
                (button, index) =>
                  !locationFullPath.startsWith(button.link) && (
                    <Group justify="flex-start">
                      <IconCornerDownRight
                        style={{
                          display: button.blockSpecific ? 'block' : 'none',
                        }}
                      />
                      <Button
                        key={index}
                        rightSection={<IconExternalLink size={14} />}
                        onClick={() => {
                          navigate(button.link)
                          close()
                        }}
                        fullWidth={button.blockSpecific ? false : true}
                      >
                        {button.label}
                      </Button>
                    </Group>
                  ),
              )}
          </Stack>
        )}
        {isOnTrackerPage && (
          <Stack>
            {trackerGroup
              .filter(
                (button) =>
                  !button.blockSpecific ||
                  (button.blockSpecific &&
                    trackerGroup.some(
                      (b) =>
                        b.blockSpecific && locationFullPath.startsWith(b.link),
                    )),
              )
              .map(
                (button, index) =>
                  !locationFullPath.startsWith(button.link) && (
                    <Group justify="flex-start">
                      <IconCornerDownRight
                        style={{
                          display: button.blockSpecific ? 'block' : 'none',
                        }}
                      />
                      <Button
                        key={index}
                        rightSection={<IconExternalLink size={14} />}
                        onClick={() => {
                          navigate(button.link)
                          close()
                        }}
                        fullWidth={button.blockSpecific ? false : true}
                      >
                        {button.label}
                      </Button>
                    </Group>
                  ),
              )}
          </Stack>
        )}
      </Drawer>
      {!opened && isOnAnyPage && (
        <Affix position={{ top: 70, right: 20 }} zIndex={500}>
          <ActionIcon
            onClick={open}
            color={theme.primaryColor}
            radius="xl"
            size={40}
            style={{
              boxShadow: '0px 0px 4px 0px black',
            }}
          >
            <IconMap stroke={1.5} size={20} />
          </ActionIcon>
        </Affix>
      )}
    </Group>
  )
}

export default SmartNav

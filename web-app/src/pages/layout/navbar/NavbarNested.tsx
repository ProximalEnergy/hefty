import { useGetUserType } from '@/api/admin'
import {
  DeviceTypeEnum,
  ProjectTypeEnum,
  UserTypeEnum,
} from '@/api/enumerations'
import { useGetUserSelf } from '@/api/v1/admin/users'
import type { DeviceType as DeviceTypeData } from '@/api/v1/operational/device_types'
import { useGetDeviceTypes } from '@/api/v1/operational/device_types'
import {
  DroneIntegration,
  DronePermission,
  useGetDroneIntegrations,
  useGetDronePermissions,
} from '@/api/v1/operational/drone_integrations'
import { useSelectProject } from '@/api/v1/operational/projects'
import { useGetQSEAccess } from '@/api/v1/protected/web-application/projects/financial/qse_access'
import { useCreateFeedbackMutation } from '@/hooks/api'
import * as types from '@/hooks/types'
import { getCompanyLogoUrl } from '@/utils/cdn'
import { useUser } from '@clerk/react'
import {
  ActionIcon,
  AppShell,
  Button,
  Center,
  Divider,
  Group,
  Image,
  Modal,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Textarea,
  Tooltip,
  rem,
  useComputedColorScheme,
} from '@mantine/core'
import { Dropzone, FileWithPath, IMAGE_MIME_TYPE } from '@mantine/dropzone'
import { useForm } from '@mantine/form'
import { useDisclosure } from '@mantine/hooks'
import { IconArrowBackUp, IconMessageChatbot, IconX } from '@tabler/icons-react'
import { useMemo, useState } from 'react'
import { useLocation, useParams } from 'react-router'

import { HomeLinkWithDashboards } from './HomeLinkWithDashboards'
import { LinksGroup } from './NavbarLinksGroup'
import ProjectPicture from './ProjectPicture'
import * as links from './links'

// Mapping from device_type_id to equipment-analysis tab value
// Note: Multiple device types can map to the same tab (e.g., BESS_STRING and BESS_BLOCK both map to 'bess')
const DEVICE_TYPE_TO_TAB_MAP: Record<number, string> = {
  [DeviceTypeEnum.PV_INVERTER]: 'pv-pcs',
  [DeviceTypeEnum.PV_DC_COMBINER]: 'pv-dc-combiner',
  [DeviceTypeEnum.TRACKER_ROW]: 'tracker',
  [DeviceTypeEnum.MET_STATION]: 'met-station',
  [DeviceTypeEnum.BESS_PCS]: 'bess-pcs',
  [DeviceTypeEnum.BESS_STRING]: 'bess',
  [DeviceTypeEnum.BESS_BLOCK]: 'bess', // BESS Block also maps to bess tab
  [DeviceTypeEnum.PV_FEEDER]: 'circuit',
}

// Priority order for device types when multiple map to the same tab (lower number = higher priority)
const DEVICE_TYPE_PRIORITY: Record<number, number> = {
  [DeviceTypeEnum.BESS_STRING]: 1,
  [DeviceTypeEnum.BESS_BLOCK]: 2,
}

// Custom sort order for menu items (lower number = appears earlier)
const DEVICE_TYPE_MENU_ORDER: Record<number, number> = {
  [DeviceTypeEnum.PV_FEEDER]: 1,
  [DeviceTypeEnum.PV_INVERTER]: 2,
  [DeviceTypeEnum.PV_DC_COMBINER]: 3,
  [DeviceTypeEnum.TRACKER_ROW]: 4,
  [DeviceTypeEnum.BESS_PCS]: 5,
  [DeviceTypeEnum.BESS_STRING]: 6,
  [DeviceTypeEnum.BESS_BLOCK]: 7,
  [DeviceTypeEnum.MET_STATION]: 8,
}

const withCurrentDayTab = (path: string) => `${path}?tab=current-day`
const withRealtimeTab = (path: string) => `${path}?tab=realtime`

const generatePerformanceLinks = (
  projectId: string,
  usedDeviceTypeIds: number[] | undefined,
  deviceTypes: DeviceTypeData[] | undefined,
  isSuperadmin: boolean = false,
): links.Link[] => {
  // Always include System
  const performanceLinks: links.Link[] = [
    {
      to: withCurrentDayTab(`/projects/${projectId}/equipment-analysis/system`),
      label: 'System',
    },
  ]

  if (!usedDeviceTypeIds || !deviceTypes || usedDeviceTypeIds.length === 0) {
    return performanceLinks
  }

  // Create a map of device_type_id to DeviceTypeData for quick lookup
  const deviceTypeMap = new Map(
    deviceTypes.map((dt) => [dt.device_type_id, dt]),
  )

  // Get device types that are used and have a corresponding tab
  const availableDeviceTypeIds = usedDeviceTypeIds.filter(
    (id) => DEVICE_TYPE_TO_TAB_MAP[id] !== undefined,
  )

  // Group device types by tab value, keeping only the highest priority one for each tab
  const tabToDeviceType = new Map<
    string,
    { deviceTypeId: number; deviceType: DeviceTypeData }
  >()

  availableDeviceTypeIds.forEach((deviceTypeId) => {
    const tabValue = DEVICE_TYPE_TO_TAB_MAP[deviceTypeId]
    const deviceType = deviceTypeMap.get(deviceTypeId)
    if (!tabValue || !deviceType) return

    const existing = tabToDeviceType.get(tabValue)
    if (!existing) {
      tabToDeviceType.set(tabValue, { deviceTypeId, deviceType })
    } else {
      // If multiple device types map to same tab, use priority to decide
      const existingPriority =
        DEVICE_TYPE_PRIORITY[existing.deviceTypeId] ?? 999
      const currentPriority = DEVICE_TYPE_PRIORITY[deviceTypeId] ?? 999
      if (currentPriority < existingPriority) {
        tabToDeviceType.set(tabValue, { deviceTypeId, deviceType })
      }
    }
  })

  // Convert to array and sort by custom menu order, then by device_type_id
  const deviceTypesForTabs = Array.from(tabToDeviceType.values()).sort(
    (a, b) => {
      const orderA = DEVICE_TYPE_MENU_ORDER[a.deviceTypeId] ?? 999
      const orderB = DEVICE_TYPE_MENU_ORDER[b.deviceTypeId] ?? 999
      if (orderA !== orderB) {
        return orderA - orderB
      }
      // Fallback to device_type_id if not in menu order
      return a.deviceTypeId - b.deviceTypeId
    },
  )

  // Add links for each available device type
  deviceTypesForTabs.forEach(({ deviceType }) => {
    const tabValue = DEVICE_TYPE_TO_TAB_MAP[deviceType.device_type_id]
    if (tabValue) {
      // Filter PV Circuit for non-superadmins
      if (
        deviceType.device_type_id === DeviceTypeEnum.PV_FEEDER &&
        !isSuperadmin
      ) {
        return
      }

      const link: links.Link = {
        to:
          deviceType.device_type_id === DeviceTypeEnum.BESS_PCS
            ? withRealtimeTab(
                `/projects/${projectId}/equipment-analysis/${tabValue}`,
              )
            : withCurrentDayTab(
                `/projects/${projectId}/equipment-analysis/${tabValue}`,
              ),
        label: deviceType.name_long,
      }

      // Add tooltip for PV Circuit
      if (deviceType.device_type_id === DeviceTypeEnum.PV_FEEDER) {
        link.tooltip =
          'This page (and tooltip) is currently only visible to superadmins'
      }

      performanceLinks.push(link)
    }
  })

  return performanceLinks
}

const generateLinksGroup = (
  links: links.DropdownLink[],
  demo: boolean = false,
  projectId: string,
  collapsed: boolean,
  onExpandNavbar?: () => void,
) => {
  const processedLinks = links
    .filter((link) => !link.underDevelopment || demo)
    .map((link) => {
      // If link.to is a function, call it to ensure the result is a string
      const processedTo =
        typeof link.to === 'function' ? link.to(projectId) : link.to

      const processedDropdownLinks = link.links
        ? link.links
            .filter((dropdown) => !dropdown.underDevelopment || demo)
            .map((dropdown) => ({
              ...dropdown,
              // Ensure to is a string for dropdown links as well
              to:
                typeof dropdown.to === 'function'
                  ? dropdown.to(projectId)
                  : dropdown.to,
            }))
        : undefined

      return {
        ...link,
        to: processedTo,
        links: processedDropdownLinks,
      }
    })

  return processedLinks.map((link) => (
    <LinksGroup
      {...link}
      key={link.label}
      links={link.links?.map((dropdownLink) => ({
        label: dropdownLink.label,
        to: dropdownLink.to,
        underDevelopment: dropdownLink.underDevelopment ?? false,
        tooltip: dropdownLink.tooltip,
      }))}
      collapsed={collapsed}
      onExpandNavbar={onExpandNavbar}
    />
  ))
}

export function NavbarNested({
  collapsed,
  onExpandNavbar,
}: {
  collapsed: boolean
  onExpandNavbar?: () => void
}) {
  const [modalOpened, { open, close }] = useDisclosure(false)
  const location = useLocation()
  const { projectId } = useParams<{ projectId: string }>()
  const { user, isLoaded } = useUser()
  const userType = useGetUserType({})

  const project = useSelectProject(projectId!)
  const qseAccess = useGetQSEAccess({
    pathParams: { projectId: projectId! },
    queryOptions: { enabled: !!projectId },
  })
  const hasQSEAccess = qseAccess.data?.has_access === true
  const { data: integrations } = useGetDroneIntegrations()
  const { data: dronePermissions } = useGetDronePermissions()
  const self = useGetUserSelf({})
  const deviceTypes = useGetDeviceTypes({})

  const hasDroneIntegration = useMemo(() => {
    if (!project.data || !dronePermissions || !self.data || !integrations) {
      return false
    }

    const projectTypeId = project.data.project_type_id
    // Drone inspections are only available for PV and PV_BESS projects, not for BESS-only projects
    if (projectTypeId === ProjectTypeEnum.BESS) {
      return false
    }
    if (
      projectTypeId !== ProjectTypeEnum.PV &&
      projectTypeId !== ProjectTypeEnum.PVS
    ) {
      return false
    }

    const companyId = self.data.company_id
    if (!companyId) {
      return false
    }

    return dronePermissions.some(
      (p: DronePermission) =>
        p.company_id === companyId &&
        integrations.some(
          (i: DroneIntegration) =>
            i.drone_integration_id === p.drone_integration_id &&
            i.project_id === project.data?.project_id &&
            p.can_view,
        ),
    )
  }, [project.data, dronePermissions, self.data, integrations])

  // Generate Performance links dynamically based on project's used_device_type_ids
  // This must be called before any early returns to maintain hook order
  const performanceLinks = useMemo(() => {
    if (!project.data || !deviceTypes.data || !projectId) {
      return []
    }
    const usedDeviceTypeIds = project.data.spec?.used_device_type_ids
    const isSuperadmin = userType.data?.user_type_id === UserTypeEnum.SUPERADMIN
    return generatePerformanceLinks(
      projectId,
      usedDeviceTypeIds,
      deviceTypes.data,
      isSuperadmin,
    )
  }, [project.data, deviceTypes.data, projectId, userType.data])

  if (!isLoaded || !user || userType.isLoading) {
    return null
  }

  // Check if "development" is in the pathname
  const isDevelopmentPath = location.pathname.includes('development')

  // Check if we are on the project home page
  const isProjectHomePage = location.pathname === `/projects/${projectId}`

  const demo =
    typeof user.publicMetadata.demo === 'boolean'
      ? user.publicMetadata.demo
      : false

  const userIsSuperadmin =
    userType.data?.user_type_id === UserTypeEnum.SUPERADMIN

  // Remove unnecessary links based on project characteristics
  const removePVLinks = project.data?.project_type_id === ProjectTypeEnum.BESS
  const removeMetStationsLinks = !project.data?.has_met_stations
  const removePVDCCombinerLinks = !project.data?.has_pv_dc_combiners
  const removeTrackersLinks = !project.data?.has_trackers
  const removeBESSBlocksLinks = !project.data?.has_bess_blocks
  const removeBESSEnclosuresLinks = !project.data?.has_bess_enclosures
  const removeBESSPCSLinks = !project.data?.has_bess_pcss
  const removeBESSLinks =
    removeBESSBlocksLinks && removeBESSEnclosuresLinks && removeBESSPCSLinks
  const removeRealTimeDataLinks = !project.data?.has_real_time_data
  const removeReportIntegrationLinks = !project.data?.has_report_integration

  // Replace Performance link with dynamically generated one
  // Set StackTrace route based on project type
  let projectLinks = links.projectLinks.map((link) => {
    if (link.label === 'Performance') {
      return {
        ...link,
        links: performanceLinks,
      }
    }
    if (link.label === 'StackTrace' && project.data) {
      const projectTypeId = project.data.project_type_id
      const stackTracePath =
        projectTypeId === ProjectTypeEnum.BESS
          ? `/projects/${projectId}/device-details/horizontal/bess`
          : `/projects/${projectId}/device-details/horizontal/pv`
      return {
        ...link,
        to: stackTracePath,
        label:
          projectTypeId === ProjectTypeEnum.PVS
            ? 'StackTrace (PV)'
            : 'StackTrace',
      }
    }
    return link
  })

  projectLinks = projectLinks
    .map((link) => {
      // child‑level filtering
      const filteredChildren = link.links?.filter(
        (dropdownLink) =>
          // Remove PV links if necessary
          !(dropdownLink.requiresPV && removePVLinks) &&
          // Remove BESS links if necessary
          !(dropdownLink.requiresBESS && removeBESSLinks) &&
          // Remove Met Station links if necessary
          !(dropdownLink.requiresMetStations && removeMetStationsLinks) &&
          // Remove DC Combiner links if necessary
          !(dropdownLink.requiresPVDCCombiners && removePVDCCombinerLinks) &&
          // Remove Trackers links if necessary
          !(dropdownLink.requiresTrackers && removeTrackersLinks) &&
          // Remove BESS Block links if necessary
          !(dropdownLink.requiresBESSBlocks && removeBESSBlocksLinks) &&
          // Remove BESS Enclosure links if necessary
          !(dropdownLink.requiresBESSEnclosures && removeBESSEnclosuresLinks) &&
          // Remove BESS PCS links if necessary
          !(dropdownLink.requiresBESSPCSs && removeBESSPCSLinks) &&
          // Remove Real Time Data links if necessary
          !(dropdownLink.requiresRealTimeData && removeRealTimeDataLinks) &&
          // Remove Report Integration links if necessary
          !(
            dropdownLink.requiresReportIntegration &&
            removeReportIntegrationLinks
          ) &&
          // Remove Drone Integration links if necessary
          !(dropdownLink.requiresDroneIntegration && !hasDroneIntegration) &&
          // Remove links by user type (nested link)
          !(
            dropdownLink.userTypeRequired === 'superadmin' &&
            userType.data?.name_short !== 'superadmin'
          ) &&
          !(
            dropdownLink.userTypeRequired === 'admin' &&
            !['admin', 'superadmin'].includes(userType.data?.name_short ?? '')
          ),
      )

      return { ...link, links: filteredChildren }
    })
    // parent‑level filtering
    .filter((link) => {
      // keep everything that never was a dropdown
      if (!Array.isArray(link.links)) return true

      // for arrow‑only groups, keep them even if
      // children were stripped, because the parent still navigates
      if (
        link.dropdownBehavior === 'arrow-only' &&
        typeof link.to === 'string'
      ) {
        return true
      }

      // drop dropdowns whose children were all removed
      return link.links.length > 0
    })
  // ==============================================================

  // Remove project links that require integrations that the project does not have
  projectLinks = projectLinks.filter(
    (link) =>
      !(
        link.requiresEventIntegration && !project.data?.has_event_integration
      ) &&
      !(
        link.requiresReportIntegration && !project.data?.has_report_integration
      ) &&
      !(link.requiresRealTimeData && !project.data?.has_real_time_data) &&
      !(
        link.requiresPV &&
        project.data?.project_type_id === ProjectTypeEnum.BESS
      ) &&
      !(link.requiresQSEIntegration && !hasQSEAccess),
  )

  // Remove links based on user type
  if (userType.data?.name_short === 'user') {
    projectLinks = projectLinks.filter(
      (link) =>
        !(
          link.userTypeRequired === 'admin' ||
          link.userTypeRequired === 'superadmin'
        ),
    )
  }

  // Remove links based on user type
  if (userType.data?.name_short === 'admin') {
    projectLinks = projectLinks.filter(
      (link) => !(link.userTypeRequired === 'superadmin'),
    )
  }

  return (
    <AppShell.Navbar
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
      }}
    >
      <>
        {!isDevelopmentPath && projectId && project.data && (
          <AppShell.Section>
            <ProjectPicture
              project={project.data}
              showText={!isProjectHomePage}
              collapsed={collapsed}
            />
          </AppShell.Section>
        )}

        <AppShell.Section component={ScrollArea} grow>
          <Stack pb="md" gap={0}>
            {!isDevelopmentPath && (
              <>
                {projectId && project.data && (
                  <>
                    <Divider label="Project" labelPosition="center" />
                    <HomeLinkWithDashboards collapsed={collapsed} />
                    <>
                      {generateLinksGroup(
                        projectLinks,
                        demo,
                        projectId,
                        collapsed,
                        onExpandNavbar,
                      )}
                    </>
                  </>
                )}
                <Divider label="Portfolio" labelPosition="center" pt={0} />
                {generateLinksGroup(
                  links.portfolioLinks,
                  demo,
                  projectId || '',
                  collapsed,
                  onExpandNavbar,
                )}
              </>
            )}
            {isDevelopmentPath && (
              <>
                <Divider label="Development" labelPosition="center" />
                {generateLinksGroup(
                  links.developmentLinks,
                  demo,
                  projectId || '',
                  collapsed,
                  onExpandNavbar,
                )}
              </>
            )}
          </Stack>
        </AppShell.Section>
      </>

      <AppShell.Section>
        <Stack pb="md" gap={0}>
          {userIsSuperadmin && (
            <>
              <Divider mt="0.375rem" mb="0.375rem" />
              <LinksGroup
                {...(isDevelopmentPath
                  ? {
                      to: '/portfolio/list',
                      label: 'Operational',
                      icon: IconArrowBackUp,
                    }
                  : {
                      to: '/development',
                      label: 'Development',
                      icon: IconArrowBackUp,
                    })}
                collapsed={collapsed}
              />
            </>
          )}
          <Divider mt="0.375rem" />
          {collapsed ? (
            <Tooltip label="Feedback" position="right" withArrow>
              <Center>
                <ActionIcon
                  mx="md"
                  mt="md"
                  variant="filled"
                  aria-label="Settings"
                  size={30}
                  onClick={open}
                >
                  <IconMessageChatbot
                    style={{ width: rem(18), height: rem(18) }}
                    stroke={1.5}
                  />
                </ActionIcon>
              </Center>
            </Tooltip>
          ) : (
            <Button mx="md" mt="md" variant="filled" onClick={open}>
              Feedback
            </Button>
          )}
          <Modal opened={modalOpened} onClose={close} title="Feedback" centered>
            <FeedbackForm userId={user.id} close={close} />
          </Modal>
          <PoweredBy collapsed={collapsed} />
        </Stack>
      </AppShell.Section>
    </AppShell.Navbar>
  )
}

const PoweredBy = ({ collapsed }: { collapsed: boolean }) => {
  const { user } = useUser()
  const computedColorScheme = useComputedColorScheme()
  const logoFilename =
    computedColorScheme === 'dark'
      ? 'logo_color_inverse_one_line.svg'
      : 'logo_color_one_line.svg'

  if (user) {
    if (user.publicMetadata.parent_company) {
      if (collapsed) {
        return null
      }
      return (
        <>
          <Divider mt="md" />
          <Group w="100%" mt="md" gap={3} justify="center">
            <Text fz="sm" ta="center">
              Powered by
            </Text>
            <Image
              src={getCompanyLogoUrl(logoFilename)}
              alt="Proximal Energy"
              style={{ width: '60%' }} // Ensures the image respects the width
            />
          </Group>
        </>
      )
    }
  }
}

const FeedbackForm = ({
  userId,
  close,
}: {
  userId: string
  close: () => void
}) => {
  const [file, setFile] = useState<FileWithPath | null>(null)
  const location = useLocation()
  const mutation = useCreateFeedbackMutation()
  const MAX_CHARS_SUBJECT = 100
  const MAX_CHARS_COMMENT = 250

  const form = useForm<types.FeedbackFormData>({
    validateInputOnChange: true,
    initialValues: {
      subject: '',
      url: location.pathname + location.search,
      comment: '',
    },
    validate: {
      subject: (value) =>
        value.length === 0
          ? 'Subject is required'
          : value.length > MAX_CHARS_SUBJECT
            ? `Subject must be ${MAX_CHARS_SUBJECT} characters or less (currently ${value.length})`
            : undefined,
      comment: (value) =>
        value.length === 0
          ? 'Comment is required'
          : value.length > MAX_CHARS_COMMENT
            ? `Comment must be ${MAX_CHARS_COMMENT} characters or less (currently ${value.length})`
            : undefined,
    },
  })

  const handleRemoveFile = () => {
    setFile(null)
  }

  const handleNavbarNestedDrop = (acceptedFiles: FileWithPath[]) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      const file = acceptedFiles[0]
      setFile(file)
    }
  }

  let preview = null
  if (file) {
    const imageUrl = URL.createObjectURL(file)
    preview = (
      <div style={{ position: 'relative' }}>
        <Image
          src={imageUrl}
          onLoad={() => URL.revokeObjectURL(imageUrl)}
          alt="Screenshot"
          p="sm"
        />
        <ActionIcon
          variant="default"
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            cursor: 'pointer',
            borderRadius: '50%',
          }}
        >
          <IconX size={18} onClick={() => handleRemoveFile()} />
        </ActionIcon>
      </div>
    )
  }

  const { user } = useUser()

  const handleNavbarNestedSubmit = async (values: types.FeedbackFormData) => {
    const formData = new FormData()

    formData.append('user_id', userId)
    formData.append('subject', values.subject)
    formData.append('url', values.url)
    formData.append('comment', values.comment)
    if (file) {
      formData.append('screenshot', file)
    }
    if (user && user.primaryEmailAddress) {
      formData.append('email', user.primaryEmailAddress.emailAddress)
    }

    mutation.mutate(formData)
  }

  if (mutation.isSuccess) {
    return (
      <Stack gap="md">
        <Text>Thank you for your feedback!</Text>
        <Button onClick={close} variant="default">
          Close
        </Button>
      </Stack>
    )
  }

  return (
    <form onSubmit={form.onSubmit(handleNavbarNestedSubmit)}>
      <Stack gap="md">
        <TextInput
          withAsterisk
          label="Subject"
          placeholder="Subject"
          {...form.getInputProps('subject')}
        />
        <TextInput
          label="URL"
          placeholder="URL"
          {...form.getInputProps('url')}
        />
        <Textarea
          withAsterisk
          label="Comment"
          placeholder="Comment"
          {...form.getInputProps('comment')}
        />
        {file === null && (
          <Dropzone
            onDrop={handleNavbarNestedDrop}
            maxFiles={1}
            maxSize={500 * 1024}
            multiple={false}
            accept={IMAGE_MIME_TYPE}
            acceptColor="green"
          >
            <Text inline>Have a screenshot?</Text>
            <Text size="sm" c="dimmed" inline mt={7}>
              Drag image here or click to select a file. File cannot exceed
              500KB.
            </Text>
          </Dropzone>
        )}
        {preview}
        <Button loading={mutation.isPending} type="submit" variant="default">
          Submit Feedback
        </Button>
        {mutation.isError && (
          <Text c="red" size="sm">
            An error occurred. Please try again. If the problem persists,
            contact support.
          </Text>
        )}
        <Text size="sm">
          Want to talk? Email us at{' '}
          <a href="mailto:support@proximal.energy" style={{ color: 'inherit' }}>
            support@proximal.energy
          </a>
          .
        </Text>
      </Stack>
    </form>
  )
}

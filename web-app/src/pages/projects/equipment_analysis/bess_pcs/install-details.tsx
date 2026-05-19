import { type OMContractorScope } from '@/api/v1/operational/project/om_contractors'
import {
  getProjectInfoTabPath,
  getProjectOMContractorsTabPath,
} from '@/pages/projects/project-settings-paths'
import { ActionIcon, Group, Stack, Text } from '@mantine/core'
import { IconEdit } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { Link } from 'react-router'

type InstallDetailsProps = {
  projectId?: string
  isAdmin: boolean
  placedInServiceDate?: string | null
  epcContractor: OMContractorScope | null
  isContractorLoading: boolean
}

const linkStyle = {
  textDecoration: 'none',
  color: 'inherit',
}

export function InstallDetails({
  projectId,
  isAdmin,
  placedInServiceDate,
  epcContractor,
  isContractorLoading,
}: InstallDetailsProps) {
  const projectInfoPath = getProjectInfoTabPath(projectId)
  const omContractorsPath = getProjectOMContractorsTabPath(projectId)
  const epcCompanyName =
    epcContractor?.company_name_long ||
    epcContractor?.company_name_short ||
    'Unknown'

  return (
    <Stack gap="xs" align="flex-start">
      <Text size="md" fw={500}>
        Installed:
      </Text>

      <Group gap="xs" align="center">
        <Text size="sm" c="dimmed">
          Placed in Service:{' '}
          {placedInServiceDate ? (
            <Text component="span" fw={500}>
              {dayjs(placedInServiceDate).format('MMM D, YYYY')}
            </Text>
          ) : isAdmin ? (
            <Link to={projectInfoPath} style={linkStyle}>
              <Text component="span" fw={500} style={{ cursor: 'pointer' }}>
                Set
              </Text>
            </Link>
          ) : (
            <Text component="span" fw={500}>
              Not set
            </Text>
          )}
        </Text>

        {isAdmin && (
          <ActionIcon
            variant="transparent"
            size="sm"
            component={Link}
            to={projectInfoPath}
            style={{ cursor: 'pointer' }}
          >
            <IconEdit size={16} />
          </ActionIcon>
        )}
      </Group>

      <Group gap="xs" align="center">
        <Text size="sm" c="dimmed">
          EPC:{' '}
          {isContractorLoading ? (
            <Text component="span" fw={500}>
              Loading...
            </Text>
          ) : epcContractor ? (
            <Text component="span" fw={500}>
              {epcCompanyName}
            </Text>
          ) : isAdmin ? (
            <Link to={omContractorsPath} style={linkStyle}>
              <Text component="span" fw={500} style={{ cursor: 'pointer' }}>
                Set
              </Text>
            </Link>
          ) : (
            <Text component="span" fw={500}>
              Not set
            </Text>
          )}
        </Text>

        {isAdmin && (
          <ActionIcon
            variant="transparent"
            size="sm"
            component={Link}
            to={omContractorsPath}
            style={{ cursor: 'pointer' }}
          >
            <IconEdit size={16} />
          </ActionIcon>
        )}
      </Group>
    </Stack>
  )
}

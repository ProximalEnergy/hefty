import { type OMContractorScope } from '@/api/v1/operational/project/om_contractors'
import { ActionIcon, Group, Stack, Text } from '@mantine/core'
import { IconEdit, IconMail, IconPhone } from '@tabler/icons-react'
import { Link } from 'react-router'

type ServiceDetailsProps = {
  projectId?: string
  isAdmin: boolean
  serviceContractor: OMContractorScope | null
  isContractorLoading: boolean
}

const omContractorsTab = (projectId?: string) => {
  return projectId
    ? `/projects/${projectId}/settings?tab=om-contractors`
    : '/projects'
}

const linkStyle = {
  textDecoration: 'none',
  color: 'inherit',
}

export function ServiceDetails({
  projectId,
  isAdmin,
  serviceContractor,
  isContractorLoading,
}: ServiceDetailsProps) {
  const omContractorsPath = omContractorsTab(projectId)
  const companyName =
    serviceContractor?.company_name_long ||
    serviceContractor?.company_name_short

  return (
    <Stack gap="xs" align="flex-start">
      <Group gap="xs" align="center">
        <Text size="md" fw={500}>
          Service by:
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

      {isContractorLoading ? (
        <Text size="sm" c="dimmed">
          Loading...
        </Text>
      ) : serviceContractor?.contractor_addressee ? (
        <>
          <Text size="sm" c="dimmed">
            Name:{' '}
            <Text component="span" fw={500}>
              {serviceContractor.contractor_addressee}
              {companyName ? ` (${companyName})` : ''}
            </Text>
          </Text>

          {(serviceContractor.contractor_phone ||
            serviceContractor.contractor_email) && (
            <Group gap="xs" align="center">
              <Text size="sm" c="dimmed">
                Contact:
              </Text>

              {serviceContractor.contractor_phone && (
                <Group gap={4} align="center">
                  <IconPhone size={14} />
                  <Text size="sm" fw={500}>
                    {serviceContractor.contractor_phone}
                  </Text>
                </Group>
              )}

              {serviceContractor.contractor_email && (
                <Group gap={4} align="center">
                  <IconMail size={14} />
                  <Text size="sm" fw={500}>
                    {serviceContractor.contractor_email}
                  </Text>
                </Group>
              )}
            </Group>
          )}
        </>
      ) : (
        <Group gap="xs" align="center">
          <Text size="sm" c="dimmed" style={{ fontStyle: 'italic' }}>
            O&M provider scope not set
          </Text>

          {isAdmin && (
            <Link to={omContractorsPath} style={linkStyle}>
              <Text
                component="span"
                size="sm"
                fw={500}
                style={{ cursor: 'pointer' }}
              >
                Set
              </Text>
            </Link>
          )}
        </Group>
      )}
    </Stack>
  )
}

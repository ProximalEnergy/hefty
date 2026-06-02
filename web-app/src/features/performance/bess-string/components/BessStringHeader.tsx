import type { BessStringContext } from '@/features/performance/bess-string/hooks/use-bess-string-context'
import {
  ActionIcon,
  Box,
  Group,
  Image,
  Skeleton,
  Stack,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import {
  IconEdit,
  IconInfoCircle,
  IconMail,
  IconPhone,
} from '@tabler/icons-react'
import dayjs from 'dayjs'
import type { SyntheticEvent } from 'react'
import { useState } from 'react'
import { Link } from 'react-router'

import { BessStringHeaderModal } from '@/features/performance/bess-string/components/BessStringHeaderModal'

type BessStringHeaderProps = {
  context: BessStringContext
}

function formatNameplateValue(value: number | null) {
  return value !== null ? value.toFixed(2) : 'N/A'
}

function matchesBessStringAssetUrl(currentUrl: string, expectedUrl: string) {
  if (!expectedUrl) return false
  return currentUrl === expectedUrl || currentUrl.endsWith(expectedUrl)
}

export function BessStringHeader({ context }: BessStringHeaderProps) {
  const colorScheme = useComputedColorScheme()
  const [imageModalOpened, setImageModalOpened] = useState(false)

  const handleBessStringDeviceModelImageError = (
    event: SyntheticEvent<HTMLImageElement>,
  ) => {
    const target = event.currentTarget
    const shouldTryFallback =
      context.deviceModelImageFallbackUrl &&
      !matchesBessStringAssetUrl(
        target.src,
        context.deviceModelImageFallbackUrl,
      ) &&
      !matchesBessStringAssetUrl(target.src, context.deviceModelIconUrl)

    if (shouldTryFallback) {
      target.src = context.deviceModelImageFallbackUrl
      return
    }

    if (!matchesBessStringAssetUrl(target.src, context.deviceModelIconUrl)) {
      target.src = context.deviceModelIconUrl
    }
  }

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start">
        <Group gap="md" align="flex-start">
          {context.mostCommonDeviceModelId !== null ? (
            <>
              <Box
                w={100}
                h={100}
                style={{
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Image
                  src={context.deviceModelImageUrl}
                  alt={context.stringBrandModel || 'Device Model'}
                  w="100%"
                  h="100%"
                  fit="contain"
                  radius="md"
                  style={{ objectFit: 'contain', cursor: 'pointer' }}
                  onClick={() => setImageModalOpened(true)}
                  onError={handleBessStringDeviceModelImageError}
                />
              </Box>
              <BessStringHeaderModal
                opened={imageModalOpened}
                onClose={() => setImageModalOpened(false)}
                title={context.stringBrandModel || 'Device Model'}
                deviceModelImageUrl={context.deviceModelImageUrl}
                deviceModelImageFallbackUrl={
                  context.deviceModelImageFallbackUrl
                }
                onDeviceModelImageError={handleBessStringDeviceModelImageError}
                bessString={context.bessStringSpec}
                isLoading={context.bessStrings.isLoading}
                brand={context.headerDeviceModel?.brand ?? null}
                model={context.headerDeviceModel?.model ?? null}
                deviceCount={context.deviceCount}
                mwdcPerDevice={context.mwdcPerDevice}
                totalMWdc={context.totalMWdc}
                poiMwac={context.project?.poi ?? null}
              />
            </>
          ) : context.headerModelLoading ? (
            <Skeleton w={100} h={100} radius="md" />
          ) : (
            <Box
              w={100}
              h={100}
              style={{
                flexShrink: 0,
                padding: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Image
                src={context.deviceModelIconUrl}
                alt="BESS String Icon"
                w="100%"
                h="100%"
                fit="contain"
                radius="md"
                style={{
                  objectFit: 'contain',
                  filter:
                    colorScheme === 'dark' ? 'invert(1) brightness(0.7)' : '',
                }}
              />
            </Box>
          )}

          <Stack gap="xs">
            <Group gap="md">
              <Text
                fw={600}
                size="lg"
                style={{ cursor: 'pointer' }}
                onClick={() => setImageModalOpened(true)}
              >
                {context.headerModelLoading ? (
                  'Loading...'
                ) : context.stringBrandModel ? (
                  <>
                    {context.stringBrandModel}
                    <Text component="span" c="dimmed" fw={400} ml="xs" mr="xs">
                      (x {context.deviceCount})
                    </Text>
                    <ActionIcon
                      variant="transparent"
                      size="sm"
                      onClick={(event) => {
                        event.stopPropagation()
                        setImageModalOpened(true)
                      }}
                      style={{
                        display: 'inline-flex',
                        verticalAlign: 'middle',
                        cursor: 'pointer',
                      }}
                    >
                      <IconInfoCircle size={18} />
                    </ActionIcon>
                  </>
                ) : null}
              </Text>
            </Group>
            <Stack gap={2}>
              {context.nameplateLoading ? (
                <>
                  <Skeleton h={18} w={360} radius="sm" />
                  <Skeleton h={18} w={330} radius="sm" />
                </>
              ) : (
                <>
                  <Text size="sm" c="dimmed">
                    Power:{' '}
                    <Text component="span" fw={500}>
                      {formatNameplateValue(context.kwdcPerDevice)} kW DC
                    </Text>
                    {' - '}
                    Total{' '}
                    <Text component="span" fw={500}>
                      {formatNameplateValue(context.totalMWdc)} MW DC
                    </Text>
                    {context.project?.poi && (
                      <>
                        {' '}
                        <Text component="span" c="dimmed" size="xs">
                          (POI limit: {context.project.poi.toFixed(2)} MWac)
                        </Text>
                      </>
                    )}
                  </Text>
                  <Text size="sm" c="dimmed">
                    Energy:{' '}
                    <Text component="span" fw={500}>
                      {formatNameplateValue(context.kwhdcPerDevice)} kWh DC
                      nameplate
                    </Text>
                    {' - '}
                    Total{' '}
                    <Text component="span" fw={500}>
                      {formatNameplateValue(context.totalMWhdc)} MWh DC
                      nameplate
                    </Text>
                  </Text>
                </>
              )}
            </Stack>
          </Stack>
        </Group>

        <Group gap="xl" align="flex-start">
          <Stack gap="xs" align="flex-start">
            <Text size="md" fw={500}>
              Installed:
            </Text>
            <Group gap="xs" align="center">
              <Text size="sm" c="dimmed">
                Placed in Service:{' '}
                {context.projectQuery.isLoading ? (
                  <Text component="span" fw={500}>
                    Loading...
                  </Text>
                ) : context.project?.placed_in_service_date ? (
                  <Text component="span" fw={500}>
                    {dayjs(context.project.placed_in_service_date).format(
                      'MMM D, YYYY',
                    )}
                  </Text>
                ) : context.isAdmin ? (
                  <Link
                    to={`/projects/${context.projectId}/settings?tab=project-info`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Text
                      component="span"
                      fw={500}
                      style={{ cursor: 'pointer' }}
                    >
                      Set
                    </Text>
                  </Link>
                ) : (
                  <Text component="span" fw={500}>
                    Not set
                  </Text>
                )}
              </Text>
              {context.isAdmin && (
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  component={Link}
                  to={`/projects/${context.projectId}/settings?tab=project-info`}
                  style={{ cursor: 'pointer' }}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              )}
            </Group>
            <Group gap="xs" align="center">
              <Text size="sm" c="dimmed">
                EPC:{' '}
                {context.omContractorScopes.isLoading ? (
                  <Text component="span" fw={500}>
                    Loading...
                  </Text>
                ) : context.epcContractor ? (
                  <Text component="span" fw={500}>
                    {context.epcContractor.company_name_long ||
                      context.epcContractor.company_name_short ||
                      'Unknown'}
                  </Text>
                ) : context.isAdmin ? (
                  <Link
                    to={`/projects/${context.projectId}/settings?tab=om-contractors`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Text
                      component="span"
                      fw={500}
                      style={{ cursor: 'pointer' }}
                    >
                      Set
                    </Text>
                  </Link>
                ) : (
                  <Text component="span" fw={500}>
                    Not set
                  </Text>
                )}
              </Text>
              {context.isAdmin && (
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  component={Link}
                  to={`/projects/${context.projectId}/settings?tab=om-contractors`}
                  style={{ cursor: 'pointer' }}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              )}
            </Group>
          </Stack>

          <Stack gap="xs" align="flex-start">
            <Group gap="xs" align="center">
              <Text size="md" fw={500}>
                Service by:
              </Text>
              {context.isAdmin && (
                <ActionIcon
                  variant="transparent"
                  size="sm"
                  component={Link}
                  to={`/projects/${context.projectId}/settings?tab=om-contractors`}
                  style={{ cursor: 'pointer' }}
                >
                  <IconEdit size={16} />
                </ActionIcon>
              )}
            </Group>
            {context.omContractor?.contractor_addressee ? (
              <>
                <Text size="sm" c="dimmed">
                  Name:{' '}
                  <Text component="span" fw={500}>
                    {context.omContractor.contractor_addressee}
                    {context.omContractor.company_name_long ||
                    context.omContractor.company_name_short
                      ? ` (${
                          context.omContractor.company_name_long ||
                          context.omContractor.company_name_short
                        })`
                      : ''}
                  </Text>
                </Text>
                {(context.omContractor.contractor_phone ||
                  context.omContractor.contractor_email) && (
                  <Group gap="xs" align="center">
                    <Text size="sm" c="dimmed">
                      Contact:
                    </Text>
                    {context.omContractor.contractor_phone && (
                      <Group gap={4} align="center">
                        <IconPhone size={14} />
                        <Text size="sm" fw={500}>
                          {context.omContractor.contractor_phone}
                        </Text>
                      </Group>
                    )}
                    {context.omContractor.contractor_email && (
                      <Group gap={4} align="center">
                        <IconMail size={14} />
                        <Text size="sm" fw={500}>
                          {context.omContractor.contractor_email}
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
                {context.isAdmin && (
                  <Link
                    to={`/projects/${context.projectId}/settings?tab=om-contractors`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
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
        </Group>
      </Group>
    </Stack>
  )
}

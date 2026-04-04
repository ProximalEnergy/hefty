import {
  ActionIcon,
  Box,
  Group,
  Image,
  Modal,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  useComputedColorScheme,
} from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { useEffect, useState } from 'react'

export type EquipmentSummaryStat = {
  label: string
  value: string
  detail?: string
}

type EquipmentSummaryProps = {
  title: string
  countLabel?: string
  imageAlt: string
  imageSrc: string | null
  imageFallbackSrc: string | null
  imagePlaceholderSrc: string
  isLoadingImage: boolean
  stats: EquipmentSummaryStat[]
  modalStats: EquipmentSummaryStat[]
}

export function EquipmentSummary({
  title,
  countLabel,
  imageAlt,
  imageSrc,
  imageFallbackSrc,
  imagePlaceholderSrc,
  isLoadingImage,
  stats,
  modalStats,
}: EquipmentSummaryProps) {
  const colorScheme = useComputedColorScheme()
  const [imageModalOpened, setImageModalOpened] = useState(false)
  const [displaySrc, setDisplaySrc] = useState(imageSrc || imagePlaceholderSrc)

  useEffect(() => {
    setDisplaySrc(imageSrc || imagePlaceholderSrc)
  }, [imagePlaceholderSrc, imageSrc])

  const canOpenDetails = !!imageSrc || !!imageFallbackSrc

  const openDetails = () => {
    if (canOpenDetails) {
      setImageModalOpened(true)
    }
  }

  const handleImageError = () => {
    if (imageFallbackSrc && displaySrc !== imageFallbackSrc) {
      setDisplaySrc(imageFallbackSrc)
      return
    }

    if (displaySrc !== imagePlaceholderSrc) {
      setDisplaySrc(imagePlaceholderSrc)
    }
  }

  const imageFilter =
    displaySrc === imagePlaceholderSrc && colorScheme === 'dark'
      ? 'invert(1) brightness(0.7)'
      : 'none'

  return (
    <Group gap="md" align="flex-start">
      {isLoadingImage ? (
        <Skeleton w={100} h={100} radius="md" />
      ) : (
        <Box
          w={100}
          h={100}
          p={displaySrc === imagePlaceholderSrc ? 12 : 0}
          style={{
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Image
            src={displaySrc}
            alt={imageAlt}
            w="100%"
            h="100%"
            fit="contain"
            radius="md"
            style={{
              objectFit: 'contain',
              cursor: canOpenDetails ? 'pointer' : 'default',
              filter: imageFilter,
            }}
            onClick={openDetails}
            onError={handleImageError}
          />
        </Box>
      )}

      <Stack gap="xs" style={{ flex: 1, minWidth: 0 }}>
        <Group gap="md">
          <Text
            fw={600}
            size="lg"
            style={{ cursor: canOpenDetails ? 'pointer' : 'default' }}
            onClick={openDetails}
          >
            {title}
            {countLabel && (
              <Text component="span" c="dimmed" fw={400} ml="xs" mr="xs">
                ({countLabel})
              </Text>
            )}
          </Text>

          {canOpenDetails && (
            <ActionIcon
              variant="transparent"
              size="sm"
              onClick={(event) => {
                event.stopPropagation()
                openDetails()
              }}
              aria-label="Open equipment details"
            >
              <IconInfoCircle size={18} />
            </ActionIcon>
          )}
        </Group>

        <Box maw={520} w="100%">
          <SimpleGrid
            cols={{ base: 1, sm: 2 }}
            spacing="sm"
            verticalSpacing="xs"
          >
            {stats.map((stat) => (
              <Box key={stat.label} style={{ minWidth: 0 }}>
                <Text size="sm" c="dimmed">
                  {stat.label}:{' '}
                  <Text component="span" fw={500}>
                    {stat.value}
                  </Text>
                  {stat.detail && (
                    <Text component="span" c="dimmed" size="xs">
                      {' '}
                      ({stat.detail})
                    </Text>
                  )}
                </Text>
              </Box>
            ))}
          </SimpleGrid>
        </Box>
      </Stack>

      <Modal
        opened={imageModalOpened}
        onClose={() => setImageModalOpened(false)}
        title={title}
        size="lg"
        centered
      >
        <Stack gap="md">
          <Image
            src={displaySrc}
            alt={imageAlt}
            maw={280}
            mah={280}
            fit="contain"
            radius="md"
            mx="auto"
            style={{ filter: imageFilter }}
            onError={handleImageError}
          />

          {modalStats.length > 0 && (
            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="md">
              {modalStats.map((stat) => (
                <Text key={stat.label} size="sm" c="dimmed">
                  {stat.label}:{' '}
                  <Text component="span" fw={500}>
                    {stat.value}
                  </Text>
                  {stat.detail && (
                    <Text component="span" c="dimmed" size="xs">
                      {' '}
                      ({stat.detail})
                    </Text>
                  )}
                </Text>
              ))}
            </SimpleGrid>
          )}
        </Stack>
      </Modal>
    </Group>
  )
}

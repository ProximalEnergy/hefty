import {
  ActionIcon,
  Badge,
  Card,
  Group,
  HoverCard,
  Text,
  Tooltip,
} from '@mantine/core'
import { useFullscreenElement } from '@mantine/hooks'
import {
  IconArrowsMaximize,
  IconArrowsMinimize,
  IconChevronDown,
  IconChevronUp,
  IconInfoCircle,
} from '@tabler/icons-react'
import { useEffect, useState } from 'react'

export const iconSize = 20
export const iconStroke = 1.5

const CardTitle = ({
  beta,
  title,
  info,
  quality,
  toggle,
  fullscreen,
  showDownload,
  children,
  allowFullscreen,
  minimized,
  onMinimizeToggle,
  allowMinimize,
}: {
  beta?: boolean
  title?: React.ReactNode
  info?: React.ReactNode
  quality?: React.ReactNode
  toggle: () => void
  fullscreen: boolean
  showDownload?: boolean
  children?: React.ReactNode
  allowFullscreen?: boolean
  minimized?: boolean
  onMinimizeToggle?: () => void
  allowMinimize?: boolean
}) => {
  return (
    <Group justify="space-between" wrap="nowrap">
      <Group gap={3} wrap="nowrap">
        {beta && <Badge variant="filled">Beta</Badge>}
        {title && <span style={{ fontWeight: 500 }}>{title}</span>}
        {info && (
          <span onClick={(e) => e.stopPropagation()}>
            <HoverCard
              shadow="md"
              openDelay={200}
              closeDelay={100}
              width={420}
              withinPortal
            >
              <HoverCard.Target>
                <IconInfoCircle
                  size={iconSize}
                  stroke={iconStroke}
                  style={{ cursor: 'help', display: 'block' }}
                />
              </HoverCard.Target>
              <HoverCard.Dropdown maw={460} p="md">
                {typeof info === 'string' ? (
                  <Text size="sm" component="div">
                    {info}
                  </Text>
                ) : (
                  info
                )}
              </HoverCard.Dropdown>
            </HoverCard>
          </span>
        )}
        {quality}
      </Group>
      <Group style={{ flex: 1 }} />
      {children}
      <Group gap="xs" onClick={(e) => e.stopPropagation()}>
        {showDownload && (
          <ActionIcon>{/* <IconDownload onClick={download} /> */}</ActionIcon>
        )}
        {allowMinimize && onMinimizeToggle && (
          <Tooltip label={minimized ? 'Expand' : 'Minimize'}>
            <ActionIcon
              onClick={onMinimizeToggle}
              variant="transparent"
              color="text"
            >
              {minimized ? (
                <IconChevronUp size={iconSize} stroke={iconStroke} />
              ) : (
                <IconChevronDown size={iconSize} stroke={iconStroke} />
              )}
            </ActionIcon>
          </Tooltip>
        )}
        {allowFullscreen && (
          <Tooltip label={fullscreen ? 'Exit Fullscreen' : 'Enter Fullscreen'}>
            <ActionIcon onClick={toggle} variant="transparent" color="text">
              {fullscreen ? (
                <IconArrowsMinimize size={iconSize} stroke={iconStroke} />
              ) : (
                <IconArrowsMaximize size={iconSize} stroke={iconStroke} />
              )}
            </ActionIcon>
          </Tooltip>
        )}
      </Group>
    </Group>
  )
}

const CustomCard = ({
  beta,
  title,
  info,
  quality,
  showDownload,
  fill,
  style,
  header = true,
  headerChildren,
  children,
  allowFullscreen = true,
  hideBody = false,
  bodyStyle,
  allowMinimize = false,
  storageKey,
}: {
  beta?: boolean
  title?: React.ReactNode
  info?: React.ReactNode
  quality?: React.ReactNode
  showDownload?: boolean
  fill?: boolean
  style?: React.CSSProperties
  header?: boolean
  headerChildren?: React.ReactNode
  children: React.ReactNode
  allowFullscreen?: boolean
  hideBody?: boolean
  bodyStyle?: React.CSSProperties
  allowMinimize?: boolean
  storageKey?: string
}) => {
  const { ref, toggle, fullscreen } = useFullscreenElement()

  // Load minimized state from localStorage if storageKey is provided
  const getInitialMinimizedState = () => {
    if (!storageKey || !allowMinimize) return false
    try {
      const stored = localStorage.getItem(`card-minimized-${storageKey}`)
      return stored === 'true'
    } catch {
      return false
    }
  }

  const [minimized, setMinimized] = useState(getInitialMinimizedState)

  // Save minimized state to localStorage whenever it changes
  useEffect(() => {
    if (storageKey && allowMinimize) {
      try {
        localStorage.setItem(`card-minimized-${storageKey}`, String(minimized))
      } catch (error) {
        // Silently fail if localStorage is not available
        console.warn('Failed to save card state to localStorage:', error)
      }
    }
  }, [minimized, storageKey, allowMinimize])

  let padding: string | number = 'md'

  if (fill) {
    padding = 0
  }

  const isBodyHidden = hideBody || (allowMinimize && minimized)

  // When minimized, override height to auto so card only shows header
  // Extract height from style to prevent it from overriding when minimized
  const { height: _height, minHeight: _minHeight, ...restStyle } = style || {}
  const cardStyle: React.CSSProperties =
    isBodyHidden && allowMinimize
      ? {
          display: 'flex',
          flexDirection: 'column',
          height: 'auto',
          minHeight: 'auto',
          ...restStyle,
        }
      : {
          display: 'flex',
          flexDirection: 'column',
          ...style,
        }

  return (
    <Card withBorder radius="md" style={cardStyle} ref={ref}>
      {header && (
        <Card.Section
          withBorder
          inheritPadding
          py={5}
          style={{
            flexShrink: 0,
            cursor: allowMinimize ? 'pointer' : 'default',
          }}
          onClick={allowMinimize ? () => setMinimized(!minimized) : undefined}
        >
          <CardTitle
            beta={beta}
            title={title}
            info={info}
            quality={quality}
            toggle={toggle}
            fullscreen={fullscreen}
            showDownload={showDownload}
            allowFullscreen={allowFullscreen}
            minimized={minimized}
            onMinimizeToggle={() => setMinimized(!minimized)}
            allowMinimize={allowMinimize}
          >
            {headerChildren}
          </CardTitle>
        </Card.Section>
      )}
      {!isBodyHidden && (
        <Card.Section
          p={padding}
          style={{
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            ...bodyStyle,
          }}
        >
          {children}
        </Card.Section>
      )}
    </Card>
  )
}

export default CustomCard

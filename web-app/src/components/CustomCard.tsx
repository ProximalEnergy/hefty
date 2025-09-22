import {
  ActionIcon,
  Badge,
  Card,
  Group,
  HoverCard,
  Text,
  Tooltip,
} from '@mantine/core'
import { useFullscreen } from '@mantine/hooks'
import {
  IconArrowsMaximize,
  IconArrowsMinimize,
  IconInfoCircle,
} from '@tabler/icons-react'

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
}) => {
  return (
    <Group justify="apart">
      <Group gap={3}>
        {beta && <Badge variant="filled">Beta</Badge>}
        {title && <span style={{ fontWeight: 500 }}>{title}</span>}
        {info && (
          <HoverCard shadow="md">
            <HoverCard.Target>
              <IconInfoCircle size={iconSize} stroke={iconStroke} />
            </HoverCard.Target>
            <HoverCard.Dropdown maw="50%">
              <Text size="sm">{info}</Text>
            </HoverCard.Dropdown>
          </HoverCard>
        )}
        {quality}
      </Group>
      <Group style={{ flex: 1 }} />
      {children}
      <Group gap="xs">
        {showDownload && (
          <ActionIcon>{/* <IconDownload onClick={download} /> */}</ActionIcon>
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
}) => {
  const { ref, toggle, fullscreen } = useFullscreen()

  let padding: string | number = 'md'

  if (fill) {
    padding = 0
  }

  return (
    <Card
      withBorder
      radius="md"
      style={{
        display: 'flex',
        flexDirection: 'column',
        ...style,
      }}
      ref={ref}
    >
      {header && (
        <Card.Section withBorder inheritPadding py={5}>
          <CardTitle
            beta={beta}
            title={title}
            info={info}
            quality={quality}
            toggle={toggle}
            fullscreen={fullscreen}
            showDownload={showDownload}
            children={headerChildren}
            allowFullscreen={allowFullscreen}
          />
        </Card.Section>
      )}
      <Card.Section p={padding} style={{ height: '100%' }}>
        {children}
      </Card.Section>
    </Card>
  )
}

export default CustomCard

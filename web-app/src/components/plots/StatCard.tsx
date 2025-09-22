import { Quality } from '@/hooks/types'
import {
  Group,
  HoverCard,
  List,
  Paper,
  Space,
  Text,
  ThemeIcon,
  rem,
} from '@mantine/core'
import {
  IconCheck,
  IconExclamationMark,
  IconInfoCircle,
  IconLetterQ,
} from '@tabler/icons-react'

// Import the Quality type

const VALUE_FONT_SIZE = 42

interface StatCardProps {
  title: string
  info?: string
  value: number // Assuming value is a number
  prefix?: string
  suffix?: string
  unit?: string
  change?: number // Assuming change is a number
  icon?: React.ReactNode // Assuming icon is a React node
  quality?: Quality // Add the quality prop
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  info,
  value,
  prefix,
  suffix,
  unit,
  change,
  icon,
  quality, // Destructure the quality prop
}) => {
  const colorMap = {
    good: 'green',
    warning: 'yellow',
    bad: 'red',
  }

  const iconMap = {
    good: <IconCheck style={{ width: rem(16), height: rem(16) }} />,
    warning: (
      <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />
    ),
    bad: <IconExclamationMark style={{ width: rem(16), height: rem(16) }} />,
  }

  return (
    <Paper withBorder p="xs" radius="md">
      <Group justify="apart">
        <div>
          <Group gap={3}>
            <Text fz="sm">{title}</Text>
            {info && (
              <HoverCard shadow="md" width="50%">
                <HoverCard.Target>
                  <IconInfoCircle size={15} />
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text size="sm">{info}</Text>
                </HoverCard.Dropdown>
              </HoverCard>
            )}
            {quality && (
              <HoverCard shadow="md">
                <HoverCard.Target>
                  <ThemeIcon
                    color={colorMap[quality.level]}
                    size={20}
                    radius="xl"
                  >
                    <IconLetterQ style={{ width: rem(16), height: rem(16) }} />
                  </ThemeIcon>
                </HoverCard.Target>
                <HoverCard.Dropdown>
                  <Text>{quality.message}</Text>
                  <Space h="xs" />
                  <List spacing="xs" size="sm" center>
                    {quality.details.map((detail, i) => (
                      <List.Item
                        key={i}
                        icon={
                          <ThemeIcon
                            color={colorMap[detail.level]}
                            size={20}
                            radius="xl"
                          >
                            {iconMap[detail.level]}
                          </ThemeIcon>
                        }
                      >
                        {detail.message}
                      </List.Item>
                    ))}
                  </List>
                </HoverCard.Dropdown>
              </HoverCard>
            )}
          </Group>
          <Group
            gap={0}
            style={{
              alignItems: 'flex-end',
            }}
          >
            {prefix && (
              <Text fz={VALUE_FONT_SIZE} style={{ lineHeight: 1 }}>
                {prefix}
              </Text>
            )}
            <Text fz={VALUE_FONT_SIZE} style={{ lineHeight: 1 }}>
              {value.toLocaleString()}
            </Text>
            {suffix && (
              <Text fz={VALUE_FONT_SIZE} style={{ lineHeight: 1 }}>
                {suffix}
              </Text>
            )}
            {unit && (
              <Text fz="sm" style={{ paddingLeft: 3, lineHeight: 1 }}>
                {unit}
              </Text>
            )}
          </Group>
        </div>
        {icon && (
          <ThemeIcon color="gray" variant="light" size={38} radius="md">
            {icon}
          </ThemeIcon>
        )}
      </Group>
      {change && (
        <Text c="dimmed" fz="sm">
          <Text c={change > 0 ? 'teal' : 'red'} fw={700}>
            {change > 0 ? '+' : null}
            {change}%
          </Text>{' '}
          compared to yesterday
        </Text>
      )}
    </Paper>
  )
}

export default StatCard

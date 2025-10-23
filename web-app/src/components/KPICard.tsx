import { KPISummaryCard } from '@/api/v1/operational/project/kpi_data'
import {
  Group,
  HoverCard,
  Paper,
  Stack,
  Text,
  ThemeIcon,
  Tooltip,
  rem,
} from '@mantine/core'
import { IconEyeOff, IconInfoCircle } from '@tabler/icons-react'
import { Link } from 'react-router-dom'

const TEXT_SIZE_PRIMARY = 36
const TEXT_SIZE_SECONDARY = 24
const TEXT_SIZE_TERTIARY = 12

const KPICard: React.FC<KPISummaryCard> = ({
  title,
  info,
  value,
  prefix,
  unit,
  change,
  link,
  is_visible,
  onClick,
}) => {
  return (
    <Paper h="100%" withBorder p="xs" radius="md" onClick={onClick} miw={400}>
      <Stack justify="apart" gap={0}>
        <Group gap="xs" preventGrowOverflow={true} wrap="nowrap">
          {!is_visible && (
            <ThemeIcon color="gray" size={20} radius="xl">
              <IconEyeOff style={{ width: rem(16), height: rem(16) }} />
            </ThemeIcon>
          )}
          <Link to={link} style={{ color: 'inherit' }}>
            {' '}
            <Group maw={300}>
              <Tooltip label={title} position="bottom">
                <Text size="lg" style={{ fontWeight: 'bold' }} truncate="end">
                  {title}
                </Text>
              </Tooltip>{' '}
            </Group>
          </Link>
          {info && (
            <HoverCard shadow="md" styles={{ dropdown: { maxWidth: '33%' } }}>
              <HoverCard.Target>
                <IconInfoCircle size={15} />
              </HoverCard.Target>
              <HoverCard.Dropdown>
                <Text size="sm" component="div">
                  {info}
                </Text>
              </HoverCard.Dropdown>
            </HoverCard>
          )}
        </Group>

        <Group align="flex-end" gap="xs" justify="flex-start">
          <Stack justify="apart" gap={0}>
            <Group
              gap={unit === '%' || unit === 'deg' || unit === null ? 0 : 5}
              align="flex-end"
            >
              {(value || value === 0) && (
                <Text fz={TEXT_SIZE_PRIMARY} lh={1}>
                  {value === 0 || value === -0 ? '0' : value.toLocaleString()}
                </Text>
              )}
              {unit && (
                <Text fz={TEXT_SIZE_PRIMARY} lh={1} truncate="end" maw={120}>
                  {unit === 'deg' ? '°' : unit}
                </Text>
              )}
            </Group>
            {prefix && (
              <Text c="dimmed" fz={TEXT_SIZE_TERTIARY}>
                {prefix}
              </Text>
            )}
          </Stack>
          <Stack justify="flex-end" gap={0} align="flex-start">
            {(change || change === 0) && (
              <Text
                fz={TEXT_SIZE_SECONDARY}
                c={change >= 0 ? 'teal' : 'red'}
                lh={1}
                truncate="end"
                maw={150}
              >
                {change > 0 ? '+' : null}(
                {unit && unit !== '%'
                  ? `${change.toLocaleString()} ${unit}`
                  : `${change}%`}
                )
              </Text>
            )}
            {(change || change === 0) && (
              <Text c="dimmed" fz={TEXT_SIZE_TERTIARY}>
                Compared to prior day
              </Text>
            )}
          </Stack>
        </Group>
      </Stack>
    </Paper>
  )
}

// Empty KPI card for when data is loading
export const EmptyKPICard = () => {
  return (
    <KPICard
      title="Empty"
      value={1}
      prefix="Test"
      unit="Test"
      change={0}
      link=""
      is_visible={false}
      kpi_type_id={0}
      contract_id={null}
    />
  )
}

export default KPICard

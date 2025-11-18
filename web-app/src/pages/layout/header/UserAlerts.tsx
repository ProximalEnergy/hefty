import { useGetTriggeredKPIAlerts } from '@/hooks/api'
import {
  ActionIcon,
  Divider,
  Group,
  Indicator,
  Popover,
  Text,
} from '@mantine/core'
import { IconAlertTriangle, IconBell, IconSettings } from '@tabler/icons-react'
import cx from 'clsx'
import { useState } from 'react'
import { Link, useParams } from 'react-router'

import classes from './ThemeToggle.module.css'

const UserAlerts = () => {
  const { data } = useGetTriggeredKPIAlerts({})
  const [checked, setChecked] = useState<boolean>(false)
  const { projectId } = useParams<{ projectId?: string }>()

  const showIndicator = data?.length ? checked && data?.length > 0 : true
  const firstProjectId =
    projectId || (data && data.length > 0 ? data[0].project_id : null)

  return (
    <Group justify="center">
      <Popover position="bottom" withArrow shadow="md">
        <Popover.Target>
          <Indicator
            disabled={showIndicator}
            processing
            label={data?.length}
            size={16}
            color="red"
          >
            <ActionIcon
              variant="default"
              size="lg"
              aria-label="Toggle color scheme"
              onClick={() => setChecked(true)}
            >
              <IconBell
                className={cx(classes.icon, classes.light)}
                stroke={1.5}
              />
              <IconBell
                className={cx(classes.icon, classes.dark)}
                stroke={1.5}
              />
            </ActionIcon>
          </Indicator>
        </Popover.Target>
        <Popover.Dropdown>
          {Array.isArray(data) && data.length === 0 ? (
            <>
              <Text>No alerts at this time.</Text>
              {firstProjectId && (
                <>
                  <Divider my="xs" />
                  <Link
                    to={`/projects/${firstProjectId}/kpis/alerts`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Group gap="xs">
                      <IconSettings size={16} />
                      <Text size="sm">Set up alerts</Text>
                    </Group>
                  </Link>
                </>
              )}
            </>
          ) : (
            <>
              <Text>Triggered Alerts ({data?.length}):</Text>
              {data?.map((alert, index) => (
                <Group key={index} align="center">
                  <IconAlertTriangle size={20} />
                  <Link
                    key={index}
                    to={`projects/${alert.project_id}/kpis/type/${alert.kpi_type_id}`}
                  >
                    {alert.config.alert_name}
                  </Link>
                </Group>
              ))}
              {firstProjectId && (
                <>
                  <Divider my="xs" />
                  <Link
                    to={`/projects/${firstProjectId}/kpis/alerts`}
                    style={{ textDecoration: 'none', color: 'inherit' }}
                  >
                    <Group gap="xs">
                      <IconSettings size={16} />
                      <Text size="sm">Set up alerts</Text>
                    </Group>
                  </Link>
                </>
              )}
            </>
          )}
        </Popover.Dropdown>
      </Popover>
    </Group>
  )
}

export default UserAlerts

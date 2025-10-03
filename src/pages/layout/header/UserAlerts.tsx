import { useGetTriggeredKPIAlerts } from '@/hooks/api'
import { ActionIcon, Group, Indicator, Popover, Text } from '@mantine/core'
import { IconAlertTriangle, IconBell } from '@tabler/icons-react'
import cx from 'clsx'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import classes from './ThemeToggle.module.css'

const UserAlerts = () => {
  const { data } = useGetTriggeredKPIAlerts({})
  const [checked, setChecked] = useState<boolean>(false)

  const showIndicator = data?.length ? checked && data?.length > 0 : true
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
            <Text>No alerts at this time.</Text>
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
            </>
          )}
        </Popover.Dropdown>
      </Popover>
    </Group>
  )
}

export default UserAlerts

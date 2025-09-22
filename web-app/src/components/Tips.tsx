import { useLocalStorage } from '@mantine/hooks'
import { NotificationData, notifications } from '@mantine/notifications'
import { useEffect } from 'react'

type DefaultValue = {
  version: number | null
}

const keyPrefix = 'proximal-tips'

const useTips = ({
  key,
  currentVersion,
  notification,
}: {
  key: string
  currentVersion: number
  notification: NotificationData
}) => {
  const [hasVisited, setHasVisited] = useLocalStorage<DefaultValue>({
    key: `${keyPrefix}-${key}`,
    defaultValue: { version: null },
    getInitialValueInEffect: false,
  })

  useEffect(() => {
    if (hasVisited.version !== currentVersion) {
      notifications.show({ ...notification })
      setHasVisited({ version: currentVersion })
    }
  }, [hasVisited, setHasVisited, currentVersion, notification])
}

export const useTipsPCSGIS = () => {
  const id = 'pcs-gis'

  useTips({
    key: id,
    currentVersion: 2,
    notification: {
      id: id,
      title: 'PCS GIS',
      message:
        'You can view live power output or aggregated energy generation. By default, the map shows live power. Select a date range to view aggregated energy generation. Clear the date range to return to live power.',
      autoClose: false,
    },
  })
}

export const useTipsPersonalPortfolio = () => {
  const id = 'personal-portfolio'

  useTips({
    key: id,
    currentVersion: 1,
    notification: {
      id: id,
      message:
        'Customize visible projects by creating your own Personal Portfolio. Click on Application Settings under your profile to configure.',
      autoClose: false,
    },
  })
}

export const useTipsEventsTable = () => {
  const id = 'events-table'

  useTips({
    key: id,
    currentVersion: 1,
    notification: {
      id: id,
      title: 'Dynamic Events Table',
      message:
        "Click the 'Column Actions' buttons to change the grouping, filtering, and sorting of the table. Click the 'Show/Hide Columns' button to view total losses for each Event.",
      autoClose: false,
    },
  })
}

export const useTipsPortfolioKPIHome = () => {
  const id = 'portfolio-kpi-home'

  useTips({
    key: id,
    currentVersion: 1,
    notification: {
      id: id,
      title: 'Portfolio KPIs',
      message:
        "Click the arrows in any column to sort projects by KPI performance. Click any cell to navigate to the project's KPI details, or click a project name to navigate to its homepage.",
      autoClose: false,
    },
  })
}

export const clearTips = () => {
  Object.keys(localStorage).forEach((key) => {
    if (key.startsWith(keyPrefix)) {
      localStorage.removeItem(key)
    }
  })
}

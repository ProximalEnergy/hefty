import { Tabs as MantineTabs } from '@mantine/core'
import type { ReactNode } from 'react'

type PvInverterTabsProps = {
  value: string
  onChange: (value: string | null) => void
  isSuperadmin: boolean
  children: ReactNode
}

export function PvInverterTabs({
  value,
  onChange,
  isSuperadmin,
  children,
}: PvInverterTabsProps) {
  return (
    <MantineTabs
      value={value}
      onChange={onChange}
      variant="outline"
      keepMounted={false}
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        width: '100%',
      }}
    >
      <MantineTabs.List>
        <MantineTabs.Tab value="realtime">Real-time</MantineTabs.Tab>
        <MantineTabs.Tab value="current-day">Day View</MantineTabs.Tab>
        {isSuperadmin && (
          <MantineTabs.Tab value="long-term">Long Term</MantineTabs.Tab>
        )}
      </MantineTabs.List>
      <MantineTabs.Panel
        value={value}
        pt="md"
        style={{ flex: 1, minHeight: 0 }}
      >
        {children}
      </MantineTabs.Panel>
    </MantineTabs>
  )
}

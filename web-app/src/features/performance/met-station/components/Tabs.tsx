import { Tabs as MantineTabs } from '@mantine/core'
import type { ReactNode } from 'react'

type TabsProps = {
  value: string
  onChange: (value: string | null) => void
  isSuperadmin: boolean
  children: ReactNode
}

export function Tabs({ value, onChange, isSuperadmin, children }: TabsProps) {
  return (
    <MantineTabs
      value={value}
      onChange={onChange}
      h="100%"
      style={{
        display: 'flex',
        flex: 1,
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <MantineTabs.List>
        {isSuperadmin && (
          <MantineTabs.Tab value="realtime">Real Time</MantineTabs.Tab>
        )}
        <MantineTabs.Tab value="current-day">Day</MantineTabs.Tab>
        {isSuperadmin && (
          <MantineTabs.Tab value="long-term">Long Term</MantineTabs.Tab>
        )}
      </MantineTabs.List>
      <MantineTabs.Panel
        style={{ flex: 1, minHeight: 0 }}
        value={value}
        pt="md"
      >
        {children}
      </MantineTabs.Panel>
    </MantineTabs>
  )
}

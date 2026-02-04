// Wrapper component for metric cell content that optionally displays a file icon.
// Handles text truncation and proper alignment of icon and content.
import { IconFileText } from '@tabler/icons-react'
import { type ReactNode } from 'react'

type MetricCellWithIconProps = {
  children: ReactNode
  showIcon: boolean
}

const MetricCellWithIcon = ({
  children,
  showIcon,
}: MetricCellWithIconProps) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.25rem',
      minWidth: 0, // Allows text to truncate
    }}
  >
    {showIcon && (
      <div
        style={{
          flexShrink: 0,
          display: 'flex',
          alignItems: 'center',
          lineHeight: 0, // Prevents icon from adding extra height
        }}
      >
        <IconFileText size={16} />
      </div>
    )}
    <div
      style={{
        flex: 1,
        minWidth: 0,
        overflow: 'hidden',
      }}
    >
      {children}
    </div>
  </div>
)

export default MetricCellWithIcon

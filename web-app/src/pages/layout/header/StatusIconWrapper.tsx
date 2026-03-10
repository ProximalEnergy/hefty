import { Box, Text } from '@mantine/core'
import type { ReactNode } from 'react'

export const StatusIconWrapper = ({
  children,
  label,
  color,
}: {
  children: ReactNode
  label: string
  color: 'green' | 'yellow' | 'red'
}) => (
  <Box
    pos="relative"
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      height: 32,
    }}
  >
    {children}
    <Text
      fw={800}
      c={color}
      style={{
        position: 'absolute',
        bottom: -4,
        left: '50%',
        transform: 'translateX(-50%)',
        lineHeight: 1,
        fontSize: 7,
        letterSpacing: 0.3,
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
      }}
    >
      {label}
    </Text>
  </Box>
)

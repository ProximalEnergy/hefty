import { MantineLoaderComponent } from '@mantine/core'
import React, { forwardRef } from 'react'

export const HexLoaderInline: MantineLoaderComponent = forwardRef(
  ({ style, ...others }, ref) => (
    <svg
      {...others}
      ref={ref}
      style={
        {
          // Set default size relative to font size (slightly larger than line height)
          '--loader-size': '1.2em',
          // Ensure vertical alignment is good for inline use
          verticalAlign: 'middle',
          // Allow overriding size and color via props/style
          width: 'var(--loader-size)',
          height: 'var(--loader-size)',
          stroke: 'var(--loader-color, currentColor)', // Default stroke to text color if not set
          ...style, // Spread incoming style prop last to allow overrides
        } as React.CSSProperties
      }
      viewBox="-6 -6 112 112"
      xmlns="http://www.w3.org/2000/svg"
    >
      <polygon
        points="50,3 91,25 91,75 50,97 9,75 9,25"
        fill="none"
        strokeWidth="8"
      >
        <animateTransform
          attributeName="transform"
          type="rotate"
          from="0 50 50"
          to="360 50 50"
          dur="2s"
          repeatCount="indefinite"
        />
      </polygon>
    </svg>
  ),
)

import { MantineLoaderComponent } from '@mantine/core'
import { forwardRef } from 'react'

export const HexLoader: MantineLoaderComponent = forwardRef(
  ({ style, ...others }, ref) => (
    <svg
      {...others}
      ref={ref}
      style={{
        width: 'var(--loader-size)',
        height: 'var(--loader-size)',
        stroke: 'var(--loader-color)',
        ...style,
      }}
      viewBox="0 0 100 100"
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

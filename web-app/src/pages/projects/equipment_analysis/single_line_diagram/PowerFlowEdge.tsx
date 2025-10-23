import { useComputedColorScheme, useMantineTheme } from '@mantine/core'
import { EdgeProps, getStraightPath } from '@xyflow/react'
import React from 'react'

export const PowerFlowEdge = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style = {},
  data,
  markerEnd,
}: EdgeProps): React.JSX.Element => {
  const theme = useMantineTheme()
  const [edgePath] = getStraightPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  const [reversedEdgePath] = getStraightPath({
    sourceX: targetX,
    sourceY: targetY,
    targetX: sourceX,
    targetY: sourceY,
  })

  const computedColorScheme = useComputedColorScheme('light')
  const isDarkMode = computedColorScheme === 'dark'
  const strokeColor = isDarkMode ? theme.colors.dark[8] : theme.white

  // We can make the animation speed dependent on the power flow
  const duration =
    data && typeof data.power === 'number'
      ? `${Math.max(0.5, 5 / (Math.abs(data.power) / 1000 + 1))}s`
      : '2s'

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />
      {data?.isCharging ? (
        <g>
          <circle
            r="4"
            fill={theme.colors[theme.primaryColor][6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
          <circle
            r="4"
            fill={theme.colors[theme.primaryColor][6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              begin="1s"
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
          <circle
            r="4"
            fill={theme.colors[theme.primaryColor][6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              begin="2s"
              repeatCount="indefinite"
              path={edgePath}
            />
          </circle>
        </g>
      ) : null}
      {data?.isDischarging ? (
        <g>
          <circle
            r="4"
            fill={theme.colors.orange[6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              repeatCount="indefinite"
              path={reversedEdgePath}
            />
          </circle>
          <circle
            r="4"
            fill={theme.colors.orange[6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              begin="1s"
              repeatCount="indefinite"
              path={reversedEdgePath}
            />
          </circle>
          <circle
            r="4"
            fill={theme.colors.orange[6]}
            stroke={strokeColor}
            strokeWidth={0.5}
          >
            <animateMotion
              dur={duration}
              begin="2s"
              repeatCount="indefinite"
              path={reversedEdgePath}
            />
          </circle>
        </g>
      ) : null}
    </>
  )
}

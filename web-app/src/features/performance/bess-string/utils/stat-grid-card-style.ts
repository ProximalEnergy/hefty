import type { CSSProperties } from 'react'

/** Uniform stat tile height so the grid stays aligned (no wrap growth). */
const STAT_GRID_CARD_HEIGHT_PX = 120

export function statGridCardStyle(extra?: CSSProperties): CSSProperties {
  return {
    height: STAT_GRID_CARD_HEIGHT_PX,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    ...extra,
  }
}

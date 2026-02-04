// Filter component for the favorites column that allows users to toggle between showing all KPIs
// or only favorited KPIs. Displays a heart icon that changes opacity based on filter state.
import { Tooltip } from '@mantine/core'
import { IconHeartFilled } from '@tabler/icons-react'
import { type Column } from '@tanstack/react-table'

import type { EnrichedKPISummaryTableRow } from '../ProjectKPIHome'

type FavoriteFilterProps = {
  column: Column<EnrichedKPISummaryTableRow, unknown>
}

const FavoriteFilter = ({ column }: FavoriteFilterProps) => {
  // Decode: Convert [showFavorites, showNonFavorites] to favoritesButtonOn
  const filterValue = column.getFilterValue() as [boolean, boolean] | undefined
  const [showFavorites, showNonFavorites] = filterValue ?? [true, true]
  const favoritesButtonOn = showFavorites && !showNonFavorites

  // Encode: Convert favoritesButtonOn back to [showFavorites, showNonFavorites]
  const encodeFilter = (favoritesOn: boolean): [boolean, boolean] => {
    const showFavorites = true // Always true
    const showNonFavorites = !favoritesOn
    return [showFavorites, showNonFavorites]
  }

  // Color constants
  const HEART_COLOR = 'var(--mantine-color-red-6)'

  // Opacity values
  const OPACITY_ON = 1
  const OPACITY_OFF = 0.4

  // Toggle function
  const toggleFavorites = () => {
    column.setFilterValue(encodeFilter(!favoritesButtonOn))
  }

  return (
    <Tooltip label="Favorites only">
      <div
        onClick={toggleFavorites}
        style={{
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
        onMouseEnter={(e) => {
          const icon = e.currentTarget.querySelector('svg')
          if (icon) icon.style.opacity = OPACITY_ON.toString()
        }}
        onMouseLeave={(e) => {
          const icon = e.currentTarget.querySelector('svg')
          if (icon)
            icon.style.opacity = (
              favoritesButtonOn ? OPACITY_ON : OPACITY_OFF
            ).toString()
        }}
      >
        <IconHeartFilled
          size={14}
          style={{
            color: HEART_COLOR,
            opacity: favoritesButtonOn ? OPACITY_ON : OPACITY_OFF,
          }}
        />
      </div>
    </Tooltip>
  )
}

export default FavoriteFilter

// Interactive heart icon component that allows users to favorite or unfavorite a KPI.
// Displays a filled red heart when favorited, or an outline heart when not favorited.
import { ActionIcon, rem } from '@mantine/core'
import { IconHeart, IconHeartFilled } from '@tabler/icons-react'

type FavoriteHeartProps = {
  kpiTypeId: number
  isFavorite: boolean
  onToggle: (kpiTypeId: number, isFavorited: boolean) => void
}

const FavoriteHeart = ({
  kpiTypeId,
  isFavorite,
  onToggle,
}: FavoriteHeartProps) => {
  return (
    <ActionIcon
      variant="transparent"
      onClick={(e) => {
        e.stopPropagation()
        onToggle(kpiTypeId, !isFavorite)
      }}
      aria-label="Favorite KPI"
    >
      {isFavorite ? (
        <IconHeartFilled
          style={{ width: rem(16), height: rem(16) }}
          color="red"
        />
      ) : (
        <IconHeart style={{ width: rem(16), height: rem(16) }} />
      )}
    </ActionIcon>
  )
}

export default FavoriteHeart

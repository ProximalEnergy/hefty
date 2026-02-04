// Simple info icon component that displays a description in a hover card when the user hovers over it.
// Used in column headers to provide additional context.
import { HoverCard, Text } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

type SimpleInfoHoverCardProps = {
  description: string
}

const SimpleInfoHoverCard = ({ description }: SimpleInfoHoverCardProps) => {
  return (
    <HoverCard shadow="md" withArrow>
      <HoverCard.Target>
        <IconInfoCircle
          size={14}
          stroke={1.5}
          style={{ display: 'block', cursor: 'help' }}
        />
      </HoverCard.Target>
      <HoverCard.Dropdown maw={300}>
        <Text
          size="xs"
          style={{ whiteSpace: 'normal', wordWrap: 'break-word' }}
        >
          {description}
        </Text>
      </HoverCard.Dropdown>
    </HoverCard>
  )
}

export default SimpleInfoHoverCard

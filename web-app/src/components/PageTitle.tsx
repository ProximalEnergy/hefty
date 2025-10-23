import { Group, HoverCard, Text, Title } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'
import { ComponentPropsWithoutRef, ReactNode } from 'react'

type PageTitleProps = {
  children: ReactNode
  order?: number
  lh?: number
  info?: ReactNode
} & ComponentPropsWithoutRef<typeof Title>

const iconSize = 20
const iconStroke = 1.5

/**
 * PageTitle component
 *
 * A wrapper around Mantine's Title component that provides consistent styling for page titles.
 */
export const PageTitle = ({
  children,
  order = 1,
  lh = 1,
  info,
  ...props
}: PageTitleProps) => {
  return (
    <Group gap="xs">
      <Title order={order} lh={lh} {...props}>
        {children}
      </Title>
      {info && (
        <HoverCard shadow="md">
          <HoverCard.Target>
            <IconInfoCircle size={iconSize} stroke={iconStroke} />
          </HoverCard.Target>
          <HoverCard.Dropdown maw="50%">
            <Text size="sm" component="div">
              {info}
            </Text>
          </HoverCard.Dropdown>
        </HoverCard>
      )}
    </Group>
  )
}

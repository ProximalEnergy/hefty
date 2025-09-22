import { ActionIcon } from '@mantine/core'
import { HoverCard, Text } from '@mantine/core'
import { IconBook } from '@tabler/icons-react'

const DocsButton = ({
  href,
  dropdownText,
}: {
  href: string
  dropdownText?: string
}) => {
  return (
    <>
      {dropdownText && (
        <HoverCard>
          <HoverCard.Target>
            <ActionIcon
              size="lg"
              onClick={() => {
                window.open(href, '_blank')
              }}
            >
              <IconBook />
            </ActionIcon>
          </HoverCard.Target>
          <HoverCard.Dropdown>
            <Text>{dropdownText}</Text>
          </HoverCard.Dropdown>
        </HoverCard>
      )}
      {!dropdownText && (
        <ActionIcon
          size="lg"
          onClick={() => {
            window.open(href, '_blank')
          }}
        >
          <IconBook />
        </ActionIcon>
      )}
    </>
  )
}

export default DocsButton

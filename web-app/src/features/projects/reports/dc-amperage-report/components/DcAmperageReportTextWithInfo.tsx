import { Group, HoverCard, Stack, Text, TextProps } from '@mantine/core'
import { IconInfoCircle } from '@tabler/icons-react'

type DcAmperageReportTextWithInfoProps = {
  text: string
  textProps?: TextProps
  subText?: string
  subTextProps?: TextProps
  info: string
  infoProps?: TextProps
}

export function DcAmperageReportTextWithInfo({
  text,
  textProps,
  subText,
  subTextProps,
  info,
  infoProps,
}: DcAmperageReportTextWithInfoProps) {
  return (
    <Stack gap={0}>
      <Group>
        <Text {...textProps}>{text}</Text>
        <HoverCard>
          <HoverCard.Target>
            <IconInfoCircle size={16} />
          </HoverCard.Target>
          <HoverCard.Dropdown maw={600}>
            <Text {...infoProps}>{info}</Text>
          </HoverCard.Dropdown>
        </HoverCard>
      </Group>
      {subText && <Text {...subTextProps}>{subText}</Text>}
    </Stack>
  )
}

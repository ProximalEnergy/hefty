import { ActionIcon, Group, Popover, Text } from '@mantine/core'
import { DatePicker, TimeInput } from '@mantine/dates'
import { IconCalendar } from '@tabler/icons-react'
import dayjs from 'dayjs'
import { useState } from 'react'

export function TimestampPicker({
  value,
  onChange,
  minDate,
  maxDate,
  timezone,
}: {
  value: Date
  onChange: (value: Date) => void
  minDate?: Date
  maxDate?: Date
  timezone?: string
}) {
  const [popoverOpened, setPopoverOpened] = useState(false)
  const dayjsValue = dayjs(value).tz(timezone)

  const handleDateChange = (date: Date | null) => {
    if (date) {
      const newDateTime = dayjs(date)
        .hour(dayjsValue.hour())
        .minute(dayjsValue.minute())
        .second(0)
        .millisecond(0)
      onChange(newDateTime.toDate())
    }
    setPopoverOpened(false)
  }

  const handleTimeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const [hours, minutes] = e.target.value.split(':')
    const newDateTime = dayjsValue
      .hour(parseInt(hours, 10))
      .minute(parseInt(minutes, 10))
      .second(0)
      .millisecond(0)
    onChange(newDateTime.toDate())
  }

  return (
    <Group>
      <Popover
        opened={popoverOpened}
        onClose={() => setPopoverOpened(false)}
        position="bottom-end"
      >
        <Popover.Target>
          <ActionIcon onClick={() => setPopoverOpened((o) => !o)}>
            <IconCalendar size={20} />
          </ActionIcon>
        </Popover.Target>
        <Popover.Dropdown>
          <DatePicker
            value={value}
            onChange={handleDateChange}
            minDate={minDate}
            maxDate={maxDate || new Date()}
          />
        </Popover.Dropdown>
      </Popover>
      <Text>{dayjsValue.format('YYYY-MM-DD')}</Text>
      <TimeInput
        value={dayjsValue.format('HH:mm')}
        onChange={handleTimeChange}
      />
    </Group>
  )
}

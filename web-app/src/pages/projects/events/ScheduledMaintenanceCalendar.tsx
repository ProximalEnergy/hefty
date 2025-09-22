import { useMantineTheme } from '@mantine/core'
import { DatePicker, DatePickerProps } from '@mantine/dates'
import dayjs from 'dayjs'

const getNextMonthWithDay1or15 = () => {
  const today = dayjs()
  if (today.date() > 15) return today.add(1, 'month').toDate()
  return today.date(today.date() > 1 ? 15 : 1).toDate()
}

const ScheduledMaintenanceCalendar = () => {
  const theme = useMantineTheme()

  const defaultMonth = getNextMonthWithDay1or15()
  const getDayProps: DatePickerProps['getDayProps'] = (date) => {
    if (date.getDate() === 1 || date.getDate() === 15) {
      return {
        style: {
          backgroundColor: `var(--mantine-color-${theme.primaryColor}-filled)`,
          color: 'var(--mantine-color-white)',
        },
      }
    }
    return {}
  }
  return (
    <DatePicker
      numberOfColumns={2}
      getDayProps={getDayProps}
      defaultDate={defaultMonth}
    />
  )
}

export default ScheduledMaintenanceCalendar

import * as types from '@/hooks/types'
import { Stepper } from '@mantine/core'
import dayjs from 'dayjs'

const EventStepper = ({ event }: { event: types.Event }) => {
  if (!event) return null
  const active =
    event.time_end != null ? 6 : event.time_last_analyzed != null ? 3.5 : 1.5
  return (
    <Stepper size="sm" active={active}>
      <Stepper.Step
        label="Start"
        description={dayjs(event.time_start).format('MM/DD/YYYY')}
      />
      <Stepper.Step
        label="Detected"
        description={dayjs(event.time_detected).format('MM/DD/YYYY')}
      />
      <Stepper.Step
        label="Analyzed"
        description={
          event.time_last_analyzed
            ? dayjs(event.time_last_analyzed).format('MM/DD/YYYY')
            : ''
        }
      />
      {event.time_last_analyzed === null ? (
        <Stepper.Step label="Recommendation" />
      ) : (
        <Stepper.Step
          label="Recommendation"
          description={dayjs().format('MM/DD/YYYY')}
        />
      )}
      <Stepper.Step label="Ticketed" />
      <Stepper.Step
        label="Fixed"
        description={
          event.time_end ? dayjs(event.time_end).format('MM/DD/YYYY') : ''
        }
      />
    </Stepper>
  )
}

export default EventStepper

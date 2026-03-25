import { List, Stack, Text } from '@mantine/core'

export function LossWaterfallCardInfo() {
  return (
    <Stack gap="sm">
      <Text size="sm" component="div">
        The waterfall walks from reference production down through known losses
        to metered output. Use Component to group by equipment type, or Failure
        Mode to group by event cause. Bars after expected are Proximal event
        losses; remaining gap before the meter is unaccounted difference.
      </Text>
      <Text size="sm" component="div" fw={600}>
        Budgeted bridge (when PV budgeted data exists)
      </Text>
      <List size="sm" spacing="xs" type="unordered" withPadding>
        <List.Item>
          <Text size="sm" component="span">
            <strong>Budgeted</strong> — Energy from the project&apos;s PV
            budgeted series (TMY-style hourly profile). If several series exist,
            the newest is used. Hours are aligned by local month, day, and hour;
            there is no budgeted bar without series data.
          </Text>
        </List.Item>
        <List.Item>
          <Text size="sm" component="span">
            <strong>COD degradation on budgeted</strong> — Each matched hour is
            scaled from commercial operation date; see{' '}
            <strong>Degradation assumptions</strong> below for the exact formula.
          </Text>
        </List.Item>
        <List.Item>
          <Text size="sm" component="span">
            <strong>Weather adjustment</strong> — Difference between PV expected
            (model) and budgeted for the same time range, so the bridge reflects
            weather vs the budget case.
          </Text>
        </List.Item>
        <List.Item>
          <Text size="sm" component="span">
            <strong>PV Expected</strong> — EEM POI expected energy for the range
            after that bridge. Series choice follows{' '}
            <strong>Degradation assumptions</strong>; downstream steps match the
            no-budgeted chart.
          </Text>
        </List.Item>
      </List>
      <Text size="sm" component="div" fw={600}>
        Degradation assumptions
      </Text>
      <List size="sm" spacing="xs" type="unordered" withPadding>
        <List.Item>
          <Text size="sm" component="span">
            <strong>Budgeted bar</strong> — The waterfall API applies a fixed{' '}
            0.5%/yr compound factor per hour:{' '}
            <code style={{ whiteSpace: 'nowrap' }}>
              (1 − 0.005)^years_since_COD
            </code>
            , with <code>years_since_COD</code> as days after project COD divided
            by 365.25. If COD is missing, that exponent is 0 (factor 1, no
            budgeted degradation). This rate is not tied to EEM warranted
            degradation or other product settings.
          </Text>
        </List.Item>
        <List.Item>
          <Text size="sm" component="span">
            <strong>PV Expected (EEM)</strong> — Uses POI expected production
            from EEM for the period. The chart picks the richest series
            available: warranted degradation with soiling, then warranted
            degradation only, then soiling without warranted degradation, then
            a base POI run. Values reflect that EEM export, not the 0.5%/yr
            budgeted rule.
          </Text>
        </List.Item>
      </List>
    </Stack>
  )
}

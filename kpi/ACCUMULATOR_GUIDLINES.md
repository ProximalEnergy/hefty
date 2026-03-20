# Accumulator Guidelines

All of these guidelines are assuming that the energy totals have been forward filled
and then backfilled so that there are no NaNs. Preferably, there has been a generous
lookback period to get the initial time stamp.

If the accumulator has no modulus, i.e. it doesn't wrap around after some large integer,
then it is best to use the difference in bookend midnight values for the energy total.
This allows for missing values and catch-up jumps during the middle of the day to not
affect the day's energy total.

Then, the values can be filtered to the range `- EPSILON` to `12 * power_capacity` (assuming
that the battery was constantly cycling on and off).

If the accumulator does wrap around a modulus, there are two options:

1. If the accumulator makes multiple wraps in a single day, then first derive energy
   and sum it up to get the total energy for the day.

2. If the accumulator is slow, use the mod difference in midnights approach.

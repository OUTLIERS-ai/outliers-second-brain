# What I stole

| Taken from | What was taken |
|---|---|
| cron, and Windows Task Scheduler | Things happen on a clock rather than when somebody remembers. Both are decades old and neither has been improved on for this job. |
| Append-only logs | A record that is only ever added to. What it said last month still says the same thing today, which is the whole point and the thing a rewritable note cannot do. |
| Rate limiting | One budget shared between everything rather than one each. Five things each politely limited still add up to an unreasonable number. |
| Human-in-the-loop review | The work stops at a queue and a person moves it. Old, unfashionable, and the reason nothing here has sent something it should not have. |

## What was learned the hard way

A job of mine ran sixty-four times, produced nothing, and reported success every time. Nobody noticed,
because a job with nothing to do and a job that has broken look identical from the outside.

That is why this layer ends with a comparison - what should be true against what is - rather than with
another feature. Silence is not evidence that things are fine.

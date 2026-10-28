# FAO-56 — Effective Rain and Irrigation Efficiency

Reference notes the explanation module may cite. They never replace the
formula in code.

## Effective rain

Not all forecast rain reaches the root zone. A fraction is subtracted from the
demand, because intense or poorly timed rain is partly lost.

- `effective_rain_mm` is a fraction of `rain_forecast_mm`.
- The whole forecast is **not** removed from today's demand.

## Irrigation efficiency

- Drip: 0.90
- Surface: 0.70

Net deficit is converted to a gross amount:

`gross_irrigation_mm = net_deficit_mm / efficiency`

The engine stores the millimetres; the explanation only states them.
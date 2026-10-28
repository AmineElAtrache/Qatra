# INRA — Citrus Disease Risk (Morocco)

Public agronomy notes the explanation module may cite. For v1 the label stays
`fungal_risk`; mildiou and oïdium are vine and vegetable diseases, so they are
not the citrus labels.

## Risk drivers

- Temperature
- Relative humidity
- Recent rain

When wind is below 5 km/h **and** effective rain is above 5 mm, the risk is
raised to `high`. Otherwise it is `low` (or `medium` when intermediate).

## Spray rule

A spray is blocked when wind is above 15 km/h. The computed spray volume comes
from the plot area and the rate per 100 L; the rule and the factors are stored
with the alert.

## What the explanation says

The explanation restates the label and the block. It does not invent a disease
name the agronomist has not yet given.
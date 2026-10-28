# FAO-56 — Crop Coefficients (Kc) for Citrus

Source: FAO-56, simplified MVP table. The values live in code
(`app/services/agronomy_service.py:KC_TABLE`); this page is the reference
the explanation module may quote.

## Table

| Stage | Kc | Typical window (Morocco) |
| --- | --- | --- |
| initial | 0.70 | post-planting / cover < 10 % |
| flowering | 0.75 | bloom |
| fruit_growth | 0.75 | fruit set → veraison |
| maturity | 0.70 | ripening |
| dormant | 0.65 | winter rest |

## Formula

`ETc = Kc × ET0`

ET0 comes from the Penman-Monteith equation (FAO-56). The dose is computed by
the agronomy engine; the explanation module only restitutes the result.
# Metric Methodology

## Source-of-truth direction

Colombia core market metrics are being migrated to SFC Formato 290 from Datos Abiertos Colombia dataset `e967-4a8r`.

## Premiums

The pipeline searches official Formato 290 concepts for:

- `gross_written_premium`
- `direct_written_premium`
- `accepted_premium`
- `ceded_premium`
- `retained_premium`
- `earned_premium`

The current compatibility table used by the Streamlit dashboard labels its core premium as written premium. It is built from:

- Unidad de Captura 1, Subcuenta 5: primas emitidas directas.
- Unidad de Captura 1, Subcuenta 10: primas aceptadas en coaseguro.
- Unidad de Captura 1, Subcuentas 20 and 25: primas aceptadas en reaseguro.

This is suitable for scale, ranking and market share once the period basis is confirmed. It should not be confused with earned premium, retained premium or ceded premium.

## Claims

The pipeline searches for:

- `claims_incurred`
- `claims_paid`
- `claims_liquidated`
- recoveries or salvage if available.

The current compatibility table maps claims from Unidad de Captura 8, Subcuenta 999: `SINIESTROS CTA CIA`, treated as an incurred claims / technical account movement. This can include reserve, recovery or net technical movements and can be negative. Paid/liquidated claims are available separately and should not be silently used as incurred claims.

## Loss ratio

Loss ratio must be calculated from totals:

```text
total selected claims numerator / total selected premium denominator
```

It must not be calculated as an average of company-level or line-level ratios.

Preferred conventional definition for future formal loss ratio work:

```text
claims_incurred / earned_premium
```

Current dashboard compatibility ratio, clearly labelled:

```text
technical incurred claims movement / written premium
```

Negative values should not be shown or interpreted as ordinary gross siniestralidad. If the numerator or denominator mapping is pending, zero, negative or missing, the dashboard must show a warning rather than a false precision ratio.

## Period basis

Formato 290 includes `Año` and `Mes`, but the period basis must be confirmed before annualizing:

- monthly flow,
- year-to-date accumulated,
- annual close,
- or another reporting basis.

Until confirmed, annual comparisons and YTD/full-year comparisons require a methodology warning.

## Commissions and technical result

The pipeline searches for concepts related to commissions, intermediation, discounts, administrative expenses and technical result. If the dataset does not expose a confirmed concept, the metric remains pending/unavailable rather than zero.

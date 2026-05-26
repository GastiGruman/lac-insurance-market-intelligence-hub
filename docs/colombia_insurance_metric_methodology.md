# Colombia Insurance Metric Methodology Review

## Purpose

This note documents the first methodology review for using SFC / Datos Abiertos Colombia Formato 290 as the Colombia source of truth in the LAC Insurance Market Intelligence Hub.

The goal is to avoid showing broker-facing metrics that look precise but are not methodologically confirmed.

## Official Sources Reviewed

- Superintendencia Financiera de Colombia / Datos Abiertos Colombia dataset `e967-4a8r`, "Información estadística y financiera por ramos de seguros Formato 290". The dataset is provided by Superintendencia Financiera de Colombia, has national coverage, monthly update frequency, and states that values are in pesos except Unidad de Captura 19 in millions of pesos and Unidad de Captura 20 in units.
- Superintendencia Financiera page for Formato 290. It states that the published information corresponds to data transmitted by supervised entities in Formato 290 / Proforma F3000-32 and that figures are subject to review.
- Formato 290 / Proforma F-3000-32 instructive, "Resultado técnico y estadístico". The stated objective is to establish the result by insurance line operated by the supervised entity and the result of autonomous patrimony administration. It applies to general insurers, life insurers, insurance cooperatives and reinsurers, with monthly periodicity.
- The Formato 290 instructive states that ramo columns reflect movement "en lo corrido del periodo respectivo". Therefore 2026 through March must not be compared directly with full-year 2025.

## Key Period Methodology Finding

Formato 290 is a monthly reporting format, but the line columns represent movement in the period-to-date cut. For dashboard use, the safe default is:

- Compare YTD through the same month cutoff across years.
- Do not compare March 2026 against December 2025 as if both were full-year comparable.
- Full-year comparisons should use December cuts only.

The current dashboard load now uses the latest available month cutoff across all years for Formato 290.

## Premium Concepts

| Concept | Formato 290 support | Methodology status | Dashboard use |
|---|---|---|---|
| Direct Written Premium | UC1 / Subcuenta 005, Primas emitidas directas | Confirmed | Safe as Direct Written Premium |
| Accepted Coinsurance Premium | UC1 / Subcuenta 010 | Confirmed | Safe as Accepted Premium |
| Accepted Reinsurance Premium | UC1 / Subcuentas 020 and 025 | Confirmed | Safe as accepted reinsurance premium |
| Ceded Premium | UC1 / Subcuentas 035 and 040, marked as resta; UC21 contains reinsurance ceded detail | Available but sign/basis requires review | Show only with methodology warning |
| Retained Premium | UC1 / Subcuenta 999 subtotal | Available, requires reconciliation | Show only with methodology warning |
| Earned Premium | UC3 / Subcuenta 999, Primas devengadas | Confirmed | Safe as earned premium |

The current compatibility dashboard metric `gross_written_premium` should be understood as written premium composed of direct written premium plus accepted co-insurance plus accepted reinsurance premium. It should not be labelled generically as "premium" when precision matters.

## Claims Concepts

| Concept | Formato 290 support | Methodology status | Dashboard use |
|---|---|---|---|
| Liquidated Claims | UC5 / Subcuenta 999 | Available | Show as Liquidated Claims, not automatically paid claims |
| Claims Reimbursements | UC6 / Subcuenta 999 | Available | Useful for reinsurance-adjusted analysis after review |
| Recoveries and Salvage | UC7 / Subcuenta 999 | Available | Useful after sign review |
| Claims Company Account | UC8 / Subcuenta 999 | Available, signed technical account | Do not label as ordinary gross siniestralidad |

UC8 is defined in the instructive as `UC4 - UC5 + UC6 + UC7`. Because this is a signed technical account, values and ratios can be negative. Negative values should not be hidden, but they must be labelled as signed technical movement rather than ordinary gross loss ratio.

## Reinsurance Concepts

Formato 290 supports several reinsurance views:

- Ceded premium through UC1 ceded subaccounts and UC21 reinsurance information.
- Accepted reinsurance premium through UC1 accepted reinsurance subaccounts.
- Reinsurance commissions and net reinsurance income/expense through UC9.
- Claims reimbursements from reinsurance through UC6.

The following are available but require business review before formal broker use:

- Reinsurance cession ratio.
- Retention ratio.
- Net retained premium formula.
- Reinsurance-adjusted claims and combined ratios.

Recommended interim position:

- Show ceded premium and retained premium as source-supported values with caveats.
- Do not present cession/retention ratios as final unless the numerator sign convention and denominator basis are approved.

## Expenses, Commissions and Acquisition Costs

Formato 290 includes:

- UC11 administrative and personnel expenses.
- UC12 commission expenses.
- UC26/UC27 intermediary charges information.
- UC9 net reinsurance income/expense including ceded reinsurance commissions.

Commission ratio and administrative expense ratio can be calculated mechanically, but the denominator basis must be approved. Acquisition cost ratio is not ready for dashboard display because the exact inclusion of commissions, intermediary charges and other acquisition components requires business review.

## Technical Result

Formato 290 includes UC14 / Subcuenta 999 Technical Result. The instructive defines it as `UC3 + UC8 + UC13`.

This is currently the safest technical profitability indicator because it is provided by the official format instead of being reconstructed manually from partially reviewed components.

Recommended interim dashboard metrics:

- Technical Result.
- Technical Result Ratio / Technical Margin only after the denominator is approved.

## Combined Ratio Readiness

The dashboard should not show Combined Ratio, Final Combined Ratio or Reinsurance-adjusted Combined Ratio yet.

Reason:

- Claims account is signed and net/company-account based.
- Expense and acquisition components require inclusion review.
- Reinsurance components require basis and sign review.
- Denominator choice must be approved.

Safer alternative:

- Use Technical Result and, after review, Technical Result Ratio.

## Technical Bridge Result

The methodology script creates `mart_formato_290_technical_bridge` and reconciliation outputs to test whether reconstructed technical account candidates reconcile to official Technical Result UC14 / Subcuenta 999.

Candidate 1 is a simple business bridge:

`earned premium + signed incurred claims - absolute commissions - absolute administrative expenses`

This does not represent the official Formato 290 technical result formula and is expected not to reconcile.

Candidate 2 follows the official technical result structure more closely:

`earned premium + signed incurred claims + UC13 subtotal`

This candidate is used only as a reconciliation bridge against official Technical Result. Even when it reconciles, it does not automatically validate a conventional combined ratio, because a combined ratio requires approved component inclusion, sign convention and denominator basis.

Generated files:

- `outputs/data_quality/formato_290_combined_ratio_readiness.csv`
- `outputs/data_quality/formato_290_technical_bridge_summary.csv`
- `outputs/reconciliation/formato_290_technical_bridge_sample.csv`

Current recommendation: keep Combined Ratio hidden from the main dashboard. Use Technical Result and Technical Result Ratio as the safer profitability path once the denominator is approved.

## Metric Readiness Summary

See:

- `outputs/data_dictionary/formato_290_metric_methodology_map.csv`
- `outputs/data_quality/formato_290_metric_readiness_matrix.csv`

## Open Questions For Business Review

1. Should dashboard written premium include accepted reinsurance premium for broker ranking and market share, or should direct written premium be the default?
2. Should cession ratios use UC1 ceded premium subaccounts or UC21 reinsurance information?
3. Should ceded premium be presented as signed source value or absolute ceded amount?
4. Should the claims ratio use UC8 technical claims account, UC5 liquidated claims, or another approved numerator?
5. Which premium denominator is preferred for technical ratios: written, retained or earned premium?
6. Which components should be included in acquisition cost ratio?
7. Should technical margin use earned premium or written premium as denominator?
8. Can Formato 290 data be reconciled to official Power BI / SFC exports for selected companies, ramos and periods?

## Current Recommendation

Use Formato 290 for official traceable volume and technical-account analysis, but keep profitability ratios conservative until reconciliation and business methodology review are completed.

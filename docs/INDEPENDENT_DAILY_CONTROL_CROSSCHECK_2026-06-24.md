# Independent daily floorsheet control — 2026-06-24

## Control evidence

The 2026-06-24 market totals are independently corroborated by contemporaneous publications:

| Published source | Shares / quantity | Transactions | Turnover |
|---|---:|---:|---:|
| MeroLagani, 24 Jun 2026 | 10,777,582 | 72,917 | NPR 4.41 billion (rounded) |
| ShareSansar, 24 Jun 2026 | 10,777,582 | 72,917 | NPR 4.41 Arba (rounded) |
| The Rising Nepal, 25 Jun 2026, p.2 | 10,777,582 | not shown in cited table | **NPR 4,418,607,486.62** |

Sources:
- MeroLagani: https://eng.merolagani.com/NewsDetail.aspx?newsID=127826
- ShareSansar: https://www.sharesansar.com/newsdetail/nepse-index-loses-for-third-consecutive-day-to-close-at-266002-points-2026-06-24
- The Rising Nepal e-paper, page 2: https://epaper.gorkhapatraonline.com/uploads/file/2026/6/risingnepal/2026-06-24-11-49-05-trn-25jun-1.pdf

A conflicting secondary summary from HamroShare reports 91.58 lakh shares, 72,066 transactions and NPR 4.32 billion: https://hamroshare.com.np/news/market-wrap/2026-06-24. It is retained as unresolved conflicting evidence and is not used as the accepted control because it disagrees with three contemporaneous reports and the exact newspaper total.

## Source-file reconciliation

The pinned 2026-06-24 source files produce:

| Measure | Samir / MeroLagani-derived CSV | SocrateAI CSV | Published control |
|---|---:|---:|---:|
| Physical contracts / transactions | 24,000 | 72,917 | 72,917 |
| Quantity | 5,564,078 | 10,777,582 | 10,777,582 |
| Gross amount | NPR 1,874,967,415.91 | NPR 4,418,607,486.62 | NPR 4,418,607,486.62 |

Control comparison:
- **SocrateAI passed all three exact checks:** transaction count, quantity and gross amount.
- **Samir failed all three:** 48,917 fewer rows, 5,213,504 fewer shares and NPR 2,543,640,070.71 less turnover.
- All 24,000 Samir contract IDs are present in SocrateAI; SocrateAI has 48,917 additional contract IDs across 237 symbols.
- There are no shared contract field conflicts.

This is strong evidence that the archived Samir file is incomplete for this date, while the SocrateAI file matches the published daily controls exactly. The 24,000-row file size is a truncation/capture-limit lead; the exact mechanism has not yet been established.

## Automated evidence

The independent control was added to the pinned manifest and compared by the pipeline, including transaction count:

- SocrateAI: `passed`
- Samir: `failed`
- Overall date-level control status: review required (because one source failed)
- No canonical source was automatically selected; no data was promoted to training.

Workflow:
- https://github.com/jaljala044/nepse-elite-ai-scanner-pro/actions/runs/45599320707

Artifact:
- ID: `15014378224`
- ZIP SHA-256: `88bdf8da1f6830b51b945e10036ee73cb49c3f052ede78415008eef8871514b9`
- Report SHA-256: `398c5172e870ead4de923541f8ce4235cffd80d3ac2ae84553bf3663014a1cfb`
- Manifest SHA-256: `513229359f641af126710dd7a48b3e36e5739d1db3f468d240306c5f32b3448a`

## Acceptance boundary

The control is cross-publisher published daily evidence, not a raw NEPSE API export. It supports the conclusion that the Samir archive file is incomplete on 2026-06-24 and that SocrateAI's file matches published totals on that date. It does not establish SocrateAI's provenance or rights, nor does it prove completeness on other dates. Continue collecting dated daily controls across the remaining shared dates before source promotion.

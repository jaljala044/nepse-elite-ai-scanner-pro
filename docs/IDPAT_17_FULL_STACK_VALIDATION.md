# IDPAT-17 — Full-stack research validation bridge

- Connects the existing point-in-time feature pipeline to the admitted NEPSE history gate.
- Exposes Wyckoff, Minervini trend, relative strength, broker footprint, VSA, SMC, sector strength, liquidity/tradability, market breadth and existing aggregate preview scores.
- Optionally evaluates IDPAT horizon research for supplied symbol snapshots.
- Blocks all analysis when trusted reference/raw/reconciliation/120-session evidence is not admitted.
- Preserves existing hard blocks for Stage-1 quality, structure, liquidity, market regime and reward/risk; no BUY/SELL or overall score is emitted.
- Broker and sector components remain evidence-dependent; no unsupported neutral scoring.
- This is integration plumbing, not a calibrated production scanner. No actual NEPSE performance or live data is claimed.

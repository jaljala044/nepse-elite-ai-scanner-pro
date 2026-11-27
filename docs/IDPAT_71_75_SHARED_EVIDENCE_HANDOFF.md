# IDPAT 71–75 shared evidence handoff
RHGCL official capture blob aa18187e8a01c18477ee55c9229b4f74581dadb8; reference/official_eod_captures/RHGCL_2026-11-19_nepse_eod.json in nepse-smc-data. Official correction already preserved in derived v2: close 258, volume 9054. Do not modify raw.
P4.37 cross-sector audit documents 1455 closed-date carry-forward rows across 19 securities, with 81 unique dates. Upstream scraper uses computer date rather than businessDate. This explains a documented contamination pattern, not every flagged date.
Use derived v2 pinned commit 4255cc293a347857ac77c04a947beb784203062f for candidate review only. 1329 invalid rows remain; corporate action coverage only three events. API/RHGCL complete action histories not verified.
Canonical calendar scope is limited; candidate weekdays and sampled security observations are not full per-security session evidence. No eligible six-scanner pilot executed. Reuse shared evidence rather than duplicate acquisition.

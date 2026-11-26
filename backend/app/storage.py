import csv, io
from decimal import Decimal
from math import isfinite
from datetime import date
from collections import defaultdict

DATA: dict[str, list[dict]] = {}
IMPORTS: list[dict] = []
REQUIRED = {"symbol", "date", "open", "high", "low", "close", "volume"}

def store_rows(csv_text: str, source: str) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise ValueError("CSV is empty or has no header")
    fields = {f.strip().lower() for f in reader.fieldnames if f}
    missing = REQUIRED - fields
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(sorted(missing)))
    parsed, seen = defaultdict(list), {}
    for line, raw in enumerate(reader, start=2):
        row = {str(k).strip().lower(): (v.strip() if v else "") for k, v in raw.items() if k}
        try:
            symbol = row["symbol"].upper()
            if not symbol or len(symbol) > 20:
                raise ValueError("invalid symbol")
            d = date.fromisoformat(row["date"])
            o, h, lo, c = (float(row[k]) for k in ("open", "high", "low", "close"))
            volume = Decimal(row["volume"])
            if not volume.is_finite() or volume < 0 or volume != volume.to_integral_value():
                raise ValueError("invalid volume")
            vol = int(volume)
            if not all(isfinite(x) for x in (o,h,lo,c)):
                raise ValueError("nonfinite price")
            if min(o, h, lo, c) <= 0 or vol < 0 or h < max(o, c, lo) or lo > min(o, c, h):
                raise ValueError("invalid OHLCV values")
            item = {"date": d, "open": o, "high": h, "low": lo, "close": c, "volume": vol}
        except Exception as exc:
            raise ValueError(f"Invalid row {line}: {exc}") from exc
        key = (symbol, d)
        if key in seen and seen[key] != item:
            raise ValueError(f"Conflicting duplicate row for {symbol} on {d}")
        seen[key] = item
    for (symbol, d), item in seen.items():
        parsed[symbol].append(item)
    for symbol, rows in parsed.items():
        existing = {r["date"]: r for r in DATA.get(symbol, [])}
        for row in rows:
            if row["date"] in existing and existing[row["date"]] != row:
                raise ValueError(f"Conflicting stored row for {symbol} on {row['date']}")
    for symbol, rows in parsed.items():
        merged = {r["date"]: r for r in DATA.get(symbol, [])}
        merged.update({r["date"]: r for r in rows})
        DATA[symbol] = sorted(merged.values(), key=lambda x: x["date"])
    record = {"source": source, "rows_accepted": len(seen),
              "symbols": sorted(parsed), "latest_session": str(max((d for _, d in seen), default=""))}
    IMPORTS.append(record)
    return record

def snapshot():
    return {"symbols": len(DATA), "imports": len(IMPORTS)}

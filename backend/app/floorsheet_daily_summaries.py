"""Review-only daily stock and broker summaries from one pinned floorsheet.

Reject mixed dates, mixed provenance, duplicate contracts and arithmetic defects.
Broker codes are observed publisher codes, not verified beneficial owners.
"""
from collections import defaultdict
from decimal import Decimal
from datetime import date
from app.floorsheet_contract import reconcile_floorsheet_rows

def summarize_daily_contracts(rows, *, expected_date):
    if date.fromisoformat(expected_date).isoformat() != expected_date:
        raise ValueError("noncanonical expected date")
    rows = list(rows)
    if not rows:
        raise ValueError("empty floorsheet")
    provenance = {(r.source_id, r.source_payload_sha256) for r in rows}
    if len(provenance) != 1 or any(r.trade_date != expected_date for r in rows):
        raise ValueError("mixed source or date")
    if any(r.quantity != r.quantity.to_integral_value() for r in rows):
        raise ValueError("fractional traded quantity")
    audit = reconcile_floorsheet_rows(rows)
    if any(audit["counts"][k] for k in ("exact_duplicate", "conflicting_duplicate", "amount_reconciliation_exception")):
        raise ValueError("unresolved contract exceptions")
    stocks = defaultdict(lambda: [0, Decimal(0), Decimal(0)])
    brokers = defaultdict(lambda: [0, Decimal(0), Decimal(0), 0, Decimal(0), Decimal(0)])
    broker_symbols = defaultdict(lambda: [0, Decimal(0), Decimal(0), 0, Decimal(0), Decimal(0)])
    for r in rows:
        s = stocks[r.symbol]
        s[0] += 1
        s[1] += r.quantity
        s[2] += r.amount
        for table, buy, sell in ((brokers,r.buyer_broker_code,r.seller_broker_code),
                                  (broker_symbols,(r.symbol,r.buyer_broker_code),(r.symbol,r.seller_broker_code))):
            for key, offset in ((buy,0),(sell,3)):
                a = table[key]
                a[offset] += 1
                a[offset+1] += r.quantity
                a[offset+2] += r.amount
    totals = [len(rows), sum((r.quantity for r in rows),Decimal(0)), sum((r.amount for r in rows),Decimal(0))]
    for table in (brokers,broker_symbols):
        for offset in (0,3):
            if [sum(v[offset+i] for v in table.values()) for i in range(3)] != totals:
                raise RuntimeError("broker conservation failure")
    if [sum(v[i] for v in stocks.values()) for i in range(3)] != totals:
        raise RuntimeError("stock conservation failure")
    def broker_row(v):
        return dict(buy_transactions=v[0], buy_quantity=str(v[1]), buy_amount=str(v[2]),
                    sell_transactions=v[3], sell_quantity=str(v[4]), sell_amount=str(v[5]),
                    net_quantity=str(v[1]-v[4]), net_amount=str(v[2]-v[5]))
    source, digest = next(iter(provenance))
    return {"date":expected_date,"source_id":source,"source_sha256":digest,
            "stock_rows":[{"symbol":k,"transactions":v[0],"quantity":str(v[1]),"amount":str(v[2])} for k,v in sorted(stocks.items())],
            "broker_rows":[{"broker_code":k,**broker_row(v)} for k,v in sorted(brokers.items())],
            "broker_symbol_rows":[{"symbol":k[0],"broker_code":k[1],**broker_row(v)} for k,v in sorted(broker_symbols.items())],
            "totals":{"transactions":totals[0],"quantity":str(totals[1]),"amount":str(totals[2])},
            "canonical_promotion_allowed":False,"broker_identity_verified":False,"session_completeness_verified":False}

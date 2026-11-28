"""Read-only guard extending Issue #5's original pinned overlay contract."""
import csv
import hashlib
import re
from datetime import date
from pathlib import Path

EXPECTED_SHA256 = '956b525427e2c6b733ebe3274647aa888dff5518e32db28c0562089cf318d8ec'
EXPECTED_COUNT = 32241
PREFIX = '03_stock_charts_ohlcv/'

def key(row):
    repo, commit, path = (row[k] for k in ('repository','commit_sha','source_file'))
    line = int(row['target_csv_row'])
    if not repo or not re.fullmatch(r'[0-9a-f]{40}',commit) or not path or line < 2:
        raise ValueError('Invalid locator')
    path = path.removeprefix(PREFIX)
    if not path or path.startswith('/') or '..' in path.split('/'):
        raise ValueError('Invalid path')
    return repo, commit, path, line

def provenance(row):
    return (re.fullmatch(r'[0-9a-f]{64}',row['source_file_sha256']) is not None
            and bool(row['symbol']) and date.fromisoformat(row['target_date']).isoformat() == row['target_date'])

class Quarantine:
    def __init__(self,path):
        path=Path(path)
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA256:
            raise ValueError('Overlay checksum mismatch; refuse admission')
        self.rows={}
        from io import StringIO
        for row in csv.DictReader(StringIO(raw.decode('utf-8'),newline='')):
            k=key(row)
            flags=(row['confirmed_carry_forward'],row['explicit_closure_review'])
            if k in self.rows or flags not in {('True','False'),('False','True')} or not provenance(row) or row['eligible_trading_candle']!='False' or row['canonical_training_allowed']!='False':
                raise ValueError('Invalid exclusion overlay')
            self.rows[k]=row
        if len(self.rows)!=EXPECTED_COUNT:
            raise ValueError('Overlay count mismatch')
    def disposition(self, observation):
        """Never admits a record; absent rows still require other gates."""
        try:
            k=key(observation)
            if not provenance(observation):
                return 'hold_missing_provenance'
        except (KeyError,TypeError,ValueError):
            return 'hold_missing_provenance'
        row=self.rows.get(k)
        if row is None:
            return 'not_in_overlay_requires_other_gates'
        if any(observation.get(field)!=row[field] for field in ('source_file_sha256','symbol','target_date')):
            return 'hold_provenance_conflict'
        return ('excluded_confirmed_carry_forward' if row['confirmed_carry_forward']=='True' else 'hold_explicit_closure_review')

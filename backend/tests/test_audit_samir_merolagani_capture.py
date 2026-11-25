import csv
import tempfile
import unittest
from pathlib import Path

from audit_samir_merolagani_capture import audit_capture, EXPECTED_HEADERS


def fixture(rows):
    import io
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=EXPECTED_HEADERS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue().encode("utf-8")


class SamirCaptureAuditTests(unittest.TestCase):
    def write(self, payload):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.write(payload)
        tmp.close()
        self.addCleanup(lambda: Path(tmp.name).unlink(missing_ok=True))
        return Path(tmp.name)

    def test_row_math_serials_and_independent_controls(self):
        payload = fixture([
            {"date":"2026-11-24","sn":"1","contract_no":"2026112401","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"200"},
            {"date":"2026-11-24","sn":"3","contract_no":"2026112402","stock_symbol":"NABIL",
             "buyer":"12","seller":"22","quantity":"3","rate":"110","amount":"330"},
        ])
        report = audit_capture(
            self.write(payload),
            require_pinned_identity=False,
            control_totals={
                "trade_date":"2026-11-24","quantity":"5",
                "gross_amount":"530","average_rate":"106",
            },
        )
        self.assertEqual(report["row_quality"]["data_rows"], 2)
        self.assertEqual(report["row_quality"]["unique_contract_ids"], 2)
        self.assertEqual(report["row_quality"]["quantity_rate_amount_mismatch_rows"], 0)
        self.assertEqual(report["serial_sequence"]["missing_serial_numbers"], [2])
        self.assertEqual(report["independent_daily_control"]["status"], "passed")
        self.assertFalse(report["acceptance"]["canonical_promotion_allowed"])

    def test_control_mismatch_and_capture_date_mismatch_are_exposed(self):
        payload = fixture([
            {"date":"2026-11-23","sn":"1","contract_no":"2026112401","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"200"},
        ])
        report = audit_capture(
            self.write(payload),
            require_pinned_identity=False,
            control_totals={
                "trade_date":"2026-11-24","quantity":"3",
                "gross_amount":"300","average_rate":"100",
            },
        )
        self.assertEqual(report["independent_daily_control"]["status"], "failed")
        self.assertFalse(report["row_quality"]["all_rows_on_expected_date"])
        self.assertFalse(report["acceptance"]["canonical_promotion_allowed"])

    def test_rejects_incorrect_pinned_hash_and_size(self):
        payload = fixture([
            {"date":"2026-11-24","sn":"1","contract_no":"2026112401","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"200"},
        ])
        with self.assertRaisesRegex(ValueError, "byte size mismatch|SHA-256"):
            audit_capture(self.write(payload), require_pinned_identity=True)

    def test_rejects_header_mismatch(self):
        path = self.write(b"wrong,header\nx,y\n")
        with self.assertRaisesRegex(ValueError, "source header mismatch"):
            audit_capture(path, require_pinned_identity=False)

    def test_duplicate_contract_and_invalid_amount_are_counted_as_rejected(self):
        payload = fixture([
            {"date":"2026-11-24","sn":"1","contract_no":"2026112401","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"2","rate":"100","amount":"201"},
            {"date":"2026-11-24","sn":"2","contract_no":"2026112401","stock_symbol":"NABIL",
             "buyer":"11","seller":"22","quantity":"bad","rate":"100","amount":"200"},
        ])
        report = audit_capture(
            self.write(payload), require_pinned_identity=False,
            control_totals={
                "trade_date":"2026-11-24","quantity":"0",
                "gross_amount":"0","average_rate":"0",
            },
        )
        self.assertEqual(report["row_quality"]["duplicate_contract_id_rows"], 1)
        self.assertEqual(report["row_quality"]["malformed_rows"], 1)
        self.assertEqual(report["row_quality"]["quantity_rate_amount_mismatch_rows"], 1)


if __name__ == "__main__":
    unittest.main()

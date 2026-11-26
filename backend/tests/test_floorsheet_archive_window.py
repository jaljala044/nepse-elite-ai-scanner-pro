import hashlib
import unittest

from audit_floorsheet_archive_window import git_blob_sha1, verify_pinned_payload


class FloorsheetArchiveWindowTests(unittest.TestCase):
    def test_git_blob_hash_matches_git_object_format(self):
        payload = b"abc"
        self.assertEqual(
            git_blob_sha1(payload),
            "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f",
        )

    def test_pinned_payload_returns_size_git_hash_and_sha256(self):
        payload = b"pinned fixture"
        result = verify_pinned_payload(
            payload,
            expected_size=len(payload),
            expected_blob_sha1=git_blob_sha1(payload),
            label="fixture",
        )
        self.assertEqual(result["byte_size"], len(payload))
        self.assertEqual(result["git_blob_sha1"], git_blob_sha1(payload))
        self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())

    def test_wrong_size_and_git_blob_are_rejected(self):
        payload = b"pinned fixture"
        with self.assertRaisesRegex(ValueError, "byte-size mismatch"):
            verify_pinned_payload(
                payload, expected_size=len(payload) + 1,
                expected_blob_sha1=git_blob_sha1(payload), label="fixture",
            )
        with self.assertRaisesRegex(ValueError, "Git blob SHA-1 mismatch"):
            verify_pinned_payload(
                payload, expected_size=len(payload),
                expected_blob_sha1="0" * 40, label="fixture",
            )


if __name__ == "__main__":
    unittest.main()

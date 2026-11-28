"""Offline regression coverage for immutable raw archive collection."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from app import source_collector as sc


class ImmutableArchiveCollectorTests(unittest.TestCase):
    revision = "a" * 40
    repo = "jaljala044/nepse-history-starter"
    label = "jaljala_history_starter"
    path = "03_stock_charts_ohlcv/ABC OHLCV.csv"
    content = b"date,open,high,low,close,volume\n2025-01-01,10,12,9,11,100\n"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "raw"
        self.requests = []

    def collect(self, *, revision=None, truncated=False, corrupt=False, bad_size=False):
        revision = self.revision if revision is None else revision
        blob = hashlib.sha1(f"blob {len(self.content)}\0".encode("ascii") + self.content).hexdigest()
        def handle(request):
            self.requests.append(str(request.url))
            if request.url.path.endswith("/commits/main"):
                return httpx.Response(200, json={"sha": revision})
            if "/git/trees/" in request.url.path:
                return httpx.Response(200, json={"truncated": truncated, "tree": [
                    {"type": "blob", "path": self.path, "sha": blob,
                     "size": len(self.content) + int(bad_size)}
                ]})
            if request.url.host == "raw.githubusercontent.com":
                return httpx.Response(200, content=self.content + b"x" if corrupt else self.content)
            raise AssertionError(str(request.url))
        with patch.object(sc, "ROOT", self.root), httpx.Client(transport=httpx.MockTransport(handle)) as client:
            return sc.collect_user_github_repos(client, {self.label})

    def test_pinned_revision_and_manifest_provenance(self):
        row, = self.collect()
        self.assertNotIn("error", row)
        self.assertEqual(row["repository"], self.repo)
        self.assertEqual(row["commit_sha"], self.revision)
        self.assertEqual(row["source_file"], self.path)
        self.assertEqual(row["source_file_sha256"], hashlib.sha256(self.content).hexdigest())
        self.assertFalse(row["canonical_training_allowed"])
        self.assertTrue(row["eligibility_review_required"])
        self.assertEqual((self.root.parent / row["path"]).read_bytes(), self.content)
        self.assertIn("/git/trees/" + self.revision, self.requests[1])
        self.assertIn("/" + self.revision + "/", self.requests[2])
        self.assertIn("ABC%20OHLCV.csv", self.requests[2])

    def test_invalid_revision_blocks_download(self):
        row, = self.collect(revision="main")
        self.assertIn("Invalid immutable source revision", row["error"])
        self.assertEqual(len(self.requests), 1)

    def test_truncated_tree_blocks_download(self):
        row, = self.collect(truncated=True)
        self.assertIn("completeness not established", row["error"])
        self.assertEqual(len(self.requests), 2)

    def test_corrupt_blob_is_not_saved(self):
        row, = self.collect(corrupt=True)
        self.assertIn("Source blob identity or size mismatch", row["error"])
        self.assertFalse(self.root.exists())

    def test_size_mismatch_is_not_saved(self):
        row, = self.collect(bad_size=True)
        self.assertIn("Source blob identity or size mismatch", row["error"])
        self.assertFalse(self.root.exists())

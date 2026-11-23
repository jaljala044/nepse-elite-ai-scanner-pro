import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.hf_dataset_collector import _download_one

class NoNetworkClient:
    def stream(self, *args, **kwargs):
        raise AssertionError("A verified local copy should not be downloaded again")

class HuggingFaceResumeTests(unittest.TestCase):
    def test_existing_file_is_skipped_only_when_lfs_sha_and_size_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            payload=b"verified public source bytes"
            digest=hashlib.sha256(payload).hexdigest()
            target=root/"owner__dataset"/"main"/"floorsheet"/"file.csv.gz"
            target.parent.mkdir(parents=True)
            target.write_bytes(payload)
            item={
                "path":"floorsheet/file.csv.gz",
                "size":len(payload),
                "oid":"git-blob-oid",
                "lfs":{"oid":digest,"size":len(payload)},
            }
            with patch("app.hf_dataset_collector.RAW_ROOT",root), patch(
                "app.hf_dataset_collector._safe_repo_dir",return_value="owner__dataset"
            ), patch("app.hf_dataset_collector.REPO_ROOT",root):
                result=_download_one(
                    NoNetworkClient(),"owner/dataset","main",item,"test",
                    max_file_bytes=1024,total_remaining=1024,
                )
            self.assertEqual(result["status"],"already_present")
            self.assertEqual(result["sha256"],digest)
            self.assertEqual(result["bytes"],len(payload))

    def test_wrong_size_is_not_accepted_as_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            target=root/"owner__dataset"/"main"/"floorsheet"/"file.csv.gz"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"bad")
            item={
                "path":"floorsheet/file.csv.gz",
                "size":100,
                "oid":"git-blob-oid",
                "lfs":{"oid":"0"*64,"size":100},
            }
            class NoBudgetClient:
                pass
            with patch("app.hf_dataset_collector.RAW_ROOT",root), patch(
                "app.hf_dataset_collector._safe_repo_dir",return_value="owner__dataset"
            ), patch("app.hf_dataset_collector.REPO_ROOT",root):
                # Since the existing file is not trustworthy, a zero byte budget
                # stops the network transfer after the local-copy check.
                from app.hf_dataset_collector import _download_one
                result=_download_one(
                    NoBudgetClient(),"owner/dataset","main",item,"test",
                    max_file_bytes=1024,total_remaining=0,
                )
            self.assertEqual(result["status"],"skipped_total_budget")
            self.assertEqual(target.read_bytes(),b"bad")

if __name__=="__main__":
    unittest.main()

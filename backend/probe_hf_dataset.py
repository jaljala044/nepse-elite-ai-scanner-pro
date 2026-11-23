"""Print a safe summary of the Hugging Face dataset tree response for troubleshooting."""
from __future__ import annotations
import argparse
import json
import httpx

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="urekmazino69/Nepse-floorsheet-and-indices")
    parser.add_argument("--revision", default="main")
    args = parser.parse_args()
    url = f"https://huggingface.co/api/datasets/{args.repo}/tree/{args.revision}"
    params = {"recursive": "true", "expand": "false", "limit": 1000}
    with httpx.Client(timeout=30, follow_redirects=True,
                      headers={"User-Agent": "NEPSE-ELITE-AI-SCANNER dataset probe"}) as client:
        response = client.get(url, params=params)
        print("HTTP", response.status_code)
        print("URL", response.url)
        print("CONTENT-TYPE", response.headers.get("content-type"))
        print("LINK", response.headers.get("Link"))
        response.raise_for_status()
        payload = response.json()
    print("PAYLOAD-TYPE", type(payload).__name__)
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        print("TOP-LEVEL-KEYS", sorted(payload.keys()))
        items = payload.get("items", payload.get("files", []))
    else:
        items = []
    print("ITEM-COUNT", len(items))
    for item in items[:20]:
        if isinstance(item, dict):
            safe = {key: item.get(key) for key in
                    ("type", "path", "rfilename", "name", "size", "oid", "blob_id", "lfs")}
            print(json.dumps(safe, ensure_ascii=False))
        else:
            print(repr(item))
if __name__ == "__main__":
    main()

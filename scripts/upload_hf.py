"""Upload the dataset/ folder to HuggingFace.

Requires: pip install huggingface_hub, and HF_TOKEN (a write token for the
target account/org) in the environment. Does nothing without it.

Usage: python scripts/upload_hf.py <repo_id>   e.g. zoeb-nomi/ledgerlane-eval-episodes
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dataset"


def main() -> None:
    repo = sys.argv[1] if len(sys.argv) > 1 else "zoeb-nomi/ledgerlane-eval-episodes"
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if not token:
        print("HF_TOKEN not set — dataset is built in dataset/ but not uploaded. "
              "Create a write token at https://huggingface.co/settings/tokens, "
              "export HF_TOKEN, re-run with: python scripts/upload_hf.py <repo_id>")
        return
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(repo_id=repo, repo_type="dataset", exist_ok=True)
    api.upload_folder(repo_id=repo, repo_type="dataset", folder_path=str(DATA))
    print(f"uploaded dataset/ -> https://huggingface.co/datasets/{repo}")


if __name__ == "__main__":
    main()

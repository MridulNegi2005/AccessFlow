"""Install an explicit public ASR snapshot before evaluation; no runtime downloads."""

import argparse
import hashlib
import json
from pathlib import Path
import re

from scripts.package_media import MODEL_OPTIONAL, MODEL_REQUIRED, MODEL_LIMIT_BYTES


def install(repo, revision, output, *, workspace=None, downloader=None):
    if (not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo)
            or not re.fullmatch(r"[0-9a-f]{40}", revision)):
        raise ValueError("Provide a public repository name and immutable 40-character commit revision")
    workspace = Path(workspace or Path(__file__).resolve().parents[1]).resolve()
    model_root = (workspace / "models").resolve()
    output = Path(output).resolve()
    if (not model_root.is_relative_to(workspace) or not output.is_relative_to(model_root)
            or output == model_root or output.exists()):
        raise ValueError("Choose a new directory strictly beneath the workspace models directory")
    if downloader is None:
        from huggingface_hub import snapshot_download
        downloader = snapshot_download
    # Downloads may leave partial files on failure; no installation record is
    # issued until all required files exist. Never overwrite an earlier install.
    downloader(repo, revision=revision, local_dir=output,
               allow_patterns=sorted(MODEL_REQUIRED | MODEL_OPTIONAL), token=False)
    hashes = {}
    total = 0
    for name in sorted(MODEL_REQUIRED | MODEL_OPTIONAL):
        path = output / name
        if not path.exists():
            if name in MODEL_REQUIRED:
                raise ValueError(f"Downloaded snapshot lacks {name}")
            continue
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(output):
            raise ValueError("Downloaded model path violates the installation boundary")
        total += path.stat().st_size
        if total > MODEL_LIMIT_BYTES:
            raise ValueError("Downloaded model exceeds the supported size bound")
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    if not any(name in hashes for name in ("vocabulary.txt", "vocabulary.json")):
        raise ValueError("Downloaded snapshot lacks its vocabulary")
    record = {"repository": repo, "revision": revision, "files": hashes}
    (output / "installation_source.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        record = install(args.repository, args.revision, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({"directory": str(args.output.resolve()), "repository": record["repository"],
                      "revision": record["revision"], "files": len(record["files"]),
                      "live_inference_verified": False}))


if __name__ == "__main__":
    main()

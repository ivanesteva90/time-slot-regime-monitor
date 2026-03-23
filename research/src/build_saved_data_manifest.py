from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat()


def build_manifest(data_dir: Path) -> dict:
    csv_files = sorted(path for path in data_dir.glob("*.csv") if path.is_file())
    files = []

    for path in csv_files:
        stat = path.stat()
        uploaded_at = iso_from_timestamp(stat.st_mtime)
        files.append(
            {
                "name": path.name,
                "path": f"{data_dir.name}/{path.name}",
                "size": stat.st_size,
                "uploaded_at": uploaded_at,
                "modified_at": uploaded_at,
            }
        )

    latest_upload_at = max((file["uploaded_at"] for file in files), default=None)
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "source_dir": data_dir.name,
        "file_count": len(files),
        "latest_upload_at": latest_upload_at,
        "files": files,
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Build DATA/manifest.json for saved dashboard CSVs.")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("DATA"),
        help="Directory containing saved CSV files (default: DATA)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("DATA/manifest.json"),
        help="Manifest output path (default: DATA/manifest.json)",
    )
    args = parser.parse_args()

    data_dir = (project_root / args.data_dir).resolve() if not args.data_dir.is_absolute() else args.data_dir.resolve()
    if not data_dir.exists():
        raise SystemExit(f"Data directory not found: {data_dir}")

    manifest = build_manifest(data_dir)
    output_path = (project_root / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Saved manifest to {output_path}")
    print(f"CSV files indexed: {manifest['file_count']}")
    if manifest["latest_upload_at"]:
        print(f"Latest upload detected: {manifest['latest_upload_at']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

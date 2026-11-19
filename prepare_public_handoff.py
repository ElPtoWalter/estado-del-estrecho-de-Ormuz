"""Prepare an audited public-only repository skeleton locally. No network or git pushes."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
from build_public_site import audit_public_build
from check_public_links import check

WORKFLOW = """name: Public-only Pages publication
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803 # v6
        with:
          persist-credentials: false
      - uses: actions/upload-pages-artifact@fc324d3547104276b827a68afc52ff2a11cc49c9 # v5
        with:
          path: public
          include-hidden-files: true
  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
    steps:
      - uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5
"""


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError("Destination already exists; no files overwritten")
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("Source and destination must be separate")
    audit_public_build(source)
    errors = check(source)
    if errors:
        raise ValueError("; ".join(errors))
    shutil.copytree(source, destination / "public")
    workflow = destination / ".github/workflows/pages.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(WORKFLOW, encoding="utf-8")
    manifest = {p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                for p in source.rglob("*") if p.is_file()}
    # Evidence stays alongside the new repository, never in the deploy directory.
    destination.with_suffix(".manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    return len(manifest)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=Path("_site"))
    parser.add_argument("--destination",type=Path,required=True)
    args=parser.parse_args()
    print("Prepared public-only files:",prepare(args.source,args.destination))

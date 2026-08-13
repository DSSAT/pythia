"""Build a portable release archive from a Simulation_Data directory."""

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Iterable, Tuple

from pythia.example_data import EXAMPLE_CONFIGS, validate_example_data


GITHUB_ASSET_LIMIT = 2 * 1024 * 1024 * 1024
IGNORED_NAMES = {".DS_Store", ".history", "__MACOSX", "__pycache__"}


def _is_excluded(relative: Path) -> bool:
    if any(part in IGNORED_NAMES for part in relative.parts):
        return True
    if relative.parts and relative.parts[0] == "OUTPUT":
        return True
    return relative.suffix in {".log", ".pyc", ".template"}


def _release_files(root: Path) -> Iterable[Tuple[Path, Path]]:
    """Yield (source, archive-relative-path), substituting clean JSON templates."""
    example_names = set(EXAMPLE_CONFIGS)
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(root)
        if _is_excluded(relative):
            continue
        if relative.parent == Path("Sri_Lanka") and relative.name in example_names:
            template = source.with_suffix(source.suffix + ".template")
            yield (template if template.is_file() else source), relative
        else:
            yield source, relative


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_example_archive(data_root, output, package_readme=None):
    """Validate and create a deterministic, portable ZIP plus SHA-256 file."""
    root = Path(data_root).expanduser().resolve()
    destination = Path(output).expanduser().resolve()
    if destination.suffix.lower() != ".zip":
        raise ValueError("The release archive must use the .zip extension.")
    if root == destination or root in destination.parents:
        raise ValueError("Write the release archive outside Simulation_Data.")

    validate_example_data(root, allow_placeholders=True)
    destination.parent.mkdir(parents=True, exist_ok=True)

    archive_root = "Simulation_Data"
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
    ) as archive:
        archive.writestr(f"{archive_root}/OUTPUT/", b"")
        if package_readme:
            readme = Path(package_readme).expanduser().resolve()
            archive.write(readme, f"{archive_root}/README.md")
        for source, relative in _release_files(root):
            archive.write(source, (Path(archive_root) / relative).as_posix())

    size = destination.stat().st_size
    if size >= GITHUB_ASSET_LIMIT:
        raise ValueError(
            f"Archive is {size / 1024**3:.2f} GiB; GitHub release assets must be "
            "smaller than 2 GiB. Split the data into multiple archives."
        )

    checksum = _sha256(destination)
    checksum_path = destination.with_suffix(destination.suffix + ".sha256")
    checksum_path.write_text(f"{checksum}  {destination.name}\n", encoding="utf-8")
    return destination, checksum_path, size


def inspect_archive(path) -> dict:
    """Return a small manifest used by release checks and tests."""
    archive_path = Path(path)
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        bad = [
            name
            for name in names
            if any(part in IGNORED_NAMES for part in Path(name).parts)
        ]
        configs = {}
        for name in EXAMPLE_CONFIGS:
            member = f"Simulation_Data/Sri_Lanka/{name}"
            configs[name] = json.loads(archive.read(member).decode("utf-8"))
    return {"members": names, "excluded_members": bad, "configs": configs}

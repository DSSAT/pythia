"""Configure and validate the downloadable Pythia example data package."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List


DATA_ROOT_TOKEN = "<</path/to/folder>>"
DSSAT_EXECUTABLE_TOKEN = "<</path/to/dssat/executable>>"
EXAMPLE_CONFIGS = ("SL_Maize.json", "SL_Rice.json", "SL_Rice_env.json")


class ExampleDataError(ValueError):
    """Raised when the example-data package is incomplete or misconfigured."""


def _config_paths(data_root: Path) -> Iterable[Path]:
    sri_lanka = data_root / "Sri_Lanka"
    for name in EXAMPLE_CONFIGS:
        yield sri_lanka / name


def _template_path(config_path: Path) -> Path:
    return config_path.with_suffix(config_path.suffix + ".template")


def _release_template(config_path: Path) -> Path:
    """Return the reusable template, including after a local configuration."""
    backup = _template_path(config_path)
    if backup.is_file():
        return backup
    return config_path


def _replace_tokens(value, replacements: Dict[str, str]):
    if isinstance(value, str):
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
        return value
    if isinstance(value, list):
        return [_replace_tokens(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: _replace_tokens(item, replacements) for key, item in value.items()}
    return value


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _referenced_paths(config: dict) -> Iterable[Path]:
    for key in ("workDir", "templateDir", "weatherDir", "ghr_root"):
        if config.get(key):
            yield Path(config[key])

    dssat = config.get("dssat", {})
    if dssat.get("executable"):
        yield Path(dssat["executable"])

    setup = config.get("default_setup", {})
    for include in setup.get("include", []):
        yield Path(include)

    template_dir = config.get("templateDir")
    if template_dir and setup.get("template"):
        yield Path(template_dir) / setup["template"]

    for value in _strings(config):
        parts = value.split("::")
        for marker in ("raster", "vector"):
            if marker in parts:
                index = parts.index(marker)
                if index + 1 < len(parts):
                    yield Path(parts[index + 1])


def validate_example_data(data_root, allow_placeholders=False) -> List[Path]:
    """Validate package structure and all paths referenced by its JSON examples."""
    root = Path(data_root).expanduser().resolve()
    errors = []

    required = (
        root / "Sri_Lanka",
        root / "weather_data" / "Sri_Lanka",
        root / "eGHR" / "GHR.db",
        root / "eGHR" / "LK.SOL",
        root / "raster" / "ggcmi_soils_2.tif",
        root / "raster" / "spam2010V2r0_global_H_MAIZ_H.tif",
        root / "raster" / "spam2010V2r0_global_H_RICE_I.tif",
    )
    for path in required:
        if not path.exists():
            errors.append(f"Required example-data path is missing: {path}")

    configs = list(_config_paths(root))
    for config_path in configs:
        if not config_path.is_file():
            errors.append(f"Example configuration is missing: {config_path}")
            continue
        source_path = (
            _release_template(config_path) if allow_placeholders else config_path
        )
        try:
            source_text = source_path.read_text(encoding="utf-8")
            config = json.loads(source_text)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON file {source_path}: {exc}")
            continue

        has_root_token = DATA_ROOT_TOKEN in source_text
        has_dssat_token = DSSAT_EXECUTABLE_TOKEN in source_text
        if allow_placeholders:
            if not has_root_token:
                errors.append(f"Data-root placeholder is missing from {source_path}")
            if not has_dssat_token:
                errors.append(f"DSSAT placeholder is missing from {source_path}")
            continue

        if has_root_token or has_dssat_token:
            errors.append(
                f"Example is not configured yet: {config_path}. "
                "Run 'pythia --configure-example ...' first."
            )
            continue

        for path in _referenced_paths(config):
            # workDir is intentionally created by Pythia.
            if str(path) == str(config.get("workDir")):
                continue
            if not path.exists():
                errors.append(
                    f"Referenced path does not exist in {config_path}: {path}"
                )

    if errors:
        raise ExampleDataError("\n".join(errors))
    return configs


def _atomic_json_write(path: Path, config: dict) -> None:
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            json.dump(config, output, indent=2, ensure_ascii=False)
            output.write("\n")
        os.replace(temporary_name, str(path))
    except Exception:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def configure_example_data(data_root, dssat_executable) -> List[Path]:
    """Replace release placeholders and validate the configured examples."""
    root = Path(data_root).expanduser().resolve()
    dssat_path = Path(dssat_executable).expanduser().resolve()
    if not dssat_path.is_file():
        raise ExampleDataError(f"DSSAT executable was not found: {dssat_path}")

    validate_example_data(root, allow_placeholders=True)
    replacements = {
        DATA_ROOT_TOKEN: root.as_posix(),
        DSSAT_EXECUTABLE_TOKEN: dssat_path.as_posix(),
    }

    configured = []
    for config_path in _config_paths(root):
        backup = _template_path(config_path)
        if not backup.exists():
            shutil.copy2(str(config_path), str(backup))
        config = json.loads(backup.read_text(encoding="utf-8"))
        _atomic_json_write(config_path, _replace_tokens(config, replacements))
        configured.append(config_path)

    validate_example_data(root)
    return configured

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.transform import from_origin


DEFAULT_GRID = {
    "crs": "EPSG:4326",
    "width": 4320,
    "height": 2160,
    "pixel_size": (0.08333333333333333, 0.08333333333333333),
    "origin": (-180.0, 90.0),
    "dtype": "uint32",
    "nodata": 0,
    "count": 2,
}


_FLOAT_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_PROFILE_RE = re.compile(r"^([A-Za-z]{2}|[A-Za-z]{4})(\d+)$")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def encode_prefix(prefix: str) -> int:
    if not isinstance(prefix, str):
        raise TypeError("country_ascii must be a string with 2 or 4 letters (e.g., 'BR' or 'EBPF').")
    p = prefix.strip().upper()
    if len(p) == 2 and p.isalpha():
        return int(f"{ord(p[0]):02d}{ord(p[1]):02d}")
    if len(p) == 4 and p.isalpha():
        b = p.encode("ascii")
        return (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]
    raise ValueError("country_ascii must be 2 or 4 letters (e.g., 'BR' or 'EBPF').")


def decode_prefix(code: int) -> str:
    if int(code) <= 9999:
        s = f"{int(code):04d}"
        return chr(int(s[:2])) + chr(int(s[2:]))
    b0 = (int(code) >> 24) & 0xFF
    b1 = (int(code) >> 16) & 0xFF
    b2 = (int(code) >> 8) & 0xFF
    b3 = int(code) & 0xFF
    return bytes([b0, b1, b2, b3]).decode("ascii")


def build_profile_code_from_bands(prefix_code: int, numeric_id: int) -> str:
    prefix = decode_prefix(prefix_code)
    if len(prefix) == 2:
        return f"{prefix}{int(numeric_id):08d}"
    if len(prefix) == 4:
        return f"{prefix}{int(numeric_id):06d}"
    raise ValueError("Invalid decoded prefix length.")


def _parse_profile_id(profile_id: str) -> Tuple[str, int]:
    if not isinstance(profile_id, str):
        raise TypeError("profile_id must be a string.")
    pid = profile_id.strip().upper()
    m = _PROFILE_RE.match(pid)
    if not m:
        raise ValueError(f"Invalid profile_id format: {profile_id}")
    prefix = m.group(1)
    digits = m.group(2)

    if len(prefix) == 4:
        if len(digits) != 6:
            raise ValueError(f"4-letter profile IDs must have 6 digits: {profile_id}")
        return prefix, int(digits)

    if len(prefix) == 2:
        if len(digits) != 8:
            raise ValueError(f"2-letter profile IDs must have 8 digits: {profile_id}")
        return prefix, int(digits)

    raise ValueError(f"Invalid profile_id: {profile_id}")


def _build_meta_and_bands() -> Tuple[dict, np.ndarray]:
    """Create an empty 2-band raster using the fixed DEFAULT_GRID template.

    Note: custom grid definitions via config were intentionally removed.
    """
    width = int(DEFAULT_GRID["width"])
    height = int(DEFAULT_GRID["height"])
    resx, resy = DEFAULT_GRID["pixel_size"]
    x0, y0 = DEFAULT_GRID["origin"]
    nodata = DEFAULT_GRID["nodata"]
    dtype = DEFAULT_GRID["dtype"]
    count = int(DEFAULT_GRID["count"])
    crs = DEFAULT_GRID["crs"]

    transform = from_origin(float(x0), float(y0), float(resx), float(resy))

    meta = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": count,
        "dtype": dtype,
        "crs": crs,
        "transform": transform,
        "nodata": nodata,
    }

    bands = np.full((count, height, width), nodata, dtype=np.dtype(dtype))
    return meta, bands

class _RasterIndexProxy:
    def __init__(self, transform):
        self._transform = transform

    def index(self, lon, lat):
        return rasterio.transform.rowcol(self._transform, lon, lat)


def coord_to_pixel(src, lat: float, lon: float) -> Tuple[int, int]:
    return src.index(lon, lat)


def _normalize_update(u: dict) -> dict:
    if "lat" not in u or "lon" not in u:
        raise ValueError("Each update must include 'lat' and 'lon'.")

    if "profile_id" in u and u["profile_id"] is not None:
        prefix, numeric = _parse_profile_id(str(u["profile_id"]))
        return {
            "lat": float(u["lat"]),
            "lon": float(u["lon"]),
            "prefix_code": int(encode_prefix(prefix)),
            "numeric_id": int(numeric),
        }

    if "country_ascii" not in u:
        raise ValueError("Each update must include 'country_ascii' as a 2- or 4-letter string (or use 'profile_id').")
    if "numeric_id" not in u:
        raise ValueError("Each update must include 'numeric_id' (or use 'profile_id').")

    prefix = str(u["country_ascii"]).strip().upper()
    if len(prefix) == 4:
        numeric = int(u["numeric_id"])
        if numeric < 0 or numeric > 999999:
            raise ValueError("For 4-letter prefixes, numeric_id must fit 6 digits (0..999999).")
    elif len(prefix) == 2:
        numeric = int(u["numeric_id"])
        if numeric < 0 or numeric > 99999999:
            raise ValueError("For 2-letter prefixes, numeric_id must fit 8 digits (0..99999999).")
    else:
        raise ValueError("country_ascii must be 2 or 4 letters.")

    return {
        "lat": float(u["lat"]),
        "lon": float(u["lon"]),
        "prefix_code": int(encode_prefix(prefix)),
        "numeric_id": int(numeric),
    }


def apply_updates(src, bands: np.ndarray, updates: List[dict]) -> np.ndarray:
    for raw in updates:
        u = _normalize_update(raw)
        row, col = coord_to_pixel(src, u["lat"], u["lon"])
        bands[0, row, col] = int(u["prefix_code"])
        bands[1, row, col] = int(u["numeric_id"])
    return bands


def _safe_unlink(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
        except PermissionError:
            raise
        except Exception:
            try:
                os.remove(str(path))
            except Exception:
                pass


def write_raster(path: Path, bands: np.ndarray, meta: dict) -> None:
    meta2 = meta.copy()
    meta2.update(count=2, dtype=bands.dtype)
    _safe_unlink(path)
    with rasterio.open(str(path), "w", **meta2) as dst:
        dst.write(bands)


def _resolve_mode(cfg: dict) -> str:
    has_updates = "updates" in cfg and cfg["updates"] is not None
    has_sol_inputs = "sol_inputs" in cfg and cfg["sol_inputs"] is not None

    if has_updates and has_sol_inputs:
        raise ValueError("Invalid raster build config: provide only one of 'updates' or 'sol_inputs'.")

    if has_sol_inputs:
        return "sol"

    if has_updates:
        return "manual"

    raise ValueError("Invalid raster build config: expected 'updates' or 'sol_inputs'.")


def _resolve_output_path(cfg: dict, base_raster: Optional[Path], output_override: Optional[str]) -> Path:
    if output_override:
        o = Path(output_override)
        if o.is_absolute():
            return o
        if base_raster is not None:
            return base_raster.parent / o
        return o

    if "output_raster" not in cfg or not cfg["output_raster"]:
        raise ValueError("Missing 'output_raster' in raster build config")

    return Path(cfg["output_raster"])


def _expand_sol_inputs(sol_inputs: dict) -> List[Path]:
    if not isinstance(sol_inputs, dict):
        raise ValueError("'sol_inputs' must be an object.")

    paths = sol_inputs.get("paths")
    if not isinstance(paths, list) or not paths:
        raise ValueError("'sol_inputs.paths' must be a non-empty list.")

    recursive = bool(sol_inputs.get("recursive", False))
    out: List[Path] = []

    for p in paths:
        pp = Path(str(p))
        if pp.is_dir():
            if recursive:
                out.extend(sorted(pp.rglob("*.SOL")))
                out.extend(sorted(pp.rglob("*.sol")))
            else:
                out.extend(sorted(pp.glob("*.SOL")))
                out.extend(sorted(pp.glob("*.sol")))
        else:
            out.append(pp)

    out2 = [p for p in out if p.exists()]
    if not out2:
        raise ValueError("No .SOL files found from 'sol_inputs.paths'.")
    return out2


def _parse_site_line_country_lat_lon(line: str) -> Tuple[str, float, float]:
    matches = list(_FLOAT_RE.finditer(line))
    if len(matches) < 2:
        raise ValueError("Could not find LAT/LON in @SITE data line.")

    values = [(m, float(m.group(0))) for m in matches]

    real_vals = [(m, v) for (m, v) in values if v != -99.0]

    if len(real_vals) < 2:
        raise ValueError("Could not find valid LAT/LON in @SITE data line.")

    lat_m, lat = real_vals[0]
    lon_m, lon = real_vals[1]

    prefix = line[:lat_m.start()].strip()
    parts = [p for p in prefix.split() if p]
    if not parts:
        raise ValueError("Could not parse country name from @SITE line.")

    country_name = parts[-1].strip().upper()

    return country_name, lat, lon


def _iter_sol_profiles(sol_path: Path) -> List[dict]:
    lines = sol_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    profiles: List[dict] = []

    i = 0
    n = len(lines)
    while i < n:
        line = lines[i].rstrip("\n")
        if line.startswith("*"):
            tokens = line[1:].strip().split()
            if not tokens:
                i += 1
                continue

            profile_id = tokens[0].strip()
            country_name = None
            lat = None
            lon = None

            j = i + 1
            while j < n and not lines[j].startswith("*"):
                if lines[j].lstrip().startswith("@SITE"):
                    k = j + 1
                    while k < n and (lines[k].strip() == "" or lines[k].lstrip().startswith("@")):
                        k += 1
                    if k < n and not lines[k].startswith("*"):
                        cn, la, lo = _parse_site_line_country_lat_lon(lines[k])
                        country_name = cn
                        lat = la
                        lon = lo
                    break
                j += 1

            if lat is not None and lon is not None:
                profiles.append(
                    {
                        "profile_id": profile_id,
                        "country_name": country_name,
                        "lat": lat,
                        "lon": lon,
                        "sol_path": str(sol_path),
                    }
                )

            i = j
            continue

        i += 1

    return profiles


def _country_to_iso2(country_name: str, country_map: Dict[str, str]) -> str:
    key = (country_name or "").strip().upper()
    if key in country_map:
        return str(country_map[key]).strip().upper()
    raise ValueError(f"Country '{country_name}' not found in 'country_map'.")


def _sol_mode_to_updates(cfg: dict) -> List[dict]:
    sol_inputs = cfg.get("sol_inputs")
    sol_files = _expand_sol_inputs(sol_inputs)

    unique = {}
    for p in sol_files:
        rp = Path(p).resolve()
        unique[str(rp).lower()] = rp
    sol_files = list(unique.values())

    updates: List[dict] = []
    
    for sol_path in sol_files:
        for p in _iter_sol_profiles(Path(sol_path)):
            profile_id = str(p["profile_id"]).strip().upper()
            prefix, numeric = _parse_profile_id(profile_id)

            updates.append(
                {
                    "lat": float(p["lat"]),
                    "lon": float(p["lon"]),
                    "country_ascii": prefix,
                    "numeric_id": int(numeric),
                }
            )

    if not updates:
        raise ValueError("No profiles with @SITE lat/lon found in the provided .SOL files.")

    return updates



def main(config_path: str, output_override: Optional[str] = None) -> None:
    cfg = load_config(config_path)
    mode = _resolve_mode(cfg)

    base_raster = Path(cfg["base_raster"]) if cfg.get("base_raster") else None
    output = _resolve_output_path(cfg, base_raster, output_override)

    if mode == "manual":
        if not isinstance(cfg.get("updates"), list):
            raise ValueError("'updates' must be a list.")
        updates = cfg["updates"]
    else:
        updates = _sol_mode_to_updates(cfg)

    # Custom grid definitions were removed; reject legacy configs explicitly.
    if cfg.get("grid") not in (None, {}, ""):
        raise ValueError(
            "Config key 'grid' is no longer supported. "
            "Provide 'base_raster' to update an existing raster, "
            "or omit 'base_raster' to generate a raster using the fixed DEFAULT_GRID template."
        )

    if base_raster is None:
        meta, bands = _build_meta_and_bands()
        proxy = _RasterIndexProxy(meta["transform"])
        bands = apply_updates(proxy, bands, updates)
        write_raster(output, bands, meta)
    else:
        with rasterio.open(str(base_raster)) as src:
            bands = src.read()
            meta = src.meta.copy()
            bands = apply_updates(src, bands, updates)
        write_raster(output, bands, meta)

    print("Raster created:", str(output))

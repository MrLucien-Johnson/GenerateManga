#!/usr/bin/env python3
"""Check whether local diffusion generation is READY or BLOCKED."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import handle_cli_errors, root  # noqa: E402


def _try_import(name: str) -> tuple[bool, str]:
    try:
        mod = __import__(name)
        ver = getattr(mod, "__version__", "?")
        return True, str(ver)
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _ram_gb() -> float | None:
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    kb = int(line.split()[1])
                    return round(kb / (1024 * 1024), 2)
    except Exception:
        return None
    return None


def _disk_gb(path: Path) -> dict:
    usage = shutil.disk_usage(path)
    return {
        "total_gb": round(usage.total / (1024**3), 2),
        "free_gb": round(usage.free / (1024**3), 2),
    }


def _cuda_info() -> dict:
    info: dict = {
        "torch_available": False,
        "cuda_available": False,
        "gpu_name": None,
        "vram_gb": None,
        "torch_version": None,
        "cuda_version": None,
    }
    ok, ver = _try_import("torch")
    if not ok:
        info["torch_error"] = ver
        return info
    import torch

    info["torch_available"] = True
    info["torch_version"] = ver
    info["cuda_available"] = bool(torch.cuda.is_available())
    info["cuda_version"] = getattr(torch.version, "cuda", None)
    if info["cuda_available"]:
        try:
            info["gpu_name"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["vram_gb"] = round(props.total_memory / (1024**3), 2)
        except Exception as exc:  # noqa: BLE001
            info["gpu_error"] = str(exc)
    return info


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Report LOCAL_GENERATION READY/BLOCKED.")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    project = root()
    blockers: list[str] = []

    packages = {}
    for name in ("diffusers", "transformers", "accelerate", "safetensors", "PIL"):
        ok, ver = _try_import(name if name != "PIL" else "PIL")
        packages[name] = {"ok": ok, "version": ver if ok else None, "error": None if ok else ver}
        if not ok and name != "PIL":
            blockers.append(f"Missing package: {name}")

    cuda = _cuda_info()
    if not cuda["torch_available"]:
        blockers.append("torch not installed")
    elif not cuda["cuda_available"]:
        blockers.append("CUDA not available (CPU-only torch or no GPU)")

    # Local model path check
    model_path = os.environ.get("ECHO_LOCAL_MODEL_PATH")
    try:
        from echo.core.config import get_config

        gen = get_config("generation", root=project, use_cache=False)
        model_path = model_path or gen.get("local_model_path")
    except Exception:
        gen = {}
    if not model_path or not Path(str(model_path)).exists():
        blockers.append("No local_model_path configured or path missing (no auto-download)")

    report = {
        "os": platform.platform(),
        "python": sys.version.split()[0],
        "ram_gb": _ram_gb(),
        "disk": _disk_gb(project),
        "packages": packages,
        "cuda": cuda,
        "local_model_path": model_path,
        "use_mock_backend": bool(gen.get("use_mock_backend")) if isinstance(gen, dict) else None,
        "default_backend": (gen.get("default_backend") if isinstance(gen, dict) else None),
        "blockers": blockers,
        "LOCAL_GENERATION": "BLOCKED" if blockers else "READY",
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"OS: {report['os']}")
        print(f"Python: {report['python']}")
        print(f"RAM: {report['ram_gb']} GB")
        print(f"Disk free: {report['disk']['free_gb']} GB")
        print(f"Torch: {cuda.get('torch_version')} cuda={cuda.get('cuda_available')} gpu={cuda.get('gpu_name')} vram={cuda.get('vram_gb')}")
        for name, meta in packages.items():
            print(f"  {name}: {'OK ' + str(meta['version']) if meta['ok'] else 'MISSING'}")
        print(f"local_model_path: {model_path}")
        if blockers:
            print("Blockers:")
            for b in blockers:
                print(f"  - {b}")
        print(f"LOCAL_GENERATION: {report['LOCAL_GENERATION']}")

    raise SystemExit(0 if not blockers else 2)


if __name__ == "__main__":
    main()

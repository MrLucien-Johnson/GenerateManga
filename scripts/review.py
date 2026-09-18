#!/usr/bin/env python3
"""Launch the Streamlit Review Studio."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _cli_common import die, handle_cli_errors, root  # noqa: E402


@handle_cli_errors
def main() -> None:
    parser = argparse.ArgumentParser(description="Launch Echo Review Studio (Streamlit).")
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--host", default="localhost")
    args = parser.parse_args()

    project = root()
    app = project / "app.py"
    if not app.is_file():
        die(f"app.py not found at {app}")

    streamlit = shutil.which("streamlit")
    if not streamlit:
        die(
            "streamlit executable not found.",
            hint="pip install streamlit  (or: pip install -e .)",
        )

    print("Launching Echo of the Inkwell Review Studio ...")
    print(f"  streamlit run {app} --server.port {args.port}")
    print("Tip: from the project root you can also run:  streamlit run app.py\n")
    env = os.environ.copy()
    env.setdefault("ECHO_PROJECT_ROOT", str(project))
    raise SystemExit(
        subprocess.call(
            [
                streamlit,
                "run",
                str(app),
                "--server.port",
                str(args.port),
                "--server.address",
                args.host,
            ],
            cwd=str(project),
            env=env,
        )
    )


if __name__ == "__main__":
    main()

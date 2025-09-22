#!/usr/bin/env python3
"""
Python wrapper for uv_wrapper.sh script.
This allows uv to execute the shell script through a Python entry point.
"""

import subprocess
import sys
from pathlib import Path


def main():
    """Execute the uv_wrapper.sh script."""
    # Get the project root directory (go up from app/scripts to project root)
    project_root = Path(__file__).parent.parent.parent
    script_dir = project_root / "_scripts"
    shell_script = script_dir / "uv_wrapper.sh"

    if not shell_script.exists():
        sys.stderr.write(f"❌ Shell script not found: {shell_script}\n")
        sys.exit(1)

    try:
        # Execute the shell script with all arguments passed through
        result = subprocess.run([str(shell_script)] + sys.argv[1:], check=True)
        sys.exit(result.returncode)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        sys.stderr.write("\n❌ Interrupted by user\n")
        sys.exit(130)
    except Exception as e:
        sys.stderr.write(f"❌ Error executing script: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

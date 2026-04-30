#!/usr/bin/env python3
"""Capture screenshots for routes inferred from git diff vs dev."""

from __future__ import annotations

import json
import os
import re
import shlex
import socket
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from urllib.error import HTTPError
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
WEB_PORT = int(os.environ.get("WEB_SCREENSHOT_PORT", "5173"))
WEB_HOST = os.environ.get("WEB_SCREENSHOT_HOST", "localhost")
WEB_URL = f"http://{WEB_HOST}:{WEB_PORT}"
ACTIVE_WEB_URL = WEB_URL
_SEMGREP_FAILURE_WARNED = False
_SEMGREP_DISABLED = False
SCREENSHOT_PROJECT_ID = "e69ddc19-e2c6-4537-a236-93849c4bc847"
SCREENSHOT_WAIT_TIMEOUT_MS = int(
    os.environ.get("WEB_SCREENSHOT_WAIT_TIMEOUT_MS", "15000")
)
SCREENSHOT_NAV_TIMEOUT_MS = int(
    os.environ.get("WEB_SCREENSHOT_NAV_TIMEOUT_MS", "120000")
)
SCREENSHOT_BOT_EMAIL = "bot@proximal.energy"
SCREENSHOT_PWCLI = (
    Path.home() / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"
)


def run_cmd(*, cmd: list[str], cwd: Path = ROOT) -> str:
    """Run a command and return stdout."""
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        text=True,
        capture_output=True,
    )
    return proc.stdout.strip()


def load_env_value(*, key: str) -> str | None:
    """Load KEY from process env or local .env files."""
    direct = os.environ.get(key)
    if direct:
        return direct
    env_files = [ROOT / "web-app" / ".env", ROOT / ".env"]
    for env_file in env_files:
        if not env_file.exists():
            continue
        text = env_file.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            env_key, env_value = stripped.split("=", 1)
            if env_key.strip() != key:
                continue
            value = env_value.strip().strip("'").strip('"')
            if value:
                return value
    return None


def run_pwcli(
    *,
    session: str,
    args: list[str],
    cwd: Path = ROOT,
    env_extra: dict[str, str] | None = None,
) -> None:
    """Run playwright-cli wrapper with a fixed session."""
    if not SCREENSHOT_PWCLI.exists():
        raise RuntimeError(f"Missing playwright wrapper at {SCREENSHOT_PWCLI}")
    cmd = ["bash", str(SCREENSHOT_PWCLI), "--session", session, *args]
    env = {**os.environ, "TMPDIR": "/tmp"}
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(  # noqa: S603
        cmd,
        cwd=cwd,
        check=False,
        text=True,
        env=env,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip().splitlines()[:2]
        summary = " | ".join(detail) if detail else "no stderr/stdout"
        action = args[0] if args else "unknown"
        raise RuntimeError(f"playwright-cli {action} failed: {summary}")


def capture_with_login(*, session: str, url: str, dest: Path, cli_cwd: Path) -> None:
    """Open URL, authenticate as bot if needed, and capture a screenshot."""
    bot_password = load_env_value(key="BOT_PASSWORD")
    if not bot_password:
        raise RuntimeError("Missing BOT_PASSWORD in env or .env files.")
    pw_env = {"BOT_PASSWORD": bot_password}
    run_pwcli(session=session, args=["open", url], cwd=cli_cwd, env_extra=pw_env)
    script = f"""async (...args) => {{
  const scope = args[0] ?? {{}};
  const pageRef = scope.page ?? (typeof page !== 'undefined' ? page : null);
  if (!pageRef) {{
    throw new Error('No Playwright page in run-code scope');
  }}
  const targetUrl = {json.dumps(url)};
  const screenshotPath = {json.dumps(str(dest))};
  const botEmail = {json.dumps(SCREENSHOT_BOT_EMAIL)};
  const botPassword = {json.dumps(bot_password)};
  const navTimeout = {SCREENSHOT_NAV_TIMEOUT_MS};
  const settleMs = {SCREENSHOT_WAIT_TIMEOUT_MS};
  const overlaySelectors = [
    '[class*="mantine-LoadingOverlay-root"]',
    '[class*="LoadingOverlay-root"]',
    '.mantine-LoadingOverlay-root',
    '[data-loading-overlay]',
  ];

  const isSignIn = (rawUrl) => {{
    try {{
      return new URL(rawUrl).pathname.startsWith('/sign-in');
    }} catch {{
      return false;
    }}
  }};

  const authRoots = () => {{
    const frames = pageRef
      .frames()
      .filter((frame) => /clerk|sign-in/i.test(frame.url()));
    return [pageRef, ...frames];
  }};

  const hasAny = async (selectors) => {{
    for (const root of authRoots()) {{
      for (const selector of selectors) {{
        const field = root.locator(selector).first();
        if ((await field.count()) > 0) {{
          return true;
        }}
      }}
    }}
    return false;
  }};

  const fillFirst = async (selectors, value) => {{
    for (const root of authRoots()) {{
      for (const selector of selectors) {{
        const field = root.locator(selector).first();
        if ((await field.count()) > 0) {{
          await field.fill(value);
          return true;
        }}
      }}
    }}
    return false;
  }};

  const clickFirst = async (selectors) => {{
    for (const root of authRoots()) {{
      for (const selector of selectors) {{
        const button = root.locator(selector).first();
        if ((await button.count()) > 0) {{
          await button.click();
          return true;
        }}
      }}
    }}
    return false;
  }};

  await pageRef.waitForTimeout(1200);
  const emailSelectors = ['input[name="identifier"]', 'input[type="email"]'];
  const passwordSelectors = ['input[type="password"]', 'input[name="password"]'];
  const submitSelectors = [
    'button:has-text("Continue")',
    'button:has-text("Sign in")',
    '[data-localization-key*="formButtonPrimary"]',
  ];
  const shouldLogin = isSignIn(pageRef.url()) || (await hasAny(emailSelectors));
  if (shouldLogin) {{
    await fillFirst(emailSelectors, botEmail);
    await clickFirst(submitSelectors);
    await pageRef.waitForTimeout(600);
    await fillFirst(passwordSelectors, botPassword);
    await clickFirst(submitSelectors);
    try {{
      await pageRef.waitForURL((next) => !next.pathname.startsWith('/sign-in'), {{
        timeout: navTimeout,
      }});
    }} catch {{
      // explicit validation below decides whether to fail
    }}
  }}

  if (isSignIn(pageRef.url())) {{
    throw new Error('Still on /sign-in after login attempt');
  }}

  if (pageRef.url() !== targetUrl) {{
    await pageRef.goto(targetUrl, {{
      timeout: navTimeout,
      waitUntil: 'domcontentloaded',
    }});
  }}

  try {{
    await pageRef.waitForLoadState('networkidle', {{ timeout: navTimeout }});
  }} catch {{
    // ignore networkidle timeout for long polling pages
  }}

  try {{
    await pageRef.waitForFunction(
      (selectors) => {{
        const isVisible = (el) => {{
          const style = window.getComputedStyle(el);
          if (style.display === 'none' || style.visibility === 'hidden') {{
            return false;
          }}
          if (Number(style.opacity || '1') === 0) {{
            return false;
          }}
          const rect = el.getBoundingClientRect();
          return rect.width > 1 && rect.height > 1;
        }};
        const all = selectors.flatMap((selector) =>
          Array.from(document.querySelectorAll(selector)),
        );
        return !all.some((el) => isVisible(el));
      }},
      overlaySelectors,
      {{ timeout: navTimeout }},
    );
  }} catch {{
    // continue even if overlay selector doesn't match this page
  }}

  await pageRef.waitForTimeout(settleMs);
  await pageRef.screenshot({{ path: screenshotPath, fullPage: true }});
}}"""
    run_pwcli(
        session=session,
        args=["run-code", script],
        cwd=cli_cwd,
        env_extra=pw_env,
    )
    if not dest.exists():
        raise RuntimeError(f"Screenshot was not created: {dest}")


def choose_base_ref(*, cwd: Path = ROOT) -> str:
    """Select a merge-base against dev when available."""
    for ref in ["origin/dev", "dev"]:
        proc = subprocess.run(
            ["git", "merge-base", "HEAD", ref],
            cwd=cwd,
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    return "HEAD~1"


def changed_files_vs_dev(*, cwd: Path = ROOT) -> list[str]:
    """Return changed files in branch plus local working tree changes."""
    base_ref = choose_base_ref(cwd=cwd)
    ahead = run_cmd(cmd=["git", "diff", "--name-only", f"{base_ref}...HEAD"], cwd=cwd)
    local = run_cmd(cmd=["git", "diff", "--name-only", "HEAD"], cwd=cwd)
    files = sorted({*(ahead.splitlines()), *(local.splitlines())})
    return [file for file in files if file]


def semgrep_matches(*, files: list[str], rule_yaml: str) -> list[dict[str, object]]:
    """Run semgrep with an inline config and return result objects."""
    global _SEMGREP_DISABLED
    if _SEMGREP_DISABLED:
        return []
    if not files:
        return []
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp:
        tmp.write(rule_yaml)
        tmp_path = tmp.name
    try:
        proc = run_semgrep_scan(files=files, tmp_path=tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    if proc.returncode not in {0, 1}:
        _SEMGREP_DISABLED = True
        warn_semgrep_failure(proc=proc)
        return []
    try:
        data = json.loads(proc.stdout or "{}")
    except JSONDecodeError:
        warn_semgrep_failure(proc=proc, context="invalid JSON output")
        return []
    return data.get("results", [])


def extract_routes_from_files(*, files: list[str]) -> list[str]:
    """Extract literal routes from changed files with semgrep."""
    rule = """
rules:
  - id: route-literals
    languages: [typescript, javascript]
    message: route
    severity: INFO
    patterns:
      - pattern-either:
          - pattern: <Route ... path="$PATH" ... />
          - pattern: navigate("$PATH")
          - pattern: to="$PATH"
          - pattern: const $NAME = "$PATH"
      - metavariable-regex:
          metavariable: $PATH
          regex: ^/[A-Za-z0-9_/:.-]*$
"""
    matches = semgrep_matches(files=files, rule_yaml=rule)
    routes = extract_routes_with_regex(files=files)
    for match in matches:
        metavars = match.get("extra", {}).get("metavars", {})
        path = metavars.get("$PATH", {}).get("abstract_content")
        if isinstance(path, str):
            routes.add(path)
    return sorted(routes)


def extract_app_route_map() -> dict[str, str]:
    """Map component names used in App.tsx routes to literal route paths."""
    app_file = "web-app/src/App.tsx"
    rule = """
rules:
  - id: app-route-component
    languages: [typescript]
    message: route mapping
    severity: INFO
    pattern: <Route ... path="$PATH" ... element={<$COMP ... />} ... />
"""
    matches = semgrep_matches(files=[app_file], rule_yaml=rule)
    route_map = extract_app_route_map_with_regex(app_file=app_file)
    for match in matches:
        metavars = match.get("extra", {}).get("metavars", {})
        comp = metavars.get("$COMP", {}).get("abstract_content")
        path = metavars.get("$PATH", {}).get("abstract_content")
        if isinstance(comp, str) and isinstance(path, str) and path.startswith("/"):
            route_map[comp] = path
    return route_map


def extract_routes_with_regex(*, files: list[str]) -> set[str]:
    """Parse changed files to find common literal route strings."""
    patterns = [
        re.compile(
            r"<Route[^>]*\bpath\s*=\s*[\"']"
            r"(?P<path>/[A-Za-z0-9_/:.-]*)[\"']"
        ),
        re.compile(r"navigate\(\s*[\"'](?P<path>/[A-Za-z0-9_/:.-]*)[\"']\s*\)"),
        re.compile(r"\bto\s*=\s*[\"'](?P<path>/[A-Za-z0-9_/:.-]*)[\"']"),
        re.compile(
            r"\bconst\s+[A-Za-z_][A-Za-z0-9_]*\s*=\s*[\"']"
            r"(?P<path>/[A-Za-z0-9_/:.-]*)[\"']"
        ),
    ]
    routes: set[str] = set()
    for file in files:
        text = (ROOT / file).read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            for match in pattern.finditer(text):
                routes.add(match.group("path"))
    return routes


def extract_app_route_map_with_regex(*, app_file: str) -> dict[str, str]:
    """Parse App.tsx route elements and resolve nested full paths."""
    text = (ROOT / app_file).read_text(encoding="utf-8", errors="ignore")
    route_map: dict[str, str] = {}
    token_pattern = re.compile(r"<Route\b[^>]*>|</Route>")
    path_pattern = re.compile(r"\bpath\s*=\s*[\"'](?P<path>[^\"']+)[\"']")
    comp_pattern = re.compile(
        r"\belement\s*=\s*\{\s*<(?P<comp>[A-Za-z_][A-Za-z0-9_]*)"
    )
    stack: list[str] = [""]

    def join_route(*, base: str, segment: str) -> str:
        if segment.startswith("/"):
            return re.sub(r"/{2,}", "/", segment)
        if not base:
            return f"/{segment}".replace("//", "/")
        return f"{base.rstrip('/')}/{segment.lstrip('/')}"

    for token in token_pattern.finditer(text):
        value = token.group(0)
        if value.startswith("</Route"):
            if len(stack) > 1:
                stack.pop()
            continue

        parent = stack[-1]
        path_match = path_pattern.search(value)
        full_path = parent
        if path_match:
            full_path = join_route(base=parent, segment=path_match.group("path"))

        comp_match = comp_pattern.search(value)
        if comp_match and full_path.startswith("/"):
            route_map[comp_match.group("comp")] = full_path

        if not value.rstrip().endswith("/>"):
            stack.append(full_path)
    return route_map


def semgrep_env(*, tmp_dir: str) -> dict[str, str]:
    """Build an environment that avoids semgrep network/setup side effects."""
    return {
        **os.environ,
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
        "SEMGREP_LOG_FILE": str(Path(tmp_dir) / "semgrep.log"),
        "SEMGREP_SETTINGS_FILE": str(Path(tmp_dir) / "settings.yml"),
        "SEMGREP_VERSION_CACHE_PATH": str(Path(tmp_dir) / "version-cache"),
    }


def run_semgrep_scan(*, files: list[str], tmp_path: str) -> subprocess.CompletedProcess:
    """Run semgrep via uv to match local mise toolchain behavior."""
    with tempfile.TemporaryDirectory(prefix="web-screenshot-semgrep-") as tmp_dir:
        env = semgrep_env(tmp_dir=tmp_dir)
        return subprocess.run(
            [
                "uvx",
                "semgrep@1.160",
                "scan",
                "--config",
                tmp_path,
                "--json",
                "--metrics=off",
                *files,
            ],
            cwd=ROOT,
            check=False,
            text=True,
            capture_output=True,
            env=env,
        )


def warn_semgrep_failure(
    *,
    proc: subprocess.CompletedProcess,
    context: str = "scan failed",
) -> None:
    """Emit semgrep failure warning once, with concrete command output."""
    global _SEMGREP_FAILURE_WARNED
    if _SEMGREP_FAILURE_WARNED:
        return
    max_line = 220
    stderr_lines = (proc.stderr or "").strip().splitlines()
    stdout_lines = (proc.stdout or "").strip().splitlines()
    detail_lines = [*stderr_lines[:2], *stdout_lines[:2]]
    detail_lines = [line[:max_line] for line in detail_lines if line]
    if not detail_lines:
        detail_lines = ["no stderr/stdout from semgrep"]
    detail = " | ".join(detail_lines)
    print(
        "Warning: semgrep failed "
        f"({context}; exit={proc.returncode}; detail={detail}); "
        "using regex route fallback."
    )
    _SEMGREP_FAILURE_WARNED = True


def infer_page_routes(*, changed_files: list[str]) -> list[str]:
    """Infer App.tsx routes for changed page components."""
    changed_pages = [
        Path(file) for file in changed_files if file.startswith("web-app/src/pages/")
    ]
    if not changed_pages:
        return []
    route_map = extract_app_route_map()
    routes: set[str] = set()
    for file in changed_pages:
        stem = file.stem
        if stem in route_map:
            routes.add(route_map[stem])
    return sorted(routes)


def discover_dev_server_url() -> str | None:
    """Return a reachable dev server URL for host aliases."""
    hosts = [WEB_HOST, "localhost", "127.0.0.1"]
    seen: set[str] = set()
    for host in hosts:
        if host in seen:
            continue
        seen.add(host)
        if not tcp_port_open(host=host, port=WEB_PORT):
            continue
        base_url = f"http://{host}:{WEB_PORT}"
        for path in ("", "/@vite/client"):
            url = f"{base_url}{path}"
            try:
                with urlopen(url, timeout=1):  # noqa: S310
                    return base_url
            except HTTPError:
                return base_url
            except URLError:
                continue
    return None


def tcp_port_open(*, host: str, port: int) -> bool:
    """Return true when a TCP listener is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def ensure_dev_server(*, cwd: Path = ROOT) -> None:
    """Start mise run dev in background if localhost is not up."""
    global ACTIVE_WEB_URL
    running_url = discover_dev_server_url()
    if running_url:
        ACTIVE_WEB_URL = running_url
        print(f"Dev server already running at {ACTIVE_WEB_URL}")
        return

    log_path = cwd / ".web-screenshot-dev.log"
    print("Starting `mise run dev --no-sync` in background...")
    with log_path.open("a", encoding="utf-8") as log_file:
        subprocess.Popen(  # noqa: S603
            ["mise", "run", "dev", "--no-sync"],
            cwd=cwd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    timeout_seconds = int(os.environ.get("WEB_SCREENSHOT_WAIT_SECONDS", "180"))
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        running_url = discover_dev_server_url()
        if running_url:
            ACTIVE_WEB_URL = running_url
            print(f"Dev server started at {ACTIVE_WEB_URL}")
            return
        time.sleep(2)

    raise RuntimeError(
        f"Timed out waiting for dev server on localhost/127.0.0.1:{WEB_PORT}. "
        f"Check {log_path} for logs."
    )


def materialize_route(*, route: str) -> str:
    """Replace dynamic path params with deterministic values."""
    route = re.sub(r":projectId\b", SCREENSHOT_PROJECT_ID, route)
    return re.sub(r":[A-Za-z_][A-Za-z0-9_]*", "1", route)


def safe_filename(*, route: str) -> str:
    """Convert route path into a safe file name."""
    materialized = materialize_route(route=route).strip("/")
    if not materialized:
        return "root"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", materialized)


def take_screenshots(*, routes: list[str], output_dir: Path) -> list[Path]:
    """Capture page screenshots with playwright CLI + auth flow."""
    output_dir.mkdir(parents=True, exist_ok=True)
    shots: list[Path] = []
    session = "ws"
    with tempfile.TemporaryDirectory(prefix="web-screenshot-pwcli-") as tmp_dir:
        cli_cwd = Path(tmp_dir)
        for route in routes:
            concrete = materialize_route(route=route)
            url = f"{ACTIVE_WEB_URL}{concrete}"
            dest = output_dir / f"{safe_filename(route=route)}.png"
            print(f"Capturing {url} -> {dest}")
            capture_with_login(session=session, url=url, dest=dest, cli_cwd=cli_cwd)
            shots.append(dest)
        try:
            run_pwcli(session=session, args=["close"], cwd=cli_cwd)
        except RuntimeError:
            pass
    return shots


def web_screenshot() -> None:
    """Entry point."""
    changed_files = changed_files_vs_dev()
    web_files = [
        file
        for file in changed_files
        if file.startswith("web-app/") and file.endswith((".ts", ".tsx", ".js", ".jsx"))
    ]

    routes = set(extract_routes_from_files(files=web_files))
    routes.update(infer_page_routes(changed_files=changed_files))

    if not routes:
        routes = {"/"}

    ensure_dev_server()

    stamp = datetime.now(tz=UTC).strftime("%Y%m%d-%H%M%S")
    output_dir = ROOT / "_screenshot" / stamp
    captured = take_screenshots(routes=sorted(routes), output_dir=output_dir)

    print("\nSaved screenshots:")
    for shot in captured:
        rel = shot.relative_to(ROOT)
        print(f" - {rel}")

    route_preview = ", ".join(sorted(routes))
    print(f"\nRoutes discovered via semgrep: {route_preview}")
    print(f"Output directory: {output_dir.relative_to(ROOT)}")
    print(f"Re-run command: {shlex.join(['mise', 'run', 'web:screenshot'])}")


if __name__ == "__main__":
    web_screenshot()

#!/usr/bin/env python3
"""Convenient test runner with optional HTML report generation."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

REPORT_DIR = Path("test_reports")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass
class TestRecord:
    """Holds metadata about individual test execution."""

    id: str
    status: str
    duration: float
    message: Optional[str] = None


class TrackingTestResult(unittest.TextTestResult):
    """Collects per-test data while delegating to TextTestResult."""

    def __init__(self, *args, **kwargs):  # noqa: D401
        super().__init__(*args, **kwargs)
        self.records: List[TestRecord] = []
        self._status_map: dict[unittest.case.TestCase, Tuple[str, Optional[str]]] = {}

    def startTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802 (unittest API)
        self._start_time = time.perf_counter()
        super().startTest(test)

    def stopTest(self, test: unittest.case.TestCase) -> None:  # noqa: N802 (unittest API)
        duration = time.perf_counter() - getattr(self, "_start_time", time.perf_counter())
        status, message = self._status_map.get(test, ("success", None))
        self.records.append(
            TestRecord(
                id=str(test.id()),
                status=status,
                duration=duration,
                message=message,
            )
        )
        super().stopTest(test)

    def addSuccess(self, test: unittest.case.TestCase) -> None:  # noqa: N802 (unittest API)
        self._status_map[test] = ("success", None)
        super().addSuccess(test)

    def addFailure(self, test: unittest.case.TestCase, err) -> None:  # noqa: N802 (unittest API)
        self._status_map[test] = ("failure", self._exc_info_to_string(err, test))
        super().addFailure(test, err)

    def addError(self, test: unittest.case.TestCase, err) -> None:  # noqa: N802 (unittest API)
        self._status_map[test] = ("error", self._exc_info_to_string(err, test))
        super().addError(test, err)

    def addSkip(self, test: unittest.case.TestCase, reason: str) -> None:  # noqa: N802 (unittest API)
        self._status_map[test] = ("skipped", reason)
        super().addSkip(test, reason)


class TrackingTestRunner(unittest.TextTestRunner):
    resultclass = TrackingTestResult

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("verbosity", 2)
        super().__init__(*args, **kwargs)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run project tests with optional HTML summary.")
    parser.add_argument("--pattern", default="test*.py", help="Glob pattern for unittest discovery (default: test*.py)")
    parser.add_argument("--start-dir", default="tests", help="Directory to start discovery (default: tests)")
    parser.add_argument("--top-level-dir", default=None, help="Project top-level directory")
    parser.add_argument("--html", action="store_true", help="Generate HTML report under test_reports/")
    parser.add_argument("--report-name", default=None, help="Custom HTML report filename (default: timestamped)")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first failure")
    return parser.parse_args(argv)


def ensure_env_vars() -> None:
    """Set fallback values for configuration env vars to avoid import errors."""
    os.environ.setdefault("API_ID", os.environ.get("API_ID", "123456"))
    os.environ.setdefault("API_HASH", os.environ.get("API_HASH", "testhash"))
    os.environ.setdefault("PHONE", os.environ.get("PHONE", "+10000000000"))


def build_summary(result: TrackingTestResult) -> str:
    passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)

    lines = [
        "\n=== Test Summary ===",
        f"Total: {result.testsRun}",
        f"Passed: {passed}",
        f"Failures: {len(result.failures)}",
        f"Errors: {len(result.errors)}",
        f"Skipped: {len(result.skipped)}",
    ]
    return "\n".join(lines)


def write_html_report(result: TrackingTestResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows = []
    for record in getattr(result, "records", []):
        safe_message = (record.message or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        rows.append(
            f"<tr class='{record.status}'>"
            f"<td>{record.id}</td>"
            f"<td>{record.status.title()}</td>"
            f"<td>{record.duration:.3f}s</td>"
            f"<td><pre>{safe_message}</pre></td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>Test Report</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 2rem; }}
h1 {{ margin-bottom: 0.5rem; }}
.summary {{ margin-bottom: 1.5rem; }}
summary-item {{ display: inline-block; margin-right: 1rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; }}
tr.success {{ background: #f0fff4; }}
tr.failure, tr.error {{ background: #fff5f5; }}
tr.skipped {{ background: #fdf6b2; }}
pre {{ white-space: pre-wrap; margin: 0; font-family: Menlo, Monaco, Consolas, monospace; }}
</style>
</head>
<body>
<h1>Test Report</h1>
<p class='summary'>Generated at {generated_at}. Total tests: {result.testsRun}</p>
<table>
<thead>
<tr><th>Test</th><th>Status</th><th>Duration</th><th>Message</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    ensure_env_vars()
    args = parse_args(argv)

    loader = unittest.defaultTestLoader
    tests = loader.discover(
        start_dir=args.start_dir,
        pattern=args.pattern,
        top_level_dir=args.top_level_dir,
    )

    runner = TrackingTestRunner(failfast=args.fail_fast, buffer=True)
    print("Running tests...", file=sys.stderr)
    result = runner.run(tests)

    print(build_summary(result))

    if args.html:
        report_name = args.report_name or f"report_{dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        report_path = REPORT_DIR / report_name
        write_html_report(result, report_path)
        print(f"HTML report written to {report_path}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

import pytest
from scripts.summarize_http import summarize


def test_http_summary_reports_p95_and_consistent_counts():
    rows = [
        {"mode": "local", "ok": "1", "http_ms": str(i), "count": "20"}
        for i in range(1, 21)
    ] + [
        {"mode": "onion", "ok": "1", "http_ms": str(i * 10), "count": "20"}
        for i in range(1, 21)
    ]
    result = summarize(rows)
    assert result["local"]["median_http_ms"] == 10.5
    assert result["local"]["p95_http_ms"] == 19.0
    assert result["onion"]["p95_http_ms"] == 190.0
    assert result["same_record_count_across_paths"] is True


def test_http_summary_handles_failures_and_mismatches():
    rows = [
        {"mode": "local", "ok": "1", "http_ms": "2", "count": "3"},
        {"mode": "local", "ok": "0", "http_ms": "90", "count": ""},
        {"mode": "onion", "ok": "1", "http_ms": "12", "count": "4"},
    ]
    result = summarize(rows)
    assert result["local"]["failures"] == 1
    assert result["onion"]["failures"] == 0
    assert result["same_record_count_across_paths"] is False


def test_http_summary_works_with_no_successes():
    rows = [
        {"mode": "local", "ok": "0", "http_ms": "20", "count": ""},
        {"mode": "onion", "ok": "0", "http_ms": "40", "count": ""},
    ]
    result = summarize(rows)
    assert result["local"]["p95_http_ms"] is None
    assert result["onion"]["median_http_ms"] is None
    assert result["same_record_count_across_paths"] is False

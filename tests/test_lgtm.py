"""Tests for core.lgtm — Grafana Loki and Alerting payload parsing."""

from __future__ import annotations

import json

from rca_agent.core.lgtm import extract_traceback_from_lgtm, parse_lgtm_payload


def test_parse_grafana_alert_payload():
    alert_payload = json.dumps({
        "receiver": "rca-agent",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "ServiceHigh5xx",
                    "service": "orders-api",
                },
                "annotations": {
                    "summary": "5xx error rate exceeded 5%",
                    "description": "Traceback (most recent call last):\n  File 'src/order.py', line 50\nValueError: Invalid order",
                },
                "startsAt": "2026-10-20T17:00:00Z",
            }
        ],
    })
    entries = parse_lgtm_payload(alert_payload)
    assert len(entries) == 1
    assert entries[0].source_type == "grafana_alert"
    assert entries[0].service_name == "orders-api"
    assert "ValueError: Invalid order" in entries[0].message


def test_parse_loki_stream_payload():
    loki_payload = json.dumps({
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service": "checkout-svc", "env": "prod"},
                    "values": [
                        ["1713600000000000000", "2026-10-20 17:01:00 ERROR [checkout-svc] NullPointerException in payment.go:42"]
                    ],
                }
            ],
        },
    })
    entries = parse_lgtm_payload(loki_payload)
    assert len(entries) == 1
    assert entries[0].source_type == "loki_stream"
    assert entries[0].service_name == "checkout-svc"
    assert "NullPointerException" in entries[0].message


def test_extract_traceback_from_lgtm():
    loki_payload = json.dumps({
        "status": "success",
        "data": {
            "resultType": "streams",
            "result": [
                {
                    "stream": {"service": "api-gateway"},
                    "values": [
                        ["1713600000000000000", "Traceback (most recent call last):\n  File 'app.py', line 10\nZeroDivisionError"]
                    ],
                }
            ],
        },
    })
    extracted = extract_traceback_from_lgtm(loki_payload)
    assert "api-gateway" in extracted
    assert "ZeroDivisionError" in extracted

"""LGTM Stack (Loki, Grafana, Tempo, Mimir) Log & Alert Ingestion Adapter.

Normalizes log streams from Grafana Loki query exports, Grafana Alerting webhooks,
and Tempo distributed trace error spans into structured logs for autonomous triage.
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class LGTMLogEntry:
    """Normalized log record extracted from an LGTM stack source."""

    source_type: str  # "loki_stream", "grafana_alert", "tempo_trace"
    service_name: str | None
    timestamp: str | None
    message: str
    labels: dict[str, str]


def parse_lgtm_payload(payload_text: str) -> list[LGTMLogEntry]:
    """Parse JSON or raw log exports from Grafana Loki or Grafana Alerting webhooks.

    Supports:
    - Grafana Loki query API response (JSON)
    - Grafana unified alerting webhook payload (JSON)
    - Grafana Tempo trace JSON
    - Plain text log extracts
    """
    entries: list[LGTMLogEntry] = []

    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError:
        # Plain text logs from Loki / Grafana explore view
        return [
            LGTMLogEntry(
                source_type="raw_text",
                service_name=None,
                timestamp=None,
                message=payload_text,
                labels={},
            )
        ]

    # Case 1: Grafana Alerting Webhook Payload (has "alerts" array)
    if isinstance(data, dict) and "alerts" in data:
        for alert in data.get("alerts", []):
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            msg = annotations.get("description") or annotations.get("summary") or alert.get("generatorURL", "")
            entries.append(
                LGTMLogEntry(
                    source_type="grafana_alert",
                    service_name=labels.get("service") or labels.get("app") or labels.get("job"),
                    timestamp=alert.get("startsAt"),
                    message=msg,
                    labels=labels,
                )
            )
        return entries

    # Case 2: Grafana Loki Query API response (data.resultType == "streams")
    if isinstance(data, dict) and "data" in data and "result" in data.get("data", {}):
        results = data["data"].get("result", [])
        for res in results:
            stream_labels = res.get("stream", {})
            service = stream_labels.get("service") or stream_labels.get("app") or stream_labels.get("job")
            for val in res.get("values", []):
                if isinstance(val, list) and len(val) >= 2:
                    ts_ns, log_line = val[0], val[1]
                    entries.append(
                        LGTMLogEntry(
                            source_type="loki_stream",
                            service_name=service,
                            timestamp=str(ts_ns),
                            message=log_line,
                            labels=stream_labels,
                        )
                    )
        return entries

    # Case 3: Tempo Trace or generic JSON containing error fields
    if isinstance(data, dict):
        error_msg = data.get("error") or data.get("message") or str(data)
        return [
            LGTMLogEntry(
                source_type="generic_json",
                service_name=data.get("service"),
                timestamp=data.get("timestamp"),
                message=str(error_msg),
                labels={},
            )
        ]

    return entries


def extract_traceback_from_lgtm(payload_text: str) -> str:
    """Extract and aggregate all error logs / tracebacks from an LGTM payload."""
    entries = parse_lgtm_payload(payload_text)
    if not entries:
        return payload_text

    aggregated_lines: list[str] = []
    for entry in entries:
        header = f"[Source: {entry.source_type}"
        if entry.service_name:
            header += f" | Service: {entry.service_name}"
        if entry.timestamp:
            header += f" | Time: {entry.timestamp}"
        header += "]"
        aggregated_lines.append(f"{header}\n{entry.message}")

    return "\n\n".join(aggregated_lines)

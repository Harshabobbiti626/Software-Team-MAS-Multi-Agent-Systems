"""
OpenTelemetry (OTLP) Production Trace Exporter for MAS.
Formats execution spans into standard OpenTelemetry JSON payloads and exports them
to local telemetry sinks, files, or corporate APM endpoints (Datadog, Jaeger, Honeycomb, GCP).
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

from mas.observability.tracer import TraceSpan

logger = logging.getLogger(__name__)


class OTLPTraceExporter:
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        output_file_path: Optional[str] = ".mas_traces.jsonl",
        service_name: str = "mas-multi-agent-system"
    ):
        self.endpoint_url = endpoint_url
        self.output_file_path = Path(output_file_path) if output_file_path else None
        self.service_name = service_name

    def format_span_to_otlp(self, span: TraceSpan) -> Dict[str, Any]:
        """
        Converts internal TraceSpan to OpenTelemetry v1 OTLP JSON span specification.
        """
        start_nano = int(span.start_time.timestamp() * 1e9)
        end_nano = start_nano + int(span.duration_ms * 1e6)

        attributes = [
            {"key": "service.name", "value": {"stringValue": self.service_name}},
            {"key": "mas.task_id", "value": {"stringValue": span.task_id}},
            {"key": "mas.agent_name", "value": {"stringValue": span.agent_name}},
            {"key": "mas.agent_role", "value": {"stringValue": span.agent_role}},
            {"key": "mas.operation", "value": {"stringValue": span.operation}},
            {"key": "llm.prompt_tokens", "value": {"intValue": str(span.prompt_tokens)}},
            {"key": "llm.candidate_tokens", "value": {"intValue": str(span.candidate_tokens)}},
            {"key": "llm.thinking_tokens", "value": {"intValue": str(span.thinking_tokens)}},
            {"key": "llm.total_tokens", "value": {"intValue": str(span.total_tokens)}},
        ]

        for k, v in span.attributes.items():
            attributes.append({"key": f"mas.custom.{k}", "value": {"stringValue": str(v)}})

        status_code = 1 if span.status == "OK" else 2  # 1 = STATUS_CODE_OK, 2 = STATUS_CODE_ERROR

        return {
            "traceId": span.task_id.replace("-", "").ljust(32, "0")[:32],
            "spanId": span.span_id.replace("-", "").ljust(16, "0")[:16],
            "parentSpanId": span.parent_span_id.replace("-", "").ljust(16, "0")[:16] if span.parent_span_id else "",
            "name": f"{span.agent_role}.{span.operation}",
            "kind": 1,  # SPAN_KIND_INTERNAL
            "startTimeUnixNano": str(start_nano),
            "endTimeUnixNano": str(end_nano),
            "attributes": attributes,
            "status": {
                "code": status_code,
                "message": span.status
            }
        }

    def export_spans(self, spans: List[TraceSpan]) -> bool:
        if not spans:
            return True

        otlp_spans = [self.format_span_to_otlp(s) for s in spans]
        otlp_payload = {
            "resourceSpans": [
                {
                    "resource": {
                        "attributes": [
                            {"key": "service.name", "value": {"stringValue": self.service_name}}
                        ]
                    },
                    "scopeSpans": [
                        {
                            "scope": {"name": "mas.tracer", "version": "0.1.0"},
                            "spans": otlp_spans
                        }
                    ]
                }
            ]
        }

        # 1. File export
        if self.output_file_path:
            try:
                self.output_file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.output_file_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(otlp_payload) + "\n")
            except Exception as e:
                logger.error(f"Failed to write OTLP spans to file: {e}")

        # 2. HTTP OTLP export
        if self.endpoint_url:
            try:
                res = requests.post(
                    self.endpoint_url,
                    json=otlp_payload,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                return res.status_code in [200, 202]
            except Exception as e:
                logger.warning(f"Could not reach remote OTLP endpoint {self.endpoint_url}: {e}")
                return False

        return True


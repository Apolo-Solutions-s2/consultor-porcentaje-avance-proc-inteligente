import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from flask import jsonify
import functions_framework

import google.auth
from google.api_core.exceptions import PermissionDenied, GoogleAPICallError
from google.cloud.logging_v2.services.logging_service_v2 import LoggingServiceV2Client
from google.cloud.logging_v2.types import ListLogEntriesRequest
from google.protobuf.json_format import MessageToDict

logging.basicConfig(level=logging.INFO, force=True)


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_project_id() -> str:
    _, project_id = google.auth.default()
    if not project_id:
        raise RuntimeError("No se pudo resolver project_id via google.auth.default()")
    return project_id


def _extract_json_from_textpayload(text_payload: str) -> Optional[Dict[str, Any]]:
    # Tus logs vienen como: INFO:root:{...json...}
    if not text_payload:
        return None
    i = text_payload.find("{")
    if i < 0:
        return None
    candidate = text_payload[i:].strip()
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


@functions_framework.http
def progress_consultor(request):
    if request.method != "POST":
        return jsonify({"error": "Method not allowed"}), 405

    data = request.get_json(silent=True) or {}
    run_id = str(data.get("run_id", "")).strip()
    if not run_id:
        return jsonify({"error": "run_id is required"}), 400

    resource_type = str(data.get("resource_type", "cloud_run_revision")).strip()
    service_name = str(data.get("service_name", "")).strip()  # opcional

    try:
        project_id = _get_project_id()
    except Exception as e:
        logging.exception("Project id resolution failed")
        return jsonify({"error": "project_id_resolution_failed", "details": str(e)}), 500

    # Buscamos el ÚLTIMO evento "progress" de ese run_id
    flt = (
        f'resource.type="{resource_type}" '
        f'AND textPayload:"\\"event_type\\": \\"progress\\"" '
        f'AND textPayload:"\\"run_id\\": \\"{run_id}\\""'
    )
    if service_name:
        flt += f' AND resource.labels.service_name="{service_name}"'

    client = LoggingServiceV2Client()

    try:
        req = ListLogEntriesRequest(
            resource_names=[f"projects/{project_id}"],
            filter=flt,
            order_by="timestamp desc",
            page_size=1,  # aquí SÍ va, dentro del request proto
        )
        it = client.list_log_entries(request=req)
        entry = next(iter(it), None)

    except PermissionDenied as e:
        return jsonify({
            "error": "permission_denied",
            "details": str(e),
            "hint": "Da roles/logging.viewer al service account del consultor.",
        }), 403
    except GoogleAPICallError as e:
        logging.exception("Logging API call failed")
        return jsonify({"error": "logging_api_error", "details": str(e)}), 502
    except Exception as e:
        logging.exception("Unexpected error")
        return jsonify({"error": "unexpected_error", "details": str(e)}), 500

    if entry is None:
        return jsonify({
            "found": False,
            "run_id": run_id,
            "checked_at_utc": _utc_iso(),
            "filter": flt,
        }), 404

    payload: Optional[Dict[str, Any]] = None
    if entry.json_payload:
        payload = MessageToDict(entry.json_payload, preserving_proto_field_name=True)
    elif entry.text_payload:
        payload = _extract_json_from_textpayload(entry.text_payload)

    if not payload:
        return jsonify({
            "found": True,
            "run_id": run_id,
            "checked_at_utc": _utc_iso(),
            "warning": "Found log entry but could not parse payload",
        }), 200

    return jsonify({
        "found": True,
        "run_id": run_id,
        "percent": payload.get("percent"),
        "step": payload.get("step"),
        "ts_utc": payload.get("ts_utc"),
        "checked_at_utc": _utc_iso(),
    }), 200
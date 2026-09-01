#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = REPO_ROOT / "documentation"
START_MARKER = "<!-- AUTO-GENERATED:TOOL-SCHEMA START -->"
END_MARKER = "<!-- AUTO-GENERATED:TOOL-SCHEMA END -->"

TOOL_PAGES = {
    "ocr": DOCS_ROOT / "content/platform-api/tool-ocr.mdx",
    "image_tag": DOCS_ROOT / "content/platform-api/tool-image-tag.mdx",
    "caption": DOCS_ROOT / "content/platform-api/tool-caption.mdx",
    "image_celebrity_recognition": DOCS_ROOT / "content/platform-api/tool-image-celebrity-recognition.mdx",
    "video_celebrity_recognition": DOCS_ROOT / "content/platform-api/tool-video-celebrity-recognition.mdx",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _as_object(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _read_json(url: str) -> Dict[str, Any]:
    with urlopen(url) as response:  # noqa: S310 - local/internal URL controlled by operator
        return json.loads(response.read().decode("utf-8"))


def _json_block(payload: Dict[str, Any]) -> str:
    return "```json\n" + json.dumps(payload, indent=2, ensure_ascii=True) + "\n```"


def _bash_block(content: str) -> str:
    return "```bash\n" + content.rstrip() + "\n```"


def _schema_title(schema: Dict[str, Any], fallback: str) -> str:
    return _clean(schema.get("title")) or fallback


def _example_string(field_key: str, tool_slug: str) -> str:
    key = _clean(field_key).lower()
    if key in {"image", "image_url", "media", "media_url"}:
        return "https://example.com/editorial-image.jpg"
    if key in {"video", "video_url"}:
        return "https://example.com/news-clip.mp4"
    if key in {"audio", "audio_url"}:
        return "https://example.com/audio-clip.mp3"
    if key in {"language"}:
        return "English"
    if key in {"lang"}:
        return "en"
    if key == "mode":
        return "Editorial" if tool_slug == "caption" else "editorial"
    if key == "event":
        return "Champions League final"
    if key == "city":
        return "Madrid"
    if key == "country":
        return "Spain"
    if key.endswith("_id"):
        return "example-id"
    if key.endswith("_ids"):
        return "example-scope"
    if key == "caption":
        return "Players celebrate on the pitch after the final whistle in Madrid."
    if key in {"text", "ocr"}:
        return "WESOG SUMMIT 2026"
    if key == "label":
        return "Example celebrity"
    if key == "id":
        return "Q1"
    if key in {"uri", "url"}:
        return "https://example.com/resource"
    return f"example-{key or 'value'}"


def _example_value(schema_like: Any, *, field_key: str, tool_slug: str, depth: int = 0) -> Any:
    schema = _as_object(schema_like)
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        schema_type = next((item for item in schema_type if isinstance(item, str) and item != "null"), "string")
    if schema.get("enum"):
        enum_values = [item for item in _as_list(schema.get("enum")) if item is not None]
        if enum_values:
            return enum_values[0]
    if schema_type == "object" or (not schema_type and schema.get("properties")):
        properties = _as_object(schema.get("properties"))
        required = {
            _clean(item)
            for item in _as_list(schema.get("required"))
            if _clean(item)
        }
        out: Dict[str, Any] = {}
        for key, subschema in properties.items():
            clean_key = _clean(key)
            if not clean_key:
                continue
            if required and clean_key not in required and depth > 0:
                continue
            out[clean_key] = _example_value(subschema, field_key=clean_key, tool_slug=tool_slug, depth=depth + 1)
        return out
    if schema_type == "array":
        if field_key in {"keywords", "tags"}:
            return ["politics", "press conference", "government"]
        if field_key == "colors":
            return ["#102030", "#d1d5db"]
        if field_key == "item_keys":
            return ["root"]
        if field_key == "category_entity_ids":
            return ["politics", "sports"]
        if field_key == "collection_entity_ids":
            return ["editorial-celebrities"]
        item_schema = _as_object(schema.get("items"))
        return [_example_value(item_schema, field_key=field_key, tool_slug=tool_slug, depth=depth + 1)]
    if schema_type == "integer":
        if field_key in {"start_ms", "end_ms"}:
            return 2500 if field_key == "start_ms" else 7100
        if field_key in {"timeout_ms", "timings_ms"}:
            return 5000 if field_key == "timeout_ms" else 420
        return 1
    if schema_type == "number":
        return 0.98
    if schema_type == "boolean":
        if field_key == "colors":
            return False
        return True
    return _example_string(field_key, tool_slug)


def _build_request_schema(input_schema_like: Any) -> Dict[str, Any]:
    input_schema = _as_object(input_schema_like)
    properties = _as_object(input_schema.get("properties"))
    required = [_clean(item) for item in _as_list(input_schema.get("required")) if _clean(item)]
    out_properties = {key: value for key, value in properties.items() if _clean(key)}
    out_properties["timeout_ms"] = {
        "type": "integer",
        "description": "Optional timeout override in milliseconds. If omitted, the API waits about 5000 ms before returning 202 Accepted.",
    }
    return {
        "type": "object",
        "required": required,
        "properties": out_properties,
    }


def _build_completed_response_schema(output_schema_like: Any) -> Dict[str, Any]:
    output_schema = _as_object(output_schema_like)
    return output_schema if output_schema else {"type": "object"}


def _build_accepted_response_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "required": ["run_id", "status", "response_mode", "poll_path"],
        "properties": {
            "run_id": {"type": "string"},
            "status": {
                "type": "string",
                "enum": ["queued", "running", "succeeded", "failed", "timeout"],
            },
            "response_mode": {
                "type": "string",
                "enum": ["accepted"],
            },
            "poll_path": {"type": "string"},
        },
    }


def _format_field_type(field: Dict[str, Any]) -> str:
    field_type = field.get("type")
    if isinstance(field_type, list):
        values = [str(item) for item in field_type if _clean(item)]
        return " | ".join(values) or "string"
    clean_type = _clean(field_type)
    return clean_type or "string"


def _field_table(fields: Iterable[Dict[str, Any]], *, include_required: bool) -> str:
    items = [field for field in fields if isinstance(field, dict)]
    if not items:
        return "_No published fields available for this tool version._"
    if include_required:
        lines = [
            "| Field | Type | Required | Notes |",
            "|------|------|----------|-------|",
        ]
        for field in items:
            lines.append(
                "| `{key}` | `{field_type}` | {required} | {notes} |".format(
                    key=_clean(field.get("key")) or "-",
                    field_type=_format_field_type(field),
                    required="Yes" if bool(field.get("required")) else "No",
                    notes=_clean(field.get("description")) or "-",
                )
            )
        return "\n".join(lines)
    lines = [
        "| Field | Type | Notes |",
        "|------|------|-------|",
    ]
    for field in items:
        lines.append(
            "| `{key}` | `{field_type}` | {notes} |".format(
                key=_clean(field.get("key")) or "-",
                field_type=_format_field_type(field),
                notes=_clean(field.get("description")) or "-",
            )
        )
    return "\n".join(lines)


def _build_request_example(tool_slug: str, schema_payload: Dict[str, Any]) -> Dict[str, Any]:
    version = _as_object(schema_payload.get("published_version"))
    input_schema = _as_object(version.get("input_schema"))
    example_input = _example_value(input_schema, field_key="input", tool_slug=tool_slug, depth=0)
    if not isinstance(example_input, dict):
        example_input = {}
    return example_input


def _build_completed_response_example(tool_slug: str, schema_payload: Dict[str, Any]) -> Dict[str, Any]:
    version = _as_object(schema_payload.get("published_version"))
    output_schema = _as_object(version.get("output_schema"))
    outputs = _example_value(output_schema, field_key="outputs", tool_slug=tool_slug, depth=0)
    if not isinstance(outputs, dict):
        outputs = {}
    return outputs


def _build_accepted_response_example(tool_slug: str, schema_payload: Dict[str, Any]) -> Dict[str, Any]:
    version = _as_object(schema_payload.get("published_version"))
    api_contract = _as_object(version.get("api_contract"))
    run_status = _as_object(api_contract.get("run_status"))
    run_token = tool_slug.replace("_", "-")
    poll_path = _clean(run_status.get("path")).replace("{run_id}", f"run-{run_token}-queued")
    return {
        "run_id": f"run-{run_token}-queued",
        "status": "running",
        "response_mode": "accepted",
        "poll_path": poll_path,
    }


def _build_curl_example(base_origin: str, tool_slug: str, schema_payload: Dict[str, Any]) -> str:
    version = _as_object(schema_payload.get("published_version"))
    api_contract = _as_object(version.get("api_contract"))
    run_sync = _as_object(api_contract.get("run_sync"))
    request_payload = _build_request_example(tool_slug, schema_payload)
    path = _clean(run_sync.get("path")) or f"/api/v1/tools/{tool_slug}"
    media_field_keys = [
        _clean(field.get("key"))
        for field in _as_list(api_contract.get("input_fields"))
        if _clean(field.get("key")) and "media" in _clean(field.get("widget")).lower()
    ]
    if not media_field_keys:
        input_schema = _as_object(version.get("input_schema"))
        for key, schema_like in _as_object(input_schema.get("properties")).items():
            schema = _as_object(schema_like)
            if _clean(schema.get("x-wesog-input-kind")) in {"image", "video", "audio", "document", "file", "asset", "media"}:
                media_field_keys.append(_clean(key))
    if media_field_keys:
        primary_media_field = media_field_keys[0]
        lines = [
            f"curl -X POST '{base_origin.rstrip('/')}{path}' \\",
            "  -H 'X-API-Key: <TENANT_API_KEY>' \\",
            f"  -F '{primary_media_field}=@/absolute/path/to/example.file' \\",
        ]
        for key, value in request_payload.items():
            if key == primary_media_field:
                continue
            lines.append(f"  -F '{key}={json.dumps(value, ensure_ascii=True) if isinstance(value, (dict, list, bool)) else value}' \\")
        return "\n".join(lines).rstrip(" \\")
    body = json.dumps(request_payload, indent=2, ensure_ascii=True)
    return (
        f"curl -X POST '{base_origin.rstrip('/')}{path}' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        "  -H 'X-API-Key: <TENANT_API_KEY>' \\\n"
        f"  -d '{body}'"
    )


def _generated_block(base_origin: str, tool_slug: str, schema_payload: Dict[str, Any]) -> str:
    version = _as_object(schema_payload.get("published_version"))
    input_schema = _as_object(version.get("input_schema"))
    output_schema = _as_object(version.get("output_schema"))
    api_contract = _as_object(version.get("api_contract"))
    input_fields = _as_list(api_contract.get("input_fields"))
    output_fields = _as_list(api_contract.get("output_fields"))
    request_schema = _build_request_schema(input_schema)
    completed_response_schema = _build_completed_response_schema(output_schema)
    accepted_response_schema = _build_accepted_response_schema()
    parts = [
        START_MARKER,
        "<!-- Regenerate with: python3 documentation/scripts/generate_tool_docs_from_api.py -->",
        "",
        "## Input schema",
        "",
        f"This top-level request schema is generated from the published `{_schema_title(input_schema, 'input')}` schema currently exposed by Core.",
        "",
        _json_block(request_schema),
        "",
        "## Input fields",
        "",
        _field_table(input_fields, include_required=True),
        "",
        "## Output schema",
        "",
        "The `200` response returns the workflow output object directly. If the run exceeds the wait timeout, the API returns `202 Accepted` with a polling envelope.",
        "",
        _json_block(completed_response_schema),
        "",
        "## Deferred response schema",
        "",
        _json_block(accepted_response_schema),
        "",
        "## Output fields",
        "",
        _field_table(output_fields, include_required=False),
        "",
        "## Request example",
        "",
        "Use `multipart/form-data` as the primary interactive mode in Swagger UI for media tools. It renders media inputs more clearly than `application/json`.",
        "",
        _bash_block(_build_curl_example(base_origin, tool_slug, schema_payload)),
        "",
        "## Completed response example",
        "",
        _json_block(_build_completed_response_example(tool_slug, schema_payload)),
        "",
        "## Deferred response contract",
        "",
        _json_block(_build_accepted_response_example(tool_slug, schema_payload)),
        "",
        END_MARKER,
    ]
    return "\n".join(parts)


def _replace_generated_block(page_path: Path, generated_block: str) -> bool:
    original = page_path.read_text(encoding="utf-8")
    start = original.find(START_MARKER)
    end = original.find(END_MARKER)
    if start < 0 or end < 0 or end < start:
        raise ValueError(f"Missing auto-generated markers in {page_path}")
    end += len(END_MARKER)
    updated = original[:start] + generated_block + original[end:]
    if updated == original:
        return False
    page_path.write_text(updated, encoding="utf-8")
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate per-tool Mintlify schema sections from Core public tool schema endpoints.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:3333",
        help="Base URL for the Core API that exposes /api/tools/{tool_slug}/schema.json.",
    )
    parser.add_argument(
        "--tool",
        action="append",
        dest="tools",
        help="Optional tool slug to regenerate. Repeat to limit the run to multiple tools.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    selected = set(args.tools or TOOL_PAGES.keys())
    unknown = sorted(selected.difference(TOOL_PAGES.keys()))
    if unknown:
        print(f"Unknown tool slugs: {', '.join(unknown)}", file=sys.stderr)
        return 2

    changed = 0
    for tool_slug in sorted(selected):
        schema_url = f"{args.base_url.rstrip('/')}/api/tools/{tool_slug}/schema.json"
        page_path = TOOL_PAGES[tool_slug]
        try:
            schema_payload = _read_json(schema_url)
        except HTTPError as exc:
            print(f"{tool_slug}: failed to fetch {schema_url} ({exc.code})", file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"{tool_slug}: failed to reach {schema_url} ({exc.reason})", file=sys.stderr)
            return 1
        generated = _generated_block("https://api.wesog.com", tool_slug, schema_payload)
        if _replace_generated_block(page_path, generated):
            changed += 1
            print(f"updated {page_path.relative_to(REPO_ROOT)}")
        else:
            print(f"unchanged {page_path.relative_to(REPO_ROOT)}")
    print(f"done: {changed} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

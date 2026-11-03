"""Exports the OpenAPI schema of the FastAPI app into Postman Collection v2.1.0 format."""

import json
from pathlib import Path
from app.main import app

OUTPUT_FILE = Path(__file__).resolve().parent / "postman_collection.json"


def export_openapi_to_postman(output_path: Path = OUTPUT_FILE) -> dict:
    openapi_schema = app.openapi()
    title = openapi_schema.get("info", {}).get("title", "Smart Leads Agent for Hoardings API")
    description = openapi_schema.get("info", {}).get("description", "")

    items = []
    base_url = "{{baseUrl}}"

    for path, methods in openapi_schema.get("paths", {}).items():
        for method, spec in methods.items():
            method_upper = method.upper()
            summary = spec.get("summary", f"{method_upper} {path}")
            endpoint_desc = spec.get("description", "")

            # Path segments
            url_path = [segment for segment in path.strip("/").split("/") if segment]
            # Replace {param} in path for Postman
            url_path_postman = [p.replace("{", ":").replace("}", "") for p in url_path]

            # Query params
            query_params = []
            for param in spec.get("parameters", []):
                if param.get("in") == "query":
                    query_params.append({
                        "key": param.get("name"),
                        "value": str(param.get("schema", {}).get("default", "")),
                        "description": param.get("description", ""),
                    })

            # URL variables
            url_vars = []
            for param in spec.get("parameters", []):
                if param.get("in") == "path":
                    url_vars.append({
                        "key": param.get("name"),
                        "value": "HRD-106" if param.get("name") == "site_id" else "CUST-38",
                        "description": param.get("description", ""),
                    })

            request_obj = {
                "method": method_upper,
                "header": [
                    {"key": "Accept", "value": "application/json"},
                ],
                "url": {
                    "raw": f"{base_url}{path}",
                    "host": [base_url],
                    "path": url_path_postman,
                },
                "description": endpoint_desc or summary,
            }

            if query_params:
                request_obj["url"]["query"] = query_params
            if url_vars:
                request_obj["url"]["variable"] = url_vars

            # Body for POST
            if method_upper in ["POST", "PUT", "PATCH"]:
                request_obj["header"].append({"key": "Content-Type", "value": "application/json"})
                if "pitch" in path:
                    sample_body = {
                        "site_id": "HRD-106",
                        "customer_id": "CUST-38"
                    }
                else:
                    sample_body = {}
                request_obj["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(sample_body, indent=2),
                }

            items.append({
                "name": summary,
                "request": request_obj,
                "response": [],
            })

    collection = {
        "info": {
            "name": title,
            "description": description,
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "version": openapi_schema.get("info", {}).get("version", "1.0.0"),
        },
        "variable": [
            {
                "key": "baseUrl",
                "value": "http://127.0.0.1:8000",
                "type": "string",
            }
        ],
        "item": items,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)

    print(f"Exported Postman Collection with {len(items)} endpoints to {output_path}")
    return collection


if __name__ == "__main__":
    export_openapi_to_postman()

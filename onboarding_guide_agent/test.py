import requests
import json

API_BASE_URL = "http://localhost:8008"
OPENAPI_JSON_URL = f"{API_BASE_URL}/openapi.json"

# Predefined payloads for specific endpoints based on the provided API spec details
PREDEFINED_PAYLOADS = {
    "/chat": {
        "user_id": "user_123",
        "session_id": "session_abc",
        "current_step": 2,
        "user_message": "My OTP isn't arriving!"
    },
    "/log_interaction": {
        "user_id": "user_123",
        "session_id": "session_001",
        "step_id": "2",
        "step_name": "WhatsApp Optimization",
        "success": True,
        "conversation_turns": [
            {"role": "user", "content": "How do I trigger OTP?", "timestamp": "2026-03-30T10:00:00Z"},
            {"role": "assistant", "content": "Click the big blue button.", "timestamp": "2026-03-30T10:01:00Z"}
        ],
        "resolution_path": ["initial_question", "success"],
        "time_to_resolution_seconds": 60,
        "user_satisfaction_score": 5,
        "metadata": {
            "issue_category": "whatsapp_otp"
        }
    }
}

def get_openapi_spec():
    try:
        response = requests.get(OPENAPI_JSON_URL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Failed to fetch OpenAPI spec: {e}")
        return None

def test_endpoint(method, url, base_url):
    full_url = base_url + url
    try:
        # Use predefined payload if available and method is POST/PUT/PATCH
        payload = None
        if method in ["post", "put", "patch"]:
            # Use exact path match first
            if url in PREDEFINED_PAYLOADS:
                payload = PREDEFINED_PAYLOADS[url]
            else:
                # If no predefined payload, send empty JSON to avoid errors
                payload = {}

        if method == "get":
            resp = requests.get(full_url)
        elif method == "post":
            resp = requests.post(full_url, json=payload)
        elif method == "put":
            resp = requests.put(full_url, json=payload)
        elif method == "delete":
            resp = requests.delete(full_url)
        elif method == "patch":
            resp = requests.patch(full_url, json=payload)
        else:
            print(f"Unsupported method {method} for {full_url}")
            return

        # Try to parse JSON response for summary
        try:
            resp_json = resp.json()
            summary = json.dumps(resp_json, indent=2)[:500]  # limit output length
        except Exception:
            summary = resp.text[:500]

        print(f"{method.upper()} {full_url} -> Status: {resp.status_code}")
        print(f"Response preview:\n{summary}\n{'-'*60}")

    except Exception as e:
        print(f"Error testing {method.upper()} {full_url}: {e}")

def main():
    spec = get_openapi_spec()
    if not spec:
        return

    paths = spec.get("paths", {})
    print(f"Found {len(paths)} paths in OpenAPI spec.")

    for path, methods in paths.items():
        for method in methods.keys():
            test_endpoint(method.lower(), path, API_BASE_URL)

if __name__ == "__main__":
    main()
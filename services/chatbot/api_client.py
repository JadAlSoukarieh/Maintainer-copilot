from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class ApiClientError(RuntimeError):
    pass


@dataclass(slots=True)
class ApiClient:
    base_url: str
    token: str | None = None
    timeout_seconds: float = 12.0

    def health(self) -> dict[str, Any]:
        return self.get("/health")

    def ready(self) -> dict[str, Any]:
        return self.get("/ready")

    def login(self, email: str, password: str) -> dict[str, Any]:
        return self.post("/auth/login", {"email": email, "password": password}, auth=False)

    def me(self) -> dict[str, Any]:
        return self.get("/auth/me")

    def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/chat", payload)

    def get_memory(self, conversation_id: str) -> dict[str, Any]:
        return self.get(f"/chat/{conversation_id}/memory")

    def list_memory(self) -> dict[str, Any]:
        return self.get("/memory")

    def search_memory(self, query: str, *, mode: str = "hybrid", top_k: int = 10) -> dict[str, Any]:
        return self.post("/memory/search", {"query": query, "mode": mode, "top_k": top_k})

    def list_widgets(self) -> dict[str, Any]:
        return self.get("/admin/widgets")

    def create_widget(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.post("/admin/widgets", payload)

    def update_widget(self, widget_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.patch(f"/admin/widgets/{widget_id}", payload)

    def delete_widget(self, widget_id: str) -> dict[str, Any]:
        return self.delete(f"/admin/widgets/{widget_id}")

    def get_reports_summary(self) -> dict[str, Any]:
        return self.get("/reports/summary", auth=False)

    def get_recent_events(
        self,
        *,
        limit: int = 100,
        event_type: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        query: list[str] = [f"limit={limit}"]
        if event_type:
            query.append(f"event_type={event_type}")
        if request_id:
            query.append(f"request_id={request_id}")
        return self.get(f"/observability/recent?{'&'.join(query)}", auth=False)

    def get(self, path: str, *, auth: bool = True) -> dict[str, Any]:
        return self._request("GET", path, auth=auth)

    def post(self, path: str, payload: dict[str, Any], *, auth: bool = True) -> dict[str, Any]:
        return self._request("POST", path, json=payload, auth=auth)

    def patch(self, path: str, payload: dict[str, Any], *, auth: bool = True) -> dict[str, Any]:
        return self._request("PATCH", path, json=payload, auth=auth)

    def delete(self, path: str, *, auth: bool = True) -> dict[str, Any]:
        return self._request("DELETE", path, auth=auth)

    def probe_model_server(self) -> bool:
        model_base_url = infer_model_server_base_url(self.base_url)
        try:
            response = requests.get(f"{model_base_url.rstrip('/')}/health", timeout=self.timeout_seconds)
        except requests.RequestException:
            return False
        return response.ok

    def _request(self, method: str, path: str, *, auth: bool = True, json: dict[str, Any] | None = None) -> dict[str, Any]:
        headers = {"accept": "application/json"}
        if auth and self.token:
            headers["authorization"] = f"Bearer {self.token}"
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            response = requests.request(method, url, headers=headers, json=json, timeout=self.timeout_seconds)
        except requests.RequestException as exc:
            raise ApiClientError(f"Could not reach API at {self.base_url}.") from exc
        if response.status_code >= 400:
            raise ApiClientError(_error_message(response))
        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiClientError("API returned a non-JSON response.") from exc
        if not isinstance(payload, dict):
            raise ApiClientError("API returned an unexpected response shape.")
        return payload


def _error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"API request failed with HTTP {response.status_code}."
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])
        if payload.get("detail"):
            return str(payload["detail"])
    return f"API request failed with HTTP {response.status_code}."


def infer_model_server_base_url(api_base_url: str) -> str:
    if "localhost" in api_base_url or "127.0.0.1" in api_base_url:
        return "http://localhost:8001"
    return "http://model-server:8001"


def build_widget_snippet(*, api_base_url: str, widget_id: str, widget_url: str) -> str:
    return (
        '<script\n'
        f'  src="{api_base_url.rstrip("/")}/widget.js?public_widget_id={widget_id}"\n'
        f'  data-widget-id="{widget_id}"\n'
        f'  data-api-base-url="{api_base_url.rstrip("/")}"\n'
        f'  data-widget-url="{widget_url.rstrip("/")}">\n'
        "</script>"
    )

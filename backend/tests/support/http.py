import json
from typing import Any

from django.test import AsyncClient

API_PREFIX = "/api/v1"


async def api_get(
    client: AsyncClient,
    path: str,
    *,
    query: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
):
    return await client.get(path, query or {}, headers=headers)


async def api_post_json(
    client: AsyncClient,
    path: str,
    body: dict[str, Any],
    *,
    headers: dict[str, str] | None = None,
):
    return await client.post(
        path,
        data=json.dumps(body),
        content_type="application/json",
        headers=headers,
    )


async def api_put_json(
    client: AsyncClient,
    path: str,
    body: dict[str, Any] | None = None,
    *,
    headers: dict[str, str] | None = None,
):
    return await client.put(
        path,
        data=json.dumps(body or {}),
        content_type="application/json",
        headers=headers,
    )


def assert_ok(response, expected_status: int = 200):
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.content!r}"
    )

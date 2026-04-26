import os
from typing import Any

import httpx


class ApiClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        self.internal_token = os.getenv("INTERNAL_SERVICE_TOKEN", "dev-internal-token")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=15)

    def _headers(self, telegram_id: int | str | None = None) -> dict[str, str]:
        headers = {"X-Internal-Token": self.internal_token}
        if telegram_id is not None:
            headers["X-Telegram-Id"] = str(telegram_id)
        return headers

    async def start_onboarding(self, user: Any, deep_link: str | None = None) -> dict:
        payload = {
            "telegram_id": str(user.id),
            "username": user.username,
            "first_name": user.first_name,
            "telegram_language_code": user.language_code,
            "deep_link": deep_link,
        }
        response = await self.client.post("/api/onboarding/start", json=payload, headers=self._headers(user.id))
        response.raise_for_status()
        return response.json()

    async def complete_onboarding(self, user: Any, data: dict) -> dict:
        payload = {
            "telegram_id": str(user.id),
            "username": user.username,
            "first_name": user.first_name,
            "telegram_language_code": user.language_code,
            **data,
        }
        response = await self.client.post("/api/onboarding/complete", json=payload, headers=self._headers(user.id))
        response.raise_for_status()
        return response.json()

    async def user_summary(self, telegram_id: int | str) -> dict:
        response = await self.client.get(f"/api/onboarding/me/{telegram_id}", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def continue_lesson(self, telegram_id: int | str) -> dict | None:
        response = await self.client.get(f"/api/lessons/continue/{telegram_id}", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def lesson(self, telegram_id: int | str, lesson_id: int) -> dict:
        response = await self.client.get(f"/api/lessons/{lesson_id}", params={"telegram_id": str(telegram_id)}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def start_lesson(self, telegram_id: int | str, lesson_id: int) -> dict:
        response = await self.client.post(f"/api/lessons/{lesson_id}/start", json={"telegram_id": str(telegram_id)}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def submit_exercise(self, telegram_id: int | str, exercise_id: int, lesson_id: int, answer: Any) -> dict:
        response = await self.client.post(
            f"/api/exercises/{exercise_id}/submit",
            json={"telegram_id": str(telegram_id), "lesson_id": lesson_id, "answer": answer},
            headers=self._headers(telegram_id),
        )
        response.raise_for_status()
        return response.json()

    async def review_queue(self, telegram_id: int | str, mistakes_only: bool = False) -> list[dict]:
        response = await self.client.get(f"/api/review/queue/{telegram_id}", params={"mistakes_only": mistakes_only}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def submit_review(self, telegram_id: int | str, review_item_id: int, is_correct: bool, quality: int) -> dict:
        response = await self.client.post(
            f"/api/review/{review_item_id}/submit",
            json={"telegram_id": str(telegram_id), "is_correct": is_correct, "quality": quality, "answer": {}},
            headers=self._headers(telegram_id),
        )
        response.raise_for_status()
        return response.json()

    async def grammar(self, telegram_id: int | str, language: str = "en") -> list[dict]:
        response = await self.client.get("/api/grammar", params={"language": language}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def vocab(self, telegram_id: int | str, language: str = "en") -> list[dict]:
        response = await self.client.get("/api/vocab", params={"language": language}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def progress(self, telegram_id: int | str) -> dict:
        response = await self.client.get(f"/api/progress/{telegram_id}", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def plan(self, telegram_id: int | str) -> dict:
        response = await self.client.get("/api/plan/current", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def streak(self, telegram_id: int | str) -> dict:
        response = await self.client.get("/api/streak", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def scenarios(self, telegram_id: int | str, topic: str | None = None) -> list[dict]:
        response = await self.client.get("/api/scenarios", params={"topic": topic} if topic else {}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def scenario_detail(self, telegram_id: int | str, scenario_id_or_slug: str) -> dict:
        response = await self.client.get(f"/api/scenarios/{scenario_id_or_slug}", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def start_quiz(self, telegram_id: int | str, topic: str | None = None) -> dict:
        response = await self.client.post("/api/quiz/start", json={"topic": topic, "limit": 5}, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def settings(self, telegram_id: int | str) -> dict:
        response = await self.client.get(f"/api/settings/{telegram_id}", headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def update_settings(self, telegram_id: int | str, payload: dict[str, Any]) -> dict:
        response = await self.client.put(f"/api/settings/{telegram_id}", json=payload, headers=self._headers(telegram_id))
        response.raise_for_status()
        return response.json()

    async def premium_catalog(self) -> list[dict]:
        response = await self.client.get("/api/premium/catalog")
        response.raise_for_status()
        return response.json()

    async def close(self) -> None:
        await self.client.aclose()

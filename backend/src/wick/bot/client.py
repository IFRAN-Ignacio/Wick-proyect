"""Wrapper de google-genai (Gemini) con function calling manual y solo herramientas de lectura."""

from __future__ import annotations

import contextlib
import json
from typing import Any

import keyring

from wick.bot import tools
from wick.bot.prompts import SYSTEM_PROMPT
from wick.db.connection import connect

KEYRING_SERVICE = "WICK"
KEYRING_USER = "gemini_api_key"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_STEPS = 8


class BotUnavailable(Exception):
    pass


def get_api_key() -> str | None:
    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)
    except Exception:
        return None


def set_api_key(key: str) -> None:
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key.strip())


def delete_api_key() -> None:
    with contextlib.suppress(Exception):
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)


def get_model() -> str:
    with connect() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key='bot_model'").fetchone()
    return str(row["value"]) if row else DEFAULT_MODEL


def set_model(model: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES ('bot_model', ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (model.strip(),),
        )


def _friendly_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return "Se agotó la cuota gratuita de tu API key por ahora. El resto de WICK sigue funcionando."
    if "API_KEY_INVALID" in text or "API key not valid" in text or "401" in text or "403" in text:
        return "La API key de Gemini no es válida. Revisala en Configuración."
    if "404" in text and "model" in text.lower():
        return "Ese modelo de Gemini no existe o no está disponible para tu key. Cambialo en Configuración."
    return f"No pude hablar con Gemini (¿hay internet?). El resto de WICK sigue funcionando. Detalle: {text[:200]}"


def chat(messages: list[dict[str, str]]) -> dict[str, Any]:
    key = get_api_key()
    if not key:
        raise BotUnavailable("No hay API key de Gemini cargada. Cargala en Configuración.")
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        tools=[
            types.Tool(
                function_declarations=[types.FunctionDeclaration(**d) for d in tools.DECLARATIONS]
            )
        ],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    contents: list[Any] = [
        types.Content(
            role="user" if m["role"] == "user" else "model", parts=[types.Part(text=m["text"])]
        )
        for m in messages[-20:]
    ]
    called: list[str] = []
    try:
        for _ in range(MAX_STEPS):
            resp = client.models.generate_content(
                model=get_model(), contents=contents, config=config
            )
            calls = resp.function_calls or []
            if not calls:
                return {"text": resp.text or "", "tool_calls": called}
            if resp.candidates and resp.candidates[0].content:
                contents.append(resp.candidates[0].content)
            parts = []
            for call in calls:
                name = call.name or ""
                args = dict(call.args or {})
                called.append(f"{name}({json.dumps(args, ensure_ascii=False)})")
                result = tools.execute(name, args)
                parts.append(types.Part.from_function_response(name=name, response=result))
            contents.append(types.Content(role="user", parts=parts))
    except Exception as exc:
        raise BotUnavailable(_friendly_error(exc)) from exc
    return {"text": "No pude completar la respuesta.", "tool_calls": called}

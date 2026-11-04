"""Bot: loop de function calling con un cliente de Gemini FALSO (sin red) y manejo sin key."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from wick.bot import client as bot_client
from wick.bot import tools
from wick.main import app


class _FakeModels:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_contents: list[Any] = []

    def generate_content(self, model: str, contents: list[Any], config: Any) -> Any:
        self.calls += 1
        self.seen_contents = list(contents)
        if self.calls == 1:  # primero pide una herramienta
            call = SimpleNamespace(name="listar_backtests", args={})
            content = SimpleNamespace(role="model", parts=[])
            return SimpleNamespace(
                function_calls=[call], candidates=[SimpleNamespace(content=content)], text=None
            )
        return SimpleNamespace(
            function_calls=None, candidates=[], text="Tenés backtests guardados."
        )


def test_chat_ejecuta_herramienta_y_devuelve_texto(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeModels()
    import google.genai as genai

    monkeypatch.setattr(genai, "Client", lambda api_key: SimpleNamespace(models=fake))
    monkeypatch.setattr(bot_client, "get_api_key", lambda: "clave-falsa-de-test")
    executed: list[str] = []
    real = tools.execute

    def spy(name: str, args: dict[str, Any]) -> dict[str, Any]:
        executed.append(name)
        return real(name, args)

    monkeypatch.setattr(tools, "execute", spy)
    out = bot_client.chat([{"role": "user", "text": "¿qué backtests tengo?"}])
    assert out["text"] == "Tenés backtests guardados."
    assert executed == ["listar_backtests"]
    assert out["tool_calls"] == ["listar_backtests({})"]
    assert fake.calls == 2


def test_solo_hay_tres_herramientas_de_lectura() -> None:
    assert {d["name"] for d in tools.DECLARATIONS} == {
        "listar_backtests",
        "obtener_backtest",
        "desglose_mensual",
    }
    assert set(tools.REGISTRY) == {"listar_backtests", "obtener_backtest", "desglose_mensual"}


def test_herramienta_con_id_inexistente_devuelve_error_no_inventa() -> None:
    out = tools.execute("obtener_backtest", {"id": "no-existe"})
    assert "error" in out


def test_sin_key_el_endpoint_lo_dice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bot_client, "get_api_key", lambda: None)
    c = TestClient(app)
    st = c.get("/api/v1/bot/status").json()
    assert st["configured"] is False and st["available"] is False
    r = c.post("/api/v1/bot/chat", json={"messages": [{"role": "user", "text": "hola"}]})
    assert r.status_code == 503
    assert "API key" in r.json()["mensaje"]


def test_cuota_agotada_mensaje_claro() -> None:
    msg = bot_client._friendly_error(Exception("429 RESOURCE_EXHAUSTED"))
    assert "cuota" in msg

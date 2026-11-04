from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from wick.api.models import ApiKeyIn, BotChatIn, BotChatOut, BotStatus
from wick.bot import client

router = APIRouter(tags=["bot"])


@router.get("/bot/status", response_model=BotStatus)
def bot_status() -> BotStatus:
    configured = client.get_api_key() is not None
    return BotStatus(
        configured=configured,
        model=client.get_model(),
        available=configured,
        message="" if configured else "No hay API key de Gemini cargada. Cargala en Configuración.",
    )


@router.post("/bot/chat", response_model=BotChatOut)
def bot_chat(body: BotChatIn) -> BotChatOut | JSONResponse:
    try:
        out = client.chat([m.model_dump() for m in body.messages])
    except client.BotUnavailable as exc:
        return JSONResponse(
            status_code=503, content={"codigo": "bot_no_disponible", "mensaje": str(exc)}
        )
    return BotChatOut.model_validate(out)


@router.put("/settings/api-key")
def put_api_key(body: ApiKeyIn) -> dict[str, bool]:
    client.set_api_key(body.api_key)
    return {"ok": True}


@router.delete("/settings/api-key")
def delete_api_key() -> dict[str, bool]:
    client.delete_api_key()
    return {"ok": True}


@router.put("/settings/bot-model")
def put_model(model: str) -> dict[str, bool]:
    client.set_model(model)
    return {"ok": True}

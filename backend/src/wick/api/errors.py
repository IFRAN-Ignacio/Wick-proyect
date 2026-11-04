"""Errores con formato uniforme {codigo, mensaje, detalle} y mensajes en español."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from wick.data.parsing import DataError


def _resp(status: int, codigo: str, mensaje: str, detalle: object = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"codigo": codigo, "mensaje": mensaje, "detalle": detalle}
    )


def install(app: FastAPI) -> None:
    @app.exception_handler(DataError)
    async def _data(_: Request, exc: DataError) -> JSONResponse:
        return _resp(400, "datos", str(exc))

    @app.exception_handler(ValidationError)
    async def _val(_: Request, exc: ValidationError) -> JSONResponse:
        return _resp(422, "validacion", "El config no es válido.", exc.errors(include_url=False))

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError) -> JSONResponse:
        return _resp(400, "valor", str(exc))

    @app.exception_handler(KeyError)
    async def _key(_: Request, exc: KeyError) -> JSONResponse:
        return _resp(404, "no_encontrado", str(exc.args[0]) if exc.args else "No encontrado.")

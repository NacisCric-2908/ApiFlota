"""Formato de error común del clúster: {"codigo": ..., "mensaje": ..., "detalle": {}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, codigo: str, mensaje: str, detalle: Any = None):
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalle = detalle if detalle is not None else {}


def cuerpo_error(codigo: str, mensaje: str, detalle: Any = None) -> dict:
    return {"codigo": codigo, "mensaje": mensaje, "detalle": detalle if detalle is not None else {}}


def _respuesta(status_code: int, codigo: str, mensaje: str, detalle: Any = None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=cuerpo_error(codigo, mensaje, detalle))


async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
    return _respuesta(exc.status_code, exc.codigo, exc.mensaje, exc.detalle)


async def _validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    # El enunciado pide 400 (no el 422 por defecto de FastAPI) para datos inválidos.
    errores = [
        {"campo": ".".join(str(p) for p in (e["loc"][1:] or e["loc"])), "mensaje": e["msg"]}
        for e in exc.errors()
    ]
    return _respuesta(400, "solicitud_invalida", "Los datos enviados no son válidos.", {"errores": errores})


async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    codigos = {404: "no_encontrado", 405: "metodo_no_permitido"}
    codigo = codigos.get(exc.status_code, "error_http")
    return _respuesta(exc.status_code, codigo, str(exc.detail))


async def _inesperado(_: Request, exc: Exception) -> JSONResponse:
    return _respuesta(500, "error_interno", "Ocurrió un error inesperado.")


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validacion)
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(Exception, _inesperado)

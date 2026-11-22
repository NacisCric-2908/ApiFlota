"""Rechaza peticiones que no vengan del API Gateway (cabecera secreta compartida)."""

import secrets

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings
from app.core.errors import cuerpo_error

CABECERA = b"x-gateway-secret"
RUTAS_PUBLICAS = {"/health", "/docs", "/openapi.json"}


class GatewaySecretMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in RUTAS_PUBLICAS:
            await self.app(scope, receive, send)
            return

        recibido = dict(scope["headers"]).get(CABECERA, b"")
        esperado = get_settings().gateway_secret.encode()
        if not secrets.compare_digest(recibido, esperado):
            respuesta = JSONResponse(
                status_code=401,
                content=cuerpo_error(
                    "gateway_no_autorizado",
                    "La petición debe llegar a través del API Gateway.",
                ),
            )
            await respuesta(scope, receive, send)
            return

        await self.app(scope, receive, send)

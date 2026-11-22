"""Alcances (scopes) del CRUD de Flota, declarados en el contrato OpenAPI.

La validación del token y de los alcances la hace el API Gateway; este servicio solo confía en
la cabecera secreta del gateway. Estas dependencias existen para que el contrato los documente
(`security` por operación) y no rechazan nada por sí mismas.
"""

from fastapi.openapi.models import OAuthFlowClientCredentials, OAuthFlows
from fastapi.security import APIKeyHeader, OAuth2

VEHICULOS_LEER = "vehiculos:leer"
VEHICULOS_ESCRIBIR = "vehiculos:escribir"

oauth2 = OAuth2(
    scheme_name="OAuth2Gateway",
    flows=OAuthFlows(
        clientCredentials=OAuthFlowClientCredentials(
            tokenUrl="/token",
            scopes={
                VEHICULOS_LEER: "Consultar vehículos",
                VEHICULOS_ESCRIBIR: "Crear, modificar, cambiar el estado y eliminar vehículos",
            },
        )
    ),
    auto_error=False,
)

cabecera_gateway = APIKeyHeader(
    name="X-Gateway-Secret", scheme_name="GatewaySecret", auto_error=False
)

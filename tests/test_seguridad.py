async def test_health_no_exige_cabecera(cliente):
    r = await cliente.get("/health", headers={"X-Gateway-Secret": ""})
    assert r.status_code == 200
    assert r.json() == {"estado": "ok"}


async def test_sin_cabecera_secreta_responde_401(cliente):
    r = await cliente.get("/vehiculos", headers={"X-Gateway-Secret": ""})
    assert r.status_code == 401
    assert r.json()["codigo"] == "gateway_no_autorizado"


async def test_cabecera_incorrecta_responde_401(cliente):
    r = await cliente.get("/vehiculos", headers={"X-Gateway-Secret": "otro"})
    assert r.status_code == 401


async def test_ruta_inexistente_usa_el_formato_de_error_comun(cliente):
    r = await cliente.get("/no-existe")
    assert r.status_code == 404
    assert set(r.json()) == {"codigo", "mensaje", "detalle"}

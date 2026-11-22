import asyncio

import pytest

VALIDAS = [
    ("disponible", "en_viaje"),
    ("disponible", "mantenimiento"),
    ("en_viaje", "disponible"),
    ("en_viaje", "mantenimiento"),
    ("mantenimiento", "disponible"),
]
INVALIDAS = [
    ("disponible", "disponible"),
    ("en_viaje", "en_viaje"),
    ("mantenimiento", "mantenimiento"),
    ("mantenimiento", "en_viaje"),
]


@pytest.mark.parametrize(("desde", "hacia"), VALIDAS)
async def test_transiciones_validas(cliente, crear_vehiculo, desde, hacia):
    v = await crear_vehiculo(estado=desde)
    r = await cliente.patch(f"/vehiculos/{v['id']}/estado", json={"estado": hacia})
    assert r.status_code == 200
    assert r.json()["estado"] == hacia


@pytest.mark.parametrize(("desde", "hacia"), INVALIDAS)
async def test_transiciones_invalidas_responden_409_y_no_cambian_nada(cliente, crear_vehiculo, desde, hacia):
    v = await crear_vehiculo(estado=desde)
    r = await cliente.patch(f"/vehiculos/{v['id']}/estado", json={"estado": hacia})
    assert r.status_code == 409
    cuerpo = r.json()
    assert cuerpo["codigo"] == "transicion_invalida"
    assert cuerpo["detalle"] == {"estadoActual": desde, "estadoSolicitado": hacia}
    assert (await cliente.get(f"/vehiculos/{v['id']}")).json()["estado"] == desde


async def test_actualiza_ubicacion_y_bateria_junto_con_el_estado(cliente, crear_vehiculo):
    v = await crear_vehiculo(estado="en_viaje", bateriaPct=80)
    nueva = {"type": "Point", "coordinates": [-74.0650, 4.7200]}
    r = await cliente.patch(
        f"/vehiculos/{v['id']}/estado",
        json={"estado": "disponible", "ubicacion": nueva, "bateriaPct": 61},
    )
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["ubicacion"] == nueva and cuerpo["bateriaPct"] == 61
    assert cuerpo["actualizadoEn"] >= v["actualizadoEn"]


async def test_sin_ubicacion_ni_bateria_se_conservan(cliente, crear_vehiculo):
    v = await crear_vehiculo(estado="disponible", bateriaPct=70)
    r = await cliente.patch(f"/vehiculos/{v['id']}/estado", json={"estado": "en_viaje"})
    assert r.json()["ubicacion"] == v["ubicacion"]
    assert r.json()["bateriaPct"] == 70


async def test_vehiculo_inexistente_responde_404(cliente):
    r = await cliente.patch("/vehiculos/no-existe/estado", json={"estado": "en_viaje"})
    assert r.status_code == 404


@pytest.mark.parametrize(
    "cuerpo",
    [
        {},
        {"estado": "volando"},
        {"estado": "disponible", "bateriaPct": 101},
        {"estado": "disponible", "ubicacion": {"type": "Point", "coordinates": [500, 4]}},
    ],
)
async def test_cuerpo_invalido_responde_400(cliente, crear_vehiculo, cuerpo):
    v = await crear_vehiculo()
    r = await cliente.patch(f"/vehiculos/{v['id']}/estado", json=cuerpo)
    assert r.status_code == 400


async def test_peticiones_simultaneas_solo_una_gana(cliente, crear_vehiculo):
    """Dos viajes no pueden reservar el mismo vehículo: la reserva es atómica."""
    v = await crear_vehiculo(estado="disponible")
    url = f"/vehiculos/{v['id']}/estado"

    respuestas = await asyncio.gather(*[cliente.patch(url, json={"estado": "en_viaje"}) for _ in range(25)])

    codigos = sorted(r.status_code for r in respuestas)
    assert codigos == [200] + [409] * 24

from app.externos.cache import CacheTTL
from tests.simulador import Reloj


def hacer(**kw):
    reloj = Reloj()
    return CacheTTL(ttl_s=10, max_antiguedad_s=100, reloj=reloj, **kw), reloj


def test_sin_dato_devuelve_none():
    cache, _ = hacer()
    assert cache.get("x") is None


def test_dato_reciente_es_fresco():
    cache, reloj = hacer()
    cache.set("x", 1)
    reloj.t += 10
    assert cache.get("x").valor == 1 and cache.get("x").fresco


def test_pasado_el_ttl_sigue_disponible_pero_no_fresco():
    cache, reloj = hacer()
    cache.set("x", 1)
    reloj.t += 11
    entrada = cache.get("x")
    assert entrada.valor == 1 and not entrada.fresco


def test_pasada_la_antiguedad_maxima_se_descarta():
    cache, reloj = hacer()
    cache.set("x", 1)
    reloj.t += 101
    assert cache.get("x") is None and len(cache) == 0


def test_volver_a_guardar_renueva_el_dato():
    cache, reloj = hacer()
    cache.set("x", 1)
    reloj.t += 50
    cache.set("x", 2)
    reloj.t += 5
    assert cache.get("x").valor == 2 and cache.get("x").fresco is True


def test_descarta_los_mas_antiguos_al_pasar_el_maximo():
    cache, _ = hacer(max_items=2)
    for clave in ("a", "b", "c"):
        cache.set(clave, clave)
    assert cache.get("a") is None
    assert cache.get("b") and cache.get("c")

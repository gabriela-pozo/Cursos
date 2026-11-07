"""El contrato del servidor: si estas pruebas pasan, Claude Code y evaluar.py pueden usarlo.

    uv run pytest -q

Llaman al servidor en memoria, igual que lo haría Claude Code, y piden datos reales al BCRP.
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


async def _con_cliente(f):
    async with Client(mcp) as c:
        return await f(c)


def llamar(herramienta, **args):
    return asyncio.run(_con_cliente(lambda c: c.call_tool(herramienta, args))).data


def test_buscar_encuentra_el_ipc():
    r = llamar("buscar_series", texto="ipc 12 meses", limite=5)
    assert "PN01273PM" in [x["codigo"] for x in r]
    assert {"codigo", "nombre", "frecuencia"} <= r[0].keys()


def test_cuatro_herramientas_como_minimo():
    nombres = {t.name for t in asyncio.run(_con_cliente(lambda c: c.list_tools()))}
    assert {"buscar_series", "serie", "resumen"} <= nombres
    assert len(nombres) >= 4, "falta su herramienta propia"


def test_serie_mensual():
    r = llamar("serie", codigo="PN01271PM", desde="2025-01", hasta="2025-12")
    assert len(r["datos"]) == 12
    assert r["datos"][0]["periodo"] == "2025-01"
    assert r["datos"][2]["valor"] == pytest.approx(0.81, abs=0.01)   # IPC de Lima, marzo de 2025
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_serie_diaria():
    r = llamar("serie", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    assert r["datos"][0]["periodo"] == "2026-10-01"
    assert r["datos"][-1] == {"periodo": "2026-10-15", "valor": pytest.approx(3.428, abs=0.001)}


def test_resumen_sin_cuentas_a_mano():
    r = llamar("resumen", codigo="PN01273PM", desde="2025-12", hasta="2026-09")
    assert r["primero"]["valor"] == pytest.approx(1.51, abs=0.01)
    assert r["ultimo"]["valor"] == pytest.approx(4.55, abs=0.01)
    assert r["maximo"]["periodo"] == "2026-09"
    assert {"cambio", "variacion_pct", "promedio", "minimo"} <= r.keys()


def test_codigo_inexistente_da_un_error_claro():
    with pytest.raises(ToolError, match="XX999"):
        llamar("serie", codigo="XX999", desde="2025-01", hasta="2025-02")


def test_un_recurso():
    async def contar(c):
        return len(await c.list_resources()) + len(await c.list_resource_templates())
    assert asyncio.run(_con_cliente(contar)) >= 1


def test_un_prompt():
    assert len(asyncio.run(_con_cliente(lambda c: c.list_prompts()))) >= 1


# =====================================================================================================================
# PRUEBAS PROPIAS (no son de la sesión 04). Evalúan graficar_serie, la herramienta propia de este proyecto.
# Escriben en una carpeta temporal (tmp_path), nunca en figuras/.
# =====================================================================================================================
import server  # noqa: E402

FIRMA_PNG = b"\x89PNG\r\n\x1a\n"


def test_propia_graficar_serie_genera_un_png_valido(tmp_path, monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(server, "FIGURAS", tmp_path / "figuras")   # el gráfico se guarda en la carpeta temporal
    r = llamar("graficar_serie", codigo="PN01271PM", desde="2025-01", hasta="2025-12")
    ruta = Path(r["ruta"])
    assert ruta.parent == tmp_path / "figuras" and ruta.suffix == ".png"
    assert ruta.exists() and ruta.stat().st_size > 0
    assert ruta.read_bytes()[:8] == FIRMA_PNG                       # los 8 primeros bytes de todo PNG
    assert r["codigo"] == "PN01271PM"                                # devuelve los datos con que se hizo
    assert r["periodo"] == "2025-01 a 2025-12" and r["observaciones"] == 12
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_propia_graficar_serie_error_claro_y_sin_archivo(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "FIGURAS", tmp_path / "figuras")
    casos = [({"codigo": "XX999", "desde": "2025-01", "hasta": "2025-02"}, "XX999"),           # código que no existe
             ({"codigo": "PN01271PM", "desde": "2025/01", "hasta": "2025-02"}, "no válida")]   # fecha mal escrita
    for args, mensaje in casos:
        with pytest.raises(ToolError, match=mensaje):
            llamar("graficar_serie", **args)
    assert not (tmp_path / "figuras").exists() and list(tmp_path.rglob("*")) == []   # no se creó ningún archivo

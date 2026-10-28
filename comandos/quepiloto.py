"""Comando /quepiloto: elige un piloto según el mes de nacimiento.

    /quepiloto          -> botones con los 12 meses
    /quepiloto marzo    -> directo (también acepta el número: /quepiloto 3)
"""
import time
import requests
from datetime import datetime
import random
from comandos.common import ErrorUsuario, jolpica, norm

PREFIJO = "qp"
PRIMER_ANIO = 2010

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
NOMBRE_MES = {v: k for k, v in reversed(list(MESES.items()))}

_pilotos_por_mes = None   # caché final (se llena la primera vez que se usa)
_vistos = {}              # driverId -> piloto, se va llenando temporada a temporada
_temporadas_ok = set()    # temporadas ya descargadas (si algo falla, no se repiten)
_puntos = {}              # driverId -> puntos sumados desde PRIMER_ANIO
_titulos = {}             # driverId -> campeonatos desde PRIMER_ANIO


def _consultar(path, **params):
    """jolpica() con reintentos solo para errores temporales (5xx, 429, timeouts, conexión).
    Los 4xx (pedido inválido) no se reintentan porque nunca se arreglan solos."""
    intentos = 4
    msg_api = ("La API de datos históricos (Jolpica) no está respondiendo ahora. "
               "Probá de nuevo en un minuto.")
    for i in range(intentos):
        try:
            return jolpica(path, **params)
        except requests.exceptions.HTTPError as e:
            codigo = e.response.status_code if e.response is not None else 0
            if 400 <= codigo < 500 and codigo != 429:
                raise ErrorUsuario(f"La API rechazó la consulta '{path}' (HTTP {codigo}).")
            if i == intentos - 1:
                raise ErrorUsuario(msg_api)
            time.sleep(1.5 * (i + 1))
        except requests.exceptions.RequestException:
            if i == intentos - 1:
                raise ErrorUsuario(msg_api)
            time.sleep(1.5 * (i + 1))


def pilotos_por_mes():
    """
    Todos los pilotos de PRIMER_ANIO al presente agrupados por mes de nacimiento.
    Se baja UNA vez (dos consultas por temporada: pilotos y standings) y queda en memoria.
    Si una temporada falla, las ya descargadas se conservan y el próximo intento sigue desde ahí.
    """
    global _pilotos_por_mes
    if _pilotos_por_mes is None:
        anio_actual = datetime.now().year
        for anio in range(PRIMER_ANIO, anio_actual + 1):
            if anio in _temporadas_ok:
                continue
            pilotos = _consultar(f"{anio}/drivers", limit=100)["DriverTable"]["Drivers"]
            listas = _consultar(f"{anio}/driverstandings", limit=100)["StandingsTable"]["StandingsLists"]

            for p in pilotos:
                _vistos[p["driverId"]] = p
            if listas:
                for s in listas[0]["DriverStandings"]:
                    did = s["Driver"]["driverId"]
                    _puntos[did] = _puntos.get(did, 0.0) + float(s.get("points") or 0)
                    # el campeón solo cuenta si la temporada ya terminó.
                    # Algunos pilotos no traen "position" (no clasificados), por eso .get()
                    if s.get("position") == "1" and anio < anio_actual:
                        _titulos[did] = _titulos.get(did, 0) + 1

            # se marca recién cuando las dos consultas salieron bien
            _temporadas_ok.add(anio)
            time.sleep(0.3)

        por_mes = {}
        for p in _vistos.values():
            fecha = p.get("dateOfBirth")
            if fecha:
                por_mes.setdefault(int(fecha[5:7]), []).append(p)
        _pilotos_por_mes = por_mes
    return _pilotos_por_mes


def estadisticas_piloto(driver_id):
    """Carreras, victorias y podios de toda la carrera (usa el campo 'total', sin paginar).
    Puntos y títulos vienen del caché de standings por temporada (desde PRIMER_ANIO)."""
    base = f"drivers/{driver_id}"
    carreras = int(_consultar(f"{base}/results", limit=1)["total"])
    victorias = int(_consultar(f"{base}/results/1", limit=1)["total"])
    segundos = int(_consultar(f"{base}/results/2", limit=1)["total"])
    terceros = int(_consultar(f"{base}/results/3", limit=1)["total"])
    return {"carreras": carreras, "victorias": victorias,
            "podios": victorias + segundos + terceros,
            "puntos": _puntos.get(driver_id, 0.0),
            "titulos": _titulos.get(driver_id, 0)}


def menu_meses():
    botones = [(NOMBRE_MES[m].capitalize(), f"{PREFIJO}:m:{m}") for m in range(1, 13)]
    filas = [botones[i:i + 3] for i in range(0, 12, 3)]
    return "🎂 ¿En qué mes naciste? Te digo qué piloto nació ese mes.", filas


def piloto_del_mes(mes):
    candidatos = pilotos_por_mes().get(mes, [])
    if not candidatos:
        raise ErrorUsuario("No encontré pilotos nacidos en ese mes.")

    p = random.choice(candidatos)
    est = estadisticas_piloto(p["driverId"])
    titulos = f"🏅 Campeonatos (desde {PRIMER_ANIO}): {est['titulos']}\n" if est["titulos"] else ""
    texto = (
        f"🏎️ TU PILOTO ES {p['givenName'].upper()} {p['familyName'].upper()}!\n\n"
        f"🌍 Nacionalidad: {p.get('nationality', '?')}\n"
        f"📅 Nació el: {p['dateOfBirth']}\n\n"
        f"🏁 Carreras: {est['carreras']}\n"
        f"🏆 Victorias: {est['victorias']}\n"
        f"🥇 Podios: {est['podios']}\n"
        f"⭐ Puntos (desde {PRIMER_ANIO}): {est['puntos']:.1f}\n"
        f"{titulos}"
    ).strip()
    filas = [[("🎲 Otro piloto de este mes", f"{PREFIJO}:m:{mes}")],
             [("⬅️ Cambiar de mes", f"{PREFIJO}:y")]]
    return texto, filas


def responder_quepiloto(args):
    """Entrada de /quepiloto. Devuelve (texto, filas | None). args debe ser una lista."""
    if not args:
        return menu_meses()
    txt = norm(args[0])
    mes = int(txt) if txt.isdigit() else MESES.get(txt)
    if not mes or not 1 <= mes <= 12:
        return "No reconocí ese mes. Probá con el nombre (marzo) o el número (3).", None
    return piloto_del_mes(mes)


def manejar_callback(data):
    """Atiende los botones 'qp:...'. Devuelve (texto, filas | None)."""
    p = data.split(":")
    if p[0] != PREFIJO or len(p) < 2:
        raise ErrorUsuario("Botón no reconocido.")
    if p[1] == "y":
        return menu_meses()
    if p[1] == "m" and len(p) == 3:
        return piloto_del_mes(int(p[2]))
    raise ErrorUsuario("Botón no reconocido.")
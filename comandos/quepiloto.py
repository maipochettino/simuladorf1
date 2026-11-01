"""Comando /quepiloto: elige un piloto según el mes de nacimiento.

    /quepiloto marzo    -> directo (también acepta el número: /quepiloto 3)
"""
import time
import requests
from datetime import datetime
import random
from comandos.common import ErrorUsuario, jolpica, norm
import re
import html

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


PREGUNTA_MES = "🎂 ¿En qué mes naciste? Escribilo con el nombre (marzo) o el número (3)."


def interpretar_mes(texto):
    """Devuelve el número de mes (1-12) o None. Acepta 'marzo', '3', 'nací en marzo', '15/03'."""
    palabras = re.findall(r"[a-z0-9]+", norm(texto))
    for pal in palabras:                      # primero busca el nombre del mes
        if pal in MESES:
            return MESES[pal]
    for pal in palabras:                      # si no, un número del 1 al 12
        if pal.isdigit() and 1 <= int(pal) <= 12:
            return int(pal)
    return None


def piloto_del_mes(mes):
    candidatos = pilotos_por_mes().get(mes, [])
    if not candidatos:
        raise ErrorUsuario("No encontré pilotos nacidos en ese mes.")

    p = random.choice(candidatos)
    est = estadisticas_piloto(p["driverId"])
    nombre = html.escape(f"{p['givenName'].upper()} {p['familyName'].upper()}")
    nacionalidad = html.escape(p.get("nationality", "?"))
    titulos = f"🏅 Campeonatos (desde {PRIMER_ANIO}): {est['titulos']}\n" if est["titulos"] else ""
    return (
        f"🏎️ TU PILOTO ES <b>{nombre}</b>!\n\n"
        f"🌍 Nacionalidad: {nacionalidad}\n"
        f"📅 Nació el: {p['dateOfBirth']}\n\n"
        f"🏁 Carreras: {est['carreras']}\n"
        f"🏆 Victorias: {est['victorias']}\n"
        f"🥇 Podios: {est['podios']}\n"
        f"⭐ Puntos (desde {PRIMER_ANIO}): {est['puntos']:.1f}\n"
        f"{titulos}\n"
        f"🎲 Para ver otro piloto, escribí /quepiloto de nuevo."
    ).strip()


def responder_quepiloto(texto):
    """Recibe el texto que escribió el usuario y devuelve el mensaje (string)."""
    mes = interpretar_mes(texto)
    if not mes:
        raise ErrorUsuario("No reconocí ese mes. Probá con el nombre (marzo) o el número (3).")
    return piloto_del_mes(mes)
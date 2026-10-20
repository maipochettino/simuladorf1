"""Comando /quepiloto: elige un piloto según el mes de nacimiento."""
import time
from datetime import datetime
import random
from comandos.common import ErrorUsuario, jolpica, norm

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
NOMBRE_MES = {v: k for k, v in reversed(list(MESES.items()))}

def pilotos_por_mes():
    """
    Todos los pilotos de 2010 al presente agrupados por mes de nacimiento.
    Se baja UNA vez (una consulta por temporada) y queda en memoria.
    """
    global _pilotos_por_mes
    if _pilotos_por_mes is None:
        vistos = {}
        for anio in range(2010, datetime.now().year + 1):
            for p in jolpica(f"{anio}/drivers", limit=100)["DriverTable"]["Drivers"]:
                vistos[p["driverId"]] = p
            time.sleep(0.3)
        por_mes = {}
        for p in vistos.values():
            fecha = p.get("dateOfBirth")
            if fecha:
                por_mes.setdefault(int(fecha[5:7]), []).append(p)
        _pilotos_por_mes = por_mes
    return _pilotos_por_mes


def estadisticas_piloto(driver_id):
    """Estadísticas de toda la carrera usando el campo 'total' (así no hay que paginar)."""
    base = f"drivers/{driver_id}"
    carreras = int(jolpica(f"{base}/results", limit=1)["total"])
    victorias = int(jolpica(f"{base}/results/1", limit=1)["total"])
    segundos = int(jolpica(f"{base}/results/2", limit=1)["total"])
    terceros = int(jolpica(f"{base}/results/3", limit=1)["total"])
    standings = jolpica(f"{base}/driverstandings", limit=100)["StandingsTable"]["StandingsLists"]
    puntos = sum(float(s["DriverStandings"][0]["points"]) for s in standings)
    titulos = sum(1 for s in standings if s["DriverStandings"][0]["position"] == "1")
    return {"carreras": carreras, "victorias": victorias, "podios": victorias + segundos + terceros,
            "puntos": puntos, "titulos": titulos}


def responder_quepiloto(args):
    if not args:
        return "Uso: /quepiloto <mes>  (por ejemplo: /quepiloto marzo  o  /quepiloto 3)"
    txt = norm(args[0])
    mes = int(txt) if txt.isdigit() else MESES.get(txt)
    if not mes or not 1 <= mes <= 12:
        return "No reconocí ese mes. Probá con el nombre (marzo) o el número (3)."

    candidatos = pilotos_por_mes().get(mes, [])
    if not candidatos:
        return "No encontré pilotos nacidos en ese mes."

    p = random.choice(candidatos)
    est = estadisticas_piloto(p["driverId"])
    titulos = f"🏅 Campeonatos: {est['titulos']}\n" if est["titulos"] else ""
    return (
        f"🏎️ TU PILOTO ES {p['givenName'].upper()} {p['familyName'].upper()}!\n\n"
        f"🌍 Nacionalidad: {p.get('nationality', '?')}\n"
        f"📅 Nació el: {p['dateOfBirth']}\n\n"
        f"🏁 Carreras: {est['carreras']}\n"
        f"🏆 Victorias: {est['victorias']}\n"
        f"🥇 Podios: {est['podios']}\n"
        f"⭐ Puntos (suma de temporadas): {est['puntos']:.1f}\n"
        f"{titulos}"
    ).strip()


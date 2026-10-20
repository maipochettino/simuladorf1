"""Comando /historico: resultados de campeonatos y carreras."""
from datetime import datetime
from comanodos.common import ErrorUsuario, jolpica, coincide

def responder_historico(args):
    if not args:
        return ("Uso:\n  /historico <año>            -> top 3 del campeonato\n"
                "  /historico <año> <carrera>  -> podio de esa carrera\n"
                "Ejemplos: /historico 2008  |  /historico 1994 brasil")
    try:
        anio = int(args[0])
    except ValueError:
        return "El primer dato tiene que ser el año, por ejemplo: /historico 2008"
    if not 1950 <= anio <= datetime.now().year:
        return f"El año tiene que estar entre 1950 y {datetime.now().year}."

    if len(args) == 1:
        listas = jolpica(f"{anio}/driverstandings", limit=3)["StandingsTable"]["StandingsLists"]
        if not listas:
            raise ErrorUsuario("No hay clasificación para ese año.")
        lineas = [f"🏆 Campeonato de pilotos {anio}"]
        for s in listas[0]["DriverStandings"][:3]:
            d = s["Driver"]
            equipo = s["Constructors"][0]["name"] if s.get("Constructors") else "?"
            lineas.append(f"{s['position']}. {d['givenName']} {d['familyName']} ({equipo}) — "
                          f"{s['points']} pts, {s['wins']} victorias")
        return "\n".join(lineas)

    consulta = " ".join(args[1:])
    carreras = jolpica(f"{anio}")["RaceTable"]["Races"]

    def texto(c):
        loc = c["Circuit"]["Location"]
        return f"{c['raceName']} {c['Circuit']['circuitName']} {loc['locality']} {loc['country']}"

    encontradas = [c for c in carreras if coincide(consulta, texto(c))]
    if not encontradas:
        lista = ", ".join(c["raceName"].replace(" Grand Prix", "") for c in carreras)
        raise ErrorUsuario(f"No encontré '{consulta}' en {anio}. Carreras de ese año: {lista}")
    if len(encontradas) > 1:
        lista = ", ".join(c["raceName"] for c in encontradas)
        raise ErrorUsuario(f"'{consulta}' coincide con varias carreras ({lista}). Sé más específico.")

    carrera = encontradas[0]
    resultados = jolpica(f"{anio}/{carrera['round']}/results", limit=40)["RaceTable"]["Races"][0]["Results"]
    medallas = ["🥇", "🥈", "🥉"]
    lineas = [f"🏁 {carrera['raceName']} {anio} ({carrera['date']})"]
    for i, r in enumerate(resultados[:3]):
        d = r["Driver"]
        tiempo = r.get("Time", {}).get("time", r["status"])
        lineas.append(f"{medallas[i]} {d['givenName']} {d['familyName']} ({r['Constructor']['name']}) — {tiempo}")
    pole = next((r for r in resultados if r.get("grid") == "1"), None)
    if pole:
        lineas.append(f"📍 Pole: {pole['Driver']['givenName']} {pole['Driver']['familyName']}")
    abandonos = sum(1 for r in resultados if not (r["status"] == "Finished" or r["status"].startswith("+")))
    lineas.append(f"🚧 Abandonos: {abandonos} de {len(resultados)} pilotos")
    return "\n".join(lineas)


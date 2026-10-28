"""Comando /historico: resultados de campeonatos y carreras.
 
Flujo con botones:
    /historico                  -> décadas -> años -> [Campeonato | carreras del año] -> resultado
    /historico 1994             -> [Campeonato | carreras de 1994]
    /historico 1994 brasil      -> podio directo (modo clásico)
 
Las funciones devuelven (texto, filas) donde filas = [[(texto_boton, callback_data), ...], ...] o None.
"""
from datetime import datetime, date
from comandos.common import ErrorUsuario, jolpica, coincide

PREFIJO = "his"
PRIMER_ANIO = 1950
 
 
def _en_filas(botones, por_fila):
    return [botones[i:i + por_fila] for i in range(0, len(botones), por_fila)]
 
 
def _nombre_corto(carrera):
    return carrera["raceName"].replace(" Grand Prix", "")

# Menús

def menu_decadas():
    hoy = datetime.now().year
    botones = [(f"{d}s", f"{PREFIJO}:d:{d}") for d in range(PRIMER_ANIO, hoy + 1, 10)]
    return "📅 ¿De qué década querés ver resultados?", _en_filas(botones, 3)
 
 
def menu_anios(decada):
    hoy = datetime.now().year
    anios = [a for a in range(decada, decada + 10) if PRIMER_ANIO <= a <= hoy]
    botones = [(str(a), f"{PREFIJO}:a:{a}") for a in anios]
    filas = _en_filas(botones, 5)
    filas.append([("⬅️ Décadas", f"{PREFIJO}:y")])
    return f"📅 Elegí el año ({decada}s):", filas
 
 
def menu_anio(anio):
    """Botón del campeonato + una carrera por botón (solo las ya disputadas)."""
    carreras = jolpica(f"{anio}")["RaceTable"]["Races"]
    hoy = date.today().isoformat()
    carreras = [c for c in carreras if c.get("date", "9999") <= hoy]
    if not carreras:
        raise ErrorUsuario(f"Todavía no hay carreras disputadas en {anio}.")
 
    botones = [(_nombre_corto(c), f"{PREFIJO}:c:{anio}:{c['round']}") for c in carreras]
    filas = [[("🏆 Campeonato de pilotos", f"{PREFIJO}:t:{anio}")]]
    filas += _en_filas(botones, 2)
    filas.append([("⬅️ Años", f"{PREFIJO}:d:{anio // 10 * 10}")])
    return f"🏁 {anio}: ¿qué querés ver?", filas

# Resultados

def campeonato(anio):
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
 
 
def podio_carrera(anio, ronda):
    carreras = jolpica(f"{anio}/{ronda}/results", limit=40)["RaceTable"]["Races"]
    if not carreras or not carreras[0].get("Results"):
        raise ErrorUsuario("Todavía no hay resultados de esa carrera.")
    carrera = carreras[0]
    resultados = carrera["Results"]
 
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
 
 
def _boton_volver(anio):
    return [[(f"⬅️ Volver a {anio}", f"{PREFIJO}:a:{anio}")]]

# Puntos de entrada

def responder_historico(args):
    """Entrada de /historico. Devuelve (texto, filas | None)."""
    if not args:
        return menu_decadas()
    try:
        anio = int(args[0])
    except ValueError:
        return "El primer dato tiene que ser el año, por ejemplo: /historico 2008", None
    if not PRIMER_ANIO <= anio <= datetime.now().year:
        return f"El año tiene que estar entre {PRIMER_ANIO} y {datetime.now().year}.", None
 
    if len(args) == 1:
        return menu_anio(anio)
 
    consulta = " ".join(args[1:])
    carreras = jolpica(f"{anio}")["RaceTable"]["Races"]
 
    def texto(c):
        loc = c["Circuit"]["Location"]
        return f"{c['raceName']} {c['Circuit']['circuitName']} {loc['locality']} {loc['country']}"
 
    encontradas = [c for c in carreras if coincide(consulta, texto(c))]
    if not encontradas:
        lista = ", ".join(_nombre_corto(c) for c in carreras)
        raise ErrorUsuario(f"No encontré '{consulta}' en {anio}. Carreras de ese año: {lista}")
    if len(encontradas) > 1:
        lista = ", ".join(c["raceName"] for c in encontradas)
        raise ErrorUsuario(f"'{consulta}' coincide con varias carreras ({lista}). Sé más específico.")
 
    return podio_carrera(anio, encontradas[0]["round"]), _boton_volver(anio)
 
 
def manejar_callback(data):
    """Atiende los botones 'his:...'. Devuelve (texto, filas | None)."""
    p = data.split(":")
    if p[0] != PREFIJO or len(p) < 2:
        raise ErrorUsuario("Botón no reconocido.")
    accion = p[1]
 
    if accion == "y":
        return menu_decadas()
    if accion == "d" and len(p) == 3:
        return menu_anios(int(p[2]))
    if accion == "a" and len(p) == 3:
        return menu_anio(int(p[2]))
    if accion == "t" and len(p) == 3:
        return campeonato(int(p[2])), _boton_volver(int(p[2]))
    if accion == "c" and len(p) == 4:
        return podio_carrera(int(p[2]), p[3]), _boton_volver(int(p[2]))
    raise ErrorUsuario("Botón no reconocido.")
 
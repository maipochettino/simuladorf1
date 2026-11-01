"""Comando /estrategia: análisis y simulación de neumáticos.

Flujo con botones:
    /estrategia                      -> botones de años
    /estrategia 2024                 -> botones de carreras de 2024
    /estrategia 2024 belgica         -> botones de pilotos de esa carrera
    /estrategia 2024 belgica HAM     -> resultado directo

Las funciones de menú devuelven (texto, filas) donde `filas` es una lista de filas
y cada fila es una lista de tuplas (texto_boton, callback_data). `filas` es None
cuando no hay que mostrar botones.
"""
from datetime import date
import numpy as np
import pandas as pd
from itertools import permutations, product
from comandos.common import (OPENF1, COMPUESTOS_SECOS, MIN_STINT, PIT_LOSS_DEFECTO, FUEL_DEFECTO, ErrorUsuario, get_json, norm, coincide, fmt_tiempo)

PREFIJO = "est"          # prefijo de los callback_data de este comando
PRIMER_ANIO = 2023       # OpenF1 tiene datos desde 2023

# Búsquedas

def carreras_del_anio(anio):
    """Carreras (session_name == Race) ya disputadas y no canceladas, ordenadas por fecha."""
    sesiones = get_json(f"{OPENF1}/sessions", {"year": anio, "session_name": "Race"})
    hoy = date.today().isoformat()
    sesiones = [s for s in sesiones
                if not s.get("is_cancelled")
                and (s.get("date_start") or "9999")[:10] <= hoy]
    if not sesiones:
        raise ErrorUsuario(f"No encontré carreras disputadas de {anio} en OpenF1 (hay datos desde {PRIMER_ANIO}).")
    return sorted(sesiones, key=lambda s: s.get("date_start") or "")

def buscar_sesion(anio, consulta):
    sesiones = carreras_del_anio(anio)

    def texto(s):
        return f"{s.get('country_name','')} {s.get('location','')} {s.get('circuit_short_name','')}"

    encontradas = [s for s in sesiones if coincide(consulta, texto(s))]
    if not encontradas:
        lista = ", ".join(sorted({s.get("location", "?") for s in sesiones}))
        raise ErrorUsuario(f"No encontré '{consulta}' en {anio}. Probá con alguna de: {lista}")
    if len(encontradas) > 1:
        lista = ", ".join(f"{s.get('location')}" for s in encontradas)
        raise ErrorUsuario(f"'{consulta}' coincide con varias carreras ({lista}). Sé más específico.")
    return encontradas[0]


def buscar_piloto(pilotos, consulta):
    q = norm(consulta)
    for p in pilotos:
        if norm(p.get("name_acronym", "")) == q or str(p.get("driver_number")) == q:
            return p
    for p in pilotos:
        if q in norm(p.get("last_name", "")) or q in norm(p.get("full_name", "")):
            return p
    lista = ", ".join(sorted(f"{p.get('name_acronym')}" for p in pilotos))
    raise ErrorUsuario(f"No encontré al piloto '{consulta}'. Pilotos de esa carrera: {lista}")

# Menús con botones

def _en_filas(botones, por_fila):
    """Parte una lista plana de botones en filas de `por_fila`."""
    return [botones[i:i + por_fila] for i in range(0, len(botones), por_fila)]


def menu_anios():
    anios = list(range(PRIMER_ANIO, date.today().year))
    botones = [(str(a), f"{PREFIJO}:a:{a}") for a in anios]
    return "📅 ¿De qué año querés ver la estrategia?", _en_filas(botones, 3)


def menu_carreras(anio):
    sesiones = carreras_del_anio(anio)
    # Si un país tiene más de una carrera (EE. UU., Italia...), uso la ciudad para distinguir.
    paises = [s.get("country_name") for s in sesiones]
    botones = []
    for s in sesiones:
        pais = s.get("country_name") or "?"
        nombre = s.get("location") or pais if paises.count(pais) > 1 else pais
        botones.append((nombre, f"{PREFIJO}:c:{s['session_key']}"))
    filas = _en_filas(botones, 2)
    filas.append([("⬅️ Años", f"{PREFIJO}:y")])
    return f"🏁 Elegí la carrera de {anio}:", filas


def _sesion_por_key(session_key):
    sesiones = get_json(f"{OPENF1}/sessions", {"session_key": session_key})
    if not sesiones:
        raise ErrorUsuario("No encontré esa carrera en OpenF1.")
    return sesiones[0]


def menu_pilotos(session_key, sesion=None):
    sesion = sesion or _sesion_por_key(session_key)
    pilotos = get_json(f"{OPENF1}/drivers", {"session_key": session_key})
    if not pilotos:
        raise ErrorUsuario("OpenF1 todavía no tiene pilotos para esa carrera.")

    vistos, unicos = set(), []
    for p in pilotos:
        n = p.get("driver_number")
        if n is None or n in vistos:
            continue
        vistos.add(n)
        unicos.append(p)
    unicos.sort(key=lambda p: p.get("name_acronym") or "")

    botones = [(p.get("name_acronym") or str(p["driver_number"]),
                f"{PREFIJO}:p:{session_key}:{p['driver_number']}") for p in unicos]
    filas = _en_filas(botones, 4)
    filas.append([("⬅️ Carreras", f"{PREFIJO}:a:{sesion.get('year')}")])
    return f"🏎️ GP de {sesion.get('country_name')} {sesion.get('year')}: ¿de qué piloto?", filas

# Modelo

def armar_tabla(laps, stints):
    """Une cada vuelta con su stint (compuesto + edad del neumático)."""
    dl = pd.DataFrame(laps)[["driver_number", "lap_number", "lap_duration", "is_pit_out_lap"]].copy()
    dl["is_pit_out_lap"] = dl["is_pit_out_lap"].fillna(False).astype(bool)
    dl = dl.dropna(subset=["lap_number"])
    dl["lap_number"] = dl["lap_number"].astype(int)
    total = int(dl["lap_number"].max())

    ds = pd.DataFrame(stints)
    ds["lap_end"] = pd.to_numeric(ds["lap_end"], errors="coerce").fillna(total)
    ds["lap_start"] = pd.to_numeric(ds["lap_start"], errors="coerce")
    ds["tyre_age_at_start"] = pd.to_numeric(ds["tyre_age_at_start"], errors="coerce").fillna(0)
    ds = ds.dropna(subset=["lap_start"])

    partes = []
    for s in ds.itertuples():
        sub = dl[(dl.driver_number == s.driver_number)
                 & (dl.lap_number >= s.lap_start)
                 & (dl.lap_number <= s.lap_end)].copy()
        sub["compuesto"] = str(s.compound).upper()
        sub["edad"] = s.tyre_age_at_start + (sub.lap_number - s.lap_start)

        sub["es_in_lap"] = (sub.lap_number == s.lap_end) & (s.lap_end < total)
        partes.append(sub)

    if not partes:
        raise ErrorUsuario("No hay datos de neumáticos para esa carrera.")
    tabla = pd.concat(partes, ignore_index=True)
    tabla = tabla.drop_duplicates(subset=["driver_number", "lap_number"])
    return tabla, total


def marcar_vueltas_neutralizadas(tabla):
    """Marca vueltas con Safety Car / VSC / bandera amarilla: todo el pelotón va lento."""
    t = tabla.copy()
    normales = t[(~t.is_pit_out_lap) & (~t.es_in_lap) & (t.lap_number > 1)].dropna(subset=["lap_duration"])
    med_por_vuelta = normales.groupby("lap_number")["lap_duration"].median()
    referencia = med_por_vuelta.median()
    t["neutralizada"] = (t.lap_number.map(med_por_vuelta) > referencia * 1.06).fillna(False).astype(bool)
    return t


def ajustar_modelo(t):
    """
    Modelo:  tiempo_vuelta = ritmo_piloto + delta_compuesto + deg_compuesto * edad + fuel * nro_vuelta
      - el ritmo propio de cada piloto (por eso el HARD ya no parece "más rápido" solo porque lo usaron los punteros)
      - el desgaste del neumático (pendiente, nunca negativa)
      - el combustible (el auto se aliviana, por eso las vueltas finales parecen "no degradar")
    """
    d = t[(~t.is_pit_out_lap) & (~t.es_in_lap) & (~t.neutralizada) & (t.lap_number > 1)
          & t.lap_duration.notna() & t.compuesto.isin(COMPUESTOS_SECOS)].copy()

    mediana_piloto = d.groupby("driver_number")["lap_duration"].transform("median")
    d = d[d.lap_duration <= mediana_piloto * 1.04]

    compuestos = [c for c in COMPUESTOS_SECOS
                  if (d.compuesto == c).sum() >= 25 and d[d.compuesto == c].edad.nunique() >= 5]
    if len(compuestos) < 2:
        raise ErrorUsuario("Hay pocos datos de neumáticos secos en esa carrera (¿carrera mojada?). "
                           "El modelo necesita al menos 2 compuestos con datos.")
    d = d[d.compuesto.isin(compuestos)]
    ref = d.compuesto.value_counts().idxmax()

    pilotos = sorted(d.driver_number.unique())
    columnas, nombres = [], []
    for p in pilotos:
        columnas.append((d.driver_number == p).astype(float).values)
        nombres.append(("piloto", p))
    for c in compuestos:
        if c != ref:
            columnas.append((d.compuesto == c).astype(float).values)
            nombres.append(("delta", c))
    for c in compuestos:
        columnas.append(((d.compuesto == c) * d.edad).astype(float).values)
        nombres.append(("deg", c))
    columnas.append(d.lap_number.astype(float).values)
    nombres.append(("fuel", None))

    X = np.column_stack(columnas)
    y = d.lap_duration.values
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    coef = dict(zip(nombres, coef))

    fuel = coef[("fuel", None)]
    if not (-0.09 <= fuel <= -0.01):
        fuel = FUEL_DEFECTO

    modelo = {
        "compuestos": compuestos,
        "off": {p: coef[("piloto", p)] for p in pilotos},
        "delta": {c: (0.0 if c == ref else coef[("delta", c)]) for c in compuestos},
        "deg": {c: float(np.clip(coef[("deg", c)], 0.0, 0.5)) for c in compuestos},
        "fuel": float(fuel),
    }
    modelo["off_medio"] = float(np.median(list(modelo["off"].values())))
    return modelo


def predecir(m, piloto, compuesto, edad, vuelta):
    off = m["off"].get(piloto, m["off_medio"])
    return off + m["delta"][compuesto] + m["deg"][compuesto] * edad + m["fuel"] * vuelta


def estimar_costo_pit(t, m):
    """Pérdida de un pit stop = (vuelta de entrada + vuelta de salida) real - lo esperado sin parar."""
    por_clave = t.set_index(["driver_number", "lap_number"]).to_dict("index")
    perdidas = []
    for (piloto, vuelta), r in por_clave.items():
        if not r["es_in_lap"] or r["neutralizada"] or pd.isna(r["lap_duration"]):
            continue
        o = por_clave.get((piloto, vuelta + 1))
        if o is None or not o["is_pit_out_lap"] or o["neutralizada"] or pd.isna(o["lap_duration"]):
            continue
        if r["compuesto"] not in m["deg"] or o["compuesto"] not in m["deg"]:
            continue
        esperado = (predecir(m, piloto, r["compuesto"], r["edad"], vuelta)
                    + predecir(m, piloto, o["compuesto"], o["edad"], vuelta + 1))
        perdidas.append(r["lap_duration"] + o["lap_duration"] - esperado)

    if len(perdidas) < 3:
        return PIT_LOSS_DEFECTO
    costo = float(np.median(perdidas))
    return costo if 12 <= costo <= 35 else PIT_LOSS_DEFECTO


def largo_maximo_stint(stints, total):
    """Stint más largo que realmente se vio en la carrera para cada compuesto (+2 de margen)."""
    maximos = {}
    for s in stints:
        c = str(s.get("compound")).upper()
        if s.get("lap_start") is None:
            continue
        fin = s.get("lap_end") or total
        maximos[c] = max(maximos.get(c, 0), fin - s["lap_start"] + 1)
    return {c: v + 2 for c, v in maximos.items()}


def tiempo_stint(m, piloto, comp, vuelta_ini, n):
    """Suma de n vueltas con neumático nuevo (edad 0,1,2,...) empezando en la vuelta vuelta_ini."""
    off = m["off"].get(piloto, m["off_medio"]) + m["delta"][comp]
    suma_k = n * (n - 1) / 2
    return n * off + m["deg"][comp] * suma_k + m["fuel"] * (n * vuelta_ini + suma_k)


def tiempo_estrategia(m, piloto, estrategia, costo_pit):
    t, vuelta = 0.0, 1
    for comp, n in estrategia:
        t += tiempo_stint(m, piloto, comp, vuelta, n)
        vuelta += n
    return t + costo_pit * (len(estrategia) - 1)


def mejores_estrategias(m, piloto, total, costo_pit, max_stint, top=3):
    """Prueba todas las de 1 y 2 paradas (con al menos 2 compuestos distintos) y devuelve las mejores."""
    comps = m["compuestos"]
    limite = {c: max_stint.get(c, total) for c in comps}
    mejor_por_secuencia = {}

    def registrar(est):
        secuencia = tuple(c for c, _ in est)
        t = tiempo_estrategia(m, piloto, est, costo_pit)
        if secuencia not in mejor_por_secuencia or t < mejor_por_secuencia[secuencia][0]:
            mejor_por_secuencia[secuencia] = (t, est)

    for a, b in permutations(comps, 2):
        for p in range(MIN_STINT, total - MIN_STINT + 1):
            if p <= limite[a] and total - p <= limite[b]:
                registrar([(a, p), (b, total - p)])

    for combo in product(comps, repeat=3):
        if len(set(combo)) < 2:
            continue
        a, b, c = combo
        for p1 in range(MIN_STINT, total - 2 * MIN_STINT + 1):
            for p2 in range(p1 + MIN_STINT, total - MIN_STINT + 1):
                n1, n2, n3 = p1, p2 - p1, total - p2
                if n1 <= limite[a] and n2 <= limite[b] and n3 <= limite[c]:
                    registrar([(a, n1), (b, n2), (c, n3)])

    ordenadas = sorted(mejor_por_secuencia.values(), key=lambda x: x[0])
    return ordenadas[:top]


def describir(est):
    partes, vuelta = [], 1
    for comp, n in est:
        partes.append(f"{comp} (v{vuelta}-{vuelta + n - 1}, {n} vueltas)")
        vuelta += n
    paradas = len(est) - 1
    return f"{paradas} parada{'s' if paradas != 1 else ''}: " + " ➜ ".join(partes)


def estrategia_real(stints, piloto_num, total, m):
    """Estrategia que hizo el piloto en la carrera real (None si no se puede comparar)."""
    mios = sorted([s for s in stints if s.get("driver_number") == piloto_num and s.get("lap_start") is not None],
                  key=lambda s: s["lap_start"])
    est = []
    for s in mios:
        fin = s.get("lap_end") or total
        comp = str(s.get("compound")).upper()
        if comp not in m["compuestos"]:
            return None
        est.append((comp, fin - s["lap_start"] + 1))
    if not est or sum(n for _, n in est) != total:
        return None
    return est

# Cálculo completo (ya con sesión y piloto elegidos)

def calcular_estrategia(session_key, piloto_ref, sesion=None):
    """piloto_ref puede ser sigla, apellido o número (string o int)."""
    sesion = sesion or _sesion_por_key(session_key)
    anio = sesion.get("year")

    pilotos = get_json(f"{OPENF1}/drivers", {"session_key": session_key})
    piloto = buscar_piloto(pilotos, str(piloto_ref))
    num = piloto["driver_number"]

    laps = get_json(f"{OPENF1}/laps", {"session_key": session_key})
    stints = get_json(f"{OPENF1}/stints", {"session_key": session_key})
    if not laps or not stints:
        raise ErrorUsuario("OpenF1 todavía no tiene vueltas/neumáticos de esa carrera.")

    tabla, total = armar_tabla(laps, stints)
    mojado = tabla.compuesto.isin(["INTERMEDIATE", "WET"]).mean()
    if mojado > 0.10:
        raise ErrorUsuario("Esa carrera fue (parcialmente) con lluvia; el modelo solo funciona con carreras secas.")

    tabla = marcar_vueltas_neutralizadas(tabla)
    modelo = ajustar_modelo(tabla)
    costo_pit = estimar_costo_pit(tabla, modelo)
    max_stint = largo_maximo_stint(stints, total)
    top = mejores_estrategias(modelo, num, total, costo_pit, max_stint, top=3)
    if not top:
        raise ErrorUsuario("No pude armar estrategias válidas con los datos de esa carrera.")

    mejor_t = top[0][0]
    medallas = ["🥇", "🥈", "🥉"]
    lineas = [
        f"🏁 GP de {sesion.get('country_name')} {anio} — {piloto.get('full_name')} ({piloto.get('name_acronym')})",
        f"Vueltas: {total} | Costo estimado de un pit stop: {costo_pit:.1f} s",
        "",
        "Mejores estrategias según el modelo:",
    ]
    for i, (t, est) in enumerate(top):
        extra = "" if i == 0 else f"  (+{t - mejor_t:.1f} s)"
        lineas.append(f"{medallas[i]} {describir(est)}")
        lineas.append(f"    Tiempo simulado: {fmt_tiempo(t)}{extra}")

    real = estrategia_real(stints, num, total, modelo)
    lineas.append("")
    if real:
        t_real = tiempo_estrategia(modelo, num, real, costo_pit)
        lineas.append(f"📋 Lo que hizo en la carrera: {describir(real)}")
        lineas.append(f"    Simulado: {fmt_tiempo(t_real)} ({t_real - mejor_t:+.1f} s vs la mejor)")
    else:
        lineas.append("📋 No se compara con la estrategia real (no terminó la carrera o usó neumáticos no secos).")

    lineas.append("")
    lineas.append("Degradación estimada (s por vuelta de uso): " +
                  ", ".join(f"{c} {modelo['deg'][c]:.3f}" for c in modelo["compuestos"]))
    lineas.append("⚠️ Modelo simplificado: no considera tráfico, Safety Car futuros ni clima.")
    return "\n".join(lineas)

# Puntos de entrada para el bot

def responder_estrategia(args):
    """Entrada del comando /estrategia. Devuelve (texto, filas_de_botones | None)."""
    if len(args) == 0:
        return menu_anios()

    try:
        anio = int(args[0])
    except ValueError:
        return "El primer dato tiene que ser el año, por ejemplo: /estrategia 2024", None
    if anio < PRIMER_ANIO:
        return f"Para estrategias solo hay datos desde {PRIMER_ANIO} (OpenF1). Para años anteriores probá /historico.", None

    if len(args) == 1:                      # solo el año -> botones de carreras
        return menu_carreras(anio)

    if len(args) == 2:                      # año + carrera -> botones de pilotos
        sesion = buscar_sesion(anio, args[1])
        return menu_pilotos(sesion["session_key"], sesion)

    # año + carrera + piloto -> resultado directo (modo clásico)
    piloto_q = args[-1]
    carrera_q = " ".join(args[1:-1])
    sesion = buscar_sesion(anio, carrera_q)
    return calcular_estrategia(sesion["session_key"], piloto_q, sesion), None


def manejar_callback(data):
    """Entrada de los botones. `data` es el callback_data (ej. 'est:p:9558:44').
    Devuelve (texto, filas_de_botones | None)."""
    partes = data.split(":")
    if partes[0] != PREFIJO or len(partes) < 2:
        raise ErrorUsuario("Botón no reconocido.")
    accion = partes[1]

    if accion == "y":                                   # volver a los años
        return menu_anios()
    if accion == "a" and len(partes) == 3:              # año elegido -> carreras
        return menu_carreras(int(partes[2]))
    if accion == "c" and len(partes) == 3:              # carrera elegida -> pilotos
        return menu_pilotos(int(partes[2]))
    if accion == "p" and len(partes) == 4:              # piloto elegido -> resultado
        return calcular_estrategia(int(partes[2]), partes[3]), None
    raise ErrorUsuario("Botón no reconocido.")
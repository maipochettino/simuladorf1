"""Funciones y constantes compartidas por los comandos del bot."""
import time
import unicodedata
import requests

OPENF1 = "https://api.openf1.org/v1"

JOLPICA = "https://api.jolpi.ca/ergast/f1"

COMPUESTOS_SECOS = ["SOFT", "MEDIUM", "HARD"]

MIN_STINT = 6

PIT_LOSS_DEFECTO = 22.0

FUEL_DEFECTO = -0.05

_cache_http = {}

ALIAS = {
    "belgica": ["belgium", "spa"],
    "italia": ["italy", "monza", "imola"],
    "espana": ["spain", "barcelona", "madrid"],
    "brasil": ["brazil", "interlagos", "paulo"],
    "japon": ["japan", "suzuka"],
    "holanda": ["netherlands", "zandvoort"],
    "paises bajos": ["netherlands", "zandvoort"],
    "hungria": ["hungary"],
    "inglaterra": ["united kingdom", "great britain", "silverstone", "uk"],
    "gran bretana": ["united kingdom", "great britain", "silverstone", "uk"],
    "reino unido": ["united kingdom", "great britain", "silverstone", "uk"],
    "azerbaiyan": ["azerbaijan", "baku"],
    "singapur": ["singapore"],
    "abu dabi": ["abu dhabi", "yas", "emirates", "uae"],
    "abu dhabi": ["abu dhabi", "yas", "emirates", "uae"],
    "emiratos": ["abu dhabi", "yas", "emirates", "uae"],
    "catar": ["qatar", "lusail"],
    "arabia saudita": ["saudi", "jeddah"],
    "arabia": ["saudi", "jeddah"],
    "estados unidos": ["united states", "usa", "austin", "miami", "las vegas"],
    "eeuu": ["united states", "usa", "austin", "miami", "las vegas"],
    "bahrein": ["bahrain", "sakhir"],
    "alemania": ["germany", "hockenheim", "nurburgring"],
    "francia": ["france", "paul ricard", "magny"],
    "turquia": ["turkey", "istanbul"],
    "rusia": ["russia", "sochi"],
    "canada": ["canada", "montreal"],
}

class ErrorUsuario(Exception):
    """Errores con mensaje pensado para mostrarle al usuario."""

def get_json(url, params=None):
    """GET con caché en memoria y reintentos si la API limita (429)."""
    clave = (url, tuple(sorted((params or {}).items())))
    if clave in _cache_http:
        return _cache_http[clave]

    for intento in range(4):
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 404:
            datos = []
            break
        if r.status_code == 429:
            time.sleep(3 * (intento + 1))
            continue
        r.raise_for_status()
        datos = r.json()
        break
    else:
        raise ErrorUsuario("La API está limitando las consultas. Probá de nuevo en un minuto.")

    _cache_http[clave] = datos
    return datos

def norm(s):
    """minúsculas y sin acentos: 'Bélgica' -> 'belgica'."""
    s = unicodedata.normalize("NFD", str(s).lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").strip()

def coincide(consulta, texto):
    """True si la consulta (o su traducción) aparece en el texto."""
    q = norm(consulta)
    tokens = ALIAS.get(q, [q])
    texto = norm(texto)
    return any(t in texto for t in tokens)

def fmt_tiempo(seg):
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{int(h)}:{int(m):02d}:{s:04.1f}"

def jolpica(ruta, **params):
    datos = get_json(f"{JOLPICA}/{ruta}.json", params)
    if not isinstance(datos, dict) or "MRData" not in datos:
        raise ErrorUsuario("No encontré datos para esa consulta.")
    return datos["MRData"]


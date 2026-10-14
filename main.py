"""Punto de entrada del bot de Telegram."""
import asyncio
import logging
import os
import sys
import requests
from comandos.common import ErrorUsuario
from comandos.estrategia import responder_estrategia
from comandos.quepiloto import responder_quepiloto
from comandos.historico import responder_historico

AYUDA = (
    "🏎️ Bot de F1\n\n"
    "/estrategia <año> <carrera> <piloto>\n   ej: /estrategia 2024 belgica HAM\n\n"
    "/quepiloto <mes>\n   ej: /quepiloto marzo\n\n"
    "/historico <año> [carrera]\n   ej: /historico 2008  |  /historico 1994 brasil"
)

def ejecutar(funcion, args):
    try:
        return funcion(args)
    except ErrorUsuario as e:
        return f"⚠️ {e}"
    except requests.RequestException:
        return "⚠️ No pude conectarme a la API de datos. Probá de nuevo en un rato."
    except Exception:
        logging.exception("Error inesperado")
        return "⚠️ Ocurrió un error inesperado calculando eso."

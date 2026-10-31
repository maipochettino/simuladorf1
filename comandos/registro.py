"""Registro de interacciones del bot en un archivo CSV.

Estas funciones no dependen de Telegram, así que se pueden probar solas.
"""
import csv
import os
from datetime import datetime

RUTA_CSV = os.path.join("data", "historial.csv")

COLUMNAS = ["timestamp", "chat_id", "nombre", "tipo", "mensaje"]


def registrar(chat_id, nombre, mensaje, tipo, ruta=RUTA_CSV):
    """Agrega una fila al CSV. Si el archivo no existe, lo crea con encabezado."""
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)

    es_nuevo = not os.path.exists(ruta)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # newline="" es lo que recomienda el módulo csv para que no queden líneas en blanco
    with open(ruta, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        if es_nuevo:
            escritor.writerow(COLUMNAS)
        escritor.writerow([timestamp, chat_id, nombre, tipo, mensaje])


def es_historial(mensaje):
    """True si el mensaje es el comando /historial (también '/historial@nombre_bot')."""
    palabras = mensaje.split()
    if not palabras:
        return False
    comando = palabras[0].split("@")[0].lower()
    return comando == "/historial"


def ultimas_consultas(chat_id, n=5, ruta=RUTA_CSV):
    """Últimas n filas de ese chat_id, de la más nueva a la más vieja, sin los /historial."""
    if not os.path.exists(ruta):
        return []

    with open(ruta, newline="", encoding="utf-8") as archivo:
        filas = list(csv.DictReader(archivo))

    # En el CSV todo se lee como texto, por eso comparamos con str(chat_id)
    del_chat = [
        fila for fila in filas
        if fila["chat_id"] == str(chat_id) and not es_historial(fila["mensaje"])
    ]

    # Las filas se agregan en orden, así que las últimas del archivo son las más nuevas
    del_chat.reverse()
    return del_chat[:n]


def formatear_historial(filas):
    """Arma el texto para mandarle al usuario."""
    if not filas:
        return (
            "📭 Todavía no tengo consultas tuyas guardadas.\n"
            "Probá alguno de los comandos de /ayuda 🏎️"
        )

    if len(filas) == 1:
        titulo = "📜 Tu última consulta:\n"
    else:
        titulo = f"📜 Tus últimas {len(filas)} consultas:\n"

    lineas = [titulo]
    for fila in filas:
        lineas.append(f"🕒 {fila['timestamp']} → {fila['mensaje']}")
    return "\n".join(lineas)

"""Pruebas de comandos/registro.py usando un CSV temporal.

Se corre desde la carpeta del proyecto con:  python tests/probar_registro.py
"""
import os
import sys
import tempfile

# Para poder importar "comandos" corriendo el archivo desde la raíz del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comandos.registro import registrar, ultimas_consultas, formatear_historial


def probar_encabezado(carpeta):
    ruta = os.path.join(carpeta, "encabezado.csv")
    registrar(111, "Ana", "/ayuda", "comando", ruta=ruta)
    registrar(111, "Ana", "hola", "texto", ruta=ruta)

    with open(ruta, encoding="utf-8") as archivo:
        lineas = archivo.read().splitlines()

    assert lineas[0] == "timestamp,chat_id,nombre,tipo,mensaje"
    assert len(lineas) == 3, "tiene que haber 1 encabezado + 2 filas"
    assert sum(1 for l in lineas if l.startswith("timestamp")) == 1, "el encabezado no se repite"
    print("✅ se crea con encabezado una sola vez")


def probar_caracteres_raros(carpeta):
    ruta = os.path.join(carpeta, "raros.csv")
    mensaje = 'hola, "Checo"\nsegunda línea; ñandú 🏎️'
    registrar(222, "Beto", mensaje, "texto", ruta=ruta)

    filas = ultimas_consultas(222, ruta=ruta)
    assert len(filas) == 1
    assert filas[0]["mensaje"] == mensaje
    assert filas[0]["nombre"] == "Beto"
    print("✅ comas, comillas y saltos de línea se guardan y se leen igual")


def probar_ultimas_consultas(carpeta):
    ruta = os.path.join(carpeta, "ultimas.csv")
    for i in range(1, 8):
        registrar(333, "Caro", f"/historico {2000 + i}", "comando", ruta=ruta)
        registrar(999, "Otro", f"mensaje de otro {i}", "texto", ruta=ruta)
    registrar(333, "Caro", "/historial", "comando", ruta=ruta)
    registrar(333, "Caro", "/historial@mi_bot", "comando", ruta=ruta)

    filas = ultimas_consultas(333, ruta=ruta)
    mensajes = [f["mensaje"] for f in filas]

    assert len(filas) == 5, "máximo 5"
    assert all(f["chat_id"] == "333" for f in filas), "solo las del chat pedido"
    assert mensajes == ["/historico 2007", "/historico 2006", "/historico 2005",
                        "/historico 2004", "/historico 2003"], "la más nueva primero"
    assert not any(m.startswith("/historial") for m in mensajes), "sin los /historial"

    # También funciona con n distinto
    assert len(ultimas_consultas(333, n=2, ruta=ruta)) == 2
    print("✅ ultimas_consultas filtra por chat, máximo 5, más nueva primero, sin /historial")


def probar_sin_archivo(carpeta):
    ruta = os.path.join(carpeta, "no_existe.csv")
    assert ultimas_consultas(444, ruta=ruta) == []
    print("✅ sin archivo devuelve lista vacía")


def probar_formatear():
    assert "/ayuda" in formatear_historial([])
    texto = formatear_historial([{"timestamp": "2026-10-14 11:51:03", "mensaje": "/quepiloto marzo"}])
    assert "2026-10-14 11:51:03" in texto and "/quepiloto marzo" in texto
    print("✅ formatear_historial arma el texto")


if __name__ == "__main__":
    # La carpeta temporal se borra sola al terminar: no tocamos data/historial.csv
    with tempfile.TemporaryDirectory() as carpeta:
        probar_encabezado(carpeta)
        probar_caracteres_raros(carpeta)
        probar_ultimas_consultas(carpeta)
        probar_sin_archivo(carpeta)
        probar_formatear()
    print("\nTodas las pruebas pasaron 🎉")

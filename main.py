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
from comandos.registro import registrar, ultimas_consultas, formatear_historial

AYUDA = (
    "🏎️ Bot de F1\n\n"
    "/estrategia <año> <carrera> <piloto>\n   ej: /estrategia 2024 belgica HAM\n\n"
    "/quepiloto <mes>\n   ej: /quepiloto marzo\n\n"
    "/historico <año> [carrera]\n   ej: /historico 2008  |  /historico 1994 brasil\n\n"
    "/historial\n   tus últimas 5 consultas"
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

def describir_update(update):
    """Devuelve (tipo, mensaje) para guardar en el CSV, o None si no hay nada que guardar."""
    if update.callback_query:
        return "boton", update.callback_query.data

    mensaje = update.effective_message
    if mensaje is None:
        return None
    if mensaje.text:
        tipo = "comando" if mensaje.text.startswith("/") else "texto"
        return tipo, mensaje.text
    if mensaje.voice or mensaje.audio:
        return "audio", "[audio]"
    if mensaje.document:
        return "documento", f"[documento: {mensaje.document.file_name}]"
    if mensaje.photo:
        return "foto", "[foto]"
    return None

def main():
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes, TypeHandler

    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        sys.exit("Falta la variable de entorno TELEGRAM_TOKEN (el token que te da @BotFather).")

    async def registrar_interaccion(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Se ejecuta antes que cualquier comando y guarda el mensaje en el CSV."""
        try:
            descripcion = describir_update(update)
            if descripcion is None or update.effective_chat is None:
                return
            tipo, mensaje = descripcion
            usuario = update.effective_user
            nombre = usuario.first_name if usuario and usuario.first_name else "desconocido"
            registrar(update.effective_chat.id, nombre, mensaje, tipo)
        except Exception:
            # Si falla el registro (ej: el CSV está abierto en Excel), el bot sigue andando
            logging.exception("No se pudo registrar la interacción")

    async def cmd_historial(update: Update, context: ContextTypes.DEFAULT_TYPE):
        filas = ultimas_consultas(update.effective_chat.id)
        await update.message.reply_text(formatear_historial(filas))

    async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(AYUDA)

    def crear_comando(funcion, mensaje_espera):
        async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(mensaje_espera)
            texto = await asyncio.to_thread(ejecutar, funcion, context.args)
            await update.message.reply_text(texto)
        return handler

    app = Application.builder().token(token).build()
    # group=-1: corre antes que los demás handlers y no les impide ejecutarse
    app.add_handler(TypeHandler(Update, registrar_interaccion), group=-1)
    app.add_handler(CommandHandler(["start", "ayuda", "help"], cmd_ayuda))
    app.add_handler(CommandHandler("estrategia", crear_comando(responder_estrategia, "⏳ Simulando estrategias, puede tardar unos segundos...")))
    app.add_handler(CommandHandler("quepiloto", crear_comando(responder_quepiloto, "🔎 Buscando tu piloto...")))
    app.add_handler(CommandHandler("historico", crear_comando(responder_historico, "📚 Buscando datos históricos...")))
    app.add_handler(CommandHandler("historial", cmd_historial))
    print("Bot corriendo. Ctrl+C para detener.")
    app.run_polling()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        comandos = {
            "estrategia": responder_estrategia,
            "quepiloto": responder_quepiloto,
            "historico": responder_historico,
        }
        if sys.argv[1] in comandos:
            print(ejecutar(comandos[sys.argv[1]], sys.argv[2:]))
            sys.exit()
    main()

# 🏎️ Simulador F1: bot de Telegram

Bot de Telegram sobre Fórmula 1, hecho para el TP de Bot con API de Telegram (Universidad Austral, 2026).

Se usa en Telegram como **[@monaco_f1_bot](https://t.me/monaco_f1_bot)**.

El bot simula estrategias de neumáticos con datos reales de carreras, te dice qué piloto nació en el mismo mes que vos y muestra resultados históricos de la F1 desde 1950.

## Comandos

| Comando | Qué hace | Ejemplo |
|---|---|---|
| `/start` | Te saluda por tu nombre y te explica qué podés hacer | `/start` |
| `/ayuda` | Lista los comandos principales | `/ayuda` |
| `/estrategia` | Simula las mejores estrategias de neumáticos de un piloto en una carrera y las compara con la que hizo en realidad | `/estrategia 2024 belgica HAM` |
| `/quepiloto` | Te dice qué piloto de F1 nació en el mismo mes que vos, con sus estadísticas | `/quepiloto marzo` |
| `/historico` | Muestra el podio de una carrera o el campeonato de pilotos de un año | `/historico 1994 brasil` |
| `/historial` | Muestra tus últimas 5 consultas | `/historial` |
| `/botones` | Atajos a la web y las redes oficiales de la F1 | `/botones` |
| `/problema` | Avisa a las administradoras que tenés un problema | `/problema` |
| `/fin` | Cierra la conversación | `/fin` |

Si escribís `/estrategia`, `/quepiloto` o `/historico` sin datos, el bot te guía con botones o preguntas.

Además, el bot:
- responde **audios, notas de voz y documentos**;
- tiene un comando oculto, **`/dolar`**, con la cotización del dólar en Argentina.

## ¿Cómo funciona `/estrategia`?

1. Descarga de OpenF1 todas las vueltas y los neumáticos de la carrera elegida.
2. Descarta las vueltas que no sirven: la primera, las de entrada y salida de boxes, las que tuvieron Safety Car o bandera amarilla, y las que son claramente más lentas de lo normal.
3. Ajusta un modelo lineal con mínimos cuadrados:

   `tiempo de vuelta = ritmo del piloto + diferencia del compuesto + degradación × edad del neumático + efecto del combustible × nro. de vuelta`

4. Estima cuánto tiempo se pierde en un pit stop.
5. Prueba todas las estrategias posibles de 1 y 2 paradas (usando al menos 2 compuestos) y muestra las 3 más rápidas.
6. Las compara con la estrategia que el piloto hizo en la carrera.

Es un modelo simplificado: no tiene en cuenta el tráfico, Safety Cars futuros ni el clima. Solo funciona con carreras en seco.

## APIs que usa

| API | Para qué |
|---|---|
| [OpenF1](https://openf1.org) | Vueltas, neumáticos y pilotos de cada carrera, desde 2023 (`/estrategia`) |
| [Jolpica (Ergast)](https://github.com/jolpica/jolpica-f1) | Resultados, campeonatos y datos de pilotos, desde 1950 (`/historico`, `/quepiloto`) |
| [DolarApi](https://dolarapi.com) | Cotización del dólar (`/dolar`) |
| [Telegram Bot API](https://core.telegram.org/bots/api) | Mensajes, botones, archivos y acciones del bot, mediante `pyTelegramBotAPI` |

## Registro de uso

Cada mensaje que recibe el bot se guarda en `data/historial.csv` con estas columnas:

`timestamp, chat_id, nombre, tipo, mensaje`

Ese archivo se usa para:
- el comando `/historial`, que devuelve las últimas 5 consultas de cada usuario;
- el notebook `notebooks/uso_del_bot.ipynb`, que analiza cómo se usa el bot.

El CSV no se sube al repositorio porque tiene datos de los usuarios. Se crea solo la primera vez que alguien usa el bot.

## Estructura del proyecto

```
simuladorf1/
├── bot.ipynb               # El bot: handlers de Telegram y arranque
├── comandos/
│   ├── common.py           # Funciones compartidas (consultas HTTP con caché, alias de países, etc.)
│   ├── estrategia.py       # Modelo y simulación de estrategias
│   ├── historico.py        # Resultados y campeonatos históricos
│   ├── quepiloto.py        # Piloto según mes de nacimiento
│   └── registro.py         # Registro en CSV e historial
├── notebooks/
│   └── uso_del_bot.ipynb   # Análisis del uso del bot
├── tests/
│   └── probar_registro.py  # Pruebas del registro en CSV
├── videos/
│   └── intro_f1.mp4        # Video de intro que manda /estrategia
├── requirements.txt
└── .env.example
```

## Cómo correrlo

1. Cloná el repositorio:
   ```bash
   git clone https://github.com/maipochettino/simuladorf1.git
   cd simuladorf1
   ```
2. Instalá las dependencias (conviene hacerlo en un entorno virtual):
   ```bash
   pip install -r requirements.txt
   ```
3. Creá un archivo `.env`, copiando `.env.example`, y poné el token que te da BotFather:
   ```
   TELEGRAM_TOKEN=tu_token_acá
   ```
4. Abrí `bot.ipynb` y ejecutá todas las celdas (**Run All**). La última celda deja el bot escuchando.

Solo puede correr **una instancia del bot a la vez**. Si hay dos prendidas, Telegram devuelve el error `409 Conflict`.

Para probar el registro en CSV:
```bash
python tests/probar_registro.py
```

## Equipo

- Mailén Pochettino
- Candela Cambiaso
- Ornella Quintanilla
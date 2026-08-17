# Sales Intel Transcriber MVP

Primera etapa de una aplicación SaaS de inteligencia conversacional para reuniones comerciales. Esta versión captura audio del micrófono, lo envía en fragmentos cortos a un servicio moderno de voz a texto y muestra la transcripción en la consola mientras hablas.

El diseño separa captura de audio, proveedor de transcripción y salida por consola para que luego puedas agregar detección de intenciones, recomendaciones al vendedor, notificaciones e integraciones con Google Meet, Zoom o Microsoft Teams.

## Requisitos

- Python 3.11 o superior.
- Un micrófono disponible y autorizado por el sistema operativo.
- Una API key de OpenAI con acceso al modelo de transcripción.

## Instalación en Windows PowerShell

```powershell
cd C:\Users\Frank\Documents\Codex\2026-07-27\hol\outputs\sales-intel-transcriber
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
copy .env.example .env
```

Edita `.env` y reemplaza `OPENAI_API_KEY` por tu clave real.

Si PowerShell bloquea la activación del entorno virtual, ejecuta:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Instalación en macOS o Linux

```bash
cd /ruta/al/proyecto/sales-intel-transcriber
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Edita `.env` y reemplaza `OPENAI_API_KEY` por tu clave real.

## Ejecución

```powershell
sales-transcriber
```

Habla por el micrófono. La aplicación imprimirá texto en la consola y se detendrá con `Ctrl+C`.

## Interfaz web local

```powershell
sales-transcriber-ui
```

La interfaz queda disponible en `http://127.0.0.1:8765` y permite iniciar o detener la captura desde el navegador.

Para preparar y correr el proyecto en otro PC con Windows:

```powershell
cd C:\Proyectos\sales-intel-transcriber
.\run-ui.ps1
```

Tambien puedes iniciar la interfaz con doble click en `start-ui.cmd`.

Para generar un ejecutable local:

```powershell
cd C:\Proyectos\sales-intel-transcriber
.\build-exe.ps1
```

El archivo queda en `dist\SalesIntelTranscriber\SalesIntelTranscriber.exe`.

## Requisito para coach IA

El ejecutable incluye la transcripcion local con Whisper, pero el coach IA usa Ollama como servidor LLM local.

En cada PC donde quieras usar el coach:

1. Instala Ollama para Windows desde `https://ollama.com/download/windows`.
2. Abre PowerShell y descarga el modelo:

```powershell
ollama run qwen3:1.7b
```

Ollama queda escuchando en `http://localhost:11434`. Si Ollama no esta instalado o no esta corriendo, la transcripcion puede funcionar, pero el panel de inteligencia comercial mostrara un error de conexion LLM.

Para un PC cliente, usa el asistente incluido en la carpeta del ejecutable:

```powershell
.\install-ollama-and-model.ps1
```

Ese script abre la descarga oficial de Ollama si falta, verifica el servidor local y descarga `qwen3:1.7b`.

## Diagnosticar el microfono

Lista los dispositivos de entrada:

```powershell
sales-audio-check --list
```

Mide el nivel del microfono por defecto:

```powershell
sales-audio-check
```

Mide un dispositivo especifico:

```powershell
sales-audio-check --device 2
```

Si encuentras el dispositivo correcto, deja su indice fijo en `.env`:

```env
AUDIO_DEVICE=2
```

Si el diagnostico dice `Sin muestras recibidas aun` o `RMS maximo detectado: 0.0` para todos los dispositivos, el problema esta antes de la app: Windows esta exponiendo el microfono, pero Python no esta recibiendo audio. Revisa:

- Configuracion > Privacidad y seguridad > Microfono.
- Activa `Acceso al microfono`.
- Activa `Permitir que las aplicaciones accedan al microfono`.
- Activa `Permitir que las aplicaciones de escritorio accedan al microfono`.
- Configuracion > Sistema > Sonido > Entrada: selecciona el microfono correcto y verifica que la barra de nivel se mueva al hablar.
- En Propiedades del microfono, verifica que el volumen de entrada no este en cero.
- En Configuracion avanzada de sonido, desactiva temporalmente el modo exclusivo si aparece disponible.

Despues vuelve a probar:

```powershell
sales-audio-check --device 12 --seconds 8
sales-audio-check --device 10 --seconds 8
sales-audio-check --device 1 --seconds 8
```

## Configuración

Variables soportadas en `.env`:

- `OPENAI_API_KEY`: clave de API requerida.
- `TRANSCRIBER_PROVIDER`: `openai` o `whisper-local`. Si no se define, usa OpenAI cuando hay API key real; de lo contrario usa Whisper local.
- `TRANSCRIBER_MODEL`: modelo de voz a texto. Por defecto `gpt-4o-transcribe`.
- `TRANSCRIBER_LANGUAGE`: idioma ISO-639-1. Por defecto `es`.
- `TRANSCRIBER_DEBUG`: imprime diagnostico tecnico cuando vale `true`.
- `WHISPER_MODEL`: modelo local de Faster Whisper. Por defecto `base`.
- `WHISPER_NO_SPEECH_THRESHOLD`: sensibilidad interna de Whisper para silencio. Por defecto `0.8`.
- `WHISPER_LOG_PROB_THRESHOLD`: filtro de confianza de Whisper. Por defecto `-0.8`.
- `AUDIO_SAMPLE_RATE`: frecuencia de muestreo. Por defecto `16000`.
- `AUDIO_CHANNELS`: canales de audio. Por defecto `1`.
- `AUDIO_CHUNK_SECONDS`: tamano base de fragmento de audio. Por defecto `1.5`.
- `AUDIO_DEVICE`: dispositivo de entrada opcional. Puede ser un índice numérico o nombre reconocido por `sounddevice`.
- `AUDIO_MIN_RMS`: umbral de volumen para ignorar silencio. Por defecto `50`.
- `MAX_SEGMENT_SECONDS`: duracion maxima de cada segmento enviado a Whisper. Por defecto `12`.
- `OVERLAP_SECONDS`: audio repetido solo cuando un segmento se corta por duracion maxima. Por defecto `0.4`.
- `MIN_SEGMENT_SECONDS`: duracion minima de un segmento para transcribir. Por defecto `1`.

## Si aparecen textos falsos como "y y y"

Whisper puede producir palabras cortas cuando recibe silencio o ruido constante. Esta version filtra audio silencioso antes de transcribir y descarta segmentos de baja informacion como `y`, `eh` o `mmm`.

Si sigue apareciendo texto sin hablar, sube el umbral:

```powershell
$env:AUDIO_MIN_RMS="600"
sales-transcriber
```

Para dejarlo fijo, agrega o cambia esta linea en `.env`:

```env
AUDIO_MIN_RMS=600
```

Si no transcribe cuando hablas bajo, baja el valor a `200` o `250`.

## Notas de arquitectura

- `audio/capture.py`: captura fragmentos PCM desde el micrófono y los convierte a WAV en memoria.
- `stt/base.py`: define el contrato reusable para proveedores de voz a texto.
- `stt/openai_client.py`: implementación OpenAI con streaming de deltas y reintentos ante fallos de conexión.
- `console.py`: presentación de transcripción en consola.
- `app.py`: orquestación del flujo continuo.

Para una integración futura con Meet, Zoom o Teams, conviene mantener el contrato `SpeechToTextClient` y crear nuevos productores de audio que entreguen `AudioChunk` desde esas fuentes.

## Manejo de errores

- Si no hay micrófono o no hay permisos, la aplicación muestra un mensaje claro y termina.
- Si la conexión con el servicio de transcripción falla, realiza reintentos con espera incremental.
- Si falta `OPENAI_API_KEY`, la aplicación falla temprano con instrucciones concretas.

## Referencia del servicio

La implementación usa el endpoint oficial de OpenAI `/v1/audio/transcriptions`, que soporta modelos como `gpt-4o-transcribe` y eventos de streaming de tipo `transcript.text.delta`.

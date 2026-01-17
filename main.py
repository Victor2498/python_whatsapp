import os
import json
import requests
from fastapi import FastAPI, Request
from openai import OpenAI

app = FastAPI()

# Configuración desde variables de entorno (más seguro)
EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- CONFIGURACIÓN DE LA INMOBILIARIA ---
AGENCY_NAME = "Agentech Propiedades"

# Cargar catálogo de propiedades
try:
    with open("propiedades.json", "r", encoding="utf-8") as f:
        PROPIEDADES = json.load(f)
except Exception:
    PROPIEDADES = []

PROPIEDADES_STR = "\n".join([f"- {p['titulo']} ({p['operacion']}): {p['precio']}. {p['descripcion']}" for p in PROPIEDADES])

AGENCY_INFO = f"""
Somos una inmobiliaria líder en Argentina, especializada en alquileres, ventas y tasaciones.
Ubicación: Buenos Aires, Argentina.
Horarios: Lunes a Viernes de 9hs a 18hs.

Nuestro catálogo actual incluye:
{PROPIEDADES_STR}
"""

SYSTEM_PROMPT = f"""
Eres el asistente virtual experto de {AGENCY_NAME}.
{AGENCY_INFO}

Instrucciones de comportamiento:
1. Sé siempre amable, profesional y servicial.
2. Si el cliente pregunta por alquileres, menciónale que pedimos garantía propietaria o seguro de caución.
3. Si el cliente pregunta por una propiedad específica, búscala en el catálogo mencionado arriba.
4. Si el cliente pregunta por algo que no está en el catálogo, dile que un asesor humano lo contactará a la brevedad.
5. Intenta siempre obtener el nombre del cliente si la conversación avanza.
6. Responde de forma concisa pero completa.
"""
# ----------------------------------------

@app.get("/")
async def health_check():
    return {"status": "ok", "message": "Agentech API is running"}

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    # Validar que el evento contenga un mensaje
    if data.get("event") == "messages.upsert":
        msg = data["data"]
        
        # Ignorar si el mensaje lo enviamos nosotros
        if msg["key"]["fromMe"]:
            return {"status": "ignored"}

        remote_jid = msg["key"]["remoteJid"]
        # Extraer texto (maneja si es texto simple o de botón)
        user_text = msg.get("message", {}).get("conversation") or \
                    msg.get("message", {}).get("extendedTextMessage", {}).get("text", "")

        # Lógica de respuesta
        print(f"Mensaje recibido de {remote_jid}: {user_text}")
        
        if user_text.lower().strip() == "hola":
            ai_response = "soy Agentech, buen día"
        else:
            # 1. Consultar a OpenAI para otros mensajes
            print("Consultando a OpenAI...")
            ai_response = get_chatgpt_response(user_text)
            print(f"Respuesta de OpenAI: {ai_response}")

        # 2. Enviar respuesta a Evolution API
        if ai_response:
            print(f"Enviando respuesta a WhatsApp: {ai_response}")
            send_to_whatsapp(remote_jid, ai_response)
        else:
            print("Error: No hay respuesta para enviar")

    return {"status": "success"}

def get_chatgpt_response(text):
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content
    except Exception as e:
        print(f"ERROR EN OPENAI: {e}")
        return "Lo siento, tengo un problema técnico para procesar tu consulta ahora mismo."

def send_to_whatsapp(jid, text):
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": jid,
        "text": text,
        "delay": 1500 # Simula escritura por 1.5 segundos
    }
    headers = {"apiKey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Estado de envío Evolution API: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"ERROR ENVIANDO A EVOLUTION: {e}")
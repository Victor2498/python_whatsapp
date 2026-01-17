import os
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

        if not user_text:
            return {"status": "no_text"}

        # 1. Consultar a OpenAI
        ai_response = get_chatgpt_response(user_text)

        # 2. Enviar respuesta a Evolution API
        send_to_whatsapp(remote_jid, ai_response)

    return {"status": "success"}

def get_chatgpt_response(text):
    completion = client.chat.completions.create(
        model="gpt-4o-mini", # Económico y rápido para inmobiliarias
        messages=[
            {"role": "system", "content": "Eres un asesor inmobiliario experto de Agentech en Argentina. Responde de forma amable y profesional."},
            {"role": "user", "content": text}
        ]
    )
    return completion.choices[0].message.content

def send_to_whatsapp(jid, text):
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": jid,
        "text": text,
        "delay": 1500 # Simula escritura por 1.5 segundos
    }
    headers = {"apiKey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)
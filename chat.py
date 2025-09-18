from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# -----------------------------
# CONFIGURACIONES
# -----------------------------
WHATSAPP_TOKEN = "TU_TOKEN_DE_META"  # token de Meta Developers
WHATSAPP_PHONE_ID = "TU_PHONE_NUMBER_ID"  # el que aparece en meta
OPENAI_API_KEY = "TU_API_KEY_OPENAI"

# URLs de las APIs
WHATSAPP_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

# -----------------------------
# FUNCIONES
# -----------------------------

def enviar_whatsapp(destino, texto):
    """Enviar un mensaje de texto a WhatsApp"""
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": destino,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(WHATSAPP_URL, headers=headers, json=data)


def responder_chatgpt(mensaje):
    """Enviar mensaje a ChatGPT y recibir respuesta"""
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Eres un coach de entrevistas de trabajo. Responde de manera clara y útil."},
            {"role": "user", "content": mensaje}
        ]
    }
    response = requests.post(OPENAI_URL, headers=headers, json=data).json()
    return response["choices"][0]["message"]["content"]


def mostrar_menu():
    return (
        "👋 Bienvenido a *Interview IA*\n"
        "Un bot que te entrena para mejorar en tus entrevistas de trabajo.\n\n"
        "Por favor elige una opción:\n"
        "1️⃣ Empezar simulación de entrevista\n"
        "2️⃣ Continuar entrevistas anteriores\n"
        "3️⃣ Salir"
    )

# -----------------------------
# ENDPOINT PRINCIPAL
# -----------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    if "messages" in data["entry"][0]["changes"][0]["value"]:
        mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
        texto_usuario = mensaje.get("text", {}).get("body", "")
        telefono = mensaje["from"]

        # Si el usuario escribe "menu" o es su primer mensaje → mostrar menú
        if texto_usuario.lower() in ["menu", "hola", "hi", "hello", "buenas"]:
            enviar_whatsapp(telefono, mostrar_menu())
        elif texto_usuario == "1":
            enviar_whatsapp(telefono, "✅ Iniciando simulación de entrevista...\nEscríbeme para comenzar.")
        elif texto_usuario == "2":
            enviar_whatsapp(telefono, "📂 Recuperando entrevistas anteriores...")
        elif texto_usuario == "3":
            enviar_whatsapp(telefono, "👋 ¡Gracias por usar Interview IA! Hasta la próxima.")
        else:
            # cualquier otra cosa → pasar a ChatGPT como parte de la simulación
            respuesta = responder_chatgpt(texto_usuario)
            enviar_whatsapp(telefono, respuesta)

    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(port=5000, debug=True)
hola soy pepito
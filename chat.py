from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# -------------------------------
# CONFIGURACIÓN
# -------------------------------
VERIFY_TOKEN = "msa1033"
WHATSAPP_TOKEN = "EAAPObyrRpkoBPoeAJonmsFiTsKBTMbZAq673uXIhvrSefoUHlgiZAjKfNvIbDvpRjDrfDnVSqA1Iqxx4TIOM9Sw2Q0ZATLYDWvdrKQGTaqbnVASyuTa69u0CHpEI70c5FUAktffmW19VqirLjTXo0f9iQycb3rsZCtyhqZCJMfXQYscsvoP401Nl5k8PYx3DEeuoZBl53ydY5pgG0N7Y8FdZCMfvbLKcteDHaZB9TKUdZCTMZD"
WHATSAPP_PHONE_ID = "857442030778486"
OPENAI_API_KEY = "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"

WHATSAPP_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"


# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def enviar_whatsapp(destino, texto):
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


# -------------------------------
# WEBHOOK (GET y POST)
# -------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    # ---- VERIFICACIÓN (GET)
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente.")
            return challenge, 200
        else:
            return "Error de verificación", 403

    # ---- RECEPCIÓN DE MENSAJES (POST)
    elif request.method == "POST":
        data = request.get_json()
        print("📩 Mensaje recibido:")
        print(data)

        try:
            if "messages" in data["entry"][0]["changes"][0]["value"]:
                mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
                texto_usuario = mensaje.get("text", {}).get("body", "").lower()
                telefono = mensaje["from"]

                if texto_usuario in ["menu", "hola", "hi", "hello", "buenas"]:
                    enviar_whatsapp(telefono, mostrar_menu())
                elif texto_usuario == "1":
                    enviar_whatsapp(telefono, "✅ Iniciando simulación de entrevista...\nEscríbeme tu primera respuesta.")
                elif texto_usuario == "2":
                    enviar_whatsapp(telefono, "📂 Recuperando entrevistas anteriores...")
                elif texto_usuario == "3":
                    enviar_whatsapp(telefono, "👋 ¡Gracias por usar Interview IA! Hasta la próxima.")
                else:
                    respuesta = responder_chatgpt(texto_usuario)
                    enviar_whatsapp(telefono, respuesta)
        except Exception as e:
            print("⚠️ Error procesando mensaje:", e)

        return "EVENT_RECEIVED", 200


# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    app.run(port=5000, debug=True)

from flask import Flask, request
import requests
import json

app = Flask(__name__)

# =========================================================
# ✅ Credenciales actualizadas
# =========================================================
VERIFY_TOKEN = "msa1033"
WHATSAPP_TOKEN = "EAAPObyrRpkoBPnL63p3XczOWpx2lImXhQBhM64HKFq0ggIL5xRsKK4wipcqwZCdIbIUtAjiiSXi4CDm9Li8ZCgAwFHFg9GSxjq5tiFhjNkw1CmfdfgIePZCYXanrCYvZBncrOYUz5VXhgauJQgV5j597xV3DNnBhk9nZAGpUhkgF7pqV8qKasONABZAYl888PbdKxLbytA0ecpKIZBVctpCDUBiVFBgHRbkCtcVXgCFYAZDZD"
WHATSAPP_PHONE_ID = "857442030778486"
OPENROUTER_API_KEY = "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"  # 👈 Pega aquí tu clave de OpenRouter

# =========================================================
# ✅ Función para obtener respuesta de la IA (OpenRouter)
# =========================================================
def obtener_respuesta_ia(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": "Eres un entrenador de entrevistas laborales, amable y profesional. Ayudas a los usuarios a prepararse para entrevistas de trabajo con ejemplos reales y consejos."},
            {"role": "user", "content": prompt}
        ]
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"⚠️ Error {response.status_code}: {response.text}"

# =========================================================
# ✅ Función para enviar mensaje por WhatsApp Cloud API
# =========================================================
def enviar_mensaje(numero, texto):
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }
    requests.post(url, headers=headers, json=data)

# =========================================================
# ✅ Menú inicial del bot
# =========================================================
def menu_principal():
    return (
        "👋 ¡Bienvenido a *Interview IA*!\n"
        "Soy tu bot entrenador para entrevistas de trabajo.\n\n"
        "Por favor elige una opción:\n\n"
        "1️⃣ Empezar simulación de entrevista\n"
        "2️⃣ Continuar entrevista anterior\n"
        "3️⃣ Ver consejos de entrevistas\n"
        "4️⃣ Salir\n\n"
        "_Escribe el número de tu opción_"
    )

# =========================================================
# ✅ Webhook de verificación
# =========================================================
@app.route('/webhook', methods=['GET'])
def verificar_token():
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    if token == VERIFY_TOKEN:
        return challenge
    return "Token inválido"

# =========================================================
# ✅ Webhook para recibir mensajes
# =========================================================
@app.route('/webhook', methods=['POST'])
def recibir_mensajes():
    data = request.get_json()
    try:
        mensaje = data['entry'][0]['changes'][0]['value']['messages'][0]
        numero = mensaje['from']
        texto = mensaje['text']['body'].strip().lower()

        # Lógica del menú
        if texto in ['hola', 'menu', 'hi', 'buenas']:
            enviar_mensaje(numero, menu_principal())

        elif texto == '1':
            enviar_mensaje(numero, "🎯 *Iniciando Simulación de Entrevista*\n\nPara personalizar tu entrevista, dime:\n¿Para qué puesto de trabajo estás aplicando?\n\nEjemplo: Desarrollador Backend, Gerente de Ventas, etc.")

        elif texto in ['2']:
            enviar_mensaje(numero, "📂 Continuar entrevista anterior: aún estamos trabajando en esta función.")

        elif texto in ['3']:
            enviar_mensaje(numero, "💡 Consejo: Investiga la empresa antes de tu entrevista y practica respuestas a preguntas comunes como '¿Por qué deberíamos contratarte?'.")

        elif texto in ['4', 'salir']:
            enviar_mensaje(numero, "👋 Gracias por usar Interview IA. ¡Mucho éxito en tus entrevistas!")

        else:
            # Si ya eligió un puesto, generamos una respuesta IA
            respuesta = obtener_respuesta_ia(f"Estoy aplicando para el puesto de {texto}. Realiza una pregunta de entrevista acorde al rol.")
            enviar_mensaje(numero, respuesta)

    except Exception as e:
        print("❌ Error procesando mensaje:", e)

    return "EVENT_RECEIVED", 200

# =========================================================
if __name__ == "__main__":
    app.run(port=5000, debug=True)

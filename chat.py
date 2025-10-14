from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)



# -------------------------------
# CONFIGURACIÓN
# -------------------------------
VERIFY_TOKEN = "msa1033"
WHATSAPP_TOKEN = "EAAPObyrRpkoBPoVLVDzsozmQdYaDrENwTgbSkLpZCiiCOhlaTJwPP6y4HPeKA60rZCMVN8FzQ8pSZBS55XZBLH9ddcilnzRc4apSnei7XjxmlCrNNHObdQy9YWrbRLKi5Af9egR4GQZAXlmMxwpvy09JjMh2sZA82ChrBkirZAStYhP7zuWWGhENn3NlB213ZA9zs1X1vp3VMbbOpsYhI3GFZCUQLFN6SXmfNUyCaIPw8ZCwZDZD"
WHATSAPP_PHONE_ID = "857442030778486"

OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

WHATSAPP_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"

# Almacenamiento en memoria (en producción usa una base de datos)
usuarios_estado = {}
entrevistas_guardadas = {}

# -------------------------------
# FUNCIONES AUXILIARES
# -------------------------------
def enviar_whatsapp(destino, texto):
    """Envía un mensaje de WhatsApp"""
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
    try:
        response = requests.post(WHATSAPP_URL, headers=headers, json=data)
        print(f"✅ Mensaje enviado a {destino}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando mensaje: {e}")
        return None


def responder_openrouter(mensaje, historial=None):
    """Obtiene respuesta desde OpenRouter (GPT/Claude/Mistral, etc.)"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = []
    if historial:
        for item in historial:
            messages.append({
                "role": item["role"],
                "content": item["content"]
            })

    messages.append({"role": "user", "content": mensaje})

    data = {
        "model": "gpt-4o-mini",  # puedes usar: gpt-4o-mini, mistralai/mixtral-8x7b, etc.
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data)
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print("⚠️ OpenRouter no devolvió respuesta:", result)
            return "Lo siento, no pude generar una respuesta en este momento."
    except Exception as e:
        print(f"❌ Error con OpenRouter API: {e}")
        return "Hubo un error al procesar tu mensaje con la IA."


def inicializar_usuario(telefono):
    usuarios_estado[telefono] = {
        "estado": "menu",
        "pregunta_actual": 0,
        "historial": [],
        "puesto": None,
        "fecha_inicio": datetime.now().isoformat()
    }


def obtener_estado_usuario(telefono):
    if telefono not in usuarios_estado:
        inicializar_usuario(telefono)
    return usuarios_estado[telefono]


def guardar_entrevista(telefono):
    estado = usuarios_estado[telefono]
    entrevistas_guardadas[telefono] = {
        "historial": estado["historial"].copy(),
        "pregunta_actual": estado["pregunta_actual"],
        "puesto": estado["puesto"],
        "fecha": estado["fecha_inicio"]
    }
    return True


def mostrar_menu():
    return (
        "👋 *Bienvenido a Interview IA*\n\n"
        "Un bot que te entrena para mejorar en tus entrevistas de trabajo.\n\n"
        "Por favor elige una opción:\n\n"
        "1️⃣ Empezar simulación de entrevista\n"
        "2️⃣ Continuar entrevista anterior\n"
        "3️⃣ Ver consejos de entrevistas\n"
        "4️⃣ Salir\n\n"
        "_Escribe el número de tu opción_"
    )


def iniciar_entrevista(telefono):
    estado = obtener_estado_usuario(telefono)
    estado["estado"] = "solicitando_puesto"
    estado["pregunta_actual"] = 0
    estado["historial"] = []
    
    return (
        "🎯 *Iniciando Simulación de Entrevista*\n\n"
        "Para personalizar tu entrevista, dime:\n"
        "¿Para qué puesto de trabajo estás aplicando?\n\n"
        "_Ejemplo: Desarrollador Backend, Gerente de Ventas, etc._"
    )


def procesar_puesto(telefono, puesto):
    estado = obtener_estado_usuario(telefono)
    estado["puesto"] = puesto
    estado["estado"] = "entrevista"
    
    sistema = (
        f"Eres un entrevistador profesional de recursos humanos. "
        f"Estás entrevistando a un candidato para el puesto de {puesto}. "
        f"Tu objetivo es hacer preguntas relevantes, evaluar las respuestas y dar feedback constructivo. "
        f"Haz preguntas una a la vez, escucha la respuesta, da un breve comentario, "
        f"y luego continúa con la siguiente pregunta. Sé profesional pero amigable."
    )
    
    estado["historial"].append({"role": "system", "content": sistema})
    
    primera_pregunta = responder_openrouter(
        f"Comienza la entrevista para el puesto de {puesto}. Haz tu primera pregunta de presentación.",
        estado["historial"]
    )
    
    estado["historial"].append({"role": "assistant", "content": primera_pregunta})
    estado["pregunta_actual"] = 1
    
    return f"📋 *Entrevista para: {puesto}*\n\n{primera_pregunta}"


def procesar_respuesta_entrevista(telefono, respuesta):
    estado = obtener_estado_usuario(telefono)
    estado["historial"].append({"role": "user", "content": respuesta})
    
    if estado["pregunta_actual"] < 7:
        prompt = "Analiza la respuesta brevemente (2-3 líneas) y haz la siguiente pregunta."
    else:
        prompt = (
            "La entrevista ha terminado. Proporciona un resumen final:\n"
            "🌟 FORTALEZAS:\n- ...\n\n📈 ÁREAS DE MEJORA:\n- ...\n\n💡 RECOMENDACIÓN FINAL:\n..."
        )
    
    siguiente = responder_openrouter(prompt, estado["historial"])
    estado["historial"].append({"role": "assistant", "content": siguiente})
    estado["pregunta_actual"] += 1
    
    if estado["pregunta_actual"] > 7:
        guardar_entrevista(telefono)
        estado["estado"] = "menu"
        return f"{siguiente}\n\n_Escribe 'menu' para volver al inicio_"
    
    return siguiente


def continuar_entrevista_anterior(telefono):
    if telefono not in entrevistas_guardadas:
        return "❌ No tienes entrevistas guardadas.\n\nEscribe 'menu' para ver las opciones."
    
    entrevista = entrevistas_guardadas[telefono]
    estado = obtener_estado_usuario(telefono)
    estado["historial"] = entrevista["historial"].copy()
    estado["pregunta_actual"] = entrevista["pregunta_actual"]
    estado["puesto"] = entrevista["puesto"]
    estado["estado"] = "entrevista"
    
    return (
        f"📂 *Continuando entrevista*\n"
        f"Puesto: {entrevista['puesto']}\n"
        f"Pregunta actual: {entrevista['pregunta_actual']}/7\n\n"
        f"Por favor, continúa con tu respuesta..."
    )


def mostrar_consejos():
    return (
        "💡 *CONSEJOS PARA ENTREVISTAS*\n\n"
        "✅ *Antes de la entrevista:*\n"
        "• Investiga sobre la empresa\n"
        "• Prepara ejemplos de logros\n"
        "• Practica respuestas comunes\n\n"
        "✅ *Durante la entrevista:*\n"
        "• Usa el método STAR (Situación, Tarea, Acción, Resultado)\n"
        "• Sé específico con ejemplos\n"
        "• Haz preguntas al entrevistador\n\n"
        "✅ *Después de la entrevista:*\n"
        "• Envía un correo de agradecimiento\n"
        "• Reflexiona sobre tu desempeño\n\n"
        "_Escribe 'menu' para volver_"
    )

# -------------------------------
# WEBHOOK
# -------------------------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("✅ Webhook verificado correctamente.")
            return challenge, 200
        else:
            return "Error de verificación", 403

    elif request.method == "POST":
        data = request.get_json()
        print("📩 Mensaje recibido:")
        print(json.dumps(data, indent=2))

        try:
            if "messages" in data["entry"][0]["changes"][0]["value"]:
                mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
                texto_usuario = mensaje.get("text", {}).get("body", "")
                telefono = mensaje["from"]

                estado = obtener_estado_usuario(telefono)
                texto_lower = texto_usuario.lower().strip()

                if texto_lower in ["menu", "hola", "hi", "hello", "buenas", "inicio"]:
                    estado["estado"] = "menu"
                    enviar_whatsapp(telefono, mostrar_menu())
                
                elif estado["estado"] == "menu":
                    if texto_lower == "1":
                        enviar_whatsapp(telefono, iniciar_entrevista(telefono))
                    elif texto_lower == "2":
                        enviar_whatsapp(telefono, continuar_entrevista_anterior(telefono))
                    elif texto_lower == "3":
                        enviar_whatsapp(telefono, mostrar_consejos())
                    elif texto_lower == "4":
                        enviar_whatsapp(telefono, "👋 ¡Gracias por usar Interview IA! Escribe 'menu' cuando quieras volver.")
                    else:
                        enviar_whatsapp(telefono, "❌ Opción no válida. Por favor elige 1, 2, 3 o 4.")
                
                elif estado["estado"] == "solicitando_puesto":
                    enviar_whatsapp(telefono, procesar_puesto(telefono, texto_usuario))
                
                elif estado["estado"] == "entrevista":
                    enviar_whatsapp(telefono, procesar_respuesta_entrevista(telefono, texto_usuario))
                
                else:
                    enviar_whatsapp(telefono, mostrar_menu())
                    
        except Exception as e:
            print(f"⚠️ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()

        return "EVENT_RECEIVED", 200


@app.route("/", methods=["GET"])
def home():
    return "🤖 Interview IA Bot (OpenRouter) está activo!", 200


# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

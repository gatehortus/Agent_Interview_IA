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
WHATSAPP_TOKEN = "EAAPObyrRpkoBPoeAJonmsFiTsKBTMbZAq673uXIhvrSefoUHlgiZAjKfNvIbDvpRjDrfDnVSqA1Iqxx4TIOM9Sw2Q0ZATLYDWvdrKQGTaqbnVASyuTa69u0CHpEI70c5FUAktffmW19VqirLjTXo0f9iQycb3rsZCtyhqZCJMfXQYscsvoP401Nl5k8PYx3DEeuoZBl53ydY5pgG0N7Y8FdZCMfvbLKcteDHaZB9TKUdZCTMZD"
WHATSAPP_PHONE_ID = "857442030778486"
GEMINI_API_KEY = "AIzaSyAMOIkpb2QhOYYF2CfiwVPIJE_h8ouH8nI"  

WHATSAPP_URL = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"

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


def responder_gemini(mensaje, historial=None):
    """Obtiene respuesta de Gemini API"""
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construir el historial de conversación
    contents = []
    if historial:
        for item in historial:
            contents.append({
                "role": item["role"],
                "parts": [{"text": item["content"]}]
            })
    
    # Agregar el mensaje actual
    contents.append({
        "role": "user",
        "parts": [{"text": mensaje}]
    })
    
    data = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }
    
    try:
        response = requests.post(GEMINI_URL, headers=headers, json=data)
        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"❌ Error con Gemini API: {e}")
        return "Lo siento, hubo un error al procesar tu respuesta. Por favor intenta nuevamente."


def inicializar_usuario(telefono):
    """Inicializa el estado de un usuario nuevo"""
    usuarios_estado[telefono] = {
        "estado": "menu",  # menu, entrevista, continuando
        "pregunta_actual": 0,
        "historial": [],
        "puesto": None,
        "fecha_inicio": datetime.now().isoformat()
    }


def obtener_estado_usuario(telefono):
    """Obtiene el estado actual del usuario"""
    if telefono not in usuarios_estado:
        inicializar_usuario(telefono)
    return usuarios_estado[telefono]


def guardar_entrevista(telefono):
    """Guarda la entrevista actual para continuarla después"""
    estado = usuarios_estado[telefono]
    entrevistas_guardadas[telefono] = {
        "historial": estado["historial"].copy(),
        "pregunta_actual": estado["pregunta_actual"],
        "puesto": estado["puesto"],
        "fecha": estado["fecha_inicio"]
    }
    return True


def mostrar_menu():
    """Muestra el menú principal"""
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
    """Inicia una nueva entrevista"""
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
    """Procesa el puesto y comienza la entrevista"""
    estado = obtener_estado_usuario(telefono)
    estado["puesto"] = puesto
    estado["estado"] = "entrevista"
    
    # Crear contexto inicial para Gemini
    sistema = (
        f"Eres un entrevistador profesional de recursos humanos. "
        f"Estás entrevistando a un candidato para el puesto de {puesto}. "
        f"Tu objetivo es hacer preguntas relevantes, evaluar las respuestas y dar feedback constructivo. "
        f"Haz preguntas una a la vez, escucha la respuesta, da un breve comentario sobre la respuesta, "
        f"y luego continúa con la siguiente pregunta. Sé profesional pero amigable. "
        f"La entrevista debe tener entre 5-7 preguntas. "
        f"Cuando hayas hecho todas las preguntas, proporciona un resumen final con fortalezas y áreas de mejora."
    )
    
    estado["historial"].append({
        "role": "user",
        "content": sistema
    })
    
    # Primera pregunta
    primera_pregunta = responder_gemini(
        f"Comienza la entrevista para el puesto de {puesto}. Haz tu primera pregunta de presentación.",
        estado["historial"]
    )
    
    estado["historial"].append({
        "role": "model",
        "content": primera_pregunta
    })
    
    estado["pregunta_actual"] = 1
    
    return f"📋 *Entrevista para: {puesto}*\n\n{primera_pregunta}"


def procesar_respuesta_entrevista(telefono, respuesta):
    """Procesa una respuesta durante la entrevista"""
    estado = obtener_estado_usuario(telefono)
    
    # Agregar respuesta al historial
    estado["historial"].append({
        "role": "user",
        "content": respuesta
    })
    
    # Obtener siguiente pregunta o feedback
    if estado["pregunta_actual"] < 7:
        prompt = "Analiza la respuesta brevemente (2-3 líneas) y haz la siguiente pregunta de la entrevista."
    else:
        prompt = (
            "La entrevista ha terminado. Proporciona un resumen final en este formato:\n\n"
            "🌟 FORTALEZAS:\n- (lista las fortalezas)\n\n"
            "📈 ÁREAS DE MEJORA:\n- (lista áreas de mejora)\n\n"
            "💡 RECOMENDACIÓN FINAL:\n(tu recomendación)"
        )
    
    siguiente = responder_gemini(prompt, estado["historial"])
    
    estado["historial"].append({
        "role": "model",
        "content": siguiente
    })
    
    estado["pregunta_actual"] += 1
    
    # Si terminó la entrevista
    if estado["pregunta_actual"] > 7:
        guardar_entrevista(telefono)
        estado["estado"] = "menu"
        return f"{siguiente}\n\n_Escribe 'menu' para volver al inicio_"
    
    return siguiente


def continuar_entrevista_anterior(telefono):
    """Continúa una entrevista guardada"""
    if telefono not in entrevistas_guardadas:
        return "❌ No tienes entrevistas guardadas.\n\nEscribe 'menu' para ver las opciones."
    
    # Restaurar estado
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
    """Muestra consejos para entrevistas"""
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
        print(json.dumps(data, indent=2))

        try:
            if "messages" in data["entry"][0]["changes"][0]["value"]:
                mensaje = data["entry"][0]["changes"][0]["value"]["messages"][0]
                texto_usuario = mensaje.get("text", {}).get("body", "")
                telefono = mensaje["from"]

                # Obtener estado del usuario
                estado = obtener_estado_usuario(telefono)
                texto_lower = texto_usuario.lower().strip()

                # Comandos globales
                if texto_lower in ["menu", "hola", "hi", "hello", "buenas", "inicio"]:
                    estado["estado"] = "menu"
                    enviar_whatsapp(telefono, mostrar_menu())
                
                # En menú
                elif estado["estado"] == "menu":
                    if texto_lower == "1":
                        respuesta = iniciar_entrevista(telefono)
                        enviar_whatsapp(telefono, respuesta)
                    elif texto_lower == "2":
                        respuesta = continuar_entrevista_anterior(telefono)
                        enviar_whatsapp(telefono, respuesta)
                    elif texto_lower == "3":
                        enviar_whatsapp(telefono, mostrar_consejos())
                    elif texto_lower == "4":
                        estado["estado"] = "menu"
                        enviar_whatsapp(telefono, "👋 ¡Gracias por usar Interview IA! Escribe 'menu' cuando quieras volver.")
                    else:
                        enviar_whatsapp(telefono, "❌ Opción no válida. Por favor elige 1, 2, 3 o 4.")
                
                # Solicitando puesto
                elif estado["estado"] == "solicitando_puesto":
                    respuesta = procesar_puesto(telefono, texto_usuario)
                    enviar_whatsapp(telefono, respuesta)
                
                # En entrevista
                elif estado["estado"] == "entrevista":
                    respuesta = procesar_respuesta_entrevista(telefono, texto_usuario)
                    enviar_whatsapp(telefono, respuesta)
                
                # Estado desconocido
                else:
                    enviar_whatsapp(telefono, mostrar_menu())
                    
        except Exception as e:
            print(f"⚠️ Error procesando mensaje: {e}")
            import traceback
            traceback.print_exc()

        return "EVENT_RECEIVED", 200


@app.route("/", methods=["GET"])
def home():
    return "🤖 Interview IA Bot está activo!", 200


# -------------------------------
# EJECUCIÓN
# -------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

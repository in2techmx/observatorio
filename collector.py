import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # El cliente busca GEMINI_API_KEY en los Secrets de GitHub automáticamente
    client = genai.Client()

    # Lista total: Desde versiones futuras hasta las Pro actuales
    modelos_a_probar = [
        "gemini-2.5-flash",       # La versión que solicitaste (Futura/Experimental)
        "gemini-2.0-flash",       # Vanguardia 2026
        "gemini-2.0-flash-exp",   # Experimental 2.0
        "gemini-1.5-pro",         # Estándar Pro (Tu cuenta)
        "gemini-1.5-pro-002",     # Producción Estable
        "gemini-1.5-flash"        # Respaldo rápido
    ]

    prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto: {"tematica": "...", "descripcion": "...", "regiones_activas": [], "perspectivas": {}}"""
    
    analisis = []
    modelo_ganador = None

    print("--- INICIANDO ESCÁNER DE MODELOS (Incluyendo 2.5) ---")

    for modelo in modelos_a_probar:
        try:
            print(f"Probando enlace con: {modelo}...")
            response = client.models.generate_content(
                model=modelo,
                contents=prompt
            )
            
            # Si responde, extraemos el texto
            raw_text = response.text.strip()
            
            # Limpiador de Markdown por si la IA se pone creativa
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            # Buscamos el JSON real dentro de la respuesta
            inicio = raw_text.find("[")
            fin = raw_text.rfind("]") + 1
            if inicio != -1:
                analisis = json.loads(raw_text[inicio:fin])
                modelo_ganador = modelo
                print(f"✅ ¡CONEXIÓN EXITOSA! El modelo activo es: {modelo_ganador}")
                break 

        except Exception as e:
            # Mostramos el error para saber por qué falló cada uno (ej. 404)
            print(f"❌ {modelo} no disponible: {str(e)[:60]}")

    if not modelo_ganador:
        print("🔴 ERROR: Ningún modelo respondió. Revisa la API KEY.")
        analisis = [{"tematica": "Error de Conexión", "descripcion": "No se pudo enlazar con la IA."}]

    # Guardado de archivos
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    # 1. Archivo para la web (Raíz)
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 2. Archivo para el histórico
    with open(os.path.join(historico_dir, f"analisis_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 3. Índice para el timeline
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files[:50], f, indent=4)

    print(f"--- PROCESO FINALIZADO (Ganador: {modelo_ganador}) ---")

if __name__ == "__main__":
    collect()

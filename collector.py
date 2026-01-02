import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # Inicializa el cliente (detecta GEMINI_API_KEY en el entorno)
    client = genai.Client()

    # Modelos a probar (priorizando el que te funcionó)
    modelos_a_probar = [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro"
    ]

    # Prompt optimizado para evitar texto plano
    prompt = """Genera un informe geopolítico mundial de hoy 2026. 
    Responde ÚNICAMENTE con un array JSON. Sin introducciones.
    Formato: [{"tematica": "...", "descripcion": "...", "regiones_activas": [], "perspectivas": {}}]"""

    analisis = []
    modelo_ganador = None

    print("--- INICIANDO COLECCIÓN ---")

    for modelo in modelos_a_probar:
        try:
            print(f"Probando: {modelo}...")
            # Forzamos formato JSON en la configuración
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            raw_text = response.text.strip()
            
            # Limpiador de seguridad para extraer el JSON
            inicio = raw_text.find("[")
            fin = raw_text.rfind("]") + 1
            
            if inicio != -1:
                analisis = json.loads(raw_text[inicio:fin])
                modelo_ganador = modelo
                print(f"✅ ÉXITO con {modelo_ganador}")
                break 

        except Exception as e:
            print(f"❌ Error en {modelo}: {str(e)[:50]}")

    if not modelo_ganador:
        analisis = [{"tematica": "Error", "descripcion": "No se pudo obtener JSON"}]

    # --- GUARDADO DE ARCHIVOS ---
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    # 1. Para la web
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 2. Para el histórico
    with open(os.path.join(historico_dir, f"analisis_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 3. Timeline
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files[:50], f, indent=4)

    print(f"--- PROCESO COMPLETADO ---")

if __name__ == "__main__":
    collect()

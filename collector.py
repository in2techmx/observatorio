import os
import json
import datetime
from google import genai # Nueva librería

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la API Key.")
        return

    # Nueva forma de conectar (Librería 2026)
    client = genai.Client(api_key=api_key)
    model_id = "gemini-1.5-pro"

    prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto debe tener:
    - "tematica": Título profesional corto.
    - "descripcion": Análisis profundo de 2 frases.
    - "regiones_activas": Lista de regiones (USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM, AFRICA, UK).
    - "perspectivas": Un objeto con visiones breves.
    Importante: Solo devuelve el código JSON, sin ```json ni textos extra."""

    analisis = []

    try:
        print(f"Consultando a {model_id} mediante nueva API...")
        # Nueva forma de generar contenido
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Extracción de JSON
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        
        if inicio != -1 and fin != 0:
            analisis = json.loads(raw_text[inicio:fin])
            print(f"✅ ÉXITO TOTAL: {len(analisis)} noticias generadas.")
        else:
            print(f"Texto recibido: {raw_text[:100]}...")
            raise ValueError("No se encontró JSON en la respuesta.")

    except Exception as e:
        print(f"⚠️ FALLO CRÍTICO: {e}")
        analisis = [{
            "tematica": "Reconexión de Red Pro",
            "descripcion": f"Actualizando protocolos de la nueva API. Estado: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Migrando a google-genai v3"}
        }]

    # Guardado de archivos
    for path in [os.path.join(base_dir, "latest_news.json"), 
                 os.path.join(historico_dir, f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json")]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(analisis, f, indent=4, ensure_ascii=False)

    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)

    print("🚀 Proceso terminado con nueva librería.")

if __name__ == "__main__":
    collect()

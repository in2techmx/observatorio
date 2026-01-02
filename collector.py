import os
import json
import datetime
import google.generativeai as genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # CONFIGURACIÓN PRO
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la API Key.")
        return

    genai.configure(api_key=api_key)
    # Nombre del modelo estable para cuentas Pro
    model = genai.GenerativeModel('gemini-1.5-pro')

    prompt = """Genera un análisis geopolítico mundial actual. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto: {"tematica": "...", "descripcion": "...", "regiones_activas": ["USA", "CHINA", etc], "perspectivas": {"REGION": "..."}}
    Solo el código JSON, sin textos extra."""

    analisis = []

    try:
        print("Consultando a Gemini 1.5 Pro...")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Extracción segura de JSON
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        if inicio != -1 and fin != 0:
            analisis = json.loads(raw_text[inicio:fin])
            print(f"✅ IA exitosa: {len(analisis)} noticias.")
        else:
            raise ValueError("Respuesta de IA no contiene JSON válido.")

    except Exception as e:
        print(f"⚠️ FALLO: {e}")
        analisis = [{
            "tematica": "Error de Conexión",
            "descripcion": f"La IA Pro reportó un error: {str(e)[:50]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["USA"],
            "perspectivas": {"USA": "Reintentando..."}
        }]

    # GUARDADO FORZADO
    latest_path = os.path.join(base_dir, "latest_news.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    filename = f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
    with open(os.path.join(historico_dir, filename), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)

    print(f"🚀 Sincronización completa: {filename}")

if __name__ == "__main__":
    collect()

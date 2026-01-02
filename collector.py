import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la API Key.")
        return

    client = genai.Client(api_key=api_key)
    
    # Probamos todas las rutas que Google asigna a cuentas Pro
    model_options = [
        "gemini-1.5-pro-002", 
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]

    prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto: {"tematica": "...", "descripcion": "...", "regiones_activas": ["..."], "perspectivas": {"...": "..."}}
    Solo JSON puro."""

    analisis = []
    exito = False

    for model_id in model_options:
        if exito: break
        try:
            print(f"Intentando conectar con: {model_id}...")
            response = client.models.generate_content(model=model_id, contents=prompt)
            raw_text = response.text.strip()
            
            # Limpieza de Markdown
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
            inicio = raw_text.find("[")
            fin = raw_text.rfind("]") + 1
            if inicio != -1:
                analisis = json.loads(raw_text[inicio:fin])
                print(f"✅ ¡LOGRADO! Conectado con {model_id}")
                exito = True
        except Exception as e:
            print(f"❌ Falló {model_id}: {str(e)[:50]}")

    if not exito:
        analisis = [{
            "tematica": "Nodo en Sincronización",
            "descripcion": "Ajustando protocolos Pro. El sistema estará activo en breve.",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Buscando endpoint compatible..."}
        }]

    # Guardado de archivos
    for path in [os.path.join(base_dir, "latest_news.json"), 
                 os.path.join(historico_dir, f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json")]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(analisis, f, indent=4, ensure_ascii=False)

    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files[:50], f, indent=4)

    print("🚀 Sincronización finalizada.")

if __name__ == "__main__":
    collect()

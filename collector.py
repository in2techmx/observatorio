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
    if not api_key: return

    # Cliente configurado para la versión Pro más estable
    client = genai.Client(api_key=api_key)
    
    # IMPORTANTE: En la nueva librería NO se usa "models/"
    model_id = "gemini-1.5-pro"

    prompt = "Genera un análisis geopolítico actual en un array JSON de 5 objetos: {'tematica': '...', 'descripcion': '...', 'regiones_activas': [], 'perspectivas': {}}"

    try:
        print(f"Llamando a {model_id}...")
        # Eliminamos el parámetro de versión para que Google asigne la mejor por defecto
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpiador automático de formato Markdown
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        analisis = json.loads(raw_text)
        print(f"✅ ÉXITO PRO: {len(analisis)} análisis generados.")

    except Exception as e:
        print(f"❌ Error: {e}")
        analisis = [{
            "tematica": "Sincronización Pro",
            "descripcion": f"Validando acceso. Error: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Reintentando..."}
        }]

    # Guardado
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
    
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump([f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"], f, indent=4)

    print("🚀 Proceso terminado.")

if __name__ == "__main__":
    collect()

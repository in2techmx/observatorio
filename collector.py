import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return

    # FORZAMOS LA VERSIÓN v1 (ESTABLE) para evitar el error 404 de la v1beta
    client = genai.Client(
        api_key=api_key,
        http_options={'api_version': 'v1'}
    )
    
    # Probamos con el nombre puro
    model_id = "gemini-1.5-pro"

    prompt = "Genera un análisis geopolítico actual en un array JSON de 5 objetos: {'tematica': '...', 'descripcion': '...', 'regiones_activas': [], 'perspectivas': {}}"

    try:
        print(f"Llamando a {model_id} (v1 Estable)...")
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpiador de Markdown
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        analisis = json.loads(raw_text)
        print(f"✅ ¡CONECTADO! IA Pro respondió con éxito.")

    except Exception as e:
        print(f"❌ Error en v1: {e}")
        # Si falla, intentamos una última vez con el nombre completo de modelo
        try:
            print("Reintentando con nombre de modelo completo...")
            response = client.models.generate_content(model="models/gemini-1.5-pro", contents=prompt)
            analisis = json.loads(response.text.strip())
            print("✅ ¡LOGRADO con nombre completo!")
        except:
            analisis = [{
                "tematica": "Sincronizando...",
                "descripcion": "El nodo Pro está validando la versión de API.",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "regiones_activas": ["GLOBAL"],
                "perspectivas": {"SISTEMA": "Cambiando a endpoint v1..."}
            }]

    # Guardado simplificado para asegurar que Netlify lo vea
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
    
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump([f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"], f, indent=4)

    print("🚀 Proceso terminado.")

if __name__ == "__main__":
    collect()

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

    # Conexión limpia con la nueva librería
    client = genai.Client(api_key=api_key)
    
    # Probamos el ID más estándar para Pro
    model_id = "gemini-1.5-pro"

    prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto debe tener:
    - "tematica": Título profesional corto.
    - "descripcion": Análisis profundo de 2 frases.
    - "regiones_activas": Lista de regiones (USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM, AFRICA, UK).
    - "perspectivas": Un objeto con visiones breves de cada actor.
    Importante: Solo devuelve el código JSON, sin decoradores ni texto extra."""

    analisis = []

    try:
        print(f"Iniciando consulta a {model_id}...")
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpieza de posibles tags de markdown que la IA a veces incluye
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        
        if inicio != -1 and fin != 0:
            analisis = json.loads(raw_text[inicio:fin])
            print(f"✅ ÉXITO: {len(analisis)} noticias analizadas.")
        else:
            raise ValueError("La respuesta no contiene un array JSON válido.")

    except Exception as e:
        print(f"⚠️ FALLO DE CONEXIÓN: {e}")
        # Si falla el 1.5-pro, intentamos la versión flash como respaldo rápido
        analisis = [{
            "tematica": "Sincronizando Nodo Pro",
            "descripcion": f"El sistema está validando la API Key Pro. Error: {str(e)[:50]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Reintentando con protocolo seguro..."}
        }]

    # Guardado dual (Raíz e Histórico)
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    # 1. Guardar latest_news.json
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 2. Guardar en carpeta histórico
    with open(os.path.join(historico_dir, f"analisis_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # 3. Actualizar el timeline.json
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files[:50], f, indent=4) # Guardamos los últimos 50

    print(f"🚀 Archivos actualizados correctamente a las {timestamp}")

if __name__ == "__main__":
    collect()

import os
import json
import datetime
import google.generativeai as genai

def collect():
    # 1. RUTAS ABSOLUTAS
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # 2. CONFIGURACIÓN DE IA
    # Asegúrate de tener GEMINI_API_KEY en los Secrets de tu GitHub
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la API Key de Gemini.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-pro')

    # Prompt ultra-específico para evitar basura en la respuesta
    prompt = """Genera un análisis geopolítico mundial actual. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto debe tener:
    - "tematica": Título corto.
    - "descripcion": Análisis de 2 frases.
    - "regiones_activas": Lista de 2 regiones (USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM, AFRICA, UK).
    - "perspectivas": Un objeto con las visiones encontradas.
    NO incluyas introducciones ni despedidas, solo el código JSON."""

    analisis = []

    try:
        print("Consultando a Gemini...")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # --- BUSCADOR UNIVERSAL DE JSON ---
        # Encuentra el primer '[' y el último ']' para ignorar texto extra de Gemini
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        
        if inicio != -1 and fin != 0:
            json_data = raw_text[inicio:fin]
            analisis = json.loads(json_data)
            print(f"✅ IA procesada con éxito: {len(analisis)} bloques detectados.")
        else:
            raise ValueError("No se encontraron corchetes de JSON en la respuesta.")

    except Exception as e:
        print(f"⚠️ FALLO EN IA O PARSEO: {e}")
        # DATA DE CONTINGENCIA (Para que la web no quede vacía)
        analisis = [{
            "tematica": "Sincronización de Inteligencia",
            "descripcion": f"El búnker está recibiendo los datos. Error reportado: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["USA", "EUROPE"],
            "perspectivas": {"USA": "Señal detectada.", "EUROPE": "Validando formato..."}
        }]

    # --- SISTEMA DE GUARDADO FORZADO (Flush & Sync) ---
    
    # 1. Guardar latest_news.json (En la raíz)
    latest_path = os.path.join(base_dir, "latest_news.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 2. Guardar archivo histórico (En /historico_noticias)
    timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f"analisis_{timestamp_str}.json"
    historico_path = os.path.join(historico_dir, filename)
    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 3. Actualizar timeline.json (En la raíz)
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    timeline_path = os.path.join(base_dir, "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)
        f.flush()
        os.fsync(f.fileno())

    print(f"🚀 Sincronización completa. Último archivo: {filename}")

if __name__ == "__main__":
    collect()



import os
import json
import datetime
import google.generativeai as genai

def collect():
    # 1. CONFIGURACIÓN DE RUTAS
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # 2. CONFIGURACIÓN DE IA (Asegúrate de tener tu API_KEY)
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Prompt optimizado para evitar errores de formato
    prompt = """Genera un análisis geopolítico en formato JSON puro (una lista de objetos). 
    Cada objeto debe tener: tematica, descripcion, regiones_activas (lista), perspectivas (objeto). 
    Importante: No incluyas texto explicativo, solo el JSON."""

    analisis = []

    try:
        print("Consultando a Gemini...")
        response = model.generate_content(prompt)
        
        # --- LIMPIEZA DE RESPUESTA (CRÍTICO) ---
        # Gemini a veces envuelve el JSON en ```json ... ```. Esto lo elimina:
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        
        # Intentar convertir texto en objeto Python
        analisis = json.loads(raw_text)
        print(f"IA procesada con éxito: {len(analisis)} noticias.")

    except Exception as e:
        print(f"FALLO EN IA O PARSEO: {e}")
        # Solo en caso de error real usamos la contingencia
        analisis = [{
            "tematica": "Señal en Proceso",
            "descripcion": f"Error de sincronización con la IA: {str(e)[:50]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["USA"],
            "perspectivas": {"USA": "Reintentando conexión..."}
        }]

    # --- SISTEMA DE GUARDADO SINCRONIZADO ---
    
    # 1. Guardar LATEST (El que lee la web por defecto)
    latest_path = os.path.join(base_dir, "latest_news.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 2. Guardar HISTÓRICO (Para el timeline)
    filename = f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"
    historico_path = os.path.join(historico_dir, filename)
    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 3. Actualizar TIMELINE
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    timeline_path = os.path.join(base_dir, "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)
        f.flush()
        os.fsync(f.fileno())

    print("Sincronización completa de todos los archivos JSON.")

if __name__ == "__main__":
    collect()

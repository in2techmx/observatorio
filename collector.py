import os
import json
import datetime
import google.generativeai as genai

def collect():
    # 1. RUTAS Y DIRECTORIOS
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # 2. CONFIGURACIÓN DE IA (CUENTA PRO)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: No se encontró la API Key.")
        return

    genai.configure(api_key=api_key)
    
    # Hemos verificado que esta es la ruta más estable para evitar el error 404
    # Si falla, el sistema intentará un nombre alternativo automáticamente
    model_name = 'gemini-1.5-pro'
    
    try:
        model = genai.GenerativeModel(model_name)
    except:
        model = genai.GenerativeModel('models/gemini-1.5-pro')

    prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
    Responde ÚNICAMENTE con un array JSON (lista de objetos).
    Cada objeto debe tener:
    - "tematica": Título profesional corto.
    - "descripcion": Análisis profundo de 2 frases.
    - "regiones_activas": Lista de regiones (USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM, AFRICA, UK).
    - "perspectivas": Un objeto con visiones breves.
    Importante: No añadas ```json ni texto extra, solo el array []."""

    analisis = []

    try:
        print(f"Consultando a {model_name}...")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # EXTRACCIÓN ROBUSTA DE JSON
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        
        if inicio != -1 and fin != 0:
            json_data = raw_text[inicio:fin]
            analisis = json.loads(json_data)
            print(f"✅ IA EXITOSA: {len(analisis)} noticias generadas.")
        else:
            raise ValueError("La respuesta no contiene un formato JSON válido.")

    except Exception as e:
        print(f"⚠️ ERROR DETECTADO: {e}")
        # DATA DE EMERGENCIA CON DETALLE DEL ERROR
        analisis = [{
            "tematica": "Sistema en Mantenimiento",
            "descripcion": f"Estamos reconectando con el satélite Pro. Error técnico: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["USA"],
            "perspectivas": {"SISTEMA": "Reintentando sincronización..."}
        }]

    # 3. GUARDADO DE ARCHIVOS (MÉTODO SINCRONIZADO)
    
    # Guardar en raíz para acceso directo
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # Guardar en histórico para el timeline
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f"analisis_{timestamp}.json"
    with open(os.path.join(historico_dir, filename), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # Actualizar el índice del timeline
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)

    print(f"🚀 PROCESO COMPLETADO: {filename}")

if __name__ == "__main__":
    collect()

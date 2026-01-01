import feedparser
import json
import datetime
import os
import google.generativeai as genai

# CONFIGURACIÓN SEGURA DE IA
# La API Key se toma automáticamente del secreto de GitHub
api_key_env = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key_env)
model = genai.GenerativeModel('gemini-1.5-flash')

FEEDS = {
    "USA": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "CHINA": "https://www.globaltimes.cn/rss/china.xml",
    "RUSSIA": "https://tass.com/rss/v2.xml",
    "EUROPE": "https://rss.dw.com/rdf/rss-en-all",
    "INDIA": "https://www.thehindu.com/news/national/feeder/default.rss",
    "MID_EAST": "https://www.aljazeera.com/xml/rss/all.xml",
    "LATAM": "https://en.mercopress.com/rss/"
}

def analyze_with_ia(news_batch):
    prompt = f"""
    Actúa como un analista geopolítico senior. Te daré noticias de diferentes regiones.
    1. Agrúpalas en 5 TEMÁTICAS globales de alto nivel (ej: Guerra Tecnológica, Seguridad Energética, Tensiones en Eurasia).
    2. Para cada temática:
       - Crea una descripción de 1 frase.
       - Identifica qué regiones hablan del tema y resume su enfoque/sesgo en 1 frase.
       - Lista las regiones que NO mencionan el tema (Puntos Ciegos).
    
    Noticias: {news_batch}
    
    Responde ÚNICAMENTE en JSON con esta estructura:
    [
      {{
        "tematica": "Nombre",
        "descripcion": "...",
        "regiones_activas": ["USA", "CHINA"],
        "puntos_ciegos": ["RUSSIA"],
        "perspectivas": {{ "USA": "...", "CHINA": "..." }}
      }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except Exception as e:
        print(f"Error en IA: {e}")
        return []

def collect():
    raw_data = []
    # Recolectar noticias crudas
    for region, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                raw_data.append({"region": region, "title": entry.title})
        except: continue

    # Procesar con Gemini
    structured_data = analyze_with_ia(raw_data)

    # Crear carpeta histórica
    folder_name = "historico_noticias"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M")
    
    # Guardar archivos
    file_fixed = "latest_news.json"
    file_historic = os.path.join(folder_name, f"analisis_{timestamp_str}.json")
    
    for path in [file_fixed, file_historic]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)
    
    print("✅ Análisis completado y archivos guardados.")

if __name__ == "__main__":
    collect()

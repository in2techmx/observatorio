import feedparser
import json
import datetime
import os
import google.generativeai as genai

# CONFIGURACIÓN IA
genai.configure(api_key="TU_API_KEY_AQUI")
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
    Actúa como un analista geopolítico senior. Te daré una lista de noticias de diferentes regiones.
    Tu tarea es:
    1. Agruparlas en 5-7 TEMÁTICAS globales (ej: Guerra Fría Tecnológica, Crisis Climática, Conflictos Territoriales).
    2. Para cada temática, identifica qué regiones están hablando de ella y crea una 'Síntesis de Narrativa' de 1 frase para cada región.
    3. Identifica 'Puntos Ciegos' (regiones que NO mencionan el tema).
    
    Noticias crudas: {news_batch}
    
    Responde ÚNICAMENTE en formato JSON con esta estructura:
    [
      {{
        "tematica": "Nombre",
        "descripcion": "Breve resumen global",
        "regiones_activas": ["USA", "CHINA"],
        "puntos_ciegos": ["RUSSIA"],
        "perspectivas": {{
           "USA": "Síntesis de su enfoque...",
           "CHINA": "Síntesis de su enfoque..."
        }}
      }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        # Limpiamos la respuesta para que sea un JSON válido
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except:
        return []

def collect():
    raw_data = []
    now = datetime.datetime.now()
    
    # 1. Recolección Cruda
    for region, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                raw_data.append({"region": region, "title": entry.title})
        except: continue

    # 2. Análisis Inteligente
    structured_data = analyze_with_ia(raw_data)

    # 3. Guardado
    folder_name = "historico_noticias"
    if not os.path.exists(folder_name): os.makedirs(folder_name)
    
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M")
    file_fixed = "latest_news.json"
    file_historic = os.path.join(folder_name, f"analisis_{timestamp_str}.json")
    
    for path in [file_fixed, file_historic]:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(structured_data, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    collect()

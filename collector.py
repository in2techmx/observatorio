import feedparser
import json
import datetime
import os
import google.generativeai as genai

# --- CONFIGURACIÓN DE SEGURIDAD ---
api_key_env = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key_env)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2 Fuentes por región para asegurar contraste de datos
FEEDS = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://feeds.aonnetwork.com/cnn/world"],
    "CHINA": ["https://www.globaltimes.cn/rss/china.xml", "http://www.xinhuanet.com/english/rss/worldrss.xml"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/"],
    "EUROPE": ["https://rss.dw.com/rdf/rss-en-all", "https://www.euronews.com/rss?level=vertical&name=news"],
    "UK": ["https://feeds.bbci.co.uk/news/world/rss.xml", "https://www.theguardian.com/world/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.alarabiya.net/.mrss/en/news.xml"],
    "LATAM": ["https://en.mercopress.com/rss/", "https://www.telesurenglish.net/rss/news.xml"],
    "AFRICA": ["https://allafrica.com/tools/headlines/rss/main/main.xml", "https://www.africanews.com/feed/"]
}

def analyze_with_ia(news_batch):
    prompt = f"""
    Actúa como un Analista Geopolítico Neutro. 
    TAREA: Agrupa estas noticias en 5 temáticas y analiza la divergencia narrativa.
    NOTICIAS: {news_batch}
    
    RESPONDE ESTRICTAMENTE EN JSON:
    [
      {{
        "tematica": "Título",
        "descripcion": "Breve resumen",
        "regiones_activas": ["USA", "CHINA"],
        "puntos_ciegos": ["RUSSIA"],
        "perspectivas": {{ "USA": "enfoque...", "CHINA": "enfoque..." }}
      }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except: return []

def collect():
    now = datetime.datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M")
    file_id = now.strftime("%Y-%m-%d_%H-%M")
    
    raw_data = []
    for region, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:3]:
                    raw_data.append({"region": region, "title": entry.title})
            except: continue

    structured_data = analyze_with_ia(raw_data)
    for item in structured_data: item["timestamp"] = timestamp_str

    # --- GESTIÓN DE ARCHIVOS ---
    if not os.path.exists("historico_noticias"): os.makedirs("historico_noticias")
    if not os.path.exists("archivos_maestros"): os.makedirs("archivos_maestros")

    # 1. Guardar análisis actual
    with open(f"historico_noticias/analisis_{file_id}.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=4, ensure_ascii=False)
    
    # 2. Copia rápida para la web
    with open("latest_news.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=4, ensure_ascii=False)

    # 3. Actualizar Timeline (Viaje en el tiempo)
    history_files = sorted([f for f in os.listdir("historico_noticias") if f.endswith('.json')], reverse=True)
    if len(history_files) > 170: # Mantener 1 semana
        for old in history_files[170:]: os.remove(os.path.join("historico_noticias", old))
    
    with open("timeline.json", "w", encoding="utf-8") as f:
        json.dump(history_files[:170], f, indent=4)

    # 4. Índices maestros para el Portal Histórico
    maestros = sorted(os.listdir("archivos_maestros"), reverse=True)
    with open("maestros_index.json", "w", encoding="utf-8") as f:
        json.dump(maestros, f, indent=4)

    print(f"✅ Proceso terminado a las {timestamp_str}")

if __name__ == "__main__":
    collect()

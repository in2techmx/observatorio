import feedparser
import json
import datetime
import os
import google.generativeai as genai

# CONFIGURACIÓN SEGURA: Obtiene la API Key desde los secretos de GitHub
api_key_env = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key_env)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2 Fuentes por región para detectar divergencias internas y vacíos informativos
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
    Actúa como un analista geopolítico senior para el 'Global News Proximity Observatory'. 
    Analiza las siguientes noticias para determinar la 'Proximidad Narrativa'.
    
    TAREAS:
    1. Agrupa las noticias en las 5 TEMÁTICAS globales más relevantes de la hora.
    2. Para cada temática:
       - Define un título y descripción breve (1 frase).
       - Identifica qué regiones están cubriendo el tema y sintetiza su enfoque o sesgo particular en 1 frase.
       - Identifica 'Puntos Ciegos': regiones que no mencionan el tema en absoluto.
    
    DATOS CRUDOS: {news_batch}
    
    Responde ESTRICTAMENTE en formato JSON con esta estructura:
    [
      {{
        "tematica": "Nombre de la Temática",
        "descripcion": "Descripción breve",
        "regiones_activas": ["USA", "CHINA", "EUROPE"],
        "puntos_ciegos": ["RUSSIA", "LATAM"],
        "perspectivas": {{
           "USA": "Enfoque en...",
           "CHINA": "Enfoque en..."
        }}
      }}
    ]
    """
    try:
        response = model.generate_content(prompt)
        # Limpieza de formato Markdown en la respuesta
        json_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(json_text)
    except Exception as e:
        print(f"Error procesando con IA: {e}")
        return []

def collect():
    raw_data = []
    print("Iniciando recolección de noticias...")
    
    # Recolectar noticias de ambas fuentes por región
    for region, urls in FEEDS.items():
        for url in urls:
            try:
                feed = feedparser.parse(url)
                # Tomamos los primeros 4 titulares de cada fuente para un batch rico
                for entry in feed.entries[:4]:
                    raw_data.append({"region": region, "title": entry.title})
            except Exception as e:
                print(f"Error en feed {url}: {e}")
                continue

    print(f"Noticias recolectadas: {len(raw_data)}. Enviando a Gemini para categorización...")
    
    # Procesamiento con IA
    structured_data = analyze_with_ia(raw_data)
    
    # Gestión de archivos
    if not os.path.exists("historico_noticias"):
        os.makedirs("historico_noticias")
    
    # Guardar archivo para la web (latest)
    with open("latest_news.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=4, ensure_ascii=False)
    
    # Guardar histórico con timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    with open(f"historico_noticias/analisis_{timestamp}.json", "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Proceso completado. Análisis guardado en latest_news.json.")

if __name__ == "__main__":
    collect()

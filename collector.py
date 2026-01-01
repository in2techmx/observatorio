import feedparser
import json
import datetime
import os

# Configuración de los nodos de información (1 por región para estabilidad)
FEEDS = {
    "USA": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "CHINA": "https://www.globaltimes.cn/rss/china.xml",
    "RUSSIA": "https://tass.com/rss/v2.xml",
    "EUROPE": "https://rss.dw.com/rdf/rss-en-all",
    "INDIA": "https://www.thehindu.com/news/national/feeder/default.rss",
    "MID_EAST": "https://www.aljazeera.com/xml/rss/all.xml",
    "LATAM": "https://en.mercopress.com/rss/"
}

def collect():
    all_news = []
    print(f"Iniciando recolección: {datetime.datetime.now()}")

    for region, url in FEEDS.items():
        try:
            print(f"Procesando {region}...")
            feed = feedparser.parse(url)
            
            # Tomamos las 8 noticias más recientes por cada fuente
            for entry in feed.entries[:8]:
                # Limpiamos el título de posibles etiquetas HTML
                title = entry.title.replace('<![CDATA[', '').replace(']]>', '').strip()
                
                all_news.append({
                    "region": region,
                    "title": title,
                    "link": entry.link,
                    "published": entry.get("published", "Sin fecha"),
                    "timestamp": datetime.datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error recolectando {region}: {e}")

    # Definir la ruta del archivo (en la raíz del repo)
    file_name = "latest_news.json"
    
    # Guardar el archivo JSON
    try:
        with open(file_name, "w", encoding="utf-8") as f:
            json.dump(all_news, f, indent=4, ensure_ascii=False)
        print(f"✅ Éxito: Se han guardado {len(all_news)} noticias en {file_name}")
    except Exception as e:
        print(f"❌ Error al escribir el archivo: {e}")

if __name__ == "__main__":
    collect()

import feedparser
import json
import datetime
import os

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
    now = datetime.datetime.now()
    # Formato: 2024-05-20_14-30
    timestamp_str = now.strftime("%Y-%m-%d_%H-%M")
    
    # Nombre de tu nueva carpeta
    folder_name = "historico_noticias"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    for region, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
                all_news.append({
                    "region": region,
                    "title": entry.title.strip(),
                    "link": entry.link,
                    "timestamp": now.isoformat()
                })
        except Exception as e:
            print(f"Error en {region}: {e}")

    # Guardamos el archivo para la web y el histórico con timestamp
    file_fixed = "latest_news.json"
    file_historic = os.path.join(folder_name, f"noticias_{timestamp_str}.json")
    
    for file_path in [file_fixed, file_historic]:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_news, f, indent=4, ensure_ascii=False)
            
    print(f"✅ Archivos generados: {file_fixed} y {file_historic}")

if __name__ == "__main__":
    collect()

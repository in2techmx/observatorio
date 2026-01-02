import os
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE BLOQUES GEOPOLÍTICOS ---
FUENTES_ESTRATEGICAS = {
    "USA": ["https://www.washingtontimes.com/rss/headlines/news/world/", "https://feeds.aoc.org/reuters/USA"],
    "Rusia": ["https://tass.com/rss/v2.xml", "https://pravda-en.com/rss/"],
    "China": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "Europa": ["https://www.dw.com/en/top-stories/rss", "https://www.france24.com/en/rss"],
    "África": ["https://www.africanews.com/feed/", "https://www.premiumtimesng.com/feed"],
    "LATAM": [
        "https://www.telesurenglish.net/rss/sport.xml",
        "https://www.clarin.com/rss/mundo/",
        "https://www.infobae.com/feeds/rss/",
        "https://www.eluniversal.com.mx/rss.xml",
        "https://www.jornada.com.mx/rss/edicion.xml?v=1"
    ],
    "Medio Oriente": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss",
        "https://www.hispantv.com/rss/noticias"
    ]
}

def get_article_content(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            soup = BeautifulSoup(response, 'html.parser')
            paragraphs = soup.find_all('p')
            return " ".join([p.get_text() for p in paragraphs[:7]])
    except: return ""

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir): os.makedirs(historico_dir)

    client = genai.Client()
    contexto = []
    
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    root = ET.parse(resp).getroot()
                    for item in root.findall('.//item')[:3]:
                        link = item.find('link').text
                        contenido = get_article_content(link)
                        contexto.append(f"BLOQUE: {bloque}\nNOTICIA: {item.find('title').text}\nCONTENIDO: {contenido}\n---")
            except: continue

    prompt = f"Analiza estas noticias y genera 6 ejes geopolíticos. Calcula 'Proximidad' (0-100%). Contrasta visiones de LATAM (TeleSUR/La Jornada vs otros) y Medio Oriente (HispanTV vs otros). Responde SOLO JSON: [{{\"tematica\":\"\", \"descripcion\":\"\", \"regiones_activas\":[], \"proximidad\":\"X%\", \"perspectivas\":{{\"Bloque\":\"Postura\"}}}}]"

    try:
        response = client.models.generate_content(model="gemini-2.0-flash", contents=f"{prompt}\n\nContexto:\n{' '.join(contexto)}", config={'response_mime_type': 'application/json'})
        analisis = json.loads(response.text.strip())
        
        # Guardar latest y histórico
        with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f: json.dump(analisis, f, indent=4, ensure_ascii=False)
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
        with open(os.path.join(historico_dir, f"analisis_{ts}.json"), "w", encoding="utf-8") as f: json.dump(analisis, f, indent=4, ensure_ascii=False)
        
        # Timeline para navegación
        files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
        with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f: json.dump(files[:100], f, indent=4)
        print("✅ Análisis completado.")
    except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__": collect()

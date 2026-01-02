import os, json, time, ssl, urllib.request, hashlib, re
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from google import genai

# --- CONFIGURACIÓN ESTRATÉGICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444",
    "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981",
    "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6",
    "Sociedad y Derechos": "#ec4899"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

FUENTES = {
    "USA": ["https://www.npr.org/rss/rss.php?id=1004", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://api.washingtontimes.com/rss/headlines/news/world/"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/", "https://en.interfax.ru/rss/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml", "https://www.globaltimes.cn/rss/index.xml"],
    "EUROPE": ["https://www.france24.com/en/rss", "https://www.dw.com/xml/rss-en-all", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss", "https://www.timesofisrael.com/feed/"],
    "INDIA": ["https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "https://www.thehindu.com/news/national/feeder/default.rss", "https://idsa.in/rss.xml"],
    "AFRICA": ["https://www.africanews.com/feeds/rss", "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml", "https://www.theafricareport.com/feed/"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {} # Backup de URLs reales

    def get_rss_fast(self):
        print("🚀 Fase 1: Recolección RSS Multipolar...")
        all_news = {reg: [] for reg in FUENTES.keys()}
        
        def fetch_feed(region, url):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    extracted = []
                    for n in items[:6]:
                        t = (n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')).text
                        l_node = n.find('link') or n.find('{http://www.w3.org/2005/Atom}link')
                        l = l_node.attrib.get('href') if (l_node is not None and l_node.attrib) else (l_node.text if l_node is not None else "")
                        if t and l: extracted.append({"title": t.strip(), "link": l.strip()})
                    return region, extracted
            except: return region, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(fetch_feed, reg, url) for reg, urls in FUENTES.items() for url in urls]
            for f in concurrent.futures.as_completed(futures):
                reg, news = f.result()
                all_news[reg].extend(news)
        return all_news

    def scrape_selected(self, news_list):
        # Scraping puro para no perder URLs reales
        def scrape_one(item):
            try:
                req = urllib.request.Request(item['link'], headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    soup = BeautifulSoup(resp.read(), 'html.parser')
                    for s in soup(["script", "style"]): s.decompose()
                    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 60]
                    text = " ".join(paragraphs[:5])[:1500]
                    item['text'] = text
                    self.link_storage[item['title']] = item['link']
                    return item
            except: return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            return list(filter(None, executor.map(scrape_one, news_list)))

    def run(self):
        # 1. RSS
        raw_rss = self.get_rss_fast()
        
        # 2. Triaje Inteligente por Bloque (Seleccionamos 3 mejores por región)
        print("🤖 Fase 2: Triaje Geopolítico...")
        final_context = ""
        for region, articles in raw_rss.items():
            if not articles: continue
            list_str = "\n".join([f"[{i}] {a['title']}" for i, a in enumerate(articles[:15])])
            prompt = f"Selecciona los 3 índices de noticias más relevantes para {region} sobre impacto global. JSON: {{\"idx\": [x,y,z]}}. Lista:\n{list_str}"
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
                idxs = json.loads(res.text.strip()).get("idx", [0,1,2])
                selected = [articles[i] for i in idxs if i < len(articles)]
                
                # 3. Scraping Selectivo de los 3 elegidos
                enriched = self.scrape_selected(selected)
                for e in enriched:
                    final_context += f"BLOQUE: {region} | TITULO: {e['title']} | LINK: {e['link']} | TEXTO: {e['text']}\n\n"
            except: continue

        # 4. Análisis de Gravedad y Proximidad Multipolar
        print("🧠 Fase 3: Cálculo de Proximidad por Áreas...")
        prompt_final = f"""
        Actúa como un Motor de Inteligencia Multipolar. Clasifica la información en estas áreas: {list(AREAS_ESTRATEGICAS.keys())}.
        
        Para cada área:
        1. PUNTO CERO: Identifica los hechos verificados por el mayor número de bloques (USA, RUSSIA, CHINA, EUROPE, LATAM, MID_EAST, INDIA, AFRICA).
        2. PROXIMIDAD: Calcula el % de cercanía de cada noticia al PUNTO CERO (100% = Hecho compartido, 0% = Narrativa única/Propaganda).
        
        JSON ESTRUCTURA:
        {{
          "carousel": [
            {{
              "area": "Nombre del Área",
              "punto_cero": "Resumen del consenso global",
              "particulas": [
                {{ "titulo": "...", "bloque": "...", "proximidad": 0-100, "sesgo": "Analisis corto", "link": "LINK_REAL" }}
              ]
            }}
          ]
        }}
        
        CONTEXTO REAL: {final_context}
        """

        try:
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt_final, config={'response_mime_type': 'application/json', 'temperature': 0.0})
            data = json.loads(res.text.strip())
            
            # Validación Final de Seguridad de URLs
            for slide in data['carousel']:
                slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#ffffff")
                for p in slide['particulas']:
                    p['link'] = self.link_storage.get(p['titulo'], p['link'])
                    p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#ffffff")

            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print("✅ JSON para Carousel generado con éxito.")
            
        except Exception as e:
            print(f"❌ Error en síntesis final: {e}")

if __name__ == "__main__":
    API_KEY = os.environ.get("GEMINI_API_KEY")
    if API_KEY:
        GeopoliticalCollector(API_KEY).run()
    else:
        print("Falta GEMINI_API_KEY")

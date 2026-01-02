import os, json, datetime, time, ssl, urllib.request, hashlib
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS ---
PATHS = {"diario": "historico_noticias/diario", "semanal": "historico_noticias/semanal", "mensual": "historico_noticias/mensual"}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

# --- MATRIZ DE FUENTES HÍBRIDA (Convencionales + Independientes) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml",
        "https://globalnews.ca/world/feed/",
        "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "https://rt.com/rss/news/",
        "https://globalvoices.org/section/world/russia/feed/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.ecns.cn/rss/rss.xml",
        "https://globalvoices.org/section/world/east-asia/feed/"
    ],
    "EUROPE": [
        "https://www.france24.com/en/rss",
        "https://www.dw.com/xml/rss-en-all",
        "https://globalvoices.org/section/world/western-europe/feed/",
        "https://www.euronews.com/rss?level=vertical&name=news"
    ],
    "LATAM": [
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://legrandcontinent.eu/es/feed/",
        "https://globalvoices.org/section/world/latin-america/feed/",
        "https://www.clarin.com/rss/mundo/"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://globalvoices.org/section/world/middle-east-north-africa/feed/"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://globalvoices.org/section/world/south-asia/feed/"
    ],
    "AFRICA": [
        "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml",
        "https://globalvoices.org/section/world/sub-saharan-africa/feed/",
        "https://www.africanews.com/feeds/rss"
    ]
}

# Feeds de Gists y Curación Externa
FUENTES_EXTRA = [
    "https://gist.githubusercontent.com/pj8912/5be498a246ddc0fe8a7b65f10487562d/raw/",
    "https://rss.feedspot.com/unbiased_news_rss_feeds/"
]

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_universal(self, region, url):
        """Intenta extraer de RSS o Scrapear HTML si el RSS falla"""
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                raw = resp.read()
                # 1. Intentar Parser XML
                try:
                    root = ET.fromstring(raw)
                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    extracted = []
                    for n in items[:12]:
                        t_node = n.find('title') or n.find('{*}title')
                        l_node = n.find('link') or n.find('{*}link')
                        d_node = n.find('description') or n.find('{*}summary')
                        
                        t = t_node.text.strip() if t_node is not None else None
                        l = (l_node.text or l_node.attrib.get('href', '')).strip() if l_node is not None else ""
                        d = d_node.text.strip() if d_node is not None and d_node.text else ""
                        
                        if t and l:
                            art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                            self.link_storage[art_id] = {"link": l, "title": t, "region": region}
                            self.title_to_id[t] = art_id
                            extracted.append({"title": t, "summary": d})
                    return extracted
                except:
                    # 2. Fallback Scraping (para Gists y Feedspot)
                    soup = BeautifulSoup(raw, 'html.parser')
                    extracted = []
                    for a in soup.find_all('a', href=True)[:15]:
                        t = a.get_text().strip()
                        l = a['href']
                        if len(t) > 30 and l.startswith('http'):
                            art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                            self.link_storage[art_id] = {"link": l, "title": t, "region": region}
                            self.title_to_id[t] = art_id
                            extracted.append({"title": t, "summary": "Análisis de Redes/Fuentes Curadas"})
                    return extracted
        except: return []

    def run(self):
        print("🚀 Iniciando Motor de Inteligencia Geopolítica...")
        batch_text = ""
        count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            # Enviar fuentes regionales
            futures = {executor.submit(self.fetch_universal, reg, url): reg for reg, urls in FUENTES.items() for url in urls}
            # Enviar fuentes extra
            for url in FUENTES_EXTRA:
                executor.submit(self.fetch_universal, "GLOBAL", url)

            results = {reg: [] for reg in FUENTES.keys()}
            for f in concurrent.futures.as_completed(futures):
                reg = futures[f]
                results[reg].extend(f.result())

        for reg, items in results.items():
            if not items: continue
            # Triaje por Gemini para elegir las 2 mejores del pool de ese bloque
            titles = "\n".join([f"[{i}] {x['title']}" for i, x in enumerate(items[:15])])
            try:
                res = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Selecciona los índices de las 2 noticias con más peso geopolítico: {titles}",
                    config={'response_mime_type': 'application/json'}
                )
                idxs = json.loads(res.text.strip()).get("idx", [0, 1])
                for i in idxs:
                    if i < len(items):
                        batch_text += f"BLOQUE: {reg} | TIT: {items[i]['title']} | INFO: {items[i]['summary'][:250]}\n\n"
                        count += 1
            except: continue

        if count < 5:
            print("❌ No hay datos."); return

        # Análisis Final
        prompt = f"Genera matriz geopolítica JSON. Llaves: 'carousel', 'area', 'punto_cero', 'particulas' [{{'titulo', 'bloque', 'proximidad', 'sesgo'}}]. Contexto: {batch_text}"
        data = json.loads(self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}).text.strip())

        for slide in data.get('carousel', []):
            slide['area'] = slide.get('area') or "Tendencia Global"
            slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#3b82f6")
            for p in slide.get('particulas', []):
                art_id = self.title_to_id.get(p.get('titulo'))
                if art_id: p['link'] = self.link_storage[art_id]['link']
                p['color_bloque'] = BLOQUE_COLORS.get(p.get('bloque'), "#94a3b8")

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Éxito: {count} noticias procesadas de medios globales.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

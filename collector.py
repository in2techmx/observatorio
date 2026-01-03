import os, json, datetime, time, urllib.request, hashlib, re, sys, math
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ESTRATÉGICA ---
MIN_TARGET = 15
MAX_TARGET = 80 # Aumentado para mayor densidad en el radar
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

NORMALIZER = {
    "USA": "USA", "RUSSIA": "RUSSIA", "CHINA": "CHINA", "EUROPE": "EUROPE", 
    "LATAM": "LATAM", "MID_EAST": "MID_EAST", "INDIA": "INDIA", "AFRICA": "AFRICA",
    "GLOBAL": "GLOBAL"
}

FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml", 
        "http://rss.cnn.com/rss/edition_us.rss", 
        "https://feeds.washingtonpost.com/rss/politics",
        "https://www.reutersagency.com/feed/?best-topics=political-news&post_type=best"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml", 
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed", 
        "https://www.chinadaily.com.cn/rss/world_rss.xml",
        "https://www.globaltimes.cn/rss/china.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss", 
        "https://www.france24.com/en/rss",
        "https://rss.dw.com/xml/rss-en-all",
        "https://elpais.com/rss/elpais/inenglish.xml",
        "https://www.euronews.com/rss?level=vertical&name=news"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/", 
        "https://elpais.com/america/rss/",
        "https://www.clarin.com/rss/lo-ultimo/",
        "https://cnnespanol.cnn.com/feed"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml", 
        "https://www.trtworld.com/rss",
        "https://www.timesofisrael.com/feed/",
        "https://www.arabnews.com/cat/1/rss.xml",
        "https://english.alarabiya.net/.mrss/en/news.xml"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss", 
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://feeds.feedburner.com/ndtvnews-latest"
    ],
    "AFRICA": [
        "https://africa.com/feed", 
        "http://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "https://www.news24.com/news24/partners24/rss"
    ],
    "GLOBAL": [
        "https://www.wired.com/feed/category/science/latest/rss",
        "https://techcrunch.com/feed/",
        "https://www.nature.com/nature.rss"
    ]
}

class CollectorV27_6:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(list)
        self.raw_ingest = defaultdict(list)

    def clean_text(self, text):
        if not text: return ""
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
        return re.sub(r'<[^>]+>', '', text).strip()

    def get_embeddings(self, texts):
        if not texts: return []
        try:
            res = self.client.models.embed_content(model="text-embedding-004", content=texts, config={'task_type': 'RETRIEVAL_DOCUMENT'})
            return [e.values for e in res.embeddings]
        except: return [None] * len(texts)

    def cosine_sim(self, v1, v2):
        if not v1 or not v2: return 0
        dot = sum(a*b for a,b in zip(v1, v2))
        n1, n2 = math.sqrt(sum(a*a for a in v1)), math.sqrt(sum(b*b for b in v2))
        return dot / (n1 * n2) if n1*n2 > 0 else 0

    def smart_scrape(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=7) as res:
                soup = BeautifulSoup(res.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "aside"]): s.extract()
                text = " ".join([p.get_text() for p in soup.find_all('p')])
                return text.strip() if len(text) > 450 else None
        except: return None

    def get_insight(self, title, content, area, consensus):
        try:
            prompt = f"ÁREA: {area}\nCONSENSO: {consensus}\nNOTICIA: {title}\nCONTENIDO: {content[:1000]}\nExplica en 12 palabras qué dato diferencia esta noticia del consenso."
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except: return "Perspectiva regional con matices fácticos propios."

    def run(self):
        print(f"🌍 FASE 1: Ingesta Masiva ({len(FUENTES)} bloques regionales)...")
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    root = ET.fromstring(urllib.request.urlopen(req, timeout=6).read())
                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    for n in items[:35]:
                        t = self.clean_text((n.find('title') or n.find('{*}title')).text)
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        s_node = n.find('description') or n.find('{*}summary')
                        s = self.clean_text(s_node.text if s_node is not None else "")
                        if t and l: self.raw_ingest[region].append({"title": t, "link": l, "region": region, "snippet": s})
                except: continue

        for region, items in self.raw_ingest.items():
            print(f"🔎 Triaje de Clasificación: {region} ({len(items)} señales)")
            if not items: continue
            
            # Clasificación en lotes de 40 para eficiencia
            for i in range(0, len(items), 40):
                sub_batch = items[i:i+40]
                batch_titles = [x['title'] for x in sub_batch]
                prompt = f"Clasifica en {AREAS_ESTRATEGICAS} y traduce a español. JSON: {{'res': [{{'idx': int, 'area': '...', 'titulo_es': '...'}}]}}\n" + "\n".join([f"{j}|{t}" for j, t in enumerate(batch_titles)])
                
                try:
                    res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
                    classes = json.loads(res.text).get('res', [])
                    for c in classes:
                        if c['area'] in AREAS_ESTRATEGICAS:
                            news = sub_batch[c['idx']]
                            news.update({"area": c['area'], "titulo_es": c['titulo_es']})
                            
                            # Triaje Nivel 2: Ruta Híbrida
                            scraped = self.smart_scrape(news['link'])
                            if scraped:
                                news['analysis_base'], news['metodo'] = scraped, "Deep Scrape"
                            else:
                                news['analysis_base'], news['metodo'] = f"{news['titulo_es']}. {news['snippet']}", "Metadata Hybrid"
                            
                            if len(self.matrix[c['area']]) < MAX_TARGET:
                                self.matrix[c['area']].append(news)
                except: continue

        print("\n📐 FASE 2: Triangulación y Generación de Radar...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = self.matrix.get(area, [])
            if not nodes: continue
            
            node_vectors = self.get_embeddings([n['analysis_base'] for n in nodes])
            valid_v = [v for v in node_vectors if v is not None and len(v) > 0]
            if not valid_v: continue
            
            dim = len(valid_v[0])
            centroid = [sum(v[j] for v in valid_v)/len(valid_v) for j in range(dim)]
            
            try:
                c_res = self.client.models.generate_content(model="gemini-2.0-flash", contents=f"Resume en 15 palabras el consenso factual de {area}: " + ". ".join([n['titulo_es'] for n in nodes[:8]]))
                consensus = c_res.text.strip()
            except: consensus = f"Análisis de convergencia en {area}."

            particles = []
            for idx, node in enumerate(nodes):
                if idx >= len(node_vectors) or node_vectors[idx] is None: continue
                sim = self.cosine_sim(node_vectors[idx], centroid)
                prox = round(max(0, min(100, (sim - 0.7) * 333.3)), 1) if len(nodes) > 1 else 100.0
                insight = self.get_insight(node['titulo_es'], node['analysis_base'], area, consensus) if prox < 75 else "Alineada con el flujo central."
                
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:6],
                    "titulo": node['titulo_es'], "link": node['link'], 
                    "bloque": NORMALIZER.get(node['region'], "GLOBAL"), 
                    "proximidad": prox, "metodo": node['metodo'], "sesgo": insight
                })
            
            final_carousel.append({"area": area, "punto_cero": consensus, "color": self.get_color(area), "particulas": particles})

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump({"carousel": final_carousel}, f, indent=2, ensure_ascii=False)
        print("✅ PROCESO COMPLETADO.")

    def get_color(self, a):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(a, "#fff")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: CollectorV27_6(key).run()

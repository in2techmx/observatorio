import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, re, sys, random, math
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

PATHS = { "diario": "historico_noticias/diario" }
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics", "https://www.foreignaffairs.com/rss.xml"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://themoscowtimes.com/rss/news"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.xinhuanet.com/english/rss/world.xml", "http://www.ecns.cn/rss/rss.xml", "https://www.chinadaily.com.cn/rss/world_rss.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.euronews.com/rss?level=vertical&name=news", "https://www.france24.com/en/rss", "https://www.dw.com/xml/rss/rss-en-all"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", "https://elpais.com/america/rss/", "https://en.mercopress.com/rss", "https://www.bbc.com/mundo/ultimas_noticias/index.xml", "https://cnnespanol.cnn.com/feed"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.middleeasteye.net/rss", "https://www.arabnews.com/cat/2/rss.xml", "https://www.jpost.com/rss/rssfeedsheadlines.aspx", "https://english.alarabiya.net/.mrss/en/news.xml", "https://www.trtworld.com/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"],
    "AFRICA": ["https://africa.com/feed", "https://newafricanmagazine.com/feed", "http://feeds.bbci.co.uk/news/world/africa/rss.xml", "https://www.news24.com/news24/partners24/rss", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"]
}

class DeepIntelligenceEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.clean_sample = [] 
        self.clusters = defaultdict(list)

    def clean_text(self, text):
        if not text: return ""
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text)
        return re.sub(r'<[^>]+>', '', text).strip()

    def get_embeddings(self, texts):
        if not texts: return []
        try:
            res = self.client.models.embed_content(model="text-embedding-004", content=texts, config={'task_type': 'RETRIEVAL_DOCUMENT'})
            return [e.values for e in res.embeddings]
        except: return [None] * len(texts)

    def smart_scrape(self, url):
        """Extracción profunda de la sustancia noticiosa."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=8) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "aside", "header", "form"]):
                    s.extract()
                paragraphs = soup.find_all('p')
                text = " ".join([p.get_text() for p in paragraphs])
                return re.sub(r'\s+', ' ', text).strip()[:2500]
        except: return ""

    def cosine_sim(self, v1, v2):
        if v1 is None or v2 is None: return 0
        dot = sum(a*b for a,b in zip(v1, v2))
        n1, n2 = math.sqrt(sum(a*a for a in v1)), math.sqrt(sum(b*b for b in v2))
        return dot / (n1 * n2) if n1*n2 > 0 else 0

    # --- FASE 1 & 2: MUESTRA REPRESENTATIVA ---
    def build_representative_sample(self):
        print("🌍 FASE 1: Ingesta y Deduplicación Vectorial...")
        raw_list = []
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    root = ET.fromstring(urllib.request.urlopen(req, timeout=5).read())
                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    for n in items[:30]:
                        t = self.clean_text((n.find('title') or n.find('{*}title')).text)
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l: raw_list.append({"title": t, "link": l, "region": region})
                except: continue

        # Deduplicación por titulares
        vectors = self.get_embeddings([x['title'] for x in raw_list])
        unique_indices = []
        for i, v_i in enumerate(vectors):
            if not any(self.cosine_sim(v_i, vectors[j]) > 0.88 for j in unique_indices):
                unique_indices.append(i)
        
        self.clean_sample = [raw_list[i] for i in unique_indices]
        print(f"   ✅ Muestra representativa: {len(self.clean_sample)} noticias únicas.")

    # --- FASE 3: SCRAPING Y CLASIFICACIÓN ---
    def process_deep_content(self):
        print("🧠 FASE 2: Scraping Profundo y Clasificación...")
        batch_size = 35
        for i in range(0, len(self.clean_sample), batch_size):
            batch = self.clean_sample[i:i+batch_size]
            prompt = f"Clasifica en: {AREAS_ESTRATEGICAS}. Traduce a español. Si no es estratégico usa area:'NONE'. JSON: {{ 'res': [{{ 'idx': int, 'area': '...', 'titulo_es': '...' }}] }}\n\n"
            prompt += "\n".join([f"IDX:{idx+i} | T:{item['title']}" for idx, item in enumerate(batch)])
            
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
                data = json.loads(res.text)
                for r in data.get('res', []):
                    if r['area'] in AREAS_ESTRATEGICAS:
                        idx = r['idx']
                        # SCRAPING SOLO DE LA MUESTRA GANADORA
                        content = self.smart_scrape(self.clean_sample[idx]['link'])
                        if len(content) > 200:
                            self.clean_sample[idx].update({"area": r['area'], "titulo_es": r['titulo_es'], "full_content": content})
                            self.clusters[r['area']].append(self.clean_sample[idx])
            except: continue

    # --- FASE 4: RADAR VECTORIAL ---
    def run_radar(self):
        print("📐 FASE 3: Generando Radar de Convergencia...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = self.clusters.get(area, [])
            if len(nodes) < 2: continue
            
            # Vectores basados en contenido profundo
            vectors = self.get_embeddings([n['full_content'] for n in nodes])
            valid_v = [v for v in vectors if v]
            centroid = [sum(v[i] for v in valid_v)/len(valid_v) for i in range(len(valid_v[0]))]
            
            particles = []
            for idx, node in enumerate(nodes):
                sim = self.cosine_sim(vectors[idx], centroid)
                prox = round(max(0, min(100, (sim - 0.7) * 333.3)), 1)
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:6],
                    "titulo": node['titulo_es'], "link": node['link'], "bloque": node['region'],
                    "proximidad": prox, "sesgo": "Convergencia fáctica." if prox > 75 else "Divergencia narrativa."
                })
            final_carousel.append({"area": area, "punto_cero": "Análisis vectorial de contenido profundo.", "color": self.get_color(area), "particulas": particles})

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump({"carousel": final_carousel}, f, indent=2, ensure_ascii=False)
        print("✅ Observatorio actualizado.")

    def get_color(self, a):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(a, "#fff")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        engine = DeepIntelligenceEngine(key)
        engine.build_representative_sample()
        engine.process_deep_content()
        engine.run_radar()

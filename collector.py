import os, json, datetime, time, urllib.request, hashlib, re, sys, math
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE INTELIGENCIA ---
MIN_TARGET = 15
MAX_TARGET = 50
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

NORMALIZER = {
    "USA": "USA", "RUSSIA": "RUSSIA", "CHINA": "CHINA", "EUROPE": "EUROPE", 
    "LATAM": "LATAM", "MID_EAST": "MID_EAST", "INDIA": "INDIA", "AFRICA": "AFRICA"
}

FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://www.chinadaily.com.cn/rss/world_rss.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.france24.com/en/rss"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", "https://elpais.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"],
    "AFRICA": ["https://africa.com/feed", "http://feeds.bbci.co.uk/news/world/africa/rss.xml"]
}

class CollectorV26:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(list)
        self.raw_ingest = defaultdict(list)

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'<[^>]+>', '', text).strip()

    def get_embeddings(self, texts):
        if not texts: return []
        try:
            res = self.client.models.embed_content(model="text-embedding-004", content=texts, config={'task_type': 'RETRIEVAL_DOCUMENT'})
            return [e.values for e in res.embeddings]
        except: return [None] * len(texts)

    def cosine_sim(self, v1, v2):
        if v1 is None or v2 is None: return 0
        dot = sum(a*b for a,b in zip(v1, v2))
        n1, n2 = math.sqrt(sum(a*a for a in v1)), math.sqrt(sum(b*b for b in v2))
        return dot / (n1 * n2) if n1*n2 > 0 else 0

    def smart_scrape(self, url):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as res:
                soup = BeautifulSoup(res.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer"]): s.extract()
                return " ".join([p.get_text() for p in soup.find_all('p')])[:2500]
        except: return ""

    def get_insight(self, title, content, area, consensus):
        try:
            prompt = f"ÁREA: {area}\nCONSENSO: {consensus}\nNOTICIA: {title}\nCONTENIDO: {content[:1000]}\nExplica en 12 palabras qué dato o matiz diferencia esta noticia del consenso."
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return res.text.strip()
        except: return "Perspectiva con matices regionales específicos."

    def run(self):
        print("🌍 INICIANDO INGESTA DINÁMICA...")
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    root = ET.fromstring(urllib.request.urlopen(req, timeout=5).read())
                    for n in (root.findall('.//item') or root.findall('.//{*}entry'))[:35]:
                        t = self.clean_text((n.find('title') or n.find('{*}title')).text)
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l: self.raw_ingest[region].append({"title": t, "link": l, "region": region})
                except: continue

        for region, items in self.raw_ingest.items():
            print(f"🔎 Clasificando {region}...")
            batch = [x['title'] for x in items]
            prompt = f"Clasifica en {AREAS_ESTRATEGICAS} y traduce a español. JSON: {{'res': [{{'idx': int, 'area': '...', 'titulo_es': '...'}}]}}\n" + "\n".join([f"{i}|{t}" for i, t in enumerate(batch)])
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
                classes = json.loads(res.text).get('res', [])
                temp_area_buckets = defaultdict(list)
                for c in classes:
                    if c['area'] in AREAS_ESTRATEGICAS:
                        items[c['idx']].update({"area": c['area'], "titulo_es": c['titulo_es']})
                        temp_area_buckets[c['area']].append(items[c['idx']])
                
                for area, a_items in temp_area_buckets.items():
                    vectors = self.get_embeddings([x['title'] for x in a_items])
                    indices = []
                    for i, v in enumerate(vectors):
                        if len(indices) >= MAX_TARGET: break
                        if not any(self.cosine_sim(v, vectors[j]) > 0.86 for j in indices): indices.append(i)
                    if len(indices) < MIN_TARGET:
                        for i in range(len(a_items)):
                            if len(indices) >= MIN_TARGET: break
                            if i not in indices: indices.append(i)
                    for idx in indices:
                        news = a_items[idx]
                        content = self.smart_scrape(news['link'])
                        if len(content) > 200:
                            news['full_content'] = content
                            self.matrix[area].append(news)
            except: continue

        print("📐 TRIANGULACIÓN FINAL...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = self.matrix[area]
            if len(nodes) < 3: continue
            node_vectors = self.get_embeddings([n['full_content'] for n in nodes])
            valid_v = [v for v in node_vectors if v]
            centroid = [sum(v[i] for v in valid_v)/len(valid_v) for i in range(len(valid_v[0]))]
            
            c_res = self.client.models.generate_content(model="gemini-2.0-flash", contents=f"Resume en 15 palabras el consenso factual de estas noticias de {area}: " + ". ".join([n['titulo_es'] for n in nodes[:8]]))
            consensus = c_res.text.strip()

            particles = []
            for idx, node in enumerate(nodes):
                if node_vectors[idx] is None: continue
                sim = self.cosine_sim(node_vectors[idx], centroid)
                prox = round(max(0, min(100, (sim - 0.7) * 333.3)), 1)
                insight = self.get_insight(node['titulo_es'], node['full_content'], area, consensus) if prox < 75 else "Alineada con el consenso global."
                particles.append({"id": hashlib.md5(node['link'].encode()).hexdigest()[:6], "titulo": node['titulo_es'], "link": node['link'], "bloque": NORMALIZER.get(node['region'], "GLOBAL"), "proximidad": prox, "sesgo": insight})
            
            final_carousel.append({"area": area, "punto_cero": consensus, "color": self.get_color(area), "particulas": particles})

        with open("gravity_carousel.json", "w", encoding="utf-8") as f: json.dump({"carousel": final_carousel}, f, indent=2, ensure_ascii=False)

    def get_color(self, a):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(a, "#fff")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: CollectorV26(key).run()

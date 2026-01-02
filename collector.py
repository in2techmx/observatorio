import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, re, sys, random
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup 

# --- CONFIGURACIÓN BASE ---
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

PATHS = { "diario": "historico_noticias/diario" }
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
}

AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

NORMALIZER = {
    "USA": "USA", "EE.UU.": "USA", "US": "USA", "UNITED STATES": "USA",
    "RUSSIA": "RUSSIA", "RUSIA": "RUSSIA", "RUSSIAN FEDERATION": "RUSSIA",
    "CHINA": "CHINA", "ASIA": "CHINA", "BEIJING": "CHINA",
    "EUROPE": "EUROPE", "EUROPA": "EUROPE", "UE": "EUROPE", "UK": "EUROPE", "GERMANY": "EUROPE", "FRANCE": "EUROPE",
    "LATAM": "LATAM", "AMERICA LATINA": "LATAM", "BRAZIL": "LATAM", "MEXICO": "LATAM",
    "MID_EAST": "MID_EAST", "MEDIO ORIENTE": "MID_EAST", "ISRAEL": "MID_EAST", "IRAN": "MID_EAST",
    "INDIA": "INDIA", "NEW DELHI": "INDIA",
    "AFRICA": "AFRICA", "SOUTH AFRICA": "AFRICA", "NIGERIA": "AFRICA"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e", "GLOBAL": "#94a3b8"
}

FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "http://rss.cnn.com/rss/edition_world.rss",
        "https://www.foreignaffairs.com/rss.xml"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.xinhuanet.com/english/rss/world.xml",
        "http://www.ecns.cn/rss/rss.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.france24.com/en/rss"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/",
        "https://en.mercopress.com/rss"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.arabnews.com/cat/2/rss.xml"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    ],
    "AFRICA": [
        "https://africa.com/feed",
        "https://newafricanmagazine.com/feed",
        "http://feeds.bbci.co.uk/news/world/africa/rss.xml"
    ]
}

class ClusterEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.raw_storage = {} 
        self.clusters = defaultdict(list)
        self.hoy = datetime.datetime.now()

    def fetch_rss(self):
        print(f"🌍 FASE 1: Recolección Masiva Global...")
        raw_items = []
        
        for region, urls in FUENTES.items():
            print(f"   -> Escaneando: {region}...")
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    content = urllib.request.urlopen(req, timeout=4).read()
                    try: root = ET.fromstring(content)
                    except: continue

                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    for n in items[:6]:
                        t = (n.find('title') or n.find('{*}title')).text.strip()
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l:
                            aid = hashlib.md5(t.encode('utf-8')).hexdigest()[:8]
                            self.raw_storage[aid] = {"id": aid, "title": t, "link": l, "region": region}
                            raw_items.append(f"ID:{aid} | TITLE:{t}")
                except: continue
        
        random.shuffle(raw_items)
        return raw_items

    def smart_scrape(self, url):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "svg", "header", "aside", "form"]): 
                    s.extract()
                return re.sub(r'\s+', ' ', soup.get_text()).strip()[:1500]
        except: return ""

    def triage_batch(self, batch_titles):
        text_block = "\n".join(batch_titles)
        prompt = f"""
        Clasifica en ÁREAS: {AREAS_ESTRATEGICAS}.
        JSON: {{ "items": [ {{ "id": "...", "area": "..." }} ] }}
        INPUT:
        {text_block}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            # FIX: strict=False permite caracteres de control (saltos de línea raros) dentro del JSON
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except: return None

    def analyze_cluster(self, area_name, item_ids):
        print(f"   ⚡ Analizando Clúster: {area_name} ({len(item_ids)} señales)...")
        
        cluster_context = []
        for aid in item_ids:
            meta = self.raw_storage[aid]
            full_text = self.smart_scrape(meta['link'])
            if len(full_text) < 50: full_text = meta['title'] 
            cluster_context.append(f"ID: {aid} | BLOQUE: {meta['region']} | TEXTO: {full_text}")

        context_string = "\n".join(cluster_context)

        prompt = f"""
        Eres PROXIMITY. Analiza las relaciones entre noticias del grupo: {area_name}.
        
        OBJETIVO:
        Mide el "AISLAMIENTO vs INTERSECCIÓN" de las narrativas. No busques la verdad, busca la coincidencia entre rivales.
        
        MÉTRICA "PROXIMIDAD RELATIVA" (0-100%):
        - 100% (CENTRO): Narrativa de Alta Intersección. Es un tema o enfoque que aparece idéntico en múltiples bloques rivales.
        - 0% (BORDE): Narrativa de Alto Aislamiento. Es una versión de los hechos que SOLO defiende un bloque.
        
        OUTPUT JSON:
        {{
            "punto_cero": "Resumen del tema que genera más intersección en este grupo.",
            "particulas": [
                {{
                    "id": "ID_EXACTO",
                    "titulo": "Título en Español",
                    "proximidad": 85.5,
                    "sesgo": "Explica por qué está aislado o intersectado"
                }}
            ]
        }}

        DATA:
        {context_string}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            # FIX: strict=False es la clave para evitar el error "Invalid control character"
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except Exception as e:
            print(f"⚠️ Error Cluster IA ({area_name}): {e}")
            return None

    def run(self):
        raw_titles = self.fetch_rss()
        if not raw_titles: return

        print(f"🗂️ FASE 2: Clasificando {len(raw_titles)} señales mezcladas...")
        batch_size = 25
        for i in range(0, len(raw_titles), batch_size):
            batch = raw_titles[i:i+batch_size]
            classification = self.triage_batch(batch)
            if classification and 'items' in classification:
                for item in classification['items']:
                    aid = item.get('id')
                    area = item.get('area')
                    if aid in self.raw_storage and area in AREAS_ESTRATEGICAS:
                        self.clusters[area].append(aid)
            time.sleep(1)

        print("🧠 FASE 3: Deep Analysis (Gravedad Relativa)...")
        final_carousel = []
        
        for area, ids in self.clusters.items():
            if not ids: continue
            
            ids_to_process = ids[:12] 
            analysis = self.analyze_cluster(area, ids_to_process)
            
            if analysis and 'particulas' in analysis:
                clean_particles = []
                for p in analysis['particulas']:
                    if p['id'] in self.raw_storage:
                        meta = self.raw_storage[p['id']]
                        p['link'] = meta['link']
                        p['bloque'] = self.normalize_block(meta['region'])
                        
                        try: p['proximidad'] = float(p['proximidad'])
                        except: p['proximidad'] = 50.0
                        clean_particles.append(p)
                
                final_carousel.append({
                    "area": area,
                    "punto_cero": analysis.get('punto_cero', 'Análisis en proceso.'),
                    "color": self.get_area_color(area),
                    "particulas": clean_particles
                })
            time.sleep(2)

        output = {"carousel": final_carousel}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("✅ CICLO COMPLETADO.")

    def normalize_block(self, region):
        return NORMALIZER.get(region, "GLOBAL")

    def get_area_color(self, area):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(area, "#94a3b8")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_

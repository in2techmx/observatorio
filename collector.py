import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, re, sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup 

# --- PARCHE DE CODIFICACIÓN (CRÍTICO) ---
# Evita errores con caracteres chinos, rusos, árabes, etc.
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

# --- CONFIGURACIÓN ---
PATHS = { "diario": "historico_noticias/diario" }
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
}

# --- DEFINICIONES VISUALES ---
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

# Mapa de normalización para asegurar que los colores coincidan en el Frontend
NORMALIZER = {
    "EE.UU.": "USA", "ESTADOS UNIDOS": "USA", "US": "USA", "UNITED STATES": "USA",
    "RUSIA": "RUSSIA", "RUSSIAN FEDERATION": "RUSSIA", "MOSCU": "RUSSIA",
    "EUROPA": "EUROPE", "UE": "EUROPE", "UK": "EUROPE", "GERMANY": "EUROPE", "FRANCE": "EUROPE",
    "MEDIO ORIENTE": "MID_EAST", "ORIENTE MEDIO": "MID_EAST", "ISRAEL": "MID_EAST", "IRAN": "MID_EAST",
    "AMERICA LATINA": "LATAM", "LATINOAMERICA": "LATAM", "BRAZIL": "LATAM", "MEXICO": "LATAM",
    "ÁFRICA": "AFRICA", "AFRICA": "AFRICA", "NIGERIA": "AFRICA", "SOUTH AFRICA": "AFRICA",
    "ASIA": "CHINA", "CHINA": "CHINA", "BEIJING": "CHINA",
    "INDIA": "INDIA", "NEW DELHI": "INDIA"
}

# --- RED DE FUENTES COMPLETA (55+ FEEDS) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "http://rss.cnn.com/rss/edition_world.rss",
        "https://www.politico.com/rss/politicopicks.xml",
        "https://www.foreignaffairs.com/rss.xml",
        "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news",
        "https://globalvoices.org/section/world/russia/feed/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.xinhuanet.com/english/rss/world.xml",
        "http://www.ecns.cn/rss/rss.xml",
        "https://globalvoices.org/section/world/east-asia/feed/"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://legrandcontinent.eu/es/feed/",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/xml/rss-en-all"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/",
        "https://en.mercopress.com/rss",
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://www.bbcmundo.com/pasoapaso/rss.xml"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.arabnews.com/cat/2/rss.xml",
        "https://www.trtworld.com/rss"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.ndtv.com/rss/top-stories.xml"
    ],
    "AFRICA": [
        "https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en",
        "https://africa.com/feed",
        "https://newafricanmagazine.com/feed",
        "https://theconversation.com/africa/articles.atom",
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
        print(f"🌍 FASE 1: Recolección Masiva desde {len([u for r in FUENTES.values() for u in r])} fuentes...")
        raw_items = []
        
        for region, urls in FUENTES.items():
            print(f"   -> Escaneando red: {region}...")
            for url in urls:
                try:
                    # Timeout ajustado para evitar cuellos de botella
                    req = urllib.request.Request(url, headers=HEADERS)
                    content = urllib.request.urlopen(req, timeout=4).read()
                    
                    try:
                        root = ET.fromstring(content)
                    except:
                        # Fallback simple si el XML está sucio
                        continue

                    # Capturamos máx 5 por feed para no saturar el Triaje (5 * 55 = ~275 noticias)
                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    for n in items[:5]:
                        t = (n.find('title') or n.find('{*}title')).text.strip()
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        
                        if t and l:
                            aid = hashlib.md5(t.encode('utf-8')).hexdigest()[:8]
                            self.raw_storage[aid] = {"id": aid, "title": t, "link": l, "region": region}
                            raw_items.append(f"ID:{aid} | TITLE:{t}")
                except: 
                    continue
        return raw_items

    def smart_scrape(self, url):
        """Deep Scraping: Extrae el texto real."""
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                # Limpieza agresiva
                for s in soup(["script", "style", "nav", "footer", "svg", "header", "aside", "form"]): 
                    s.extract()
                return re.sub(r'\s+', ' ', soup.get_text()).strip()[:1500]
        except: return ""

    def triage_batch(self, batch_titles):
        """FASE 2: Clasificación rápida de títulos."""
        text_block = "\n".join(batch_titles)
        prompt = f"""
        Actúa como clasificador de inteligencia.
        Asigna cada noticia a una de estas ÁREAS: {AREAS_ESTRATEGICAS}.
        Si no es relevante geopolíticamente, ignórala.
        
        FORMATO JSON: {{ "items": [ {{ "id": "...", "area": "..." }} ] }}
        
        INPUT:
        {text_block}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''))
        except: return None

    def analyze_cluster(self, area_name, item_ids):
        """FASE 3: Análisis de Consenso y Distancia."""
        print(f"   ⚡ Analizando Clúster: {area_name} ({len(item_ids)} señales)...")
        
        cluster_context = []
        for aid in item_ids:
            meta = self.raw_storage[aid]
            full_text = self.smart_scrape(meta['link'])
            if len(full_text) < 50: full_text = meta['title'] 
            # Inyectamos el bloque para que la IA sepa quién habla
            cluster_context.append(f"ID: {aid} | BLOQUE: {meta['region']} | TEXTO: {full_text}")

        prompt = f"""
        Eres el motor PROXIMITY. Estás analizando el ecosistema de noticias: {area_name}.
        
        TAREA:
        1. Lee todas las noticias y detecta el "HECHO FACTUAL" central (si existe).
        2. Mide la DISTANCIA NARRATIVA de cada noticia respecto a ese hecho neutral.
        
        MÉTRICA PROXIMIDAD (0-100%):
        - 100% (CENTRO): Narrativa Próxima. Coincide con el consenso factual/técnico.
        - 50% (MEDIA): Interpretación estándar del bloque.
        - 0% (BORDE): Narrativa Lejana. Propaganda, especulación o contradicción frontal con otros bloques.

        OUTPUT JSON:
        {{
            "punto_cero": "Resumen de 2 líneas del consenso (o conflicto) factual de este grupo.",
            "particulas": [
                {{
                    "id": "ID_EXACTO",
                    "titulo": "Título en Español",
                    "proximidad": 85.5,
                    "sesgo": "Breve análisis del encuadre (ej. 'Enfatiza X', 'Omite Y')"
                }}
            ]
        }}

        DATA DEL CLÚSTER:
        {"\n".join(cluster_context)}
        """
        
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''))
        except Exception as e:
            print(f"Error Cluster IA: {e}")
            return None

    def run(self):
        # 1. HARVEST
        raw_titles = self.fetch_rss()
        if not raw_titles: return

        # 2. TRIAGE
        print(f"🗂️ FASE 2: Triaje de {len(raw_titles)} titulares...")
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

        # 3. DEEP ANALYSIS
        print("🧠 FASE 3: Deep Analysis (Relatividad Narrativa)...")
        final_carousel = []
        
        for area, ids in self.clusters.items():
            if not ids: continue
            
            # Tomamos una muestra representativa (Top 12) para análisis profundo
            # Esto evita errores por exceso de tokens y mantiene la velocidad
            ids_to_process = ids[:12] 
            
            analysis = self.analyze_cluster(area, ids_to_process)
            
            if analysis and 'particulas' in analysis:
                clean_particles = []
                for p in analysis['particulas']:
                    if p['id'] in self.raw_storage:
                        meta = self.raw_storage[p['id']]
                        p['link'] = meta['link']
                        
                        # Normalización de Bloque/Región
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

        # 4. SAVE
        output = {"carousel": final_carousel}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("✅ CICLO COMPLETADO: Proximity Engine Actualizado.")

    def normalize_block(self, region):
        # Mapea la región del feed al bloque de color del frontend
        return NORMALIZER.get(region, "GLOBAL")

    def get_area_color(self, area):
        colors = {
            "Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", 
            "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", 
            "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"
        }
        return colors.get(area, "#94a3b8")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: ClusterEngine(key).run()

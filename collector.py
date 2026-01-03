import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, re, sys, random
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from bs4 import BeautifulSoup 

# --- CONFIGURACIÓN DE ENTORNO ---
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

PATHS = { "diario": "historico_noticias/diario" }
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
}

# --- DEFINICIONES DE CLASIFICACIÓN ---
AREAS_DEFINICIONES = """
1. Seguridad y Conflictos: Guerras, OTAN, terrorismo, fronteras, armas, espionaje.
2. Economía y Sanciones: Inflación, bloqueos, BRICS, dólar, deudas, comercio.
3. Energía y Recursos: Petróleo, gas, litio, minería, agua, cambio climático.
4. Soberanía y Alianzas: Tratados, cumbres (G20, UN), elecciones, disputas territoriales.
5. Tecnología y Espacio: IA, chips, ciberseguridad, satélites, carrera espacial, 5G.
6. Sociedad y Derechos: Protestas, migración, censura, derechos humanos.
"""

AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

NORMALIZER = {
    "USA": "USA", "EE.UU.": "USA", "US": "USA", "UNITED STATES": "USA",
    "RUSSIA": "RUSSIA", "RUSIA": "RUSSIA", "RUSSIAN FEDERATION": "RUSSIA",
    "CHINA": "CHINA", "ASIA": "CHINA", "BEIJING": "CHINA",
    "EUROPE": "EUROPE", "EUROPA": "EUROPE", "UE": "EUROPE", "UK": "EUROPE", "GERMANY": "EUROPE", "FRANCE": "EUROPE",
    "LATAM": "LATAM", "AMERICA LATINA": "LATAM", "BRAZIL": "LATAM", "MEXICO": "LATAM", "ARGENTINA": "LATAM",
    "MID_EAST": "MID_EAST", "MEDIO ORIENTE": "MID_EAST", "ISRAEL": "MID_EAST", "IRAN": "MID_EAST", "TURKEY": "MID_EAST",
    "INDIA": "INDIA", "NEW DELHI": "INDIA",
    "AFRICA": "AFRICA", "SOUTH AFRICA": "AFRICA", "NIGERIA": "AFRICA"
}

# --- FUENTES AMPLIADAS (V18.0) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Politics.xml",
        "http://rss.cnn.com/rss/edition_us.rss",
        "https://feeds.washingtonpost.com/rss/politics",
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
        "http://www.ecns.cn/rss/rss.xml",
        "https://www.chinadaily.com.cn/rss/world_rss.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/xml/rss/rss-en-all"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/",
        "https://en.mercopress.com/rss",
        "https://www.bbc.com/mundo/ultimas_noticias/index.xml", # BBC Mundo
        "https://cnnespanol.cnn.com/feed"                       # CNN Español
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.arabnews.com/cat/2/rss.xml",
        "https://www.jpost.com/rss/rssfeedsheadlines.aspx",     # Jerusalem Post
        "https://english.alarabiya.net/.mrss/en/news.xml",      # Al Arabiya
        "https://www.trtworld.com/rss"                          # TRT World
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"
    ],
    "AFRICA": [
        "https://africa.com/feed",
        "https://newafricanmagazine.com/feed",
        "http://feeds.bbci.co.uk/news/world/africa/rss.xml",
        "https://www.news24.com/news24/partners24/rss",       # News24 (Sudáfrica)
        "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf" # AllAfrica
    ]
}

class ClusterEngine:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.raw_storage = {}       
        self.clusters = defaultdict(list)
        self.hoy = datetime.datetime.now()

    def clean_json(self, text):
        try:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            clean_text = match.group(0) if match else text
            clean_text = clean_text.replace("```json", "").replace("```", "")
            return json.loads(clean_text, strict=False)
        except: return None

    # --- FASE 1: INGESTA ROBUSTA ---
    def fetch_rss_by_region(self):
        print(f"🌍 FASE 1: Ingesta Masiva (Red Expandida)...")
        regional_buffer = defaultdict(list)
        
        for region, urls in FUENTES.items():
            print(f"   -> {region}: Absorbiendo noticias...")
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    # TIMEOUT AUMENTADO A 8s para conexiones lentas en Global South
                    content = urllib.request.urlopen(req, timeout=8).read()
                    try: root = ET.fromstring(content)
                    except: continue

                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    # CAPTURAMOS HASTA 60 PARA TENER DE DONDE ELEGIR
                    for n in items[:60]: 
                        t = (n.find('title') or n.find('{*}title')).text.strip()
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l:
                            aid = hashlib.md5(t.encode('utf-8')).hexdigest()[:8]
                            self.raw_storage[aid] = {"id": aid, "title": t, "link": l, "region": region}
                            regional_buffer[region].append(f"ID:{aid} | TITULO:{t}")
                except: continue
        return regional_buffer

    def smart_scrape(self, url):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "svg", "header", "aside", "form"]): 
                    s.extract()
                return re.sub(r'\s+', ' ', soup.get_text()).strip()[:2500]
        except: return ""

    def get_area_color(self, area):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(area, "#94a3b8")
    
    def normalize_block(self, region):
        return NORMALIZER.get(region, "GLOBAL")

    # --- FASE 2: TRIAJE DE ALTO VOLUMEN ---
    def high_density_triage(self, region, titles_list):
        text_block = "\n".join(titles_list)
        
        extra_instruction = ""
        if region == "USA":
            extra_instruction = "IMPORTANTE: Para USA, INCLUYE política interna estratégica (Elecciones, Economía, Leyes) con impacto global."

        prompt = f"""
        Actúa como Analista de Inteligencia para: {region}.
        INPUT: Titulares en INGLÉS o idioma local.
        TAREA: Seleccionar entre 20 y 30 noticias. (QUEREMOS VOLUMEN ALTO).
        
        {extra_instruction}

        CRITERIOS:
        1. VOLUMEN: No seas muy estricto. Si suena mínimamente importante, SELECCIÓNALA.
        2. IMPORTANCIA: Temas geopolíticos, económicos, sociales, energéticos.
        3. IDIOMA: Lee en cualquier idioma, procesa la relevancia.
        
        CLASIFICACIÓN:
        {AREAS_DEFINICIONES}
        
        OUTPUT JSON:
        {{ "seleccionadas": [ {{ "id": "ID", "area": "AREA_EXACTA" }} ] }}
        
        TITULARES:
        {text_block}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return self.clean_json(res.text)
        except Exception as e:
            print(f"   ⚠️ Error Triaje {region}: {e}")
            return None

    # --- FASE 4: RADAR COMPARATIVO ---
    def analyze_global_proximity(self, area_name, items):
        print(f"   ⚡ Radar: Triangulando {area_name} con {len(items)} noticias...")
        
        context_data = []
        for item in items:
            context_data.append(f"ID:{item['id']} | FUENTE:{item['region']} | TEXTO:{item['full_text'][:1000]}")
        context_string = "\n---\n".join(context_data)

        prompt = f"""
        Eres PROXIMITY. Analizas el área: {area_name}.
        INPUT: Noticias de MÚLTIPLES REGIONES.
        OUTPUT: JSON en ESPAÑOL.
        
        TAREA:
        1. Determina el "CENTRO DE GRAVEDAD" (Hechos aceptados por la mayoría).
        2. Mide la distancia de CADA noticia a ese Centro.
        
        ESCALA (0-100%):
        - 100% (Consenso): Coincide con la versión aceptada por la mayoría.
        - 50% (Sesgo): Interpretación válida pero parcial.
        - 0% (Aislamiento): Realidad alternativa, propaganda.
        
        OUTPUT JSON:
        {{
            "punto_cero": "Resumen de 2 líneas del tema de consenso.",
            "particulas": [
                {{
                    "id": "ID_EXACTO",
                    "titulo": "TÍTULO TRADUCIDO AL ESPAÑOL NEUTRO",
                    "proximidad": 85.5,
                    "sesgo": "Explica la postura en 1 frase."
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
            return self.clean_json(res.text)
        except Exception as e:
            print(f"   ⚠️ Error Radar IA: {e}")
            return None

    def run(self):
        regional_data = self.fetch_rss_by_region()
        if not regional_data: return

        print(f"\n🕵️‍♂️ FASE 2 & 3: Selección de Alta Densidad y Enriquecimiento...")
        for region, titles in regional_data.items():
            if not titles: continue
            
            print(f"   -> {region}: Filtrando {len(titles)} titulares...")
            selection = self.high_density_triage(region, titles)
            
            if selection and "seleccionadas" in selection:
                count = 0
                for item in selection["seleccionadas"]:
                    aid = item.get("id")
                    area = item.get("area")
                    if aid in self.raw_storage and area in AREAS_ESTRATEGICAS:
                        meta = self.raw_storage[aid]
                        full_text = self.smart_scrape(meta['link'])
                        
                        if len(full_text) > 150: 
                            enriched_item = meta.copy()
                            enriched_item['full_text'] = full_text
                            enriched_item['area'] = area
                            self.clusters[area].append(enriched_item)
                            count += 1
                print(f"      + Agregadas {count} noticias al Observatorio.")
            time.sleep(1)

        print(f"\n🧠 FASE 4: Generación de Mapa Global (Comparativa)...")
        final_carousel = []
        for area, items in self.clusters.items():
            if len(items) < 3: continue 
            
            random.shuffle(items)
            
            # SUBIMOS CAPACIDAD DEL RADAR A 50
            analysis = self.analyze_global_proximity(area, items[:50]) 
            
            if analysis and 'particulas' in analysis:
                clean_particles = []
                for p in analysis['particulas']:
                    original = next((x for x in items if x['id'] == p['id']), None)
                    if original:
                        p['link'] = original['link']
                        p['bloque'] = self.normalize_block(original['region'])
                        try: p['proximidad'] = float(p['proximidad'])
                        except: p['proximidad'] = 50.0
                        clean_particles.append(p)
                if clean_particles:
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
        print("\n✅ CICLO COMPLETADO: Radar Calibrado y Lleno.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: ClusterEngine(key).run()

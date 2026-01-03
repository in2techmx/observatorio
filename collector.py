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
        self.raw_storage = {}       # Almacenamiento temporal de metadatos
        self.enriched_storage = {}  # Almacenamiento definitivo con Full Text
        self.clusters = defaultdict(list)
        self.hoy = datetime.datetime.now()

    # --- FASE 1: INGESTA ---
    def fetch_rss_by_region(self):
        print(f"🌍 FASE 1: Ingesta Sectorizada...")
        regional_buffer = defaultdict(list)
        
        for region, urls in FUENTES.items():
            print(f"   -> Escaneando fuentes de: {region}...")
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    content = urllib.request.urlopen(req, timeout=4).read()
                    try: root = ET.fromstring(content)
                    except: continue

                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    # Tomamos bastantes (20) para tener de donde elegir
                    for n in items[:20]:
                        t = (n.find('title') or n.find('{*}title')).text.strip()
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l:
                            aid = hashlib.md5(t.encode('utf-8')).hexdigest()[:8]
                            # Guardamos metadatos básicos
                            self.raw_storage[aid] = {"id": aid, "title": t, "link": l, "region": region}
                            # Agrupamos por región para el análisis
                            regional_buffer[region].append(f"ID:{aid} | TITULO:{t}")
                except: continue
        return regional_buffer

    # --- UTILIDADES ---
    def smart_scrape(self, url):
        """Descarga el texto completo de la noticia."""
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "svg", "header", "aside", "form", "iframe", "ads"]): 
                    s.extract()
                text = re.sub(r'\s+', ' ', soup.get_text()).strip()
                return text[:3000] # Capturamos hasta 3000 caracteres para buen contexto
        except: return ""

    def normalize_block(self, region):
        return NORMALIZER.get(region, "GLOBAL")

    def get_area_color(self, area):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(area, "#94a3b8")

    # --- FASE 2: TRIAJE INTELIGENTE (EL EDITOR) ---
    def smart_regional_triage(self, region, titles_list):
        """
        Analiza TODOS los titulares de una región en bloque.
        Busca patrones repetidos y relevancia estratégica.
        """
        text_block = "\n".join(titles_list)
        
        prompt = f"""
        Actúa como el Editor Jefe de Inteligencia para la región: {region}.
        
        TUS OBJETIVOS:
        1. Identificar las noticias más importantes basándote en la REPETICIÓN (temas que aparecen en varias fuentes) y la RELEVANCIA ESTRATÉGICA.
        2. Filtrar el ruido: Ignora deportes, crimen local menor, farándula o clima.
        3. Clasificar las seleccionadas en una de estas ÁREAS: {AREAS_ESTRATEGICAS}.
        
        INPUT (Titulares Crudos):
        {text_block}
        
        OUTPUT JSON (Selecciona las 4-6 mejores):
        {{
            "seleccionadas": [
                {{ "id": "ID_DEL_INPUT", "area": "AREA_EXACTA_DE_LA_LISTA" }}
            ]
        }}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except Exception as e:
            print(f"   ⚠️ Error en Triaje {region}: {e}")
            return None

    # --- FASE 4: ANÁLISIS DE PROXIMIDAD (EL RADAR) ---
    def analyze_proximity_context(self, area_name, items):
        """
        Analiza la distancia narrativa usando el TEXTO COMPLETO ya enriquecido.
        """
        print(f"   ⚡ Radar: Calculando vectores para {area_name} ({len(items)} items)...")
        
        context_data = []
        for item in items:
            # Usamos el texto completo que ya descargamos en la Fase 3
            context_data.append(f"ID:{item['id']} | FUENTE:{item['region']} | TEXTO_INTEGRO:{item['full_text'][:1000]}...")

        context_string = "\n---\n".join(context_data)

        prompt = f"""
        Eres PROXIMITY. Analiza este conjunto de noticias completas sobre: {area_name}.
        
        TAREA:
        Detecta las tensiones narrativas entre las diferentes regiones (USA, China, Rusia, etc.).
        
        MÉTRICA DE PROXIMIDAD (0-100%):
        - 100% (CENTRO): Hechos duros aceptados por todos los bloques (Intersección).
        - 0% (BORDE): Narrativas ideológicas aisladas, propaganda o versiones en disputa (Aislamiento).
        
        OUTPUT JSON:
        {{
            "punto_cero": "Resumen técnico de 2 líneas sobre el tema central que une a estas noticias.",
            "particulas": [
                {{
                    "id": "ID_EXACTO",
                    "titulo": "Un título sintetizado en Español neutro",
                    "proximidad": 85.5,
                    "sesgo": "Análisis de 1 frase: ¿Por qué esta noticia está cerca o lejos del consenso?"
                }}
            ]
        }}

        CORPUS DE ANÁLISIS:
        {context_string}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except Exception as e:
            print(f"   ⚠️ Error en IA Proximidad: {e}")
            return None

    # --- MOTOR PRINCIPAL ---
    def run(self):
        # 1. INGESTA
        regional_data = self.fetch_rss_by_region()
        if not regional_data: return

        # 2. TRIAJE Y ENRIQUECIMIENTO (Loop por Región)
        print(f"\n🕵️‍♂️ FASE 2 & 3: Triaje Regional y Enriquecimiento de Texto...")
        
        for region, titles in regional_data.items():
            if not titles: continue
            
            # A. Triaje (Selección de relevantes)
            print(f"   -> Analizando relevancia en {region} ({len(titles)} titulares)...")
            selection = self.smart_regional_triage(region, titles)
            
            if selection and "seleccionadas" in selection:
                # B. Enriquecimiento (Scraping de los ganadores)
                for item in selection["seleccionadas"]:
                    aid = item.get("id")
                    area = item.get("area")
                    
                    if aid in self.raw_storage and area in AREAS_ESTRATEGICAS:
                        meta = self.raw_storage[aid]
                        # Descarga de texto REAL ahora mismo
                        full_text = self.smart_scrape(meta['link'])
                        
                        if len(full_text) > 200: # Solo si pudimos bajar contenido útil
                            enriched_item = meta.copy()
                            enriched_item['full_text'] = full_text
                            enriched_item['area'] = area
                            
                            # Guardamos en la estructura final para el radar
                            self.clusters[area].append(enriched_item)
            
            time.sleep(1) # Respeto a la API

        # 3. ANÁLISIS DE PROXIMIDAD (Loop por Área Estratégica)
        print(f"\n🧠 FASE 4: Generación de Inteligencia (Global Proximity)...")
        final_carousel = []

        for area, items in self.clusters.items():
            if len(items) < 2: continue # Necesitamos al menos 2 para comparar
            
            # Analizamos todo el cluster enriquecido
            analysis = self.analyze_proximity_context(area, items)
            
            if analysis and 'particulas' in analysis:
                clean_particles = []
                for p in analysis['particulas']:
                    # Buscamos el item original para recuperar metadatos (link, region)
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

        # 4. EXPORTACIÓN
        output = {"carousel": final_carousel}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("\n✅ CICLO COMPLETADO: Inteligencia Generada con Texto Íntegro.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: ClusterEngine(key).run()

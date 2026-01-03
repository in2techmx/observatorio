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

# --- FUENTES (Monitoreo Amplio) ---
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
        self.raw_storage = {}       # Guarda TODOS los metadatos crudos por ID
        self.clusters = defaultdict(list)
        self.hoy = datetime.datetime.now()

    # --- FASE 1: INGESTA POR VOLUMEN ---
    def fetch_rss_by_region(self):
        print(f"🌍 FASE 1: Escaneando Medios por Región...")
        regional_buffer = defaultdict(list)
        
        for region, urls in FUENTES.items():
            print(f"   -> {region}: Leyendo fuentes...")
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    content = urllib.request.urlopen(req, timeout=5).read()
                    try: root = ET.fromstring(content)
                    except: continue

                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    # Leemos MUCHAS (40) para poder detectar repeticiones/frecuencia
                    for n in items[:40]:
                        t = (n.find('title') or n.find('{*}title')).text.strip()
                        l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                        if t and l:
                            # EL ID ÚNICO (ANCLAJE)
                            aid = hashlib.md5(t.encode('utf-8')).hexdigest()[:8]
                            self.raw_storage[aid] = {"id": aid, "title": t, "link": l, "region": region}
                            regional_buffer[region].append(f"ID:{aid} | TITULO:{t}")
                except: continue
        return regional_buffer

    # --- UTILIDADES ---
    def smart_scrape(self, url):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=8) as response:
                soup = BeautifulSoup(response.read(), 'html.parser')
                for s in soup(["script", "style", "nav", "footer", "svg", "header", "aside", "form", "iframe", "ads"]): 
                    s.extract()
                text = re.sub(r'\s+', ' ', soup.get_text()).strip()
                return text[:3000] # Texto suficiente para análisis profundo
        except: return ""

    def normalize_block(self, region):
        return NORMALIZER.get(region, "GLOBAL")

    def get_area_color(self, area):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(area, "#94a3b8")

    # --- FASE 2: FILTRO POR FRECUENCIA (CONSENSO REGIONAL) ---
    def frequency_based_triage(self, region, titles_list):
        """
        Aquí ocurre la magia de la relevancia.
        La IA lee 100+ titulares y solo devuelve los temas que se REPITEN
        en varios medios, descartando noticias únicas o irrelevantes.
        """
        text_block = "\n".join(titles_list)
        
        prompt = f"""
        Actúa como Jefe de Redacción para la región: {region}.
        Tienes una lista de titulares de múltiples medios (NYT, TASS, China Daily, etc).
        
        TU MISIÓN: DETECTAR LOS "HOT TOPICS" POR FRECUENCIA.
        1. Lee todos los titulares.
        2. Identifica temas que se mencionan en MÚLTIPLES titulares (repetición = relevancia).
        3. Ignora noticias que solo aparecen una vez (ruido).
        4. Selecciona EL MEJOR titular representativo para cada tema "Hot".
        5. Clasifica ese titular en una de estas ÁREAS: {AREAS_ESTRATEGICAS}.
        
        OUTPUT JSON:
        {{
            "seleccionadas": [
                {{ "id": "ID_DEL_TITULAR_ELEGIDO", "area": "AREA_ESTRATEGICA" }}
            ]
        }}
        
        TITULARES:
        {text_block}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except Exception as e:
            print(f"   ⚠️ Error Frecuencia {region}: {e}")
            return None

    # --- FASE 4: COMPARACIÓN GLOBAL (PROXIMIDAD) ---
    def analyze_global_proximity(self, area_name, items):
        """
        Toma las noticias "Ganadoras" de cada región y las enfrenta.
        Calcula qué tan cerca (consenso) o lejos (conflicto) están.
        """
        print(f"   ⚡ Radar: Triangulando posiciones para {area_name} ({len(items)} noticias)...")
        
        context_data = []
        for item in items:
            # Aquí usamos el TEXTO ÍNTEGRO descargado para comparar narrativas reales
            context_data.append(f"ID:{item['id']} | BLOQUE:{item['region']} | CONTENIDO:{item['full_text'][:1200]}")

        context_string = "\n---\n".join(context_data)

        prompt = f"""
        Eres el motor PROXIMITY. Estás analizando el Área Estratégica: {area_name}.
        Tienes noticias de bloques rivales (USA, Rusia, China, etc.).
        
        OBJETIVO: CALCULAR LA "PROXIMIDAD NARRATIVA" (0-100%).
        
        INSTRUCCIONES:
        1. Lee todas las noticias. Identifica el "Consenso Técnico" (hechos en los que todos coinciden).
        2. Para cada noticia, compárala con las demás.
        3. Asigna un valor de PROXIMIDAD:
           - 90-100%: La noticia narra hechos aceptados por todos los bloques (Centro del Radar).
           - 50%: La noticia tiene un sesgo regional moderado.
           - 0-10%: La noticia presenta una realidad alternativa o propaganda agresiva rechazada por los otros bloques (Borde del Radar).
        
        OUTPUT JSON:
        {{
            "punto_cero": "Resumen de 2 líneas del tema central que une (o divide) a estas noticias.",
            "particulas": [
                {{
                    "id": "ID_EXACTO",
                    "titulo": "Título Traducido al Español",
                    "proximidad": 85.5,
                    "sesgo": "Explicación breve de su posición (ej: 'Coincide con reporte de China', 'Aislado, niega los hechos')"
                }}
            ]
        }}

        DATA GLOBAL:
        {context_string}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'}
            )
            return json.loads(res.text.replace('```json','').replace('```',''), strict=False)
        except Exception as e:
            print(f"   ⚠️ Error Radar IA: {e}")
            return None

    # --- FLUJO DE TRABAJO ---
    def run(self):
        # 1. INGESTA MASIVA
        regional_data = self.fetch_rss_by_region()
        if not regional_data: return

        # 2. FILTRADO POR FRECUENCIA REGIONAL
        print(f"\n🕵️‍♂️ FASE 2 & 3: Detección de Temas (Frecuencia) y Descarga...")
        
        for region, titles in regional_data.items():
            if not titles: continue
            
            # Buscamos los temas "Hot" en esta región
            print(f"   -> {region}: Buscando patrones en {len(titles)} titulares...")
            selection = self.frequency_based_triage(region, titles)
            
            if selection and "seleccionadas" in selection:
                count = 0
                for item in selection["seleccionadas"]:
                    aid = item.get("id")
                    area = item.get("area")
                    
                    if aid in self.raw_storage and area in AREAS_ESTRATEGICAS:
                        # Recuperamos la metadata original usando el ID ANCLADO
                        meta = self.raw_storage[aid]
                        
                        # Descargamos el texto real para el análisis posterior
                        full_text = self.smart_scrape(meta['link'])
                        
                        if len(full_text) > 200: 
                            enriched_item = meta.copy()
                            enriched_item['full_text'] = full_text
                            enriched_item['area'] = area
                            self.clusters[area].append(enriched_item)
                            count += 1
                print(f"      + Seleccionadas {count} noticias clave.")
            time.sleep(1)

        # 3. ANÁLISIS DE PROXIMIDAD (GLOBAL)
        print(f"\n🧠 FASE 4: Generación de Mapa de Proximidad...")
        final_carousel = []

        for area, items in self.clusters.items():
            if len(items) < 3: continue # Necesitamos mínimo 3 puntos para triangular
            
            # Mezclamos para asegurar que el análisis no tenga sesgo de orden
            random.shuffle(items)
            
            # Enviamos al Radar las noticias más relevantes de cada región
            # --- AQUÍ ESTÁ EL AUMENTO DE CAPACIDAD (40 NOTICIAS) ---
            analysis = self.analyze_global_proximity(area, items[:40])
            
            if analysis and 'particulas' in analysis:
                clean_particles = []
                for p in analysis['particulas']:
                    # Re-conectamos con la metadata original usando el ID
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

        # 4. GUARDADO
        output = {"carousel": final_carousel}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
            
        print("\n✅ CICLO COMPLETADO: Radar de Proximidad Generado.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: ClusterEngine(key).run()

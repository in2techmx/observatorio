import os, json, datetime, time, ssl, urllib.request, hashlib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE ENTORNOS ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# --- ÁREAS ESTRATÉGICAS ---
AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444", 
    "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981", 
    "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6", 
    "Sociedad y Derechos": "#ec4899"
}

# --- PALETA OFICIAL ---
BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

# --- NORMALIZADOR DE BLOQUES ---
NORMALIZER = {
    "EE.UU.": "USA", "ESTADOS UNIDOS": "USA", "US": "USA",
    "RUSIA": "RUSSIA",
    "EUROPA": "EUROPE", "UE": "EUROPE", "UNION EUROPEA": "EUROPE",
    "MEDIO ORIENTE": "MID_EAST", "ORIENTE MEDIO": "MID_EAST",
    "AMERICA LATINA": "LATAM", "LATINOAMERICA": "LATAM",
    "ÁFRICA": "AFRICA",
    "ASIA": "CHINA"
}

# --- FUENTES (Todas las regiones) ---
FUENTES = {
    "USA": ["https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://www.foreignaffairs.com/rss.xml"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://globalvoices.org/section/world/russia/feed/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml", "https://globalvoices.org/section/world/east-asia/feed/"],
    "EUROPE": ["https://legrandcontinent.eu/es/feed/", "https://www.euronews.com/rss?level=vertical&name=news", "https://www.france24.com/en/rss", "https://www.dw.com/xml/rss-en-all"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", "https://elpais.com/america/rss/", "https://www.jornada.com.mx/rss/edicion.xml", "https://globalvoices.org/section/world/latin-america/feed/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.middleeasteye.net/rss", "https://www.trtworld.com/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"],
    "AFRICA": ["https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml", "https://www.africanews.com/feeds/rss"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_data(self):
        print("🌍 Capturando señales para triangulación...")
        batch_text = ""
        total_news = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=20, context=ssl_context) as resp:
                        root = ET.fromstring(resp.read())
                        for n in (root.findall('.//item') or root.findall('.//{*}entry'))[:12]:
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                                self.link_storage[art_id] = {"link": l, "title": t}
                                self.title_to_id[t] = art_id
                                batch_text += f"BLOQUE: {region} | TIT: {t}\n"
                                total_news += 1
                except: continue
        print(f"✅ Total señales: {total_news}")
        return batch_text, total_news

    def analyze(self, batch_text):
        print("🧠 IA: Ejecutando Algoritmo de Clustering Semántico (K-Means Logic)...")
        
        # PROMPT DE ALTA INGENIERÍA: LÓGICA DE VECTORES
        prompt = f"""
        Actúa como un algoritmo de clustering semántico avanzado para inteligencia OSINT.
        Tu objetivo es mapear la distancia narrativa de cada noticia respecto a un "Centroide Factual".

        PASO 1: CÁLCULO DEL CENTROIDE (PUNTO CERO)
        Lee todas las noticias y extrae los hechos duros (hard facts) indiscutibles para cada Área Estratégica.
        Este consenso define el "Punto Cero" (Proximidad = 100).

        PASO 2: CÁLCULO DE VECTORES DE DIVERGENCIA
        Para cada noticia, calcula su distancia del centroide basándote en:
        - Vector Factual: ¿Contradice hechos verificados?
        - Vector Emocional: ¿Usa lenguaje incendiario o propaganda?
        - Vector de Omisión: ¿Oculta contexto clave?

        PASO 3: ASIGNACIÓN DE PROXIMIDAD
        - 90-100: Noticia puramente factual, neutra, alineada con el consenso global.
        - 60-89: Noticia con ligero sesgo interpretativo o regional.
        - 30-59: Noticia con fuerte carga ideológica o narrativa parcial.
        - 0-29: Propaganda, desinformación o realidad alternativa (Outliers extremos).

        SALIDA: Genera un JSON estricto.
        Estructura: 'carousel' -> 'area', 'punto_cero', 'color', 'particulas'.
        
        REGLAS:
        1. TRADUCE TODO AL ESPAÑOL.
        2. Mínimo 8 partículas por área.
        3. Campo 'link': DEBE SER EL TÍTULO ORIGINAL EXACTO (para recuperar URL).
        4. Campo 'bloque': USA, CHINA, RUSSIA, EUROPE, LATAM, MID_EAST, INDIA, AFRICA.

        ÁREAS: {json.dumps(AREAS_ESTRATEGICAS)}
        CONTEXTO: {batch_text}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.15} # Temp baja para precisión matemática
            )
            return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        except Exception as e:
            print(f"Error Gemini: {e}")
            return {"carousel": []}

    def run(self):
        batch_text, total_news = self.fetch_data()
        if total_news < 10: return

        data = self.analyze(batch_text)
        
        if 'carousel' in data:
            for slide in data['carousel']:
                slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
                valid_particulas = []
                for p in slide.get('particulas', []):
                    # Recuperación de URL y Normalización
                    art_id = self.title_to_id.get(p.get('link'))
                    if art_id:
                        p['link'] = self.link_storage[art_id]['link']
                        b_raw = p.get('bloque', '').upper()
                        p['bloque'] = NORMALIZER.get(b_raw, b_raw)
                        p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#fff")
                        
                        # Asegurar proximidad float
                        try: p['proximidad'] = float(str(p.get('proximidad', 0)).replace('%', ''))
                        except: p['proximidad'] = 0
                        
                        valid_particulas.append(p)
                slide['particulas'] = valid_particulas

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Matriz K-Means generada con {total_news} nodos.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

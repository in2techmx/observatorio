import os, json, datetime, time, ssl, urllib.request, hashlib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE ENTORNOS Y RUTAS ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# --- DEFINICIÓN DE ÁREAS (Eje del Carrusel Netflix) ---
AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444", 
    "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981", 
    "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6", 
    "Sociedad y Derechos": "#ec4899"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

# --- FUENTES AMPLIADAS Y CORREGIDAS ---
FUENTES = {
    "USA": [
        "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.foreignaffairs.com/rss.xml"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://globalvoices.org/section/world/russia/feed/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.ecns.cn/rss/rss.xml",
        "https://globalvoices.org/section/world/east-asia/feed/"
    ],
    "EUROPE": [
        "https://legrandcontinent.eu/es/feed/",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/xml/rss-en-all"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/",
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://globalvoices.org/section/world/latin-america/feed/"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.trtworld.com/rss"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://globalvoices.org/section/world/south-asia/feed/"
    ],
    "AFRICA": [
        "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml",
        "https://www.africanews.com/feeds/rss",
        "https://globalvoices.org/section/world/sub-saharan-africa/feed/"
    ]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_data(self):
        print("🌍 Capturando señales multipolares...")
        batch_text = ""
        total_news = 0
        for region, urls in FUENTES.items():
            region_count = 0
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers=HEADERS)
                    with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                        root = ET.fromstring(resp.read())
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for n in items[:12]:
                            t_node = n.find('title') or n.find('{*}title')
                            l_node = n.find('link') or n.find('{*}link')
                            t = t_node.text.strip() if t_node is not None else None
                            l = (l_node.text or l_node.attrib.get('href', '')).strip() if l_node is not None else ""
                            
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                                self.link_storage[art_id] = {"link": l, "title": t}
                                self.title_to_id[t] = art_id
                                batch_text += f"BLOQUE: {region} | TIT: {t}\n"
                                total_news += 1
                                region_count += 1
                except: continue
            print(f"   ✓ {region}: {region_count} noticias.")
        return batch_text, total_news

    def analyze(self, batch_text):
        print("🧠 IA: Procesando Áreas Estratégicas y Análisis de Sesgo...")
        prompt = f"""
        Actúa como un motor de inteligencia geopolítica de vanguardia. 
        Analiza el contexto y genera un JSON donde la raíz única sea 'carousel'.
        Cada objeto dentro de 'carousel' DEBE ser una de las ÁREAS ESTRATÉGICAS especificadas.

        REGLAS DE ORO:
        1. TRADUCE TODO AL ESPAÑOL (Títulos, Sesgos y Puntos Cero).
        2. ESTRUCTURA: 'carousel' -> 'area', 'punto_cero', 'color', 'particulas'.
        3. ALTA DENSIDAD: Mínimo 5 partículas por área estratégica si el contexto lo permite.
        4. CLAVE LINK: El campo 'link' debe contener el TITULO_ORIGINAL (sin traducir) para recuperación de URL.

        LISTADO DE ÁREAS Y COLORES:
        {json.dumps(AREAS_ESTRATEGICAS, indent=2)}

        BLOQUES VÁLIDOS: USA, CHINA, RUSSIA, EUROPE, LATAM, MID_EAST, INDIA, AFRICA.

        CONTEXTO:
        {batch_text}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.1}
            )
            clean_json = res.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)
        except Exception as e:
            print(f"Error Gemini: {e}")
            return {"carousel": []}

    def run(self):
        batch_text, total_news = self.fetch_data()
        if total_news < 10:
            print("❌ Datos insuficientes para análisis."); return

        data = self.analyze(batch_text)
        
        # Post-procesamiento: Reconstrucción de Links y Colores
        if 'carousel' in data:
            for slide in data['carousel']:
                # Forzar color del área desde nuestra constante local
                slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
                
                for p in slide.get('particulas', []):
                    # Recuperar URL original usando el título que guardamos en 'link'
                    original_title = p.get('link')
                    art_id = self.title_to_id.get(original_title)
                    if art_id:
                        p['link'] = self.link_storage[art_id]['link']
                    
                    # Forzar color de bloque desde nuestra constante local
                    p['color_bloque'] = BLOQUE_COLORS.get(p.get('bloque'), "#94a3b8")

        # Guardado del snapshots y archivos históricos
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Éxito: Se procesaron {total_news} señales.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

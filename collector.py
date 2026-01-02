import os, json, datetime, time, ssl, urllib.request, hashlib
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# --- ESTÉTICA Y MAPEO ---
AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

# --- FUENTES (Híbridas y Regionales) ---
FUENTES = {
    "USA": ["https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://globalvoices.org/section/world/russia/feed/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://globalvoices.org/section/world/east-asia/feed/"],
    "EUROPE": ["https://www.france24.com/en/rss", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://legrandcontinent.eu/es/feed/", "https://globalvoices.org/section/world/latin-america/feed/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.middleeasteye.net/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://globalvoices.org/section/world/south-asia/feed/"],
    "AFRICA": ["https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://globalvoices.org/section/world/sub-saharan-africa/feed/"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_data(self):
        print("🚀 Capturando noticias para matriz de alta densidad...")
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
                        for n in items[:10]: # Aumentamos a 10 por fuente
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text if n.find('link') is not None else n.find('{*}link').attrib.get('href', '')).strip()
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                                self.link_storage[art_id] = {"link": l, "title": t}
                                self.title_to_id[t] = art_id
                                batch_text += f"BLOQUE: {region} | TIT: {t}\n"
                                total_news += 1
                                region_count += 1
                except: continue
            print(f"   ✓ {region}: {region_count} noticias capturadas.")
        return batch_text, total_news

    def analyze(self, batch_text):
        print("🧠 Generando Matriz Exhaustiva (Traducción + Densidad)...")
        prompt = f"""
        Actúa como un Analista de Inteligencia Senior. Procesa este contexto exhaustivamente.
        
        REGLAS:
        1. TRADUCE TODO AL ESPAÑOL (Títulos y Sesgos).
        2. ALTA DENSIDAD: Incluye la mayor cantidad de noticias relevantes posible (hasta 6 por área estratégica).
        3. REPRESENTATIVIDAD: Asegura que todos los bloques geopolíticos aparezcan.
        4. LINK: En el campo 'link' pon exactamente el TITULO_ORIGINAL para recuperarlo.

        ESTRUCTURA JSON:
        {{
          "carousel": [
            {{
              "area": "Nombre en Español",
              "punto_cero": "Hechos objetivos traducidos",
              "particulas": [
                {{
                  "titulo": "Título en Español",
                  "bloque": "USA, CHINA, RUSSIA, etc.",
                  "proximidad": 0-100,
                  "sesgo": "Análisis narrativo en español",
                  "link": "TITULO_ORIGINAL"
                }}
              ]
            }}
          ]
        }}
        ÁREAS: {list(AREAS_ESTRATEGICAS.keys())}
        CONTEXTO: {batch_text}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={
                    'response_mime_type': 'application/json', 
                    'temperature': 0.15,
                    'max_output_tokens': 5000 # Espacio extra para JSON grande
                }
            )
            clean_json = res.text.strip().replace('```json', '').replace('```', '')
            return json.loads(clean_json)
        except: return {"carousel": []}

    def run(self):
        batch_text, total_news = self.fetch_data()
        if total_news < 5:
            print("❌ Error: No se capturaron suficientes noticias."); return

        data = self.analyze(batch_text)
        
        if 'carousel' in data:
            for slide in data['carousel']:
                if not isinstance(slide, dict): continue
                area_name = slide.get('area', "Tendencia Global")
                slide['color'] = AREAS_ESTRATEGICAS.get(area_name, "#3b82f6")
                
                for p in slide.get('particulas', []):
                    if not isinstance(p, dict): continue
                    # Recuperación de Link Real
                    art_id = self.title_to_id.get(p.get('link'))
                    if art_id:
                        p['link'] = self.link_storage[art_id]['link']
                    p['color_bloque'] = BLOQUE_COLORS.get(p.get('bloque'), "#94a3b8")

        # Guardado de archivos
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Éxito: Matriz densa generada con {total_news} fuentes procesadas.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

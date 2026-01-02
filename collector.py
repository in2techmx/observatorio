import os, json, datetime, time, ssl, urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS Y CARPETAS ---
PATHS = {
    "diario": "historico_noticias/diario",
    "semanal": "historico_noticias/semanal",
    "mensual": "historico_noticias/mensual"
}

for p in PATHS.values():
    os.makedirs(p, exist_ok=True)

# --- CONFIGURACIÓN ESTRATÉGICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

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

FUENTES = {
    "USA": ["https://www.npr.org/rss/rss.php?id=1004", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://api.washingtontimes.com/rss/headlines/news/world/"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/", "https://en.interfax.ru/rss/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml", "https://www.globaltimes.cn/rss/index.xml"],
    "EUROPE": ["https://www.france24.com/en/rss", "https://www.dw.com/xml/rss-en-all", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss", "https://www.timesofisrael.com/feed/"],
    "INDIA": ["https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "https://www.thehindu.com/news/national/feeder/default.rss", "https://zeenews.india.com/rss/india-national-news.xml"],
    "AFRICA": ["https://www.africanews.com/feeds/rss", "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml", "https://www.theafricareport.com/feed/"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.hoy = datetime.datetime.now()
        self.es_domingo = self.hoy.weekday() == 6
        self.es_fin_mes = (self.hoy + datetime.timedelta(days=1)).day == 1

    def fetch_rss(self):
        print(f"🌍 Escaneando fuentes multipolares...")
        results = {reg: [] for reg in FUENTES.keys()}
        
        def get_feed(region, url):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    return region, [{"title": (n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')).text.strip(),
                                    "link": (n.find('link').text if n.find('link').text else n.find('link').attrib.get('href'))} 
                                   for n in items[:10] if n.find('title') is not None]
            except: return region, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_feed, reg, url) for reg, urls in FUENTES.items() for url in urls]
            for f in concurrent.futures.as_completed(futures):
                reg, news = f.result()
                results[reg].extend(news)
        return results

    def scrape_and_clean(self, articles):
        def process(item):
            try:
                req = urllib.request.Request(item['link'], headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    soup = BeautifulSoup(resp.read(), 'html.parser')
                    for s in soup(["script", "style", "nav", "footer", "ad"]): s.decompose()
                    text = " ".join([p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 60][:6])
                    item['text'] = text[:1800]
                    self.link_storage[item['title']] = item['link']
                    return item
            except: return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            return list(filter(None, executor.map(process, articles)))

    def analyze(self, context, mode="diario"):
        print(f"🧠 Sintetizando Matriz de Gravedad ({mode})...")
        prompt = f"""
        Actúa como motor de inteligencia geopolítica multipolar.
        CATEGORÍAS: {list(AREAS_ESTRATEGICAS.keys())}
        
        1. Define 'PUNTO CERO' (Consenso de hechos entre los 8 bloques).
        2. Calcula 'PROXIMIDAD' (0-100%) de cada noticia al Punto Cero.
        
        JSON: {{ "carousel": [ {{ "area": "...", "punto_cero": "...", "particulas": [ {{ "titulo": "...", "bloque": "...", "proximidad": 0-100, "sesgo": "...", "link": "LINK_REAL" }} ] }} ] }}
        CONTEXTO: {context}
        """
        res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json', 'temperature': 0.1})
        return json.loads(res.text.strip())

    def save_data(self, data):
        # El "Live" actual
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Históricos por carpeta
        diario_path = os.path.join(PATHS["diario"], f"{self.hoy.strftime('%Y-%m-%d')}.json")
        with open(diario_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        if self.es_domingo:
            sem_path = os.path.join(PATHS["semanal"], f"Semana_{self.hoy.strftime('%Y_W%U')}.json")
            with open(sem_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        if self.es_fin_mes:
            mes_path = os.path.join(PATHS["mensual"], f"Mes_{self.hoy.strftime('%Y_%m')}.json")
            with open(mes_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self):
        raw = self.fetch_rss()
        batch_text = ""
        
        for region, items in raw.items():
            if not items: continue
            # Triaje por IA (Selecciona las 2 más potentes)
            titles = "\n".join([f"[{i}] {x['title']}" for i, x in enumerate(items[:15])])
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=f"Índices de las 2 noticias más relevantes para {region}:\n{titles}", config={'response_mime_type': 'application/json'})
            try:
                idxs = json.loads(res.text.strip()).get("idx", [0, 1])
                selected = [items[i] for i in idxs if i < len(items)]
                enriched = self.scrape_and_clean(selected)
                for e in enriched:
                    batch_text += f"REGION: {region} | TITULO: {e['title']} | TEXTO: {e['text']}\n\n"
            except: continue

        final_json = self.analyze(batch_text)
        
        # Inyectar colores y validar links finales
        for slide in final_json['carousel']:
            slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#ffffff")
            for p in slide['particulas']:
                p['link'] = self.link_storage.get(p['titulo'], p['link'])
                p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#ffffff")

        self.save_data(final_json)
        print("✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()
    else: print("Error: GEMINI_API_KEY no encontrada.")

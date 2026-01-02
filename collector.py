import os, json, datetime, time, ssl, urllib.request
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS ---
PATHS = {
    "diario": "historico_noticias/diario",
    "semanal": "historico_noticias/semanal",
    "mensual": "historico_noticias/mensual"
}

for p in PATHS.values():
    os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()

# --- CONFIGURACIÓN ESTRATÉGICA ---
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
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://www.npr.org/rss/rss.php?id=1004", "https://api.washingtontimes.com/rss/headlines/news/world/"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/", "https://en.interfax.ru/rss/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml", "https://www.globaltimes.cn/rss/index.xml"],
    "EUROPE": ["https://www.dw.com/xml/rss-en-all", "https://www.france24.com/en/rss", "https://www.euronews.com/rss?level=vertical&name=news"],
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
        print(f"🌍 Escaneando {sum(len(v) for v in FUENTES.values())} fuentes multipolares...")
        results = {reg: [] for reg in FUENTES.keys()}
        
        def get_feed(region, url):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    
                    extracted = []
                    for n in items[:8]:
                        t_node = n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')
                        t = t_node.text.strip() if t_node is not None and t_node.text else None
                        
                        l_node = n.find('link') or n.find('{http://www.w3.org/2005/Atom}link')
                        l = None
                        if l_node is not None:
                            l = l_node.text.strip() if l_node.text else l_node.attrib.get('href')
                        
                        d_node = n.find('description') or n.find('{http://www.w3.org/2005/Atom}summary')
                        d = d_node.text.strip() if d_node is not None and d_node.text else ""

                        if t and l:
                            extracted.append({"title": t, "link": l, "summary": d})
                            self.link_storage[t] = l
                    return region, extracted
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
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(item['link'], headers=headers)
                with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
                    soup = BeautifulSoup(resp.read(), 'html.parser')
                    for s in soup(["script", "style", "nav", "footer", "ad", "header", "form"]): s.decompose()
                    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 65]
                    text = " ".join(paragraphs[:6])[:1800]
                    
                    # Salvavidas: si el scraping falla o es muy corto, usar el summary del RSS
                    item['text'] = text if len(text) > 150 else item.get('summary', 'Contenido no disponible para lectura profunda.')
                    return item
            except:
                if len(item.get('summary', '')) > 50:
                    item['text'] = item['summary']
                    return item
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            return list(filter(None, executor.map(process, articles)))

    def analyze(self, context):
        if not context or len(context) < 300:
            print("❌ ERROR: No hay suficiente contenido real. Abortando.")
            exit(1)

        print(f"🧠 Generando Matriz de Gravedad...")
        prompt = f"""
        Actúa como motor de inteligencia geopolítica multipolar. 
        CONTEXTO REAL: {context}
        REGLAS:
        1. Prohibido inventar noticias.
        2. Usa el TITULO EXACTO de la noticia para el campo 'link'.
        CATEGORÍAS: {list(AREAS_ESTRATEGICAS.keys())}
        JSON: {{ "carousel": [ {{ "area": "...", "punto_cero": "...", "particulas": [ {{ "titulo": "...", "bloque": "...", "proximidad": 0-100, "sesgo": "...", "link": "TITULO_EXACTO" }} ] }} ] }}
        """
        res = self.client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt, 
            config={'response_mime_type': 'application/json', 'temperature': 0.1}
        )
        return json.loads(res.text.strip())

    def run(self):
        raw = self.fetch_rss()
        batch_text = ""
        noticias_ok = 0

        for region, items in raw.items():
            if not items: continue
            titles = "\n".join([f"[{i}] {x['title']}" for i, x in enumerate(items[:15])])
            try:
                triaje = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Selecciona índices de las 2 noticias más relevantes para {region}. Solo JSON: {{'idx': [n, n]}}\n{titles}",
                    config={'response_mime_type': 'application/json'}
                )
                idxs = json.loads(triaje.text.strip()).get("idx", [0, 1])
                selected = [items[i] for i in idxs if i < len(items)]
                enriched = self.scrape_and_clean(selected)
                
                for e in enriched:
                    batch_text += f"BLOQUE: {region} | TITULO: {e['title']} | TEXTO: {e['text']}\n\n"
                    noticias_ok += 1
            except: continue

        print(f"📊 Análisis iniciado con {noticias_ok} noticias verificadas.")
        final_json = self.analyze(batch_text)
        
        for slide in final_json.get('carousel', []):
            slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#ffffff")
            for p in slide.get('particulas', []):
                p['link'] = self.link_storage.get(p['titulo'], p['link'])
                p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#94a3b8")

        # Guardado
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=4, ensure_ascii=False)
        
        # Histórico
        fecha = self.hoy.strftime('%Y-%m-%d')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=4, ensure_ascii=False)

        print("✅ Proceso completado exitosamente.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()
    else: print("❌ Error: API KEY no encontrada.")

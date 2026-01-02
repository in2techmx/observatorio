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

# --- CONFIGURACIÓN ESTRATÉGICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

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

# --- 24 FUENTES ESTRATÉGICAS (3 POR REGIÓN) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.npr.org/rss/rss.php?id=1004",
        "https://api.washingtontimes.com/rss/headlines/news/world/"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "https://rt.com/rss/news/",
        "https://en.interfax.ru/rss/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.ecns.cn/rss/rss.xml",
        "https://www.globaltimes.cn/rss/index.xml"
    ],
    "EUROPE": [
        "https://www.dw.com/xml/rss-en-all",
        "https://www.france24.com/en/rss",
        "https://www.euronews.com/rss?level=vertical&name=news"
    ],
    "LATAM": [
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://www.clarin.com/rss/mundo/",
        "https://www.infobae.com/america/rss/"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss",
        "https://www.timesofisrael.com/feed/"
    ],
    "INDIA": [
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://zeenews.india.com/rss/india-national-news.xml"
    ],
    "AFRICA": [
        "https://www.africanews.com/feeds/rss",
        "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml",
        "https://www.theafricareport.com/feed/"
    ]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {} # Almacén para URLs originales
        self.hoy = datetime.datetime.now()
        self.es_domingo = self.hoy.weekday() == 6
        self.es_fin_mes = (self.hoy + datetime.timedelta(days=1)).day == 1

    def fetch_rss(self):
        print(f"🌍 Escaneando {sum(len(v) for v in FUENTES.values())} fuentes multipolares...")
        results = {reg: [] for reg in FUENTES.keys()}
        
        def get_feed(region, url):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    extracted = []
                    for n in items[:8]:
                        title_node = n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')
                        link_node = n.find('link') or n.find('{http://www.w3.org/2005/Atom}link')
                        
                        if title_node is not None and title_node.text:
                            t = title_node.text.strip()
                            # Extraer link de texto o de atributo href (para Atom)
                            l = link_node.text if link_node is not None and link_node.text else (link_node.attrib.get('href') if link_node is not None else "")
                            if l:
                                extracted.append({"title": t, "link": l})
                                self.link_storage[t] = l # Blindaje preventivo
                    return region, extracted
            except Exception as e:
                return region, []

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
                with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
                    soup = BeautifulSoup(resp.read(), 'html.parser')
                    for s in soup(["script", "style", "nav", "footer", "ad", "header"]): s.decompose()
                    paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 70]
                    item['text'] = " ".join(paragraphs[:6])[:2000]
                    return item
            except: return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            return list(filter(None, executor.map(process, articles)))

    def analyze(self, context):
        if not context or len(context) < 500:
            print("❌ ERROR: No hay suficiente contenido real para analizar. Abortando para evitar alucinaciones.")
            exit(1)

        print(f"🧠 Generando Matriz de Gravedad Geopolítica...")
        prompt = f"""
        Actúa como motor de inteligencia geopolítica de vanguardia. 
        CONTEXTO REAL PROPORCIONADO: {context}

        INSTRUCCIONES CRÍTICAS:
        1. NO INVENTES DATOS. Si el contexto es insuficiente para un área, déjala vacía.
        2. 'PUNTO CERO': Es el hecho central donde las fuentes de distintos bloques coinciden.
        3. 'PROXIMIDAD': Qué tan cerca está la versión de esa noticia del Punto Cero oficial.
        4. Para el campo 'link', escribe exactamente el TITULO de la noticia para mapeo posterior.

        FORMATO JSON REQUERIDO:
        {{
          "carousel": [
            {{
              "area": "Nombre de Categoría de AREAS_ESTRATEGICAS",
              "punto_cero": "Resumen neutral del consenso global",
              "particulas": [
                {{
                  "titulo": "Título de la noticia",
                  "bloque": "Nombre del bloque (RUSSIA, USA, CHINA, etc.)",
                  "proximidad": 0-100,
                  "sesgo": "Breve análisis de la inclinación editorial",
                  "link": "TITULO_EXACTO"
                }}
              ]
            }}
          ]
        }}
        """
        res = self.client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt, 
            config={'response_mime_type': 'application/json', 'temperature': 0.1}
        )
        return json.loads(res.text.strip())

    def save_data(self, data):
        # Guardado del Live
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        # Guardado Histórico
        fecha_str = self.hoy.strftime('%Y-%m-%d')
        with open(os.path.join(PATHS["diario"], f"{fecha_str}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        if self.es_domingo:
            with open(os.path.join(PATHS["semanal"], f"Semana_{self.hoy.strftime('%Y_W%U')}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        if self.es_fin_mes:
            with open(os.path.join(PATHS["mensual"], f"Mes_{self.hoy.strftime('%Y_%m')}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

    def run(self):
        raw = self.fetch_rss()
        batch_text = ""
        noticias_reales = 0

        for region, items in raw.items():
            if not items: continue
            
            # Triaje: Gemini selecciona las 2 más impactantes de las 3 fuentes del bloque
            titles_list = "\n".join([f"[{i}] {x['title']}" for i, x in enumerate(items[:20])])
            try:
                triaje_res = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"Selecciona los índices de las 2 noticias geopolíticas más importantes de esta lista para {region}. Responde solo JSON: {{'idx': [n, n]}}\n{titles_list}",
                    config={'response_mime_type': 'application/json'}
                )
                idxs = json.loads(triaje_res.text.strip()).get("idx", [0, 1])
                selected = [items[i] for i in idxs if i < len(items)]
                enriched = self.scrape_and_clean(selected)
                
                for e in enriched:
                    batch_text += f"BLOQUE: {region} | TITULO: {e['title']} | TEXTO: {e['text']}\n\n"
                    noticias_reales += 1
            except: continue

        print(f"📊 Análisis iniciado con {noticias_reales} noticias verificadas.")
        final_json = self.analyze(batch_text)
        
        # Post-procesamiento: Colores y restauración de Links Reales
        for slide in final_json.get('carousel', []):
            slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#ffffff")
            for p in slide.get('particulas', []):
                # Restaurar el link original del almacenamiento usando el título como clave
                p['link'] = self.link_storage.get(p['titulo'], p['link'])
                p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#94a3b8")

        self.save_data(final_json)
        print(f"✅ Proceso completado. Archivo gravity_carousel.json actualizado.")

if __name__ == "__main__":
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        GeopoliticalCollector(api_key).run()
    else:
        print("❌ ERROR: No se encontró la variable GEMINI_API_KEY.")

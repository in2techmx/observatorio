import os, json, datetime, time, ssl, urllib.request, hashlib
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS ---
PATHS = {"diario": "historico_noticias/diario", "semanal": "historico_noticias/semanal", "mensual": "historico_noticias/mensual"}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()

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

# [NUEVO] Fuentes de alta disponibilidad (Google News como respaldo)
FUENTES = {
    "USA": ["https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "RUSSIA": ["https://news.google.com/rss/search?q=Russia+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://tass.com/rss/v2.xml"],
    "CHINA": ["https://news.google.com/rss/search?q=China+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en", "https://www.scmp.com/rss/91/feed"],
    "EUROPE": ["https://news.google.com/rss/search?q=Europe+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "LATAM": ["https://news.google.com/rss/search?q=Latin+America+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "MID_EAST": ["https://news.google.com/rss/search?q=Middle+East+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "INDIA": ["https://news.google.com/rss/search?q=India+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "AFRICA": ["https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()
        self.stats = {"total_fetched": 0, "processed": 0, "errors": 0}

    def fetch_rss(self):
        print(f"🌍 Escaneando fuentes de alta disponibilidad...")
        results = {reg: [] for reg in FUENTES.keys()}
        
        def get_feed(region, url):
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=20, context=ssl_context) as resp:
                    raw_data = resp.read()
                    content = raw_data.decode('utf-8', errors='replace')
                    root = ET.fromstring(content)
                    items = root.findall('.//item') or root.findall('.//{*}entry')
                    
                    extracted = []
                    for n in items[:15]:
                        t_node = n.find('title') or n.find('{*}title')
                        l_node = n.find('link') or n.find('{*}link')
                        d_node = n.find('description') or n.find('{*}summary')
                        
                        title = t_node.text.strip() if t_node is not None and t_node.text else None
                        link = (l_node.text or l_node.attrib.get('href', '')).strip() if l_node is not None else ""
                        description = d_node.text.strip() if d_node is not None and d_node.text else ""
                        
                        if title and link:
                            article_id = hashlib.md5(title.encode()).hexdigest()[:10]
                            article_data = {"id": article_id, "title": title, "link": link, "summary": description[:600], "region": region}
                            self.link_storage[article_id] = article_data
                            self.title_to_id[title] = article_id
                            extracted.append(article_data)
                    return region, extracted
            except Exception as e:
                return region, []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(get_feed, reg, url) for reg, urls in FUENTES.items() for url in urls]
            for f in concurrent.futures.as_completed(futures):
                region, news = f.result()
                results[region].extend(news)
                self.stats["total_fetched"] += len(news)
        return results

    def scrape_and_clean(self, articles):
        def process(article):
            # Si es Google News, el summary suele ser inútil, pero el link es un redirect. 
            # Intentamos usar el summary si es lo suficientemente largo.
            if len(article.get('summary', '')) > 300:
                article['text'] = article['summary']
                return article
            article['text'] = article['title'] # Fallback mínimo
            return article

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            return list(executor.map(process, articles))

    def select_best_articles(self, region, items):
        if not items: return []
        # Triaje rápido por títulos para no saturar API
        titles_list = "\n".join([f"[{i}] {item['title']}" for i, item in enumerate(items[:15])])
        prompt = f"Como experto en {region}, elige los índices de las 2 noticias con más impacto geopolítico. Responde JSON {{'indices': [n, n]}}:\n{titles_list}"
        try:
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
            indices = json.loads(res.text.strip()).get("indices", [0, 1])
            return [items[i] for i in indices if i < len(items)]
        except: return items[:2]

    def analyze(self, context):
        print(f"🧠 Generando Matriz Global...")
        prompt = f"Analiza estas noticias y genera una matriz geopolítica. JSON exacto: {{'carousel': [...]}}. CONTEXTO: {context}"
        try:
            res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
            return json.loads(res.text.strip())
        except: return {"carousel": []}

    def run(self):
        raw_articles = self.fetch_rss()
        batch_text = ""
        all_selected = []
        
        for region, items in raw_articles.items():
            if not items: continue
            selected = self.select_best_articles(region, items)
            for s in selected:
                batch_text += f"REGION: {region} | TITULO: {s['title']} | INFO: {s['summary']}\n\n"
                all_selected.append(s)
        
        if not all_selected:
            print("❌ No se obtuvieron noticias. Revisa la conexión."); return

        final_json = self.analyze(batch_text)
        
        # Enriquecer JSON final con colores y links
        for slide in final_json.get('carousel', []):
            slide['color'] = AREAS_ESTRATEGICAS.get(slide['area'], "#3b82f6")
            for p in slide.get('particulas', []):
                art_id = self.title_to_id.get(p['titulo'])
                if art_id:
                    p['link'] = self.link_storage[art_id]['link']
                    p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#94a3b8")

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
        print(f"✅ Proceso completado. {len(all_selected)} noticias analizadas.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()
    else: print("❌ API KEY Missing.")

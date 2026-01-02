import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, glob
import xml.etree.ElementTree as ET
from google import genai

# --- CONFIGURACIÓN ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

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

NORMALIZER = {
    "EE.UU.": "USA", "ESTADOS UNIDOS": "USA", "US": "USA", "RUSIA": "RUSSIA",
    "EUROPA": "EUROPE", "UE": "EUROPE", "MEDIO ORIENTE": "MID_EAST",
    "AMERICA LATINA": "LATAM", "LATINOAMERICA": "LATAM", "ÁFRICA": "AFRICA", "ASIA": "CHINA"
}

FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://www.foreignaffairs.com/rss.xml", "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "EUROPE": ["https://legrandcontinent.eu/es/feed/", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://elpais.com/america/rss/", "https://www.jornada.com.mx/rss/edicion.xml"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.middleeasteye.net/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss"],
    "AFRICA": ["https://allafrica.com/tools/headlines/rdf/latestnews/index.xml", "https://www.africanews.com/feeds/rss"]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    # --- 1. RESILIENCIA Y SEGURIDAD (Fetch Seguro con Retries) ---
    def fetch_with_retry(self, url, retries=3):
        for attempt in range(retries):
            try:
                # Intento Seguro (SSL Verificado)
                req = urllib.request.Request(url, headers=HEADERS)
                return urllib.request.urlopen(req, timeout=15).read()
            except urllib.error.URLError as e:
                # Fallback: Si es error de certificado, usamos contexto inseguro
                if "certificate" in str(e).lower() or "ssl" in str(e).lower():
                    try:
                        ctx = ssl._create_unverified_context()
                        return urllib.request.urlopen(req, timeout=15, context=ctx).read()
                    except: pass
                
                # Si no es SSL, esperamos y reintentamos (Backoff exponencial)
                time.sleep(1.5 * (attempt + 1))
            except Exception:
                time.sleep(1)
        return None

    # --- 2. CONTEXTO TEMPORAL (Leer el pasado) ---
    def get_historical_context(self):
        try:
            files = sorted(glob.glob(os.path.join(PATHS["diario"], "*.json")))
            if not files: return "No hay datos previos. Este es el día 1 del análisis."
            
            last_file = files[-1]
            with open(last_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            resumen = "CONTEXTO DE AYER:\n"
            for slide in data.get('carousel', [])[:3]: # Solo las primeras 3 áreas para no saturar
                resumen += f"- {slide.get('area')}: {slide.get('punto_cero')}\n"
            return resumen
        except:
            return "Error leyendo historial."

    def fetch_data(self):
        print("🌍 Capturando señales (Modo Resiliente)...")
        batch_text = ""
        total_news = 0
        for region, urls in FUENTES.items():
            region_count = 0
            for url in urls:
                content = self.fetch_with_retry(url)
                if content:
                    try:
                        root = ET.fromstring(content)
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for n in items[:10]:
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                                self.link_storage[art_id] = {"link": l, "title": t}
                                self.title_to_id[t] = art_id
                                batch_text += f"BLOQUE: {region} | TIT: {t}\n"
                                total_news += 1
                                region_count += 1
                    except: continue
            print(f"   ✓ {region}: {region_count} señales.")
        return batch_text, total_news

    def analyze(self, batch_text, historical_context):
        print("🧠 IA: Triangulando Vectores con Contexto Evolutivo...")
        
        prompt = f"""
        Actúa como motor de inteligencia OSINT.
        
        {historical_context}
        
        CONTEXTO ACTUAL (HOY):
        {batch_text}

        OBJETIVO:
        1. Compara el contexto de ayer con el de hoy. ¿Ha subido la tensión?
        2. Calcula la proximidad factual usando K-Means lógico (Hechos vs Emoción).
        3. Genera el JSON 'carousel'.

        REGLAS:
        - Traduce al Español.
        - Mínimo 6 partículas por área.
        - Link = Título original.
        - Bloques válidos: USA, CHINA, RUSSIA, EUROPE, LATAM, MID_EAST, INDIA, AFRICA.
        
        ÁREAS: {json.dumps(AREAS_ESTRATEGICAS)}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.15}
            )
            return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        except Exception as e:
            print(f"Error IA: {e}")
            return None

    # --- 3. MÉTRICAS DE CALIDAD (Validación de Output) ---
    def validate_data(self, data):
        if not data or 'carousel' not in data: return False
        if len(data['carousel']) < 4: 
            print("⚠️ Calidad baja: Pocas áreas generadas.")
            return False
        
        total_particles = sum(len(c.get('particulas', [])) for c in data['carousel'])
        if total_particles < 20:
            print("⚠️ Calidad baja: Pocas noticias totales.")
            return False
            
        print(f"🛡️ Calidad Aprobada: {len(data['carousel'])} áreas, {total_particles} nodos.")
        return True

    def run(self):
        batch_text, total_news = self.fetch_data()
        if total_news < 10: return

        # Obtenemos contexto del pasado para alimentar el presente
        historia = self.get_historical_context()
        
        data = self.analyze(batch_text, historia)
        
        # Validamos antes de procesar
        if not self.validate_data(data):
            print("❌ Abortando guardado por baja calidad de IA.")
            return

        # Post-procesamiento
        for slide in data['carousel']:
            slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
            valid_p = []
            for p in slide.get('particulas', []):
                art_id = self.title_to_id.get(p.get('link'))
                if art_id:
                    p['link'] = self.link_storage[art_id]['link']
                    b_raw = p.get('bloque', '').upper()
                    p['bloque'] = NORMALIZER.get(b_raw, b_raw)
                    p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#fff")
                    try: p['proximidad'] = float(str(p.get('proximidad', 0)).replace('%', ''))
                    except: p['proximidad'] = 0
                    valid_p.append(p)
            slide['particulas'] = valid_p

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"✅ Sistema actualizado con éxito. {total_news} señales procesadas.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

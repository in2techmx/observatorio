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
    "EE.UU.": "USA", "ESTADOS UNIDOS": "USA", "US": "USA", 
    "RUSIA": "RUSSIA", "RUSSIA": "RUSSIA",
    "EUROPA": "EUROPE", "UE": "EUROPE", "UNION EUROPEA": "EUROPE",
    "MEDIO ORIENTE": "MID_EAST", "ORIENTE MEDIO": "MID_EAST",
    "AMERICA LATINA": "LATAM", "LATINOAMERICA": "LATAM",
    "ÁFRICA": "AFRICA", "AFRICA": "AFRICA",
    "ASIA": "CHINA", "CHINA": "CHINA",
    "INDIA": "INDIA"
}

# --- FUENTES COMPLETAS (África Corregida + Resto) ---
FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "EUROPE": ["https://legrandcontinent.eu/es/feed/", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://elpais.com/america/rss/", "https://www.jornada.com.mx/rss/edicion.xml"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.middleeasteye.net/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss"],
    # ÁFRICA: Mix Blindado
    "AFRICA": [
        "https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en",
        "https://africa.com/feed",
        "https://newafricanmagazine.com/feed",
        "https://theconversation.com/africa/articles.atom"
    ]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_with_retry(self, url, retries=2):
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                return urllib.request.urlopen(req, timeout=10).read()
            except urllib.error.URLError as e:
                if "certificate" in str(e).lower() or "ssl" in str(e).lower():
                    try:
                        ctx = ssl._create_unverified_context()
                        return urllib.request.urlopen(req, timeout=10, context=ctx).read()
                    except: pass
                time.sleep(1)
            except: time.sleep(1)
        return None

    def fetch_data(self):
        print("🌍 Capturando señales...")
        raw_news_lines = [] # Lista en lugar de texto gigante
        total_news = 0
        for region, urls in FUENTES.items():
            region_count = 0
            for url in urls:
                content = self.fetch_with_retry(url)
                if content:
                    try:
                        root = ET.fromstring(content)
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for n in items[:8]: 
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:10]
                                self.link_storage[art_id] = {"link": l, "title": t, "region_origen": region}
                                self.title_to_id[t] = art_id
                                # Guardamos como línea individual
                                raw_news_lines.append(f"BLOQUE_ORIGEN: {region} | TIT: {t}")
                                total_news += 1
                                region_count += 1
                    except: continue
            print(f"   ✓ {region}: {region_count}")
        return raw_news_lines, total_news

    def analyze_batch(self, news_chunk):
        # Función auxiliar para procesar un trozo pequeño
        batch_text = "\n".join(news_chunk)
        prompt = f"""
        Actúa como analista de inteligencia. Clasifica estas noticias.
        Genera un JSON con la estructura 'carousel'.
        
        ÁREAS: {list(AREAS_ESTRATEGICAS.keys())}

        REGLAS CRÍTICAS (STRICT MODE):
        1. 'link': COPIA EXACTAMENTE el título.
        2. 'bloque': Infiérelo del "BLOQUE_ORIGEN".
        3. 'proximidad': FLOAT 0.0 - 100.0. (Evita 0.0 si es posible).
        4. 'sesgo': 5 palabras máximo.
        5. IMPORTANTE: Escapa comillas dobles dentro de los textos para no romper el JSON.

        INPUT:
        {batch_text}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.1}
            )
            return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        except Exception as e:
            print(f"⚠️ Error en lote: {e}")
            return None

    def run_analysis_pipeline(self, raw_news_lines):
        print(f"🧠 IA: Iniciando procesamiento por lotes ({len(raw_news_lines)} señales)...")
        
        # 1. Dividir en lotes de 25 noticias (Seguridad Anti-Crash)
        chunk_size = 25
        chunks = [raw_news_lines[i:i + chunk_size] for i in range(0, len(raw_news_lines), chunk_size)]
        
        merged_carousel = {} # Diccionario para unir resultados { "Area": { ... } }

        # 2. Procesar cada lote
        for i, chunk in enumerate(chunks):
            print(f"   ↳ Procesando Lote {i+1}/{len(chunks)}...")
            result = self.analyze_batch(chunk)
            
            if result and 'carousel' in result:
                for item in result['carousel']:
                    area_name = item.get('area')
                    if not area_name: continue
                    
                    if area_name not in merged_carousel:
                        merged_carousel[area_name] = {
                            "area": area_name,
                            "punto_cero": item.get('punto_cero', "Análisis agregado."),
                            "color": AREAS_ESTRATEGICAS.get(area_name, "#3b82f6"),
                            "particulas": []
                        }
                    # Fusionar partículas
                    merged_carousel[area_name]['particulas'].extend(item.get('particulas', []))
            time.sleep(1) # Pausa para no saturar API

        # 3. Convertir de vuelta a lista
        return {"carousel": list(merged_carousel.values())}

    def validate_and_fix(self, data):
        if not data or 'carousel' not in data: return False
        
        for slide in data['carousel']:
            slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
            
            # Asegurar Punto Cero
            if len(slide.get('punto_cero', '')) < 10:
                slide['punto_cero'] = "Múltiples focos de atención detectados en esta área estratégica."

            valid_p = []
            for p in slide.get('particulas', []):
                original_title = p.get('link')
                # Búsqueda robusta del ID
                art_id = self.title_to_id.get(original_title)
                
                if art_id:
                    meta = self.link_storage[art_id]
                    p['link'] = meta['link']
                    
                    # Corrección Bloque
                    b_ia = str(p.get('bloque', '')).upper()
                    b_real = meta.get('region_origen', 'GLOBAL')
                    final_block = NORMALIZER.get(b_ia, b_real)
                    if final_block not in BLOQUE_COLORS: final_block = b_real
                    
                    p['bloque'] = final_block
                    p['color_bloque'] = BLOQUE_COLORS.get(final_block, "#94a3b8")

                    # Auditoría Proximidad
                    try:
                        clean_v = str(p.get('proximidad', '0')).replace('%', '').strip()
                        val = float(clean_v)
                        p['proximidad'] = round(val, 1)
                    except:
                        print(f"⚠️ [DEBUG] Fallo Proximidad: '{p.get('titulo')}' -> 0.0")
                        p['proximidad'] = 0.0 

                    if not p.get('sesgo'): p['sesgo'] = "Sin análisis."
                    valid_p.append(p)
            
            slide['particulas'] = valid_p
        return True

    def run(self):
        # PASO 1: Captura (Lista de líneas)
        raw_news_lines, total_news = self.fetch_data()
        if total_news < 5: return

        # PASO 2: Análisis por Lotes (Merge)
        data = self.run_analysis_pipeline(raw_news_lines)
        
        # PASO 3: Validación y Guardado
        if self.validate_and_fix(data):
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
            with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Éxito: {total_news} señales procesadas en lotes.")
        else:
            print("❌ Error crítico en validación post-merge.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, glob
import xml.etree.ElementTree as ET
from google import genai

# --- CONFIGURACIÓN DE CARPETAS ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

# Headers para evitar bloqueos 403
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}

# --- DEFINICIONES VISUALES ---
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
    "EE.UU.": "USA", "ESTADOS UNIDOS": "USA", "US": "USA", "UNITED STATES": "USA",
    "RUSIA": "RUSSIA", "RUSSIAN FEDERATION": "RUSSIA", "MOSCU": "RUSSIA",
    "EUROPA": "EUROPE", "UE": "EUROPE", "UK": "EUROPE", "GERMANY": "EUROPE", "FRANCE": "EUROPE",
    "MEDIO ORIENTE": "MID_EAST", "ORIENTE MEDIO": "MID_EAST", "ISRAEL": "MID_EAST", "IRAN": "MID_EAST",
    "AMERICA LATINA": "LATAM", "LATINOAMERICA": "LATAM", "BRAZIL": "LATAM", "MEXICO": "LATAM",
    "ÁFRICA": "AFRICA", "AFRICA": "AFRICA", "NIGERIA": "AFRICA", "SOUTH AFRICA": "AFRICA",
    "ASIA": "CHINA", "CHINA": "CHINA", "BEIJING": "CHINA",
    "INDIA": "INDIA", "NEW DELHI": "INDIA"
}

# --- RED DE FUENTES EXPANDIDA (v8.0) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.washingtonpost.com/rss/world",
        "http://rss.cnn.com/rss/edition_world.rss",
        "https://www.politico.com/rss/politicopicks.xml",
        "https://www.foreignaffairs.com/rss.xml",
        "https://news.google.com/rss/search?q=USA+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news",
        "https://globalvoices.org/section/world/russia/feed/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "http://www.xinhuanet.com/english/rss/world.xml",
        "http://www.ecns.cn/rss/rss.xml",
        "https://globalvoices.org/section/world/east-asia/feed/"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://legrandcontinent.eu/es/feed/",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.france24.com/en/rss",
        "https://www.dw.com/xml/rss-en-all"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/",
        "https://en.mercopress.com/rss",
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://www.bbcmundo.com/pasoapaso/rss.xml"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss",
        "https://www.arabnews.com/cat/2/rss.xml",
        "https://www.trtworld.com/rss"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.ndtv.com/rss/top-stories.xml"
    ],
    "AFRICA": [
        "https://news.google.com/rss/search?q=Africa+geopolitics+when:24h&hl=en-US&gl=US&ceid=US:en",
        "https://africa.com/feed",
        "https://newafricanmagazine.com/feed",
        "https://theconversation.com/africa/articles.atom",
        "http://feeds.bbci.co.uk/news/world/africa/rss.xml"
    ]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {} # Almacén maestro de metadatos
        self.hoy = datetime.datetime.now()

    def fetch_with_retry(self, url, retries=2):
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                return urllib.request.urlopen(req, timeout=10).read()
            except urllib.error.URLError as e:
                # Bypass SSL errors
                if "certificate" in str(e).lower() or "ssl" in str(e).lower():
                    try:
                        ctx = ssl._create_unverified_context()
                        return urllib.request.urlopen(req, timeout=10, context=ctx).read()
                    except: pass
                time.sleep(1)
            except: time.sleep(1)
        return None

    def fetch_data(self):
        print("🌍 Iniciando captura masiva de señales...")
        raw_news_lines = [] 
        total_news = 0
        
        for region, urls in FUENTES.items():
            region_count = 0
            for url in urls:
                content = self.fetch_with_retry(url)
                if content:
                    try:
                        root = ET.fromstring(content)
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        # Capturamos hasta 10 noticias por fuente para tener volumen
                        for n in items[:10]: 
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                            if t and l:
                                # GENERACIÓN DE ID ÚNICO (CRÍTICO)
                                art_id = hashlib.md5(t.encode()).hexdigest()[:8]
                                
                                # Guardamos metadatos reales
                                self.link_storage[art_id] = {"link": l, "title": t, "region_origen": region}
                                
                                # Preparamos línea para la IA con el ID
                                raw_news_lines.append(f"ID: {art_id} | ORIGEN: {region} | TIT: {t}")
                                total_news += 1
                                region_count += 1
                    except: continue
            print(f"   ✓ {region}: {region_count} señales.")
        return raw_news_lines, total_news

    def analyze_batch(self, news_chunk):
        batch_text = "\n".join(news_chunk)
        prompt = f"""
        Actúa como analista de inteligencia. Clasifica estas noticias en ÁREAS ESTRATÉGICAS.
        
        ÁREAS: {list(AREAS_ESTRATEGICAS.keys())}

        REGLAS OBLIGATORIAS (SISTEMA DE IDs):
        1. 'id': COPIA EXACTAMENTE el código 'ID' del input (ej. a1b2c3d4). NO inventes IDs.
        2. 'titulo': Traduce el título al Español.
        3. 'bloque': Infiérelo del "ORIGEN" o del contenido (USA, CHINA, RUSSIA, etc).
        4. 'proximidad': FLOAT 0.0 - 100.0 (Evita 0.0). 
           - 90-100: Hecho factual verificado.
           - 50-70: Opinión / Interpretación.
           - 10-30: Propaganda / Especulación.
        5. 'sesgo': 5 palabras máximo.

        INPUT A PROCESAR:
        {batch_text}

        FORMATO JSON DE SALIDA:
        {{
            "carousel": [
                {{
                    "area": "Nombre del Área",
                    "punto_cero": "Resumen factual de 2 líneas.",
                    "particulas": [
                        {{ "id": "CODIGO_ID", "titulo": "...", "bloque": "...", "proximidad": 85.5, "sesgo": "..." }}
                    ]
                }}
            ]
        }}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.1}
            )
            return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        except Exception as e:
            print(f"⚠️ Error en lote IA: {e}")
            return None

    def run_analysis_pipeline(self, raw_news_lines):
        print(f"🧠 IA: Procesando {len(raw_news_lines)} señales en lotes...")
        
        # Procesamos en lotes de 20 para máxima precisión y evitar timeouts
        chunk_size = 20
        chunks = [raw_news_lines[i:i + chunk_size] for i in range(0, len(raw_news_lines), chunk_size)]
        
        merged_carousel = {} 

        for i, chunk in enumerate(chunks):
            print(f"   ↳ Lote {i+1}/{len(chunks)}...")
            result = self.analyze_batch(chunk)
            
            if result and 'carousel' in result:
                for item in result['carousel']:
                    area_name = item.get('area')
                    if not area_name: continue
                    
                    if area_name not in merged_carousel:
                        merged_carousel[area_name] = {
                            "area": area_name,
                            "punto_cero": item.get('punto_cero', "Análisis global de inteligencia en proceso."),
                            "color": AREAS_ESTRATEGICAS.get(area_name, "#3b82f6"),
                            "particulas": []
                        }
                    merged_carousel[area_name]['particulas'].extend(item.get('particulas', []))
            # Pausa táctica para API rate limits
            time.sleep(1.5)

        return {"carousel": list(merged_carousel.values())}

    def validate_and_fix(self, data):
        if not data or 'carousel' not in data: return False
        
        total_recuperados = 0
        
        for slide in data['carousel']:
            slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
            
            valid_p = []
            for p in slide.get('particulas', []):
                # BÚSQUEDA POR ID (INFALIBLE)
                news_id = p.get('id')
                meta = self.link_storage.get(news_id)
                
                if meta:
                    p['link'] = meta['link'] # Link original recuperado
                    
                    # Normalización de Bloque
                    b_ia = str(p.get('bloque', '')).upper()
                    b_real = meta.get('region_origen', 'GLOBAL')
                    final_block = NORMALIZER.get(b_ia, b_real)
                    if final_block not in BLOQUE_COLORS: final_block = b_real
                    
                    p['bloque'] = final_block
                    p['color_bloque'] = BLOQUE_COLORS.get(final_block, "#94a3b8")

                    # Validación de Proximidad
                    try:
                        clean_v = str(p.get('proximidad', '0')).replace('%', '').strip()
                        val = float(clean_v)
                        p['proximidad'] = round(val, 1)
                    except:
                        # Si falla, mantenemos 0 para revisión (no inventamos datos)
                        p['proximidad'] = 0.0 

                    if not p.get('sesgo'): p['sesgo'] = "Sin análisis."
                    valid_p.append(p)
                    total_recuperados += 1
            
            slide['particulas'] = valid_p
        
        print(f"🛡️ Integridad: {total_recuperados} noticias validadas y enlazadas.")
        return True

    def run(self):
        raw_news_lines, total_news = self.fetch_data()
        if total_news < 5: return

        data = self.run_analysis_pipeline(raw_news_lines)
        
        if self.validate_and_fix(data):
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
            with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Éxito: Base de datos actualizada con {total_news} señales.")
        else:
            print("❌ Error crítico en validación.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

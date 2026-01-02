import os, json, datetime, time, ssl, urllib.request, urllib.error, hashlib, glob, re
import xml.etree.ElementTree as ET
from google import genai
from bs4 import BeautifulSoup # Motor de extracción profunda

# --- CONFIGURACIÓN DE ENTORNO ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): os.makedirs(p, exist_ok=True)

# Headers simulando navegador real para evitar bloqueos 403
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

# --- DEFINICIONES ESTRATÉGICAS ---
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

# --- RED DE INTELIGENCIA GLOBAL (Fuentes V8.0 + África Fix) ---
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
        self.link_storage = {}
        self.title_to_id = {}
        self.hoy = datetime.datetime.now()

    def fetch_with_retry(self, url, retries=2):
        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                return urllib.request.urlopen(req, timeout=10).read()
            except urllib.error.URLError as e:
                # Bypass SSL
                if "certificate" in str(e).lower() or "ssl" in str(e).lower():
                    try:
                        ctx = ssl._create_unverified_context()
                        return urllib.request.urlopen(req, timeout=10, context=ctx).read()
                    except: pass
                time.sleep(1)
            except: time.sleep(1)
        return None

    # --- MÓDULO SMART SCRAPER (Fase 2) ---
    def smart_scrape(self, url):
        """Intenta descargar y limpiar el texto real de la noticia."""
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=6) as response: # Timeout ajustado
                html = response.read()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Limpieza quirúrgica
                for script in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                    script.extract()
                
                text = soup.get_text()
                
                # Formateo de texto
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                # Devolvemos un fragmento sustancial (1500 chars)
                return text[:1500]
        except Exception:
            return ""

    def fetch_data(self):
        print("🌍 Fase 1: Triaje de Señales Globales...")
        raw_news_data = [] 
        total_news = 0
        
        for region, urls in FUENTES.items():
            region_count = 0
            for url in urls:
                content = self.fetch_with_retry(url)
                if content:
                    try:
                        root = ET.fromstring(content)
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        
                        # TRIAJE: Top 5 noticias por fuente para profundizar
                        for n in items[:5]: 
                            t = (n.find('title') or n.find('{*}title')).text.strip()
                            l = (n.find('link').text or n.find('{*}link').attrib.get('href', '')).strip()
                            
                            # Fallback Description del RSS
                            d_node = n.find('description') or n.find('{*}description') or n.find('{*}summary')
                            rss_desc = d_node.text if (d_node is not None and d_node.text) else ""
                            
                            if t and l:
                                art_id = hashlib.md5(t.encode()).hexdigest()[:8]
                                self.link_storage[art_id] = {"link": l, "title": t, "region_origen": region}
                                
                                raw_news_data.append({
                                    "id": art_id,
                                    "region": region,
                                    "titulo": t,
                                    "link": l,
                                    "rss_desc": rss_desc
                                })
                                total_news += 1
                                region_count += 1
                    except Exception: continue
            print(f"   ✓ {region}: {region_count} objetivos identificados.")
        return raw_news_data, total_news

    def enrich_data(self, news_list):
        print(f"🕵️ Fase 2: Extracción Profunda (Scraping) de {len(news_list)} objetivos...")
        enriched_lines = []
        
        for i, item in enumerate(news_list):
            if i % 10 == 0: print(f"   ↳ Extrayendo contexto {i}/{len(news_list)}...")
            
            # Intentamos leer la web real
            full_text = self.smart_scrape(item['link'])
            
            # Si falla, usamos el resumen del RSS
            context_text = full_text if len(full_text) > 200 else item['rss_desc']
            context_text = re.sub('<[^<]+?>', '', str(context_text)) # Limpieza final HTML
            
            # Construcción del Payload para Gemini
            line = f"ID: {item['id']} | ORIGEN: {item['region']} | TITULO: {item['titulo']} | CONTEXTO: {context_text[:1200]}"
            enriched_lines.append(line)
            
        return enriched_lines

    def analyze_batch(self, news_chunk):
        batch_text = "\n".join(news_chunk)
        prompt = f"""
        Actúa como analista de inteligencia geopolítica senior.
        
        OBJETIVO:
        Analiza el TITULO y el CONTEXTO real de las noticias.
        Detecta la perspectiva regional y la carga factual.
        
        ÁREAS: {list(AREAS_ESTRATEGICAS.keys())}

        REGLAS DE SALIDA (JSON):
        1. 'id': COPIA EXACTAMENTE el ID.
        2. 'titulo': Traduce al Español.
        3. 'bloque': Infiérelo del ORIGEN.
        4. 'proximidad': FLOAT (0.0 - 100.0).
           - 85-100: Datos duros, hechos verificados, tono técnico.
           - 50-80: Análisis interpretativo o editorial.
           - 10-40: Propaganda evidente, lenguaje incendiario, falta de datos.
        5. 'sesgo': Frase breve sobre el encuadre (ej. "Enfatiza pérdidas enemigas", "Crítico con la política monetaria").

        INPUT:
        {batch_text}

        FORMATO ESPERADO:
        {{ "carousel": [ {{ "area": "...", "punto_cero": "Resumen del área...", "particulas": [ {{ "id": "...", "titulo": "...", "bloque": "...", "proximidad": 85.5, "sesgo": "..." }} ] }} ] }}
        """
        try:
            res = self.client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt, 
                config={'response_mime_type': 'application/json', 'temperature': 0.15}
            )
            return json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        except Exception as e:
            print(f"⚠️ Error Lote IA: {e}")
            return None

    def run_analysis_pipeline(self, enriched_lines):
        print(f"🧠 Fase 3: Análisis de Contraste ({len(enriched_lines)} señales)...")
        chunk_size = 12 # Lotes ajustados para contexto enriquecido
        chunks = [enriched_lines[i:i + chunk_size] for i in range(0, len(enriched_lines), chunk_size)]
        
        merged_carousel = {} 

        for i, chunk in enumerate(chunks):
            print(f"   ↳ Analizando Lote {i+1}/{len(chunks)}...")
            result = self.analyze_batch(chunk)
            
            if result and 'carousel' in result:
                for item in result['carousel']:
                    area_name = item.get('area')
                    if not area_name: continue
                    
                    if area_name not in merged_carousel:
                        merged_carousel[area_name] = {
                            "area": area_name,
                            "punto_cero": item.get('punto_cero', "Análisis global en proceso."),
                            "color": AREAS_ESTRATEGICAS.get(area_name, "#3b82f6"),
                            "particulas": []
                        }
                    merged_carousel[area_name]['particulas'].extend(item.get('particulas', []))
            time.sleep(2)

        return {"carousel": list(merged_carousel.values())}

    def validate_and_fix(self, data):
        if not data or 'carousel' not in data: return False
        
        total_ok = 0
        for slide in data['carousel']:
            slide['color'] = AREAS_ESTRATEGICAS.get(slide.get('area'), "#3b82f6")
            
            valid_p = []
            for p in slide.get('particulas', []):
                news_id = p.get('id')
                meta = self.link_storage.get(news_id)
                
                if meta:
                    p['link'] = meta['link']
                    
                    # Normalización
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
                        print(f"⚠️ [DEBUG] Fallo Proximidad ID {news_id}")
                        p['proximidad'] = 0.0

                    if not p.get('sesgo'): p['sesgo'] = "Análisis pendiente."
                    valid_p.append(p)
                    total_ok += 1
            
            slide['particulas'] = valid_p
        
        print(f"🛡️ Integridad: {total_ok} señales validadas y enriquecidas.")
        return True

    def run(self):
        # 1. Cosecha
        raw_news_data, total_news = self.fetch_data()
        if total_news < 5: return

        # 2. Enriquecimiento (Scraping)
        enriched_lines = self.enrich_data(raw_news_data)

        # 3. Análisis
        data = self.run_analysis_pipeline(enriched_lines)
        
        # 4. Guardado
        if self.validate_and_fix(data):
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            fecha = self.hoy.strftime('%Y-%m-%d_%H%M')
            with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Éxito Total: Inteligencia actualizada.")
        else:
            print("❌ Error crítico en validación.")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: GeopoliticalCollector(key).run()

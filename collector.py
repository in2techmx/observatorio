import os
import json
import datetime
import time
import urllib.request
import hashlib
import re
import sys
import math
import struct
import logging
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
import argparse
from google import genai

# ============================================================================
# CONFIGURACIÓN GLOBAL Y ARGUMENTOS
# ============================================================================
CACHE_DIR = "vector_cache"
HIST_DIR = "historico_noticias/diario"
LOG_FILE = "system_audit.log"

# Cargar configuración dinámica
if os.path.exists(".proximity_env"):
    with open(".proximity_env", "r") as f:
        for line in f:
            if "CACHE_DIR=" in line:
                CACHE_DIR = line.split("=")[1].strip()

# Gestión de Argumentos
parser = argparse.ArgumentParser()
parser.add_argument('--mode', default='tactical', help='Modo: tactical, strategic, full')
args, _ = parser.parse_known_args()

if args.mode == 'full':
    FETCH_LIMIT = 60
    print("🔥 MODO FULL: Límite 60 items/feed")
elif args.mode == 'strategic':
    FETCH_LIMIT = 40
    print("🛡️ MODO ESTRATÉGICO: Límite 40 items/feed")
else:
    FETCH_LIMIT = 20
    print("⚡ MODO TÁCTICO: Límite 20 items/feed")

# ============================================================================
# CONFIGURACIÓN DE ÁREAS Y FUENTES
# ============================================================================
AREAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos",
         "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]

FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics", "https://www.propublica.org/feeds/propublica/main", "https://www.democracynow.org/democracynow.rss", "https://theintercept.com/feed/?lang=en"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://themoscowtimes.com/rss/news", "https://meduza.io/rss/en", "https://novayagazeta.eu/feed/rss", "https://theins.ru/en/feed"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://www.chinadaily.com.cn/rss/world_rss.xml", "https://www.globaltimes.cn/rss/china.xml", "https://hongkongfp.com/feed/", "https://chinadigitaltimes.net/feed/"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.france24.com/en/rss", "https://rss.dw.com/xml/rss-en-all", "https://www.bellingcat.com/feed/", "https://www.opendemocracy.net/en/feed/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.arabnews.com/cat/1/rss.xml", "https://www.middleeasteye.net/rss", "https://www.haaretz.com/cmlink/1.4608", "https://www.al-monitor.com/rss", "https://www.972mag.com/feed/"],
    "LATAM": ["https://en.mercopress.com/rss", "https://buenosairesherald.com/feed", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/america/portada", "https://insightcrime.org/feed/", "https://nacla.org/rss.xml"],
    "AFRICA": ["https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "https://www.news24.com/news24/partner/rss/rssfeed.xml", "https://www.africanews.com/feed/", "https://www.theafricareport.com/feed/", "https://mg.co.za/feed/", "http://saharareporters.com/feeds/news"],
    "INDIA": ["https://timesofindia.indiatimes.com/rssfeeds/296589292.cms", "https://www.thehindu.com/news/international/feeder/default.rss", "https://indianexpress.com/section/india/feed/", "https://caravanmagazine.in/feed/rss", "https://thewire.in/rss", "https://scroll.in/feed"],
    "GLOBAL": ["https://www.economist.com/sections/international/rss.xml", "https://www.reutersagency.com/feed/?best-topics=political-general&post_type=best", "https://globalvoices.org/feed/", "https://theconversation.com/global/articles.atom"]
}

# ============================================================================
# INICIALIZACIÓN DE DIRECTORIOS
# ============================================================================
def initialize_directories():
    global CACHE_DIR
    targets = [CACHE_DIR, HIST_DIR]
    
    for d in targets:
        try:
            if os.path.exists(d):
                if not os.path.isdir(d):
                    try: os.remove(d)
                    except: pass
                    os.makedirs(d, exist_ok=True)
            else:
                os.makedirs(d, exist_ok=True)
        except Exception as e:
            print(f"⚠️ Error directorio {d}: {e}")
            if d == CACHE_DIR: 
                CACHE_DIR = "/tmp/vector_cache"
                os.makedirs(CACHE_DIR, exist_ok=True)

initialize_directories()

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)

# ============================================================================
# CLASES Y UTILIDADES
# ============================================================================
class NewsItem:
    def __init__(self, item_id, title, link, region, source_url):
        self.id = item_id
        self.original_title = self._sanitize(title)
        self.link = link if self._valid_url(link) else None
        self.region = region
        self.source_url = source_url
        self.translated_title = None
        self.area = None
        self.confidence = 0.0
        self.keywords = []
        self.vector = None
        self.proximity = 50.0
        self.bias_label = "Neutral"

    @staticmethod
    def _valid_url(url):
        return bool(re.match(r'^https?://', str(url), re.IGNORECASE)) if url else False

    @staticmethod
    def _sanitize(text):
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text)
        return re.sub(r'\s+', ' ', text).strip()[:400]

    def to_dict(self):
        return {
            "id": self.id[:12], "titulo": self.translated_title or self.original_title,
            "link": self.link, "bloque": self.region, "proximidad": round(self.proximity, 1),
            "sesgo": self.bias_label, "confianza": round(self.confidence, 1),
            "keywords": self.keywords[:5]
        }

class IroncladCollectorPro:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.active_items = []
        self.stats = {"items_raw": 0, "items_classified": 0, "cache_hits": 0, "cache_misses": 0, "errors": 0}
        self.start_time = time.time()

    def safe_json_extract(self, text):
        if not text: return None
        try: return json.loads(text.strip())
        except: pass
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group()) if match else None

    # --- NUEVO: SEMANTIC DEDUPLICATION ---
    def is_duplicate(self, title, existing_items):
        """Revisa si el título ya existe semánticamente en la lista dada."""
        # Limpieza básica
        def clean(t): return re.sub(r'\W+', ' ', t.lower()).strip()
        
        t_clean = clean(title)
        
        for item in existing_items:
            # 1. Coincidencia exacta o muy cercana de texto
            i_clean = clean(item.original_title)
            if t_clean == i_clean or t_clean in i_clean or i_clean in t_clean:
                return True
                
            # 2. Distancia de Jaccard simple para texto
            set_a = set(t_clean.split())
            set_b = set(i_clean.split())
            intersection = len(set_a.intersection(set_b))
            union = len(set_a.union(set_b))
            if union > 0 and (intersection / union) > 0.6: # 60% overlap de palabras
                return True
                
        return False

    # --- NUEVO: VALIDACIÓN DE RESPUESTA ---
    def validate_gemini_response(self, response_text, expected_count):
        """Valida que la respuesta de Gemini sea completa"""
        if not response_text:
            logging.error("Respuesta vacía de Gemini")
            return None
        
        data = self.safe_json_extract(response_text)
        
        if not data:
            logging.error("No se pudo extraer JSON de la respuesta")
            return None
        
        if 'res' not in data:
            logging.error("JSON no tiene clave 'res'")
            return None
        
        # Verificar que tenemos items
        if len(data['res']) < expected_count:
            logging.warning(f"⚠️ Se esperaban {expected_count} items, se recibieron {len(data['res'])}")
        
        return data

    # --- NUEVO: FALLBACK CLASSIFICATION ---
    def fallback_classification(self, batch):
        """Clasificación simple basada en keywords cuando Gemini falla"""
        if not batch: return
        
        # Keywords en inglés (fuentes originales)
        keywords_map = {
            "Seguridad y Conflictos": ["military", "defense", "war", "attack", "terror", "pentagon", "nato", "army", "strike", "conflict"],
            "Economía y Sanciones": ["economy", "finance", "sanction", "market", "trade", "bank", "inflation", "stock", "gdp", "debt"],
            "Energía y Recursos": ["energy", "oil", "gas", "mining", "climate", "renewable", "nuclear", "solar", "water", "carbon"],
            "Soberanía y Alianzas": ["alliance", "treaty", "diplomacy", "summit", "sovereignty", "brics", "un", "relations", "foreign"],
            "Tecnología y Espacio": ["technology", "space", "digital", "satellite", "ai", "cyber", "chip", "moon", "launch", "rocket"],
            "Sociedad y Derechos": ["rights", "human", "protest", "health", "education", "justice", "law", "court", "immigration"]
        }
        
        count = 0
        for item in batch:
            if item.area: continue # Ya clasificado
            
            title_lower = item.original_title.lower()
            scores = {area: 0 for area in AREAS}
            
            for area, keywords in keywords_map.items():
                for keyword in keywords:
                    if keyword in title_lower:
                        scores[area] += 1
            
            best_area = max(scores.items(), key=lambda x: x[1])
            if best_area[1] > 0:
                item.area = best_area[0]
                item.confidence = min(50 + best_area[1] * 10, 85)
                item.translated_title = item.original_title # Se queda en inglés como fallback
                item.keywords = ["fallback_mode"]
                item.bias_label = "Clasificación Automática"
                count += 1
                logging.debug(f"Fallback: '{item.original_title[:20]}...' -> {item.area}")
        
        if count > 0:
            logging.info(f"🛡️ Fallback recuperó {count} noticias.")
            self.stats["items_classified"] += count

    # --- GESTIÓN DE CACHÉ ---
    def get_cached_vector(self, text):
        if not text: return None
        v_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        path = os.path.join(CACHE_DIR, f"{v_hash}.bin")
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                    self.stats["cache_hits"] += 1
                    return list(struct.unpack(f'{len(data)//4}f', data))
            except: pass
        return None

    def save_vector(self, text, vector):
        if not text or not vector: return
        try:
            v_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            path = os.path.join(CACHE_DIR, f"{v_hash}.bin")
            with open(path, 'wb') as f:
                f.write(struct.pack(f'{len(vector)}f', *vector))
            self.stats["cache_misses"] += 1
        except: pass

    # --- CLASIFICACIÓN DE ÁREAS ---
    def classify_area(self, area_name):
        if not area_name: return None
        area_lower = area_name.lower().strip()
        
        for area in AREAS:
            if area.lower() == area_lower: return area
            
        scores = {area: 0 for area in AREAS}
        keywords_map = {
            "Seguridad y Conflictos": ["defensa", "militar", "conflicto", "terrorismo", "ataque", "ejército", "guerra"],
            "Economía y Sanciones": ["económico", "finanzas", "sanciones", "mercado", "comercio", "inflación", "banco", "pib"],
            "Energía y Recursos": ["energía", "petróleo", "gas", "minería", "renovable", "clima", "nuclear", "agua"],
            "Soberanía y Alianzas": ["soberanía", "alianza", "diplomacia", "tratado", "geopolítica", "cumbre", "brics"],
            "Tecnología y Espacio": ["tecnología", "espacio", "digital", "satélite", "ia", "ciber", "chip", "luna"],
            "Sociedad y Derechos": ["derechos", "humano", "social", "salud", "educación", "protesta", "ley", "justicia"]
        }
        
        for area, kws in keywords_map.items():
            for kw in kws:
                if kw in area_lower: scores[area] += 1
        
        best = max(scores.items(), key=lambda x: x[1])
        return best[0] if best[1] > 0 else None

    # --- FASE 1: RECOLECCIÓN ---
    def fetch_signals(self):
        logging.info(f"📡 FASE 1: Recolección (Límite: {FETCH_LIMIT})...")
        cnt = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        root = ET.fromstring(r.read().decode('utf-8', errors='ignore'))
                        items = root.findall('.//item') or root.findall('.//entry') or root.findall('.//{*}item')
                        
                        for item in items[:FETCH_LIMIT]:
                            title = getattr(item.find('title') or item.find('{*}title'), 'text', '')
                            link = getattr(item.find('link') or item.find('{*}link'), 'text', '')
                            if not link: link = (item.find('link') or item.find('{*}link') or {}).get('href', '')
                            
                            if title and link and len(title)>10:
                                uid = f"{region}_{cnt}_{hashlib.md5(link.encode()).hexdigest()[:8]}"
                                news = NewsItem(uid, title, link, region, url)
                                
                                # Check deduplication against current active items
                                if not self.is_duplicate(title, self.active_items):
                                    self.active_items.append(news)
                                    cnt += 1
                                else:
                                    logging.debug(f"Duplicate skipped: {title}")
                except: self.stats["errors"] += 1
        self.stats["items_raw"] = len(self.active_items)

    # --- FASE 2: TRIAGE (MEJORADO) ---
    def run_triage(self):
        if not self.active_items: return
        logging.info(f"🔎 FASE 2: Clasificación IA ({len(self.active_items)} items)...")

        
        
        # PROMPT DE INGENIERÍA MEJORADO
        prompt = f"""ANALISTA DE INTELIGENCIA GEOPOLÍTICA
OBJETIVO: Clasificar titulares en: {', '.join(AREAS)}

INSTRUCCIONES:
1. MANTÉN el MISMO ID numérico (0, 1, 2...).
2. TRADUCE al español (fiel al original).
3. ASIGNA SOLO UN ÁREA (la más relevante).
4. CONFIANZA: 0-100.
5. KEYWORDS: 3-5 palabras clave.

EJEMPLOS:
ID:0 | TITULO: "Pentagon announces new AI defense system"
→ {{"id": 0, "area": "Seguridad y Conflictos", "titulo_es": "Pentágono anuncia nuevo sistema de defensa IA", "confianza": 95, "keywords": ["Pentágono", "IA", "defensa"]}}

ID:1 | TITULO: "EU approves new sanctions against Russia"
→ {{"id": 1, "area": "Economía y Sanciones", "titulo_es": "UE aprueba nuevas sanciones a Rusia", "confianza": 88, "keywords": ["UE", "sanciones", "Rusia"]}}

FORMATO SALIDA (JSON PURO):
{{
  "res": [
    {{"id": 0, "area": "...", "titulo_es": "...", "confianza": ..., "keywords": [...]}}
  ]
}}"""
        
        batch_size = 20
        for i in range(0, len(self.active_items), batch_size):
            batch = self.active_items[i:i+batch_size]
            
            # IDs simples para evitar confusión de la IA
            batch_text = "\n".join([f"ID:{idx} | TITULO: {item.original_title}" for idx, item in enumerate(batch)])
            
            try:
                resp = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=f"{prompt}\n\nENTRADA:\n{batch_text}",
                    config={"temperature": 0.0}
                )
                
                # Validación mejorada
                data = self.validate_gemini_response(resp.text, len(batch))
                
                if data and 'res' in data:
                    for res in data['res']:
                        try:
                            idx = int(res.get('id', -1))
                            if 0 <= idx < len(batch):
                                target = batch[idx]
                                area = self.classify_area(res.get('area',''))
                                if area:
                                    target.area = area
                                    target.translated_title = res.get('titulo_es','')
                                    target.confidence = res.get('confianza',0)
                                    target.keywords = res.get('keywords',[])[:5]
                                    self.stats["items_classified"] += 1
                        except: continue
            except Exception as e:
                logging.error(f"Error Batch IA: {str(e)[:50]}")
                self.stats["errors"] += 1
            
            # EJECUTAR FALLBACK para lo que la IA se saltó
            unclassified = [item for item in batch if item.area is None]
            if unclassified:
                self.fallback_classification(unclassified)
            
            time.sleep(1)

    # --- FASE 3: VECTORES (ESCALA NO LINEAL MEJORADA) ---
    def compute_vectors_and_proximity(self):
        logging.info("📐 FASE 3: Análisis Vectorial (Escala No-Lineal)...")
        
        need_embedding = []
        valid_items = [it for it in self.active_items if it.area in AREAS]
        
        # Separar cacheados vs nuevos para no romper índices
        for item in valid_items:
            # Usar título traducido si existe, sino el original
            text_key = item.translated_title if item.translated_title else item.original_title
            
            cached = self.get_cached_vector(text_key)
            if cached:
                item.vector = cached
            else:
                need_embedding.append(item)
        
        # Procesar nuevos en batches
        batch_size = 100
        for i in range(0, len(need_embedding), batch_size):
            batch = need_embedding[i:i+batch_size]
            texts = [item.translated_title if item.translated_title else item.original_title for item in batch]
            
            try:
                resp = self.client.models.embed_content(
                    model="text-embedding-004", contents=texts,
                    config={'task_type': 'RETRIEVAL_DOCUMENT'}
                )
                
                # Asignación segura por índice
                for idx, item in enumerate(batch):
                    if idx < len(resp.embeddings):
                        item.vector = resp.embeddings[idx].values
                        text_key = item.translated_title if item.translated_title else item.original_title
                        self.save_vector(text_key, item.vector)
            except Exception as e:
                logging.error(f"Error Embeddings: {e}")
                # Vector aleatorio fallback
                for item in batch:
                    random.seed(hash(item.original_title))
                    item.vector = [random.uniform(-0.1, 0.1) for _ in range(768)]

        # Proximity Calculation
        for area in AREAS:
            area_items = [it for it in valid_items if it.area == area and it.vector]
            if not area_items: continue
            
            # 1. Calculate Regional Centroids (The "Voice" of each Region)
            # We group vectors by region first to treat each region as 1 unit of perspective
            region_map = defaultdict(list)
            for it in area_items:
                region_map[it.region].append(it.vector)
            
            regional_centroids = []
            for r_vecs in region_map.values():
                # Average of items within this specific region
                c = [sum(col)/len(r_vecs) for col in zip(*r_vecs)]
                regional_centroids.append(c)
                
            # 2. Global Egalitarian Centroid ("The Center of Truth")
            # Average of REGIONAL centroids, not individual items.
            if not regional_centroids: continue
            
            global_c = [sum(col)/len(regional_centroids) for col in zip(*regional_centroids)]
            mag_g = math.sqrt(sum(x*x for x in global_c))

            for it in area_items:
                # Cosine Similarity to Global Center
                mag_a = math.sqrt(sum(a*a for a in it.vector))
                if mag_a * mag_g > 0:
                    dot = sum(a*b for a,b in zip(it.vector, global_c))
                    sim = dot / (mag_a * mag_g) # Range -1 to 1
                    
                    # --- NUEVA ESCALA NO LINEAL (TUNED) ---
                    # Lower baseline to 0.5 to catch more signals
                    baseline = 0.5
                    if sim < baseline:
                        it.proximity = 0.0
                        it.bias_label = "Divergente"
                    else:
                        normalized = (sim - baseline) / (1 - baseline) # 0.0 to 1.0
                        score = math.pow(normalized, 3) * 100 # Cubic Power curve
                        it.proximity = max(0.0, min(100.0, float(score)))
                    
                        # Assign Dynamic Labels (Recalibrated for new scale)
                        if it.proximity > 80: it.bias_label = "Núcleo Narrativo"
                        elif it.proximity > 60: it.bias_label = "Alta Convergencia"
                        elif it.proximity > 40: it.bias_label = "Alineado"
                        elif it.proximity > 20: it.bias_label = "Periférico"
                        else: it.bias_label = "Divergente"
                else:
                    it.proximity = 0.0
                    it.bias_label = "Error Vectorial"

    # --- FASE 3.5: CLUSTERING & SÍNTESIS NARRATIVA ---
    def generate_narrative_syntheses(self):
        logging.info("💬 FASE 3.5: Generando Diálogo Geopolítico (Regional Clustering)...")
        valid_items = [it for it in self.active_items if it.area in AREAS]
        
        self.syntheses = {} # Store synthesis per area

        for area in AREAS:
            area_items = [it for it in valid_items if it.area == area]
            if len(area_items) < 3:
                self.syntheses[area] = "Insuficiente data para establecer diálogo."
                continue
            
            # --- 1. CLUSTER BY REGION ---
            # Instead of taking random items, we find the "Dominant Topic" per region
            grouped = defaultdict(list)
            for it in area_items: grouped[it.region].append(it)
            
            representative_headlines = []
            
            for region, items in grouped.items():
                if not items: continue
                # Simple "Center of Mass" Clustering for this Region
                # 1. Find the item closest to the region's centroid (The "Representative" Article)
                if len(items) > 1 and all(it.vector for it in items):
                    # Calculate centroid
                    vectors = [it.vector for it in items if it.vector]
                    if not vectors: continue
                    centroid = [sum(col)/len(vectors) for col in zip(*vectors)]
                    
                    # Find closest item to centroid
                    best_item = None
                    best_sim = -1
                    for it in items:
                        if not it.vector: continue
                        dot = sum(a*b for a,b in zip(it.vector, centroid))
                        mag = math.sqrt(sum(x*x for x in it.vector)) * math.sqrt(sum(x*x for x in centroid))
                        if mag > 0:
                            sim = dot / mag
                            if sim > best_sim:
                                best_sim = sim
                                best_item = it
                    
                    if best_item:
                        representative_headlines.append(f"[{region}] {best_item.original_title}")
                else:
                    # Fallback for single item or no vectors
                    representative_headlines.append(f"[{region}] {items[0].original_title}")

            if not representative_headlines: continue

            # --- 2. GENERATE DIALOGUE ---
            headlines_text = "\n".join(representative_headlines[:8])
            
            prompt = f"""ACT AS: Geopolitical Analyst.
TASK: Synthesize the 'dialogue' between these regions regarding '{area}'.
INPUT (Dominant Regional Narratives):
{headlines_text}

INSTRUCTIONS:
1. Identify the core tension or agreement.
2. Format as a single, high-impact sentence (Max 30 words).
3. Contrast perspectives (e.g., "While USA focuses on X, China emphasizes Y...").
4. Language: Spanish.

OUTPUT TEXT ONLY."""

            try:
                resp = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=prompt,
                    config={"temperature": 0.4}
                )
                if resp.text:
                    self.syntheses[area] = resp.text.strip()
            except Exception as e:
                logging.error(f"Error Synthesis {area}: {e}")
                self.syntheses[area] = "Análisis en curso..."

    # --- FASE 4: EXPORTACIÓN ---
    def export(self):
        logging.info("💾 FASE 4: Exportación...")
        carousel = []
        colors = {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}

        for area in AREAS:
            items = [it for it in self.active_items if it.area == area]
            if not items: continue
            
            particles = [it.to_dict() for it in items]
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            avg = sum(p['proximidad'] for p in particles)/len(particles)
            
            trend = "↑" if avg > 60 else "↓" if avg < 40 else "→"
            consensus = "ALTO" if avg > 80 else "MODERADO" if avg > 60 else "BAJO"
            emoji = "🟢" if avg > 80 else "🟡" if avg > 60 else "🟠" if avg > 50 else "🔴"

            # Get synthesis
            sintesis = self.syntheses.get(area, "Analizando señales globales...")

            carousel.append({
                "area": area, 
                "sintesis": sintesis, 
                "punto_cero": f"{emoji} {consensus} | Avg: {avg:.1f}% | {trend}",
                "color": colors.get(area, "#666"),
                "meta_netflix": {"consensus": consensus, "trend": trend, "avg_proximity": avg},
                "particulas": particles[:60] # INCREASED LIMIT TO 60
            })

        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "execution_seconds": round(time.time() - self.start_time, 2),
            "stats": self.stats,
            "config": {"mode": args.mode, "limit": FETCH_LIMIT}
        }
        
        final = {"carousel": carousel, "meta": meta}
        # Ensure public directory exists
        if not os.path.exists("public"):
            os.makedirs("public")
            
        with open("public/gravity_carousel.json", "w", encoding="utf-8") as f: json.dump(final, f, indent=2, ensure_ascii=False)
        try:
            with open(os.path.join(HIST_DIR, f"{datetime.datetime.now():%Y-%m-%d}.json"), "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2, ensure_ascii=False)
        except: pass

    def run(self):
        try:
            self.fetch_signals()
            self.run_triage()
            self.compute_vectors_and_proximity()
            self.generate_narrative_syntheses() # Phase 3.5
            self.export()
            return True
        except Exception as e:
            logging.error(f"FATAL: {e}", exc_info=True)
            return False

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("❌ ERROR: GEMINI_API_KEY no encontrada"); sys.exit(1)
    
    col = IroncladCollectorPro(key)
    sys.exit(0 if col.run() else 1)

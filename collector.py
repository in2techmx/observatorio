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
# GESTIÓN SEGURA DE RUTAS Y CONFIGURACIÓN
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

# Áreas Estratégicas
AREAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos",
         "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]

# ============================================================================
# GESTIÓN DE ARGUMENTOS
# ============================================================================
parser = argparse.ArgumentParser()
parser.add_argument('--mode', default='tactical', help='Modo: tactical, strategic, full')
args, _ = parser.parse_known_args()

if args.mode == 'full':
    FETCH_LIMIT = 50
    print("🔥 MODO FULL: Límite 50 items/feed")
elif args.mode == 'strategic':
    FETCH_LIMIT = 25
    print("🛡️ MODO ESTRATÉGICO: Límite 25 items/feed")
else:
    FETCH_LIMIT = 12
    print("⚡ MODO TÁCTICO: Límite 12 items/feed")

# ============================================================================
# FUENTES RSS
# ============================================================================
FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://themoscowtimes.com/rss/news"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://www.chinadaily.com.cn/rss/world_rss.xml", "https://www.globaltimes.cn/rss/china.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.france24.com/en/rss", "https://rss.dw.com/xml/rss-en-all"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss", "https://www.arabnews.com/cat/1/rss.xml"],
    "GLOBAL": ["https://www.economist.com/sections/international/rss.xml", "https://techcrunch.com/feed/", "https://www.wired.com/feed/category/science/latest/rss"]
}

# ============================================================================
# INICIALIZACIÓN DE DIRECTORIOS
# ============================================================================
def initialize_directories():
    global CACHE_DIR
    for d in [CACHE_DIR, HIST_DIR]:
        try:
            if os.path.exists(d):
                if not os.path.isdir(d):
                    os.remove(d)
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

    # --- CLASIFICACIÓN DE ÁREAS (CORREGIDA: PUNTUACIÓN POR PESO) ---
    def classify_area(self, area_name):
        if not area_name: return None
        area_lower = area_name.lower().strip()
        
        # 1. Búsqueda exacta
        for area in AREAS:
            if area.lower() == area_lower: return area
            
        # 2. Sistema de Puntuación Semántica
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
                                if news.link: 
                                    self.active_items.append(news)
                                    cnt += 1
                except: self.stats["errors"] += 1
        self.stats["items_raw"] = len(self.active_items)

    # --- FASE 2: TRIAGE ---
    def run_triage(self):
        if not self.active_items: return
        logging.info(f"🔎 FASE 2: Triage IA ({len(self.active_items)} items)...")
        prompt = f"Clasificador Geopolítico.\nÁREAS: {', '.join(AREAS)}\nJSON: {{'res': [{{'id': '...', 'area': '...', 'titulo_es': '...', 'confianza': 90, 'keywords': []}}]}}"
        
        batch_size = 25
        for i in range(0, len(self.active_items), batch_size):
            batch = self.active_items[i:i+batch_size]
            txt = "\n".join([f"ID:{x.id}|{x.original_title}" for x in batch])
            try:
                resp = self.client.models.generate_content(model="gemini-2.0-flash", contents=f"{prompt}\n\n{txt}")
                data = self.safe_json_extract(resp.text)
                if data and 'res' in data:
                    for res in data['res']:
                        target = next((x for x in batch if x.id == str(res.get('id',''))), None)
                        if target:
                            area = self.classify_area(res.get('area',''))
                            if area:
                                target.area = area
                                target.translated_title = res.get('titulo_es','')
                                target.confidence = res.get('confianza',0)
                                target.keywords = res.get('keywords',[])[:5]
                                self.stats["items_classified"] += 1
            except: self.stats["errors"] += 1
            time.sleep(1)

    # --- FASE 3: VECTORES (CORREGIDA: ALINEACIÓN PERFECTA) ---
    def compute_vectors_and_proximity(self):
        logging.info("📐 FASE 3: Análisis Vectorial...")
        
        # 1. Separar items cacheados de los nuevos
        need_embedding = []
        valid_items = [it for it in self.active_items if it.area in AREAS and it.translated_title]
        
        for item in valid_items:
            cached = self.get_cached_vector(item.translated_title)
            if cached:
                item.vector = cached
            else:
                need_embedding.append(item)
        
        # 2. Procesar embeddings en batches alineados
        batch_size = 100
        for i in range(0, len(need_embedding), batch_size):
            batch = need_embedding[i:i+batch_size]
            texts = [item.translated_title for item in batch]
            
            try:
                resp = self.client.models.embed_content(
                    model="text-embedding-004", contents=texts,
                    config={'task_type': 'RETRIEVAL_DOCUMENT'}
                )
                
                # Mapeo por índice estricto
                for idx, item in enumerate(batch):
                    if idx < len(resp.embeddings):
                        item.vector = resp.embeddings[idx].values
                        self.save_vector(item.translated_title, item.vector)
            except Exception as e:
                logging.error(f"Error embeddings: {e}")
                # Fallback
                for item in batch:
                    random.seed(hash(item.translated_title))
                    item.vector = [random.uniform(-0.1, 0.1) for _ in range(768)]

        # 3. Calcular Proximidad
        for area in AREAS:
            area_items = [it for it in valid_items if it.area == area and it.vector]
            if len(area_items) < 2: continue
            
            # Centroides
            reg_vecs = defaultdict(list)
            for it in area_items: reg_vecs[it.region].append(it.vector)
            centroids = {r: [sum(col)/len(col) for col in zip(*v)] for r,v in reg_vecs.items()}
            
            for it in area_items:
                others = [c for r,c in centroids.items() if r != it.region]
                if not others:
                    it.proximity = 50.0; it.bias_label = "Perspectiva Única"
                    continue
                
                global_c = [sum(col)/len(col) for col in zip(*others)]
                dot = sum(a*b for a,b in zip(it.vector, global_c))
                mag_a = math.sqrt(sum(a*a for a in it.vector))
                mag_b = math.sqrt(sum(b*b for b in global_c))
                
                if mag_a*mag_b > 0:
                    sim = dot/(mag_a*mag_b)
                    it.proximity = max(0.0, min(100.0, (sim+1)*50))
                    if it.proximity > 85: it.bias_label = "Consenso Global"
                    elif it.proximity > 70: it.bias_label = "Alineación"
                    elif it.proximity > 55: it.bias_label = "Tensión Moderada"
                    elif it.proximity > 40: it.bias_label = "Divergencia"
                    else: it.bias_label = "Contraste Radical"

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

            carousel.append({
                "area": area, "punto_cero": f"{emoji} {consensus} | Avg: {avg:.1f}% | {trend}",
                "color": colors.get(area, "#666"),
                "meta_netflix": {"consensus": consensus, "trend": trend, "avg_proximity": avg},
                "particulas": particles[:30]
            })

        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "execution_seconds": round(time.time() - self.start_time, 2),
            "stats": self.stats,
            "config": {"mode": args.mode, "limit": FETCH_LIMIT}
        }
        
        final = {"carousel": carousel, "meta": meta}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f: json.dump(final, f, indent=2, ensure_ascii=False)
        try:
            with open(os.path.join(HIST_DIR, f"{datetime.datetime.now():%Y-%m-%d}.json"), "w", encoding="utf-8") as f:
                json.dump(final, f, indent=2, ensure_ascii=False)
        except: pass

    def run(self):
        try:
            self.fetch_signals()
            self.run_triage()
            self.compute_vectors_and_proximity()
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

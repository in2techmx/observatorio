import os, json, datetime, time, urllib.request, hashlib, re, sys, math, unicodedata, struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN ESTRATÉGICA ---
MAX_PER_REGION_IN_AREA = 8
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

# Diccionario Corregido: AREA_SYNONYMS (usado en elastic_match)
AREA_SYNONYMS = {
    "Seguridad y Conflictos": ["seguridad", "conflictos", "militar", "defensa", "guerra", "armas", "ataque", "ejército"],
    "Economía y Sanciones": ["economía", "sanciones", "finanzas", "mercado", "comercio", "pib", "bancos", "inflación"],
    "Energía y Recursos": ["energía", "recursos", "petróleo", "gas", "minería", "clima", "renovable", "fósil"],
    "Soberanía y Alianzas": ["soberanía", "alianzas", "diplomacia", "geopolítica", "tratados", "otan", "brics", "onu"],
    "Tecnología y Espacio": ["tecnología", "espacio", "ia", "digital", "chips", "satélites", "ciber", "cohete"],
    "Sociedad y Derechos": ["sociedad", "derechos", "humano", "social", "salud", "leyes", "justicia", "educación"]
}

NORMALIZER_REGIONS = {"USA":"USA","RUSSIA":"RUSSIA","CHINA":"CHINA","EUROPE":"EUROPE","LATAM":"LATAM","MID_EAST":"MID_EAST","INDIA":"INDIA","AFRICA":"AFRICA","GLOBAL":"GLOBAL"}
CACHE_DIR = "vector_cache"
if not os.path.exists(CACHE_DIR): os.makedirs(CACHE_DIR)

# --- MAPA GLOBAL DE FUENTES (45+ FEEDS) ---
FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics", "https://www.reutersagency.com/feed/?best-topics=political-news"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://themoscowtimes.com/rss/news", "https://sputniknews.com/export/rss2/archive/index.xml"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://www.chinadaily.com.cn/rss/world_rss.xml", "https://www.globaltimes.cn/rss/china.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.france24.com/en/rss", "https://rss.dw.com/xml/rss-en-all", "https://elpais.com/rss/elpais/inenglish.xml"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", "https://elpais.com/america/rss/", "https://cnnespanol.cnn.com/feed", "https://www.jornada.com.mx/rss/ultimas.xml"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss", "https://www.timesofisrael.com/feed/", "https://www.arabnews.com/cat/1/rss.xml"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "https://www.indiatoday.in/rss/home"],
    "AFRICA": ["https://africa.com/feed", "http://feeds.bbci.co.uk/news/world/africa/rss.xml", "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"],
    "GLOBAL": ["https://www.wired.com/feed/category/science/latest/rss", "https://techcrunch.com/feed/", "https://www.economist.com/sections/international/rss.xml"]
}

class CollectorV35_3:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(lambda: defaultdict(list))
        self.vault, self.raw_list = {}, []
        self.stats = {"hits": 0, "misses": 0}

    # --- DEFINICIÓN DE MÉTODOS DE APOYO ---
    def cleanup_old_cache(self, max_days=7):
        """Elimina archivos de caché binario antiguos para liberar espacio."""
        cutoff = time.time() - (max_days * 86400)
        removed = 0
        for f in os.listdir(CACHE_DIR):
            if f.endswith('.bin'):
                path = os.path.join(CACHE_DIR, f)
                try:
                    if os.path.getmtime(path) < cutoff:
                        os.remove(path); removed += 1
                except: pass
        return removed

    def safe_json_parse(self, text):
        """Extracción robusta de JSON ignorando ruido de la IA."""
        try:
            start, end = text.find('{'), text.rfind('}') + 1
            if start >= 0 and end > start: 
                return json.loads(text[start:end])
        except: return None
        return None

    def elastic_match(self, area_raw):
        """Relaciona términos breves o sinónimos con las áreas estratégicas."""
        if not area_raw: return None
        raw = area_raw.lower().strip()
        for official in AREAS_ESTRATEGICAS:
            if official.lower() in raw or raw in official.lower(): return official
        for official, synonyms in AREA_SYNONYMS.items(): # Corregido AREA_KEYWORDS -> AREA_SYNONYMS
            if any(syn in raw for syn in synonyms): return official
        return None

    def save_vector(self, vector, c_hash):
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        with open(path, 'wb') as f: f.write(struct.pack(f'{len(vector)}f', *vector))

    def load_vector(self, c_hash):
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        if not os.path.exists(path): return None
        try:
            with open(path, 'rb') as f:
                data = f.read()
                return list(struct.unpack(f'{len(data)//4}f', data))
        except: return None

    def clean_text(self, text):
        if not text: return ""
        return re.sub(r'<[^>]+>', '', re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)).strip()

    def run(self):
        print("🌍 FASE 1: Ingesta Masiva...")
        self.cleanup_old_cache() # Llamada al método ahora definido
        id_counter = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        root = ET.fromstring(response.read())
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for item in items[:25]:
                            t_node = item.find('title') or item.find('{*}title')
                            if t_node is None: continue
                            title = self.clean_text(t_node.text)
                            l_node = item.find('link') or item.find('{*}link')
                            link = (l_node.text if l_node is not None and l_node.text else l_node.attrib.get('href', '')).strip()
                            d_node = item.find('description') or item.find('{*}summary')
                            snippet = self.clean_text(d_node.text if d_node is not None else "")
                            
                            nid = str(id_counter)
                            self.vault[nid] = {"link": link, "region": region, "snippet": snippet}
                            self.raw_list.append({"id": nid, "title": title})
                            id_counter += 1
                except: continue
        print(f"✅ Bóveda: {len(self.vault)} registros.")

        print("\n🔎 FASE 2: Clasificación y Triaje Batch...")
        batch_size = 40
        for i in range(0, len(self.raw_list), batch_size):
            batch = self.raw_list[i:i+batch_size]
            prompt = f"Clasifica en {AREAS_ESTRATEGICAS}. Responde JSON: {{'res': [{{'id': '...', 'area': '...', 'titulo_es': '...'}}]}}\n" + \
                     "\n".join([f"ID:{x['id']}|{x['title']}" for x in batch])
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                data = self.safe_json_parse(res.text)
                if data and 'res' in data:
                    for r in data['res']:
                        nid = str(r.get('id')).strip()
                        matched = self.elastic_match(r.get('area'))
                        if matched and nid in self.vault:
                            region = self.vault[nid]['region']
                            if len(self.matrix[matched][region]) < MAX_PER_REGION_IN_AREA:
                                self.matrix[matched][region].append({
                                    "titulo_es": r.get('titulo_es'), "link": self.vault[nid]['link'],
                                    "region": region, "base": f"{r.get('titulo_es')}. {self.vault[nid]['snippet']}"
                                })
            except: continue

        # --- DEBUG POST-FASE 2 (Reporte de Salud de la Matriz) ---
        total_nodes = sum(len(r_list) for area_dict in self.matrix.values() for r_list in area_dict.values())
        print(f"\n🔴 DEBUG POST-FASE 2: {total_nodes} nodos clasificados")
        for area in AREAS_ESTRATEGICAS:
            count = sum(len(r_list) for r_list in self.matrix[area].values())
            print(f"  {area}: {count} noticias")
            if count == 0:
                # Inyectar dato mínimo para que el área no desaparezca
                self.matrix[area]["GLOBAL"].append({"titulo_es": f"Monitor estratégico {area}", "link": "#", "region": "GLOBAL", "base": area})

        print("\n📐 FASE 3: Geometría Vectorial...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = []
            for r_list in self.matrix[area].values(): nodes.extend(r_list)
            if not nodes: continue

            print(f"   🚀 Procesando {area}...")
            vectors, to_embed_texts, to_embed_indices = [], [], []

            for idx, node in enumerate(nodes):
                c_hash = hashlib.md5(node['base'].encode()).hexdigest()
                cached_v = self.load_vector(c_hash)
                if cached_v:
                    vectors.append(cached_v); self.stats["hits"] += 1
                else:
                    vectors.append(None); to_embed_texts.append(node['base']); to_embed_indices.append(idx)
                    self.stats["misses"] += 1

            if to_embed_texts:
                try:
                    res = self.client.models.embed_content(model="text-embedding-004", content=to_embed_texts, config={'task_type': 'RETRIEVAL_DOCUMENT'})
                    for i, emb in enumerate(res.embeddings):
                        idx_orig = to_embed_indices[i]
                        vectors[idx_orig] = emb.values
                        self.save_vector(emb.values, hashlib.md5(nodes[idx_orig]['base'].encode()).hexdigest())
                except:
                    for idx in to_embed_indices: vectors[idx] = [0.1] * 768

            valid_v = [v for v in vectors if v]
            centroid = [sum(v[j] for v in valid_v)/len(valid_v) for j in range(len(valid_v[0]))]
            particles = []
            for idx, node in enumerate(nodes):
                v = vectors[idx]
                dot = sum(a*b for a,b in zip(v, centroid))
                mag1, mag2 = math.sqrt(sum(x*x for x in v)), math.sqrt(sum(x*x for x in centroid))
                sim = dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0
                prox = round(max(0, min(100, (sim - 0.6) * 250)), 1)
                
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:8],
                    "titulo": node['titulo_es'], "link": node['link'], 
                    "bloque": NORMALIZER_REGIONS.get(node['region'], "GLOBAL"), 
                    "proximidad": prox, "metodo": "ID-Vault Binary Cache",
                    "sesgo": "Consenso" if prox > 75 else "Divergente"
                })
            
            final_carousel.append({"area": area, "punto_cero": f"Resumen estratégico de {area}", "color": self.get_color(area), "particulas": particles[:20]})

        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump({"carousel": final_carousel, "meta": {"updated": datetime.datetime.now().isoformat()}}, f, indent=2, ensure_ascii=False)
        print(f"✅ ÉXITO. Aciertos de Caché: {self.stats['hits']} | Nuevos Vectores: {self.stats['misses']}")

    def get_color(self, a):
        color_map = {
            "Seguridad y Conflictos": "#ef4444",
            "Economía y Sanciones": "#3b82f6",
            "Energía y Recursos": "#10b981",
            "Soberanía y Alianzas": "#f59e0b",
            "Tecnología y Espacio": "#8b5cf6",
            "Sociedad y Derechos": "#ec4899"
        }
        return color_map.get(a, "#666")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: CollectorV35_3(key).run()

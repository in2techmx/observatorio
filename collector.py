import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN ---
MAX_PER_REGION = 8
AREAS_ESTRATEGICAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]
AREA_SYNONYMS = {
    "Seguridad y Conflictos": ["seguridad", "conflictos", "militar", "guerra", "armas", "ataque", "defensa"],
    "Economía y Sanciones": ["economía", "sanciones", "finanzas", "mercado", "comercio", "pib", "bancos"],
    "Energía y Recursos": ["energía", "recursos", "petróleo", "gas", "minería", "clima", "agua"],
    "Soberanía y Alianzas": ["soberanía", "alianzas", "diplomacia", "geopolítica", "tratados", "otan"],
    "Tecnología y Espacio": ["tecnología", "espacio", "ia", "digital", "chips", "satélites"],
    "Sociedad y Derechos": ["sociedad", "derechos", "humano", "social", "salud", "leyes"]
}

NORMALIZER_REGIONS = {"USA":"USA","RUSSIA":"RUSSIA","CHINA":"CHINA","EUROPE":"EUROPE","LATAM":"LATAM","MID_EAST":"MID_EAST","INDIA":"INDIA","AFRICA":"AFRICA","GLOBAL":"GLOBAL"}
CACHE_DIR = "vector_cache"
HISTORICO_DIR = "historico_noticias/diario"

for d in [CACHE_DIR, HISTORICO_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# ... [DICCIONARIO FUENTES IGUAL AL ANTERIOR] ...
FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", "http://rss.cnn.com/rss/edition_us.rss", "https://feeds.washingtonpost.com/rss/politics"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "http://en.kremlin.ru/events/president/news/feed", "https://themoscowtimes.com/rss/news"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "https://www.chinadaily.com.cn/rss/world_rss.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", "https://www.france24.com/en/rss", "https://rss.dw.com/xml/rss-en-all"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", "https://elpais.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss"],
    "INDIA": ["https://www.thehindu.com/news/national/feeder/default.rss"],
    "AFRICA": ["https://africa.com/feed", "http://feeds.bbci.co.uk/news/world/africa/rss.xml"],
    "GLOBAL": ["https://www.wired.com/feed/category/science/latest/rss", "https://techcrunch.com/feed/"]
}

class CollectorV35_9:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(lambda: defaultdict(list))
        self.vault, self.raw_list = {}, []

    def safe_json_parse(self, text):
        try:
            start, end = text.find('{'), text.rfind('}') + 1
            if start >= 0 and end > start: return json.loads(text[start:end])
        except: return None
        return None

    def elastic_match(self, area_raw):
        if not area_raw: return None
        raw = area_raw.lower().strip()
        for off in AREAS_ESTRATEGICAS:
            if off.lower() in raw or raw in off.lower(): return off
        for off, syns in AREA_SYNONYMS.items():
            if any(s in raw for s in syns): return off
        return None

    def save_vector(self, vector, c_hash):
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        with open(path, 'wb') as f: f.write(struct.pack(f'{len(vector)}f', *vector))

    def load_vector(self, c_hash):
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        if not os.path.exists(path): return None
        with open(path, 'rb') as f:
            data = f.read()
            return list(struct.unpack(f'{len(data)//4}f', data))

    def run(self):
        print("🌍 FASE 1: Ingesta...")
        id_counter = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        root = ET.fromstring(response.read())
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for item in items[:20]:
                            t_node = item.find('title') or item.find('{*}title')
                            l_node = item.find('link') or item.find('{*}link')
                            title = t_node.text if t_node is not None else ""
                            link = (l_node.text if l_node is not None and l_node.text else l_node.attrib.get('href', '')).strip()
                            nid = str(id_counter)
                            self.vault[nid] = {"link": link, "region": region}
                            self.raw_list.append({"id": nid, "title": title})
                            id_counter += 1
                except: continue

        print(f"🔎 FASE 2: Clasificación ({len(self.raw_list)} señales)...")
        batch_size = 45
        for i in range(0, len(self.raw_list), batch_size):
            batch = self.raw_list[i:i+batch_size]
            prompt = f"JSON format: {{'res': [{{'id': '...', 'area': '...', 'titulo_es': '...'}}]}}. Clasifica en {AREAS_ESTRATEGICAS}:\n" + "\n".join([f"ID:{x['id']}|{x['title']}" for x in batch])
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                data = self.safe_json_parse(res.text)
                if data and 'res' in data:
                    for r in data['res']:
                        matched = self.elastic_match(r.get('area'))
                        nid = str(r.get('id')).strip()
                        if matched and nid in self.vault:
                            region = self.vault[nid]['region']
                            if len(self.matrix[matched][region]) < MAX_PER_REGION:
                                self.matrix[matched][region].append({"titulo_es": r.get('titulo_es'), "link": self.vault[nid]['link'], "region": region, "base": r.get('titulo_es')})
            except: continue

        print("\n📐 FASE 3: Geometría de Gravedad Estable...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = []
            for r_list in self.matrix[area].values(): nodes.extend(r_list)
            if not nodes: continue

            # Vectorización
            vectors, to_embed_texts, to_embed_indices = [], [], []
            for idx, node in enumerate(nodes):
                c_hash = hashlib.md5(node['base'].encode()).hexdigest()
                cv = self.load_vector(c_hash)
                if cv: vectors.append(cv)
                else: vectors.append(None); to_embed_texts.append(node['base']); to_embed_indices.append(idx)

            if to_embed_texts:
                try:
                    res = self.client.models.embed_content(model="text-embedding-004", content=to_embed_texts, config={'task_type': 'RETRIEVAL_DOCUMENT'})
                    for i, emb in enumerate(res.embeddings):
                        vectors[to_embed_indices[i]] = emb.values
                        self.save_vector(emb.values, hashlib.md5(nodes[to_embed_indices[i]]['base'].encode()).hexdigest())
                except:
                    for idx in to_embed_indices: vectors[idx] = [0.1] * 768

            # --- CALCULO ROBUSTO DE PROXIMIDAD ---
            valid_v = [v for v in vectors if v]
            if len(valid_v) < 2:
                for idx in range(len(nodes)): nodes[idx]['prox'] = 85.0
            else:
                centroid = [sum(v[j] for v in valid_v)/len(valid_v) for j in range(768)]
                raw_sims = []
                for v in vectors:
                    dot = sum(a*b for a,b in zip(v, centroid))
                    mag1, mag2 = math.sqrt(sum(x*x for x in v)), math.sqrt(sum(x*x for x in centroid))
                    raw_sims.append(dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0)

                s_min, s_max = min(raw_sims), max(raw_sims)
                diff = s_max - s_min
                
                for idx, sim in enumerate(raw_sims):
                    # Si todas son iguales, centrar con jitter aleatorio leve
                    if diff < 0.0001:
                        nodes[idx]['prox'] = round(85.0 + (idx % 5), 1)
                    else:
                        # ESCALADO DINÁMICO: Forzamos distribución entre 35 y 98
                        nodes[idx]['prox'] = round(((sim - s_min) / diff) * 63 + 35, 1)

            particles = []
            for n in nodes:
                particles.append({
                    "id": hashlib.md5(n['link'].encode()).hexdigest()[:8],
                    "titulo": n['titulo_es'], "link": n['link'], 
                    "bloque": NORMALIZER_REGIONS.get(n['region'], "GLOBAL"), 
                    "proximidad": n['prox'],
                    "sesgo": "Consenso" if n['prox'] > 75 else "Divergente"
                })
            
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            final_carousel.append({"area": area, "punto_cero": f"Consenso: {area}", "color": self.get_color(area), "particulas": particles[:20]})

        res_json = {"carousel": final_carousel, "meta": {"updated": datetime.datetime.now().isoformat()}}
        with open("gravity_carousel.json", "w", encoding="utf-8") as f: json.dump(res_json, f, indent=2, ensure_ascii=False)
        fecha = datetime.datetime.now().strftime("%Y-%m-%d")
        with open(f"{HISTORICO_DIR}/{fecha}.json", "w", encoding="utf-8") as f: json.dump(res_json, f, indent=2, ensure_ascii=False)
        print(f"✅ Radar Diario generado con éxito.")

    def get_color(self, a):
        colors = {"Seguridad y Conflictos":"#ef4444","Economía y Sanciones":"#3b82f6","Energía y Recursos":"#10b981","Soberanía y Alianzas":"#f59e0b","Tecnología y Espacio":"#8b5cf6","Sociedad y Derechos":"#ec4899"}
        return colors.get(a, "#666")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: CollectorV35_9(key).run()

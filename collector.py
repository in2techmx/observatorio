import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN ESTRATÉGICA ---
MAX_PER_REGION_IN_AREA = 8
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

# Sinónimos para "ayudar" a la IA en el triaje inicial si es necesario
AREA_SYNONYMS = {
    "Seguridad y Conflictos": ["seguridad", "conflictos", "militar", "defensa", "guerra", "armas", "ataque", "ejército", "terrorismo"],
    "Economía y Sanciones": ["economía", "sanciones", "finanzas", "mercado", "comercio", "pib", "bancos", "inflación", "deuda"],
    "Energía y Recursos": ["energía", "recursos", "petróleo", "gas", "minería", "clima", "renovable", "fósil", "agua", "escasez"],
    "Soberanía y Alianzas": ["soberanía", "alianzas", "diplomacia", "geopolítica", "tratados", "otan", "brics", "onu", "embajador"],
    "Tecnología y Espacio": ["tecnología", "espacio", "ia", "digital", "chips", "satélites", "ciber", "cohete", "ciberataque"],
    "Sociedad y Derechos": ["sociedad", "derechos", "humano", "social", "salud", "leyes", "justicia", "educación", "protestas"]
}

# Mapeo para normalizar nombres de regiones en el frontend
NORMALIZER_REGIONS = {"USA":"USA","RUSSIA":"RUSSIA","CHINA":"CHINA","EUROPE":"EUROPE","LATAM":"LATAM","MID_EAST":"MID_EAST","INDIA":"INDIA","AFRICA":"AFRICA","GLOBAL":"GLOBAL"}

# Directorios de persistencia
CACHE_DIR = "vector_cache"
HISTORICO_DIR = "historico_noticias/diario"
for d in [CACHE_DIR, HISTORICO_DIR]:
    if not os.path.exists(d): os.makedirs(d)

# --- MAPA GLOBAL DE FUENTES (RED DE VIGILANCIA) ---
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

class CollectorV36:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(lambda: defaultdict(list))
        self.vault, self.raw_list = {}, []
        self.stats = {"hits": 0, "misses": 0}

    # --- UTILIDADES ---
    def safe_json_parse(self, text):
        """Extrae JSON válido de respuestas de IA ruidosas."""
        try:
            start, end = text.find('{'), text.rfind('}') + 1
            if start >= 0 and end > start: return json.loads(text[start:end])
        except: return None
        return None

    def clean_text(self, text):
        """Limpia basura HTML y CDATA de los feeds RSS."""
        if not text: return ""
        return re.sub(r'<[^>]+>', '', re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)).strip()

    def elastic_match(self, area_raw):
        """Valida si la IA devolvió un área estratégica correcta."""
        if not area_raw: return None
        raw = area_raw.lower().strip()
        for official in AREAS_ESTRATEGICAS:
            if official.lower() in raw or raw in official.lower(): return official
        for official, synonyms in AREA_SYNONYMS.items():
            if any(syn in raw for syn in synonyms): return official
        return None

    def save_vector(self, vector, c_hash):
        """Guarda el vector en caché binaria."""
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        with open(path, 'wb') as f: f.write(struct.pack(f'{len(vector)}f', *vector))

    def load_vector(self, c_hash):
        """Carga el vector de la caché binaria si existe."""
        path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
        if not os.path.exists(path): return None
        with open(path, 'rb') as f:
            data = f.read()
            return list(struct.unpack(f'{len(data)//4}f', data))

    def get_color(self, a):
        """Asigna colores consistentes a las áreas."""
        color_map = {"Seguridad y Conflictos":"#ef4444","Economía y Sanciones":"#3b82f6","Energía y Recursos":"#10b981","Soberanía y Alianzas":"#f59e0b","Tecnología y Espacio":"#8b5cf6","Sociedad y Derechos":"#ec4899"}
        return color_map.get(a, "#666")

    # --- MOTOR PRINCIPAL ---
    def run(self):
        # === FASE 1: INGESTA MASIVA ===
        print("🌍 FASE 1: Ingesta de la Red de Vigilancia...")
        id_counter = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; IntelBot/1.0)'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        root = ET.fromstring(response.read())
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        # Límite de ingesta por feed para evitar saturación
                        for item in items[:20]:
                            t_node = item.find('title') or item.find('{*}title')
                            title = self.clean_text(t_node.text) if t_node is not None else ""
                            l_node = item.find('link') or item.find('{*}link')
                            link = (l_node.text if l_node is not None and l_node.text else l_node.attrib.get('href', '')).strip()
                            
                            if title and link:
                                nid = str(id_counter)
                                self.vault[nid] = {"link": link, "region": region}
                                self.raw_list.append({"id": nid, "title": title})
                                id_counter += 1
                except Exception as e: 
                    # print(f"Error en feed {url}: {e}") # Debug opcional
                    continue

        # === FASE 2: TRIAJE COGNITIVO (GEMINI) ===
        print(f"\n🔎 FASE 2: Clasificación y Traducción ({len(self.raw_list)} señales)...")
        batch_size = 40 # Lotes optimizados para Gemini Flash
        for i in range(0, len(self.raw_list), batch_size):
            batch = self.raw_list[i:i+batch_size]
            # Prompt estricto para forzar JSON y traducción
            prompt = f"""
            Actúa como un analista de inteligencia. Tu tarea es clasificar y traducir titulares.
            Áreas Estratégicas válidas: {AREAS_ESTRATEGICAS}.
            Formato de respuesta JSON obligatorio: {{'res': [{{'id': 'ID_ORIGINAL', 'area': 'ÁREA_ESTRATÉGICA', 'titulo_es': 'TRADUCCIÓN_AL_ESPAÑOL'}}]}}
            Procesa estos titulares:
            """ + "\n".join([f"ID:{x['id']}|{x['title']}" for x in batch])
            
            try:
                # Usamos Gemini 2.0 Flash para velocidad y bajo costo
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
                data = self.safe_json_parse(res.text)
                if data and 'res' in data:
                    for r in data['res']:
                        matched_area = self.elastic_match(r.get('area'))
                        nid = str(r.get('id')).strip()
                        if matched_area and nid in self.vault and r.get('titulo_es'):
                            region = self.vault[nid]['region']
                            # Control de cupo por región dentro del área
                            if len(self.matrix[matched_area][region]) < MAX_PER_REGION_IN_AREA:
                                self.matrix[matched_area][region].append({
                                    "titulo_es": r.get('titulo_es'),
                                    "link": self.vault[nid]['link'],
                                    "region": region,
                                    "base_text_for_vector": r.get('titulo_es') # Usamos el título traducido para el vector
                                })
            except Exception as e:
                print(f"Error en batch {i//batch_size}: {e}")
                continue

        # === FASE 3: MOTOR DE CONTRASTE GEOPOLÍTICO (NUEVA LÓGICA V36) ===
        print("\n📐 FASE 3: Análisis de Fricción Narrativa Inter-Bloques...")
        final_carousel = []
        
        for area in AREAS_ESTRATEGICAS:
            nodes = []
            for r_list in self.matrix[area].values(): nodes.extend(r_list)
            
            # Si un área está vacía, se omite del carrusel final
            if not nodes: continue

            # 1. Vectorización (Con Caché)
            vectors = []
            to_embed_texts, to_embed_indices = [], []
            
            for idx, node in enumerate(nodes):
                c_hash = hashlib.md5(node['base_text_for_vector'].encode()).hexdigest()
                cv = self.load_vector(c_hash)
                if cv:
                    vectors.append(cv)
                    self.stats["hits"] += 1
                else:
                    vectors.append(None) # Placeholder
                    to_embed_texts.append(node['base_text_for_vector'])
                    to_embed_indices.append(idx)
                    self.stats["misses"] += 1

            if to_embed_texts:
                try:
                    # Usamos el modelo text-embedding-004 optimizado para retrieval
                    emb_res = self.client.models.embed_content(
                        model="text-embedding-004",
                        content=to_embed_texts,
                        config={'task_type': 'RETRIEVAL_DOCUMENT'}
                    )
                    for i, emb in enumerate(emb_res.embeddings):
                        idx_orig = to_embed_indices[i]
                        vectors[idx_orig] = emb.values
                        self.save_vector(emb.values, hashlib.md5(nodes[idx_orig]['base_text_for_vector'].encode()).hexdigest())
                except Exception as e:
                    print(f"Error crítico en embeddings: {e}. Usando vectores nulos para fallback.")
                    for idx in to_embed_indices: vectors[idx] = [0.0] * 768 # Fallback seguro

            # 2. Cálculo de Fricción por Contraste de Bloques (La Lógica Recuperada)
            
            # Agrupamos vectores válidos por su bloque regional
            bloques_v = defaultdict(list)
            valid_vectors_map = {} 

            for idx, v in enumerate(vectors):
                if v and any(v): # Asegurar que no sea un vector nulo/vacío
                    reg = nodes[idx]['region']
                    bloques_v[reg].append(v)
                    valid_vectors_map[idx] = v

            particles = []
            for idx, node in enumerate(nodes):
                # Manejo de errores si el vector falló
                if idx not in valid_vectors_map:
                    prox, sesgo = 50.0, "Sin Datos Vectoriales"
                else:
                    v_actual = valid_vectors_map[idx]
                    region_actual = node['region']

                    # Recopilar todos los vectores que NO son de mi región ("El Resto del Mundo")
                    v_antagonicos = []
                    for reg, vs in bloques_v.items():
                        if reg != region_actual:
                            v_antagonicos.extend(vs)

                    if not v_antagonicos:
                        # Caso: Solo esta región está hablando del tema hoy.
                        # No hay fricción porque no hay contraste. Posición neutra.
                        prox, sesgo = 50.0, "Perspectiva Regional Única"
                    else:
                        # Calcular el Centroide del "Resto del Mundo"
                        # (Promedio columna por columna de los vectores antagónicos)
                        resto_centroid = [sum(col)/len(col) for col in zip(*v_antagonicos)]

                        # Similitud Coseno: Mi Vector vs. Centroide del Resto
                        dot = sum(a*b for a,b in zip(v_actual, resto_centroid))
                        mag1 = math.sqrt(sum(x*x for x in v_actual))
                        mag2 = math.sqrt(sum(x*x for x in resto_centroid))

                        sim = dot / (mag1 * mag2) if (mag1 * mag2) > 0 else 0

                        # Escala directa: 
                        # Similitud 1.0 (Idéntico al resto) -> Proximidad 100 (Centro)
                        # Similitud 0.0 (Opuesto al resto) -> Proximidad 0 (Periferia)
                        # Usamos max/min para asegurar rango 0-100 ante posibles errores de float
                        prox = round(max(0.0, min(1.0, sim)) * 100, 1)

                        # Asignación de Etiquetas de Sesgo basadas en el contraste
                        if prox > 85: sesgo = "Consenso Inter-Bloque" # Coincide con la mayoría global
                        elif prox < 55: sesgo = "Divergencia Narrativa" # Se aleja de la mayoría global
                        else: sesgo = "Perspectiva en Tensión"

                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:8],
                    "titulo": node['titulo_es'],
                    "link": node['link'], 
                    "bloque": NORMALIZER_REGIONS.get(node['region'], "GLOBAL"), 
                    "proximidad": prox,
                    "sesgo": sesgo
                })
            
            # Ordenamos para que los más consensuados se procesen primero en el frontend
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            final_carousel.append({
                "area": area,
                # El punto cero ya no es un "resumen", es el concepto abstracto del consenso
                "punto_cero": f"Núcleo de Consenso: {area}", 
                "color": self.get_color(area),
                "particulas": particles[:25] # Top 25 señales más relevantes
            })

        # === FASE 4: PERSISTENCIA DUAL ===
        res_json = {"carousel": final_carousel, "meta": {"updated": datetime.datetime.now().isoformat(), "stats": self.stats}}
        
        # 1. Archivo "Vivo" para el Frontend
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(res_json, f, indent=2, ensure_ascii=False)
        
        # 2. Archivo Histórico para el Aggregator
        fecha_str = datetime.datetime.now().strftime("%Y-%m-%d")
        hist_path = os.path.join(HISTORICO_DIR, f"{fecha_str}.json")
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump(res_json, f, indent=2, ensure_ascii=False)
            
        print(f"✅ ÉXITO TOTAL. Radar generado con {sum(len(a['particulas']) for a in final_carousel)} nodos estratégicos.")
        print(f"📊 Estadísticas de Caché Vectorial: Hits={self.stats['hits']}, Misses={self.stats['misses']}")
        print(f"📂 Respaldo histórico guardado en: {hist_path}")

if __name__ == "__main__":
    # Verificación de seguridad de la API Key
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("❌ ERROR FATAL: No se encontró la variable de entorno GEMINI_API_KEY.")
        sys.exit(1)
    
    try:
        start_time = time.time()
        CollectorV36(key).run()
        print(f"⏱️ Tiempo de ejecución: {round(time.time() - start_time, 2)} segundos.")
    except KeyboardInterrupt:
        print("\n🛑 Ejecución interrumpida manualmente.")
    except Exception as e:
        print(f"\n❌ Error inesperado en el motor principal: {e}")

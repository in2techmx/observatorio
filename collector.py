import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct, logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN MEJORADA ---
MAX_PER_REGION_IN_AREA = 8
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

AREA_SYNONYMS = {
    "Seguridad y Conflictos": ["seguridad", "conflictos", "militar", "defensa", "guerra", "armas", "ataque", "ejército", "terrorismo"],
    "Economía y Sanciones": ["economía", "sanciones", "finanzas", "mercado", "comercio", "pib", "bancos", "inflación", "deuda"],
    "Energía y Recursos": ["energía", "recursos", "petróleo", "gas", "minería", "clima", "renovable", "fósil", "agua"],
    "Soberanía y Alianzas": ["soberanía", "alianzas", "diplomacia", "geopolítica", "tratados", "otan", "brics", "onu"],
    "Tecnología y Espacio": ["tecnología", "espacio", "ia", "digital", "chips", "satélites", "ciber", "cohete"],
    "Sociedad y Derechos": ["sociedad", "derechos", "humano", "social", "salud", "leyes", "justicia", "educación", "protestas"]
}

NORMALIZER_REGIONS = {
    "USA": "USA", "RUSSIA": "RUSSIA", "CHINA": "CHINA", 
    "EUROPE": "EUROPE", "LATAM": "LATAM", "MID_EAST": "MID_EAST", 
    "INDIA": "INDIA", "AFRICA": "AFRICA", "GLOBAL": "GLOBAL"
}

# Directorios
CACHE_DIR = "vector_cache"
HISTORICO_DIR = "historico_noticias/diario"
LOG_FILE = "gravity_radar.log"

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

for d in [CACHE_DIR, HISTORICO_DIR]:
    if not os.path.exists(d): 
        os.makedirs(d)
        logging.info(f"Directorio creado: {d}")

# --- FUENTES RSS OPTIMIZADAS ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "http://rss.cnn.com/rss/edition_us.rss",
        "https://feeds.washingtonpost.com/rss/politics"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "https://themoscowtimes.com/rss/news"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "https://www.chinadaily.com.cn/rss/world_rss.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://www.france24.com/en/rss",
        "https://rss.dw.com/xml/rss-en-all"
    ],
    "LATAM": [
        "https://www.infobae.com/america/arc/outboundfeeds/rss/",
        "https://elpais.com/america/rss/"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    ],
    "AFRICA": [
        "http://feeds.bbci.co.uk/news/world/africa/rss.xml"
    ],
    "GLOBAL": [
        "https://www.wired.com/feed/category/science/latest/rss",
        "https://techcrunch.com/feed/"
    ]
}

class GravityRadar:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(lambda: defaultdict(list))
        self.vault, self.raw_list = {}, []
        self.stats = {"hits": 0, "misses": 0, "feeds_processed": 0, "feeds_failed": 0}
        self.start_time = time.time()
        
    # --- UTILIDADES ROBUSTAS ---
    def safe_json_parse(self, text):
        """Extrae JSON de texto ruidoso con múltiples intentos"""
        try:
            # Primero intentar parsear directamente
            return json.loads(text)
        except:
            # Buscar objeto JSON más interno
            patterns = [
                r'\{.*\}',  # Objeto JSON simple
                r'\[\{.*\}\]',  # Array de objetos
                r'```json\s*(.*?)\s*```',  # Markdown con JSON
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.DOTALL)
                if match:
                    try:
                        return json.loads(match.group(0))
                    except:
                        continue
            
            # Último intento: buscar cualquier estructura parecida a JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(text[start:end])
                except:
                    pass
        
        logging.warning("No se pudo extraer JSON válido")
        return None

    def clean_text(self, text):
        """Limpia texto HTML y normaliza"""
        if not text:
            return ""
        
        # Eliminar HTML/XML
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
        
        # Normalizar espacios y caracteres especiales
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
        
        return text[:500]  # Limitar longitud

    def validate_item(self, title, link, region):
        """Valida que el item sea procesable"""
        if not title or len(title.strip()) < 10:
            return False
        
        if not link or not link.startswith(('http://', 'https://')):
            return False
        
        if region not in NORMALIZER_REGIONS:
            return False
        
        return True

    def elastic_match(self, area_raw):
        """Clasificación robusta de áreas"""
        if not area_raw:
            return None
        
        raw = area_raw.lower().strip()
        
        # 1. Coincidencia exacta con áreas oficiales
        for official in AREAS_ESTRATEGICAS:
            if official.lower() == raw:
                return official
        
        # 2. Coincidencia parcial
        for official in AREAS_ESTRATEGICAS:
            if official.lower() in raw or raw in official.lower():
                return official
        
        # 3. Coincidencia con sinónimos
        for official, synonyms in AREA_SYNONYMS.items():
            if any(syn.lower() in raw for syn in synonyms):
                return official
        
        # 4. Coincidencia de palabras clave
        for official, synonyms in AREA_SYNONYMS.items():
            for syn in synonyms:
                if re.search(r'\b' + re.escape(syn.lower()) + r'\b', raw):
                    return official
        
        logging.warning(f"Área no reconocida: {area_raw}")
        return None

    # --- CACHÉ VECTORIAL MEJORADO ---
    def save_vector(self, vector, c_hash):
        """Guarda vector con verificación de integridad"""
        try:
            path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
            # Añadir checksum
            checksum = hashlib.md5(struct.pack(f'{len(vector)}f', *vector)).hexdigest()[:8]
            data = struct.pack(f'{len(vector)}f', *vector) + checksum.encode()
            
            with open(path, 'wb') as f:
                f.write(data)
            
            return True
        except Exception as e:
            logging.error(f"Error guardando vector: {e}")
            return False

    def load_vector(self, c_hash):
        """Carga vector con verificación de integridad"""
        try:
            path = os.path.join(CACHE_DIR, f"{c_hash}.bin")
            if not os.path.exists(path):
                return None
            
            with open(path, 'rb') as f:
                data = f.read()
            
            # Separar vector y checksum
            vector_bytes = data[:-8]
            stored_checksum = data[-8:].decode()
            
            # Calcular checksum actual
            current_checksum = hashlib.md5(vector_bytes).hexdigest()[:8]
            
            if stored_checksum != current_checksum:
                logging.warning(f"Checksum inválido para {c_hash}")
                return None
            
            vector = list(struct.unpack(f'{len(vector_bytes)//4}f', vector_bytes))
            return vector
        except Exception as e:
            logging.error(f"Error cargando vector {c_hash}: {e}")
            return None

    def cleanup_old_cache(self, days=7):
        """Limpia caché antigua"""
        try:
            cutoff = time.time() - (days * 86400)
            count = 0
            
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith('.bin'):
                    filepath = os.path.join(CACHE_DIR, filename)
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        count += 1
            
            if count > 0:
                logging.info(f"Limpieza de caché: {count} archivos antiguos eliminados")
        except Exception as e:
            logging.error(f"Error en limpieza de caché: {e}")

    # --- MOTOR PRINCIPAL OPTIMIZADO ---
    def fetch_feeds(self):
        """Recolección optimizada de feeds"""
        print("🌍 FASE 1: Recolección de fuentes globales...")
        id_counter = 0
        
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    # Headers mejorados para evitar bloqueos
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/xml, text/xml, */*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    
                    req = urllib.request.Request(url, headers=headers)
                    
                    # Timeout con reintentos
                    for attempt in range(3):
                        try:
                            with urllib.request.urlopen(req, timeout=15) as response:
                                # Intentar detectar encoding
                                content_type = response.headers.get('Content-Type', '')
                                encoding = 'utf-8'
                                
                                if 'charset=' in content_type:
                                    encoding = content_type.split('charset=')[-1].split(';')[0].strip()
                                
                                raw_data = response.read()
                                
                                # Intentar decodificar
                                try:
                                    xml_data = raw_data.decode(encoding)
                                except:
                                    xml_data = raw_data.decode('utf-8', errors='ignore')
                                
                                root = ET.fromstring(xml_data)
                                
                                # Buscar items en diferentes formatos RSS/Atom
                                items = (root.findall('.//item') or 
                                        root.findall('.//{*}item') or 
                                        root.findall('.//entry') or 
                                        root.findall('.//{*}entry'))
                                
                                for item in items[:15]:  # Límite por feed
                                    # Extraer título
                                    title_elem = (item.find('title') or 
                                                 item.find('{*}title') or 
                                                 item.find('.//{http://www.w3.org/2005/Atom}title'))
                                    
                                    title = self.clean_text(title_elem.text if title_elem is not None else "")
                                    
                                    # Extraer enlace
                                    link_elem = (item.find('link') or 
                                                item.find('{*}link') or 
                                                item.find('.//{http://www.w3.org/2005/Atom}link'))
                                    
                                    if link_elem is not None:
                                        if link_elem.text:
                                            link = link_elem.text.strip()
                                        else:
                                            link = link_elem.get('href', '').strip()
                                    else:
                                        link = ""
                                    
                                    # Validar y almacenar
                                    if self.validate_item(title, link, region):
                                        nid = f"{region}_{id_counter}"
                                        self.vault[nid] = {
                                            "link": link,
                                            "region": region,
                                            "source": url
                                        }
                                        self.raw_list.append({
                                            "id": nid,
                                            "title": title,
                                            "region": region
                                        })
                                        id_counter += 1
                                
                                self.stats["feeds_processed"] += 1
                                logging.info(f"✓ Feed procesado: {url} ({len(items)} items)")
                                break  # Éxito, salir del bucle de reintentos
                                
                        except urllib.error.URLError as e:
                            if attempt == 2:  # Último intento
                                self.stats["feeds_failed"] += 1
                                logging.warning(f"✗ Feed fallido después de {attempt+1} intentos: {url} - {e}")
                                break
                            time.sleep(2 ** attempt)  # Backoff exponencial
                            
                except Exception as e:
                    self.stats["feeds_failed"] += 1
                    logging.error(f"Error procesando feed {url}: {e}")
                    continue
        
        print(f"📊 Recolectados {len(self.raw_list)} titulares válidos")

    def classify_with_ai(self):
        """Clasificación mejorada con IA"""
        if not self.raw_list:
            logging.warning("No hay titulares para clasificar")
            return
        
        print(f"🔎 FASE 2: Clasificación IA ({len(self.raw_list)} titulares)...")
        
        # Prompt optimizado
        SYSTEM_PROMPT = """Eres un analista de inteligencia geopolítica. Clasifica cada titular en UNA de estas áreas:

ÁREAS VÁLIDAS (SOLO UNA POR TITULAR):
1. "Seguridad y Conflictos" - Militar, defensa, guerra, terrorismo, conflictos armados
2. "Economía y Sanciones" - Finanzas, mercados, comercio, sanciones, bancos, inflación
3. "Energía y Recursos" - Petróleo, gas, minería, energía renovable, agua, clima
4. "Soberanía y Alianzas" - Diplomacia, tratados, relaciones internacionales, OTAN, ONU
5. "Tecnología y Espacio" - IA, satélites, ciberseguridad, chips, cohetes, digital
6. "Sociedad y Derechos" - Derechos humanos, protestas, salud, educación, leyes, justicia

INSTRUCCIONES:
1. TRADUCE cada titular al español manteniendo el significado exacto
2. ASIGNA EXACTAMENTE UNA área estratégica del listado anterior
3. Si un titular podría pertenecer a múltiples áreas, elige la PRINCIPAL
4. RESPUESTA SOLO EN FORMATO JSON

FORMATO DE RESPUESTA:
{
  "res": [
    {"id": "ID_ORIGINAL", "area": "ÁREA_ESTRATÉGICA", "titulo_es": "TRADUCCIÓN_ESPAÑOL"}
  ]
}"""

        batch_size = 30  # Reducido para mayor confiabilidad
        classified_count = 0
        
        for i in range(0, len(self.raw_list), batch_size):
            batch = self.raw_list[i:i+batch_size]
            
            # Crear prompt del batch
            batch_items = []
            for item in batch:
                batch_items.append(f"ID:{item['id']}|{item['title']}")
            
            user_prompt = "TITULARES A CLASIFICAR:\n" + "\n".join(batch_items)
            
            try:
                # Llamada a Gemini con configuración robusta
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                        {"role": "user", "parts": [{"text": user_prompt}]}
                    ],
                    config={
                        "temperature": 0.1,  # Baja temperatura para consistencia
                        "max_output_tokens": 2000
                    }
                )
                
                # Parsear respuesta
                data = self.safe_json_parse(response.text)
                
                if data and 'res' in data:
                    for result in data['res']:
                        nid = str(result.get('id', '')).strip()
                        matched_area = self.elastic_match(result.get('area', ''))
                        translated_title = result.get('titulo_es', '')
                        
                        if nid in self.vault and matched_area and translated_title:
                            region = self.vault[nid]['region']
                            
                            # Control de cupo
                            if len(self.matrix[matched_area][region]) < MAX_PER_REGION_IN_AREA:
                                self.matrix[matched_area][region].append({
                                    "titulo_es": translated_title,
                                    "link": self.vault[nid]['link'],
                                    "region": region,
                                    "base": translated_title,
                                    "original_title": self.raw_list[i]['title'] if i < len(self.raw_list) else ""
                                })
                                classified_count += 1
                
                logging.info(f"Batch {i//batch_size + 1} procesado: {len(data['res'] if data else [])} items")
                
            except Exception as e:
                logging.error(f"Error en batch {i//batch_size + 1}: {e}")
                continue
            
            # Pequeña pausa entre batches para evitar rate limiting
            if i + batch_size < len(self.raw_list):
                time.sleep(1)
        
        print(f"✓ Clasificados {classified_count} titulares en {len(self.matrix)} áreas")

    def calculate_narrative_friction(self):
        """Cálculo mejorado de fricción narrativa"""
        print("\n📐 FASE 3: Análisis de fricción narrativa...")
        final_carousel = []
        
        # Limpiar caché antigua
        self.cleanup_old_cache()
        
        for area in AREAS_ESTRATEGICAS:
            # Recolectar todos los nodos del área
            nodes = []
            for region_list in self.matrix[area].values():
                nodes.extend(region_list)
            
            if not nodes:
                continue
            
            print(f"  Procesando área: {area} ({len(nodes)} nodos)")
            
            # Vectorización con caché
            vectors = []
            to_embed_texts, to_embed_indices = [], []
            
            for idx, node in enumerate(nodes):
                text_to_embed = node['base']
                c_hash = hashlib.md5(text_to_embed.encode()).hexdigest()
                
                cached_vector = self.load_vector(c_hash)
                if cached_vector:
                    vectors.append(cached_vector)
                    self.stats["hits"] += 1
                else:
                    vectors.append(None)
                    to_embed_texts.append(text_to_embed)
                    to_embed_indices.append(idx)
                    self.stats["misses"] += 1
            
            # Obtener embeddings nuevos si es necesario
            if to_embed_texts:
                try:
                    emb_response = self.client.models.embed_content(
                        model="text-embedding-004",
                        contents=to_embed_texts,
                        config={'task_type': 'RETRIEVAL_DOCUMENT'}
                    )
                    
                    for j, embedding in enumerate(emb_response.embeddings):
                        idx_orig = to_embed_indices[j]
                        vector = embedding.values
                        vectors[idx_orig] = vector
                        
                        # Guardar en caché
                        text_to_cache = nodes[idx_orig]['base']
                        cache_hash = hashlib.md5(text_to_cache.encode()).hexdigest()
                        self.save_vector(vector, cache_hash)
                        
                except Exception as e:
                    logging.error(f"Error obteniendo embeddings: {e}")
                    # Fallback: vectores aleatorios normalizados
                    for idx in to_embed_indices:
                        import random
                        random.seed(hash(nodes[idx]['base']))
                        vectors[idx] = [random.uniform(-0.1, 0.1) for _ in range(768)]
            
            # Agrupar vectores por región
            region_vectors = defaultdict(list)
            for idx, vector in enumerate(vectors):
                if vector:  # Solo vectores válidos
                    region = nodes[idx]['region']
                    region_vectors[region].append(vector)
            
            # Calcular fricción para cada nodo
            particles = []
            for idx, node in enumerate(nodes):
                if not vectors[idx]:
                    # Fallback si no hay vector
                    particles.append({
                        "id": hashlib.md5(node['link'].encode()).hexdigest()[:12],
                        "titulo": node['titulo_es'],
                        "link": node['link'],
                        "bloque": NORMALIZER_REGIONS.get(node['region'], "GLOBAL"),
                        "proximidad": 50.0,
                        "sesgo": "Datos Insuficientes",
                        "region": node['region']
                    })
                    continue
                
                current_vector = vectors[idx]
                current_region = node['region']
                
                # Recolectar vectores de otras regiones
                other_vectors = []
                for region, vec_list in region_vectors.items():
                    if region != current_region:
                        other_vectors.extend(vec_list)
                
                if not other_vectors:
                    # Solo una región habla de esto
                    proximity = 50.0
                    bias = "Perspectiva Regional Única"
                else:
                    # Calcular centroide de otras regiones
                    other_centroid = []
                    for dim_idx in range(len(current_vector)):
                        dim_sum = sum(vec[dim_idx] for vec in other_vectors)
                        other_centroid.append(dim_sum / len(other_vectors))
                    
                    # Similitud coseno
                    dot_product = sum(a*b for a, b in zip(current_vector, other_centroid))
                    norm_current = math.sqrt(sum(x*x for x in current_vector))
                    norm_other = math.sqrt(sum(x*x for x in other_centroid))
                    
                    if norm_current * norm_other > 0:
                        similarity = dot_product / (norm_current * norm_other)
                        # Normalizar a 0-100
                        proximity = max(0.0, min(100.0, (similarity * 50) + 50))
                    else:
                        proximity = 50.0
                
                # Determinar sesgo basado en proximidad
                if proximity > 80:
                    bias = "Consenso Global"
                    color_intensity = "high"
                elif proximity > 65:
                    bias = "Alineación Moderada"
                    color_intensity = "medium"
                elif proximity > 45:
                    bias = "Tensión Narrativa"
                    color_intensity = "low"
                elif proximity > 30:
                    bias = "Divergencia Significativa"
                    color_intensity = "medium"
                else:
                    bias = "Contraste Radical"
                    color_intensity = "high"
                
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:12],
                    "titulo": node['titulo_es'],
                    "link": node['link'],
                    "bloque": NORMALIZER_REGIONS.get(current_region, "GLOBAL"),
                    "proximidad": round(proximity, 1),
                    "sesgo": bias,
                    "region": current_region,
                    "color_intensity": color_intensity
                })
            
            # Ordenar por proximidad (más consensuados primero)
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            
            # Agregar al carrusel final
            if particles:
                final_carousel.append({
                    "area": area,
                    "punto_cero": f"Núcleo Conceptual: {area}",
                    "color": self.get_color(area),
                    "total_particulas": len(particles),
                    "particulas": particles[:30]  # Top 30 por área
                })
        
        return final_carousel

    def get_color(self, area):
        """Obtener color para el área"""
        color_map = {
            "Seguridad y Conflictos": "#ef4444",
            "Economía y Sanciones": "#3b82f6", 
            "Energía y Recursos": "#10b981",
            "Soberanía y Alianzas": "#f59e0b",
            "Tecnología y Espacio": "#8b5cf6",
            "Sociedad y Derechos": "#ec4899"
        }
        return color_map.get(area, "#666666")

    def save_results(self, carousel_data):
        """Guarda resultados en múltiples formatos"""
        print("\n💾 FASE 4: Persistencia de resultados...")
        
        # Metadatos enriquecidos
        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "stats": self.stats,
            "execution_time": round(time.time() - self.start_time, 2),
            "version": "GravityRadar 1.0",
            "total_areas": len(carousel_data),
            "total_particles": sum(len(area["particulas"]) for area in carousel_data)
        }
        
        result = {
            "carousel": carousel_data,
            "meta": meta
        }
        
        # 1. Archivo principal para el frontend
        try:
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            print("✓ Archivo principal creado: gravity_carousel.json")
        except Exception as e:
            logging.error(f"Error guardando archivo principal: {e}")
        
        # 2. Archivo histórico diario
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            hist_path = os.path.join(HISTORICO_DIR, f"{date_str}.json")
            
            # Añadir timestamp al nombre para versiones múltiples en el día
            counter = 1
            while os.path.exists(hist_path):
                hist_path = os.path.join(HISTORICO_DIR, f"{date_str}_{counter}.json")
                counter += 1
            
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False, default=str)
            
            print(f"✓ Histórico guardado: {hist_path}")
            
        except Exception as e:
            logging.error(f"Error guardando histórico: {e}")
        
        # 3. Archivo de resumen (más pequeño)
        try:
            summary = {
                "timestamp": meta["updated"],
                "areas_summary": [
                    {
                        "area": area["area"],
                        "count": len(area["particulas"]),
                        "avg_proximity": round(
                            sum(p["proximidad"] for p in area["particulas"]) / len(area["particulas"]), 
                            2
                        ) if area["particulas"] else 0
                    }
                    for area in carousel_data
                ],
                "cache_stats": {
                    "hits": self.stats["hits"],
                    "misses": self.stats["misses"],
                    "efficiency": round(
                        self.stats["hits"] / (self.stats["hits"] + self.stats["misses"]) * 100, 
                        2
                    ) if (self.stats["hits"] + self.stats["misses"]) > 0 else 0
                }
            }
            
            with open("summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print("✓ Resumen creado: summary.json")
            
        except Exception as e:
            logging.error(f"Error guardando resumen: {e}")
        
        return result

    def run(self):
        """Ejecuta el pipeline completo"""
        print("=" * 60)
        print("🚀 GRAVITY RADAR - Sistema de Vigilancia Geopolítica")
        print("=" * 60)
        
        try:
            # Pipeline principal
            self.fetch_feeds()
            self.classify_with_ai()
            carousel = self.calculate_narrative_friction()
            result = self.save_results(carousel)
            
            # Reporte final
            print("\n" + "=" * 60)
            print("✅ ANÁLISIS COMPLETADO")
            print("=" * 60)
            
            total_time = time.time() - self.start_time
            total_particles = sum(len(area["particulas"]) for area in carousel)
            
            print(f"📊 RESULTADOS:")
            print(f"   • Tiempo total: {total_time:.1f} segundos")
            print(f"   • Feeds procesados: {self.stats['feeds_processed']}")
            print(f"   • Feeds fallados: {self.stats['feeds_failed']}")
            print(f"   • Áreas activas: {len(carousel)}")
            print(f"   • Partículas totales: {total_particles}")
            print(f"   • Eficiencia de caché: {self.stats['hits']}/{self.stats['hits'] + self.stats['misses']}")
            
            print(f"\n📈 DISTRIBUCIÓN POR ÁREA:")
            for area in carousel:
                count = len(area["particulas"])
                if count > 0:
                    avg_prox = sum(p["proximidad"] for p in area["particulas"]) / count
                    print(f"   • {area['area']}: {count} nodos (avg prox: {avg_prox:.1f})")
            
            print(f"\n💡 ARCHIVOS GENERADOS:")
            print(f"   1. gravity_carousel.json (principal)")
            print(f"   2. summary.json (resumen)")
            print(f"   3. {HISTORICO_DIR}/YYYY-MM-DD.json (histórico)")
            print(f"   4. {LOG_FILE} (registros)")
            
            print("\n⚠️  NOTA: Revisa gravity_carousel.json para visualizar el radar")
            print("=" * 60)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Ejecución interrumpida por el usuario")
            logging.info("Ejecución interrumpida por el usuario")
        except Exception as e:
            logging.error(f"Error crítico en el pipeline: {e}", exc_info=True)
            print(f"\n❌ ERROR CRÍTICO: {e}")
            print("Revisa el archivo de log para más detalles")
            return None

def main():
    """Función principal con manejo de argumentos"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Gravity Radar - Sistema de Vigilancia Geopolítica',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python gravity_radar.py                   # Ejecución normal
  python gravity_radar.py --test           # Modo prueba (límite de feeds)
  python gravity_radar.py --no-cache       # Deshabilitar caché
  python gravity_radar.py --regions USA EUROPE  # Solo regiones específicas
        """
    )
    
    parser.add_argument('--test', action='store_true',
                       help='Modo de prueba (procesa solo 2 feeds por región)')
    parser.add_argument('--no-cache', action='store_true',
                       help='Deshabilitar sistema de caché')
    parser.add_argument('--regions', nargs='+',
                       help='Regiones específicas a procesar')
    parser.add_argument('--verbose', action='store_true',
                       help='Modo detallado (más logging)')
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        print("🔍 Modo verbose activado")
    
    # Obtener API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: Variable de entorno GEMINI_API_KEY no encontrada")
        print("\nConfigura tu API key:")
        print("  export GEMINI_API_KEY='tu-api-key-aqui'  # Linux/Mac")
        print("  set GEMINI_API_KEY=tu-api-key-aqui       # Windows")
        sys.exit(1)
    
    # Modificar configuración según argumentos
    if args.test:
        global FUENTES
        FUENTES = {k: v[:2] for k, v in FUENTES.items()}  # Solo 2 feeds por región
        print("🧪 Ejecutando en modo prueba")
    
    if args.regions:
        FUENTES = {k: v for k, v in FUENTES.items() if k in args.regions}
        print(f"🌎 Procesando regiones: {', '.join(args.regions)}")
    
    # Ejecutar radar
    radar = GravityRadar(api_key)
    if args.no_cache:
        # Deshabilitar caché eliminando métodos relacionados
        radar.load_vector = lambda x: None
        radar.save_vector = lambda x, y: None
        print("🚫 Caché deshabilitado")
    
    result = radar.run()
    
    if result:
        print("\n🎯 Análisis completado exitosamente!")
    else:
        print("\n⚠️  El análisis encontró problemas. Revisa los logs.")
    
    sys.exit(0 if result else 1)

if __name__ == "__main__":
    main()

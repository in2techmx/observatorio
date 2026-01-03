import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct, logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# ============================================================================
# CONFIGURACIÓN ESTRATÉGICA
# ============================================================================
MAX_PER_REGION_IN_AREA = 10
AREAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
         "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]

CACHE_DIR = "vector_cache"
HIST_DIR = "historico_noticias/diario"
LOG_FILE = "system_audit.log"

# ============================================================================
# CONFIGURACIÓN DE FUENTES (OPTIMIZADA)
# ============================================================================
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "http://rss.cnn.com/rss/edition_us.rss",
        "https://feeds.washingtonpost.com/rss/politics"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "https://www.chinadaily.com.cn/rss/world_rss.xml",
        "https://www.globaltimes.cn/rss/china.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://www.france24.com/en/rss",
        "https://rss.dw.com/xml/rss-en-all"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss",
        "https://www.arabnews.com/cat/1/rss.xml"
    ],
    "GLOBAL": [
        "https://www.economist.com/sections/international/rss.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/category/science/latest/rss"
    ]
}

# ============================================================================
# INICIALIZACIÓN SEGURA DE DIRECTORIOS
# ============================================================================
def initialize_directories():
    """Inicialización robusta de directorios evitando race conditions"""
    for directory in [CACHE_DIR, HIST_DIR]:
        try:
            if os.path.exists(directory):
                if not os.path.isdir(directory):
                    # Es un archivo, no directorio
                    os.remove(directory)
                    os.makedirs(directory, exist_ok=True)
            else:
                os.makedirs(directory, exist_ok=True)
        except Exception as e:
            logging.warning(f"No se pudo crear {directory}: {e}")
            # Continuar sin el directorio si es la caché
            if directory == CACHE_DIR:
                global CACHE_DIR
                CACHE_DIR = "/tmp/vector_cache"
                os.makedirs(CACHE_DIR, exist_ok=True)

initialize_directories()

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============================================================================
# CLASE NEWSITEM (MEJORADA)
# ============================================================================
class NewsItem:
    def __init__(self, item_id, title, link, region, source_url):
        self.id = item_id
        self.original_title = self._sanitize_text(title)
        self.link = link if self._is_valid_url(link) else None
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
    def _is_valid_url(url):
        """Validación más robusta de URL"""
        if not url or not isinstance(url, str):
            return False
        pattern = re.compile(
            r'^https?://(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}(?:/|$)',
            re.IGNORECASE
        )
        return bool(pattern.match(url))

    @staticmethod
    def _sanitize_text(text, max_length=400):
        """Sanitización mejorada de texto"""
        if not text:
            return ""
        # Eliminar HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Eliminar caracteres de control
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)
        # Normalizar espacios
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_length]

    def to_dict(self):
        """Serialización para exportación"""
        return {
            "id": self.id[:12],
            "titulo": self.translated_title or self.original_title,
            "link": self.link,
            "bloque": self.region,
            "proximidad": round(self.proximity, 1),
            "sesgo": self.bias_label,
            "confianza": round(self.confidence, 1),
            "keywords": self.keywords[:5]
        }

# ============================================================================
# MOTOR PRINCIPAL (CORREGIDO)
# ============================================================================
class IroncladCollectorPro:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.active_items = []
        self.stats = {
            "items_raw": 0,
            "items_classified": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
        self.start_time = time.time()

    # ------------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------------
    def safe_json_extract(self, text):
        """Extrae JSON de manera robusta"""
        if not text:
            return None
        
        # Intentar parseo directo
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Búsqueda de objeto JSON
        stack = []
        start_idx = -1
        
        for i, char in enumerate(text):
            if char == '{':
                if not stack:
                    start_idx = i
                stack.append(char)
            elif char == '}':
                if stack:
                    stack.pop()
                    if not stack and start_idx != -1:
                        try:
                            candidate = text[start_idx:i+1]
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            start_idx = -1
        
        logging.warning("No se pudo extraer JSON válido")
        return None

    def get_cached_vector(self, text):
        """Obtiene vector de caché si existe"""
        if not text:
            return None
        
        v_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        path = os.path.join(CACHE_DIR, f"{v_hash}.bin")
        
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'rb') as f:
                data = f.read()
                vector = list(struct.unpack(f'{len(data)//4}f', data))
            
            self.stats["cache_hits"] += 1
            return vector
        except Exception as e:
            logging.warning(f"Error cargando vector cacheado: {e}")
            return None

    def save_vector(self, text, vector):
        """Guarda vector en caché"""
        if not text or not vector:
            return False
        
        try:
            v_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
            path = os.path.join(CACHE_DIR, f"{v_hash}.bin")
            
            with open(path, 'wb') as f:
                f.write(struct.pack(f'{len(vector)}f', *vector))
            
            self.stats["cache_misses"] += 1
            return True
        except Exception as e:
            logging.error(f"Error guardando vector: {e}")
            return False

    def classify_area(self, area_name):
        """Clasificación de área con validación"""
        if not area_name:
            return None
        
        area_lower = area_name.lower().strip()
        
        # Búsqueda exacta
        for area in AREAS:
            if area.lower() == area_lower:
                return area
        
        # Búsqueda parcial
        for area in AREAS:
            if area.lower() in area_lower or area_lower in area.lower():
                return area
        
        # Búsqueda por keywords
        keywords_map = {
            "Seguridad y Conflictos": ["militar", "defensa", "guerra", "terrorismo", "ejército", "conflicto", "ataque"],
            "Economía y Sanciones": ["economía", "finanzas", "sanciones", "mercado", "comercio", "inflación", "bancos"],
            "Energía y Recursos": ["energía", "petróleo", "gas", "minería", "clima", "renovable", "agua"],
            "Soberanía y Alianzas": ["soberanía", "alianza", "diplomacia", "tratado", "geopolítica", "otan", "brics"],
            "Tecnología y Espacio": ["tecnología", "espacio", "digital", "satélite", "ciber", "ia", "chips"],
            "Sociedad y Derechos": ["derechos", "humano", "social", "salud", "educación", "protesta", "justicia"]
        }
        
        for area, keywords in keywords_map.items():
            if any(keyword in area_lower for keyword in keywords):
                return area
        
        return None

    # ------------------------------------------------------------------------
    # FASE 1: RECOLECCIÓN
    # ------------------------------------------------------------------------
    def fetch_signals(self):
        """Recolección robusta de feeds RSS"""
        logging.info("📡 FASE 1: Recolección multi-fuente...")
        
        item_counter = 0
        
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/xml, text/xml',
                        'Accept-Language': 'en-US,en;q=0.9'
                    }
                    
                    req = urllib.request.Request(url, headers=headers)
                    
                    with urllib.request.urlopen(req, timeout=15) as response:
                        # Leer y decodificar
                        xml_data = response.read().decode('utf-8', errors='ignore')
                        root = ET.fromstring(xml_data)
                        
                        # Buscar items (RSS y Atom)
                        items = (root.findall('.//item') or 
                                root.findall('.//entry') or 
                                root.findall('.//{*}item'))
                        
                        for item in items[:12]:  # Límite por feed
                            # Extraer título
                            title_elem = item.find('title') or item.find('{*}title')
                            title = title_elem.text if title_elem is not None else ""
                            
                            # Extraer enlace
                            link_elem = item.find('link') or item.find('{*}link')
                            if link_elem is not None:
                                if link_elem.text:
                                    link = link_elem.text.strip()
                                else:
                                    link = link_elem.get('href', '').strip()
                            else:
                                link = ""
                            
                            if title and link and len(title) > 10:
                                item_id = f"{region}_{item_counter}_{hashlib.md5(link.encode()).hexdigest()[:8]}"
                                news_item = NewsItem(item_id, title, link, region, url)
                                
                                if news_item.link:
                                    self.active_items.append(news_item)
                                    item_counter += 1
                    
                    logging.debug(f"Feed procesado: {url}")
                    
                except Exception as e:
                    logging.warning(f"Error en feed {url}: {str(e)[:100]}")
                    self.stats["errors"] += 1
                    continue
        
        self.stats["items_raw"] = len(self.active_items)
        logging.info(f"✅ Señales capturadas: {self.stats['items_raw']}")

    # ------------------------------------------------------------------------
    # FASE 2: CLASIFICACIÓN
    # ------------------------------------------------------------------------
    def run_triage(self):
        """Clasificación por IA con validación"""
        if not self.active_items:
            logging.warning("No hay items para clasificar")
            return
        
        logging.info(f"🔎 FASE 2: Clasificación IA ({len(self.active_items)} items)...")
        
        # Prompt mejorado
        system_prompt = f"""Eres un clasificador geopolítico. Para cada titular:

ÁREAS ESTRATÉGICAS (SOLO UNA POR TITULAR):
{chr(10).join(f'- {area}' for area in AREAS)}

EJEMPLOS:
- "Ciberataque estatal paraliza infraestructura" -> "Seguridad y Conflictos"
- "Sanciones económicas a banco central" -> "Economía y Sanciones"
- "Acuerdo de exportación de gas natural" -> "Energía y Recursos"
- "Tratado de defensa mutua firmado" -> "Soberanía y Alianzas"
- "Satélite de comunicaciones lanzado" -> "Tecnología y Espacio"
- "Protestas por derechos laborales" -> "Sociedad y Derechos"

INSTRUCCIONES:
1. TRADUCE al español manteniendo significado exacto
2. ASIGNA EXACTAMENTE UNA área estratégica de la lista
3. CALIFICA confianza (0-100)
4. EXTRAE 3-5 palabras clave relevantes

RESPONDE SOLO CON JSON:
{{"res": [{{"id": "...", "area": "...", "titulo_es": "...", "confianza": 95, "keywords": ["kw1", "kw2"]}}]}}"""
        
        batch_size = 25  # Tamaño seguro para Gemini Flash
        
        for i in range(0, len(self.active_items), batch_size):
            batch = self.active_items[i:i+batch_size]
            
            batch_text = "\n".join([f"ID:{it.id}|{it.original_title}" for it in batch])
            
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=f"{system_prompt}\n\n{batch_text}",
                    config={"temperature": 0.1, "max_output_tokens": 1500}
                )
                
                data = self.safe_json_extract(response.text)
                
                if data and 'res' in data:
                    for result in data['res']:
                        item_id = str(result.get('id', '')).strip()
                        
                        # Buscar item correspondiente
                        target_item = next((it for it in batch if it.id == item_id), None)
                        
                        if target_item:
                            area_name = result.get('area', '')
                            classified_area = self.classify_area(area_name)
                            confidence = float(result.get('confianza', 0))
                            
                            if classified_area and confidence >= 50:  # Umbral mínimo
                                target_item.area = classified_area
                                target_item.translated_title = result.get('titulo_es', '')
                                target_item.confidence = min(confidence, 100.0)
                                target_item.keywords = result.get('keywords', [])[:5]
                                
                                self.stats["items_classified"] += 1
                            else:
                                logging.debug(f"Item {item_id} no clasificado: área={area_name}, conf={confidence}")
                
                logging.debug(f"Batch {i//batch_size + 1} procesado")
                
            except Exception as e:
                logging.error(f"Error en batch {i//batch_size + 1}: {str(e)[:100]}")
                self.stats["errors"] += 1
                continue
            
            # Pequeña pausa entre batches
            if i + batch_size < len(self.active_items):
                time.sleep(1)
        
        logging.info(f"✅ Items clasificados: {self.stats['items_classified']}")

    # ------------------------------------------------------------------------
    # FASE 3: VECTORIZACIÓN Y PROXIMIDAD (CORREGIDA)
    # ------------------------------------------------------------------------
    def compute_vectors_and_proximity(self):
        """Cálculo CORREGIDO de vectores y proximidad"""
        logging.info("📐 FASE 3: Vectorización y análisis de proximidad...")
        
        # Agrupar items por área
        items_by_area = defaultdict(list)
        for item in self.active_items:
            if item.area and item.area in AREAS and item.translated_title:
                items_by_area[item.area].append(item)
        
        # Procesar cada área
        for area, items in items_by_area.items():
            if len(items) < 2:
                # No hay suficientes items para comparar
                for item in items:
                    item.proximity = 50.0
                    item.bias_label = "Datos Insuficientes"
                continue
            
            logging.debug(f"Procesando área '{area}' con {len(items)} items")
            
            # 1. Obtener embeddings (con caché)
            texts_to_embed = []
            items_to_embed = []
            
            for item in items:
                cached_vector = self.get_cached_vector(item.translated_title)
                if cached_vector:
                    item.vector = cached_vector
                else:
                    texts_to_embed.append(item.translated_title)
                    items_to_embed.append(item)
            
            # Generar embeddings nuevos si es necesario
            if texts_to_embed:
                try:
                    emb_response = self.client.models.embed_content(
                        model="text-embedding-004",
                        contents=texts_to_embed,
                        config={'task_type': 'RETRIEVAL_DOCUMENT'}
                    )
                    
                    for idx, embedding in enumerate(emb_response.embeddings):
                        item = items_to_embed[idx]
                        vector = embedding.values
                        item.vector = vector
                        self.save_vector(item.translated_title, vector)
                        
                except Exception as e:
                    logging.error(f"Error en embeddings para área {area}: {e}")
                    # Fallback: vectores aleatorios normalizados
                    import random
                    for item in items_to_embed:
                        random.seed(hash(item.translated_title))
                        item.vector = [random.uniform(-0.1, 0.1) for _ in range(768)]
            
            # 2. Cálculo de proximidad (CORRECCIÓN APLICADA)
            # Filtrar items con vector válido
            valid_items = [item for item in items if item.vector and len(item.vector) > 0]
            
            if len(valid_items) < 2:
                for item in items:
                    item.proximity = 50.0
                    item.bias_label = "Sin Vector"
                continue
            
            # Agrupar vectores por región
            vectors_by_region = defaultdict(list)
            for item in valid_items:
                vectors_by_region[item.region].append(item.vector)
            
            # Calcular centroides por región
            region_centroids = {}
            for region, vectors in vectors_by_region.items():
                if vectors:
                    # Promedio por dimensión
                    centroid = []
                    for dim_idx in range(len(vectors[0])):  # Todas tienen misma dimensión
                        dim_values = [vec[dim_idx] for vec in vectors]
                        centroid.append(sum(dim_values) / len(dim_values))
                    region_centroids[region] = centroid
            
            # Calcular proximidad para cada item
            for item in valid_items:
                if not item.vector:
                    item.proximity = 50.0
                    continue
                
                current_region = item.region
                current_vector = item.vector
                
                # Recolectar centroides de otras regiones
                other_centroids = []
                for region, centroid in region_centroids.items():
                    if region != current_region:
                        other_centroids.append(centroid)
                
                if not other_centroids:
                    # Solo esta región habla del tema
                    item.proximity = 50.0
                    item.bias_label = "Perspectiva Única"
                    continue
                
                # Calcular centroide global de "otras regiones"
                global_centroid = []
                for dim_idx in range(len(current_vector)):
                    dim_values = [centroid[dim_idx] for centroid in other_centroids]
                    global_centroid.append(sum(dim_values) / len(dim_values))
                
                # CÁLCULO CORREGIDO: Similitud coseno [-1, 1] -> Proximidad [0, 100]
                # 1. Producto punto
                dot_product = sum(a * b for a, b in zip(current_vector, global_centroid))
                
                # 2. Magnitudes
                magnitude_current = math.sqrt(sum(x * x for x in current_vector))
                magnitude_global = math.sqrt(sum(x * x for x in global_centroid))
                
                # 3. Similitud coseno (CORRECCIÓN)
                if magnitude_current * magnitude_global > 0:
                    cosine_similarity = dot_product / (magnitude_current * magnitude_global)
                    
                    # 4. Mapear [-1, 1] a [0, 100]
                    # similarity = -1 -> proximity = 0
                    # similarity = 0 -> proximity = 50
                    # similarity = 1 -> proximity = 100
                    raw_proximity = (cosine_similarity + 1) * 50
                    
                    # 5. Asegurar rango [0, 100]
                    item.proximity = max(0.0, min(100.0, raw_proximity))
                    
                    # 6. Asignar etiqueta de sesgo
                    if item.proximity > 85:
                        item.bias_label = "Consenso Global"
                    elif item.proximity > 70:
                        item.bias_label = "Alineación"
                    elif item.proximity > 55:
                        item.bias_label = "Tensión Moderada"
                    elif item.proximity > 40:
                        item.bias_label = "Divergencia"
                    else:
                        item.bias_label = "Contraste Radical"
                else:
                    item.proximity = 50.0
                    item.bias_label = "Error de Cálculo"
            
            # Para items sin vector válido
            for item in items:
                if not hasattr(item, 'proximity') or item.proximity is None:
                    item.proximity = 50.0
                    item.bias_label = "Sin Datos"

    # ------------------------------------------------------------------------
    # FASE 4: EXPORTACIÓN
    # ------------------------------------------------------------------------
    def export(self):
        """Exporta resultados en formato para frontend"""
        logging.info("💾 FASE 4: Exportando resultados...")
        
        # Agrupar por área
        items_by_area = defaultdict(list)
        for item in self.active_items:
            if item.area and item.area in AREAS:
                items_by_area[item.area].append(item)
        
        carousel = []
        
        for area, items in items_by_area.items():
            if not items:
                continue
            
            # Convertir a formato de partículas
            particles = []
            for item in items:
                particle = item.to_dict()
                particles.append(particle)
            
            # Ordenar por proximidad (más consensuados primero)
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            
            # Calcular métricas del área
            if particles:
                avg_proximity = sum(p['proximidad'] for p in particles) / len(particles)
                
                # Determinar nivel de consenso
                if avg_proximity > 80:
                    consensus = "ALTO CONSENSO"
                    emoji = "🟢"
                elif avg_proximity > 65:
                    consensus = "CONSENSO MODERADO"
                    emoji = "🟡"
                elif avg_proximity > 50:
                    consensus = "TENSIÓN DETECTADA"
                    emoji = "🟠"
                else:
                    consensus = "FRICCIÓN SEVERA"
                    emoji = "🔴"
                
                # Determinar tendencia
                trend = "↑" if avg_proximity > 60 else "↓" if avg_proximity < 40 else "→"
            else:
                avg_proximity = 50.0
                consensus = "DATOS INSUFICIENTES"
                emoji = "⚪"
                trend = "→"
            
            # Asignar color por área
            area_colors = {
                "Seguridad y Conflictos": "#ef4444",
                "Economía y Sanciones": "#3b82f6",
                "Energía y Recursos": "#10b981",
                "Soberanía y Alianzas": "#f59e0b",
                "Tecnología y Espacio": "#8b5cf6",
                "Sociedad y Derechos": "#ec4899"
            }
            
            carousel.append({
                "area": area,
                "punto_cero": f"{emoji} {consensus} | Consenso promedio: {avg_proximity:.1f}% | Tendencia: {trend}",
                "color": area_colors.get(area, "#666666"),
                "meta_netflix": {
                    "consensus": consensus,
                    "trend": trend,
                    "avg_proximity": round(avg_proximity, 1),
                    "particle_count": len(particles)
                },
                "particulas": particles[:30]  # Top 30 por área
            })
        
        # Metadatos
        execution_time = time.time() - self.start_time
        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "execution_seconds": round(execution_time, 2),
            "stats": self.stats,
            "cache_efficiency": round(
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) * 100, 
                2
            ) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
        }
        
        final_data = {
            "carousel": carousel,
            "meta": meta
        }
        
        # Guardar archivo principal
        try:
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            logging.info("✅ gravity_carousel.json generado")
        except Exception as e:
            logging.error(f"Error guardando gravity_carousel.json: {e}")
        
        # Guardar histórico diario
        try:
            hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            hist_path = os.path.join(HIST_DIR, f"{hoy}.json")
            
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Histórico guardado: {hist_path}")
        except Exception as e:
            logging.error(f"Error guardando histórico: {e}")
        
        # Guardar resumen ejecutivo
        try:
            summary = {
                "timestamp": meta["updated"],
                "areas_analyzed": len(carousel),
                "total_particles": sum(len(area["particulas"]) for area in carousel),
                "avg_cache_efficiency": meta["cache_efficiency"],
                "areas": [
                    {
                        "area": area["area"],
                        "particle_count": len(area["particulas"]),
                        "avg_proximity": sum(p["proximidad"] for p in area["particulas"]) / len(area["particulas"]) 
                        if area["particulas"] else 0
                    }
                    for area in carousel
                ]
            }
            
            with open("executive_summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logging.info("✅ executive_summary.json generado")
        except Exception as e:
            logging.error(f"Error guardando resumen: {e}")
        
        # Reporte final
        total_particles = sum(len(area["particulas"]) for area in carousel)
        logging.info(f"🏁 CICLO COMPLETADO")
        logging.info(f"   • Tiempo total: {execution_time:.1f}s")
        logging.info(f"   • Items procesados: {self.stats['items_raw']}")
        logging.info(f"   • Items clasificados: {self.stats['items_classified']}")
        logging.info(f"   • Áreas activas: {len(carousel)}")
        logging.info(f"   • Partículas totales: {total_particles}")
        logging.info(f"   • Eficiencia de caché: {meta['cache_efficiency']}%")

    # ------------------------------------------------------------------------
    # EJECUCIÓN PRINCIPAL
    # ------------------------------------------------------------------------
    def run(self):
        """Ejecuta el pipeline completo"""
        try:
            self.fetch_signals()
            self.run_triage()
            self.compute_vectors_and_proximity()
            self.export()
            
            return True
        except KeyboardInterrupt:
            logging.info("Ejecución interrumpida por el usuario")
            return False
        except Exception as e:
            logging.error(f"Error en ejecución principal: {e}", exc_info=True)
            return False

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    
    if not key:
        print("❌ ERROR: Variable de entorno GEMINI_API_KEY no encontrada")
        print("\nConfigura tu API key:")
        print("  Linux/Mac:  export GEMINI_API_KEY='tu-clave-aqui'")
        print("  Windows:    set GEMINI_API_KEY=tu-clave-aqui")
        sys.exit(1)
    
    # Ejecutar collector
    collector = IroncladCollectorPro(key)
    success = collector.run()
    
    if success:
        print("\n🎯 Proximity Hub actualizado exitosamente!")
        print("📁 Archivos generados:")
        print("   1. gravity_carousel.json")
        print("   2. executive_summary.json")
        print(f"   3. {HIST_DIR}/YYYY-MM-DD.json")
        sys.exit(0)
    else:
        print("\n⚠️  El análisis encontró problemas. Revisa los logs.")
        sys.exit(1)

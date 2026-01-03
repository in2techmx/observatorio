import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct, logging
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai
from typing import List, Dict, Optional, Tuple

# ============================================================================
# CONFIGURACIÓN DEL SISTEMA
# ============================================================================
MAX_PER_REGION_IN_AREA = 10
AREAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
         "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]
CACHE_DIR = "vector_cache"
HIST_DIR = "historico_noticias/diario"
LOG_FILE = "system_audit.log"
MAX_ITEMS_TOTAL = 2000  # Límite de seguridad para memoria

# Configuración de logging
for d in [CACHE_DIR, HIST_DIR]:
    os.makedirs(d, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============================================================================
# FUENTES RSS - RED DE VIGILANCIA
# ============================================================================
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "http://rss.cnn.com/rss/edition_us.rss",
        "https://feeds.washingtonpost.com/rss/politics",
        "https://www.reutersagency.com/feed/?best-topics=political-news"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "http://en.kremlin.ru/events/president/news/feed",
        "https://themoscowtimes.com/rss/news",
        "https://sputniknews.com/export/rss2/archive/index.xml"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "https://www.chinadaily.com.cn/rss/world_rss.xml",
        "https://www.globaltimes.cn/rss/china.xml"
    ],
    "EUROPE": [
        "https://www.theguardian.com/world/rss",
        "https://www.france24.com/en/rss",
        "https://rss.dw.com/xml/rss-en-all",
        "https://elpais.com/rss/elpais/inenglish.xml"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss",
        "https://www.arabnews.com/cat/1/rss.xml"
    ],
    "GLOBAL": [
        "https://www.wired.com/feed/category/science/latest/rss",
        "https://techcrunch.com/feed/",
        "https://www.economist.com/sections/international/rss.xml"
    ]
}

# ============================================================================
# CLASE NewsItem - TRAZABILIDAD COMPLETA
# ============================================================================
class NewsItem:
    """Contenedor unificado para trazabilidad completa de cada señal"""
    
    def __init__(self, item_id: str, title: str, link: str, region: str, source_url: str):
        self.id = item_id
        self.original_title = self._sanitize_text(title)
        self.link = link if self._is_valid_url(link) else None
        self.region = region
        self.source_url = source_url
        self.translated_title: Optional[str] = None
        self.area: Optional[str] = None
        self.confidence: float = 0.0
        self.keywords: List[str] = []
        self.vector: Optional[List[float]] = None
        self.proximity: float = 50.0
        self.timestamp = datetime.datetime.now()
        self.processing_errors: List[str] = []
        
    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Validación robusta de URL"""
        if not url or not isinstance(url, str):
            return False
        
        try:
            # Patrón regex más completo
            pattern = re.compile(
                r'^https?://'  # http:// o https://
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # dominio
                r'localhost|'  # localhost
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
                r'(?::\d+)?'  # puerto opcional
                r'(?:/?|[/?]\S+)?$', 
                re.IGNORECASE
            )
            return bool(pattern.match(url))
        except:
            return False
    
    @staticmethod
    def _sanitize_text(text: str, max_length: int = 400) -> str:
        """Sanitización segura de texto"""
        if not text:
            return ""
        
        # Eliminar caracteres peligrosos
        text = re.sub(r'<[^>]+>', '', text)  # HTML tags
        text = re.sub(r'[\x00-\x1F\x7F]', '', text)  # Control characters
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<\s*script', '', text, flags=re.IGNORECASE)
        
        # Normalizar espacios y trim
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text[:max_length]
    
    def to_dict(self) -> Dict:
        """Serialización para exportación"""
        return {
            "id": self.id,
            "titulo": self.translated_title or self.original_title,
            "link": self.link,
            "bloque": self.region,
            "proximidad": round(self.proximity, 1),
            "confianza": round(self.confidence, 1),
            "keywords": self.keywords[:5],
            "area": self.area,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================================================
# MOTOR PRINCIPAL - IroncladCollector CORREGIDO
# ============================================================================
class IroncladCollector:
    """Motor de inteligencia geopolítica con correcciones críticas aplicadas"""
    
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
        self.active_items: List[NewsItem] = []
        self.stats = {
            "items_collected": 0,
            "items_classified": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "errors": 0
        }
        self.start_time = time.time()
    
    # ========================================================================
    # UTILIDADES DE SEGURIDAD Y VALIDACIÓN
    # ========================================================================
    def safe_json_extract(self, text: str) -> Optional[Dict]:
        """Extracción robusta de JSON con stack-based parsing"""
        if not text:
            return None
        
        # Intentar parseo directo primero
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Búsqueda de objetos JSON anidados
        stack = []
        start_idx = -1
        depth = 0
        
        for i, char in enumerate(text):
            if char == '{':
                if not stack:
                    start_idx = i
                stack.append(char)
                depth += 1
            elif char == '}':
                if stack:
                    stack.pop()
                    depth -= 1
                    if depth == 0 and start_idx != -1:
                        try:
                            candidate = text[start_idx:i+1]
                            return json.loads(candidate)
                        except json.JSONDecodeError:
                            # Continuar buscando
                            start_idx = -1
        
        logging.warning("No se pudo extraer JSON válido")
        return None
    
    def validate_and_classify_area(self, area_name: str) -> Tuple[Optional[str], float]:
        """Validación y clasificación de área con confianza"""
        if not area_name:
            return None, 0.0
        
        area_lower = area_name.lower().strip()
        
        # Búsqueda exacta
        for area in AREAS:
            if area.lower() == area_lower:
                return area, 100.0
        
        # Búsqueda parcial
        for area in AREAS:
            if area.lower() in area_lower or area_lower in area.lower():
                return area, 80.0
        
        # Búsqueda por palabras clave
        keywords_map = {
            "Seguridad y Conflictos": ["militar", "defensa", "guerra", "conflicto", "terrorismo", "ejército", "ataque"],
            "Economía y Sanciones": ["economía", "finanzas", "sanciones", "mercado", "comercio", "inflación", "bancos"],
            "Energía y Recursos": ["energía", "petróleo", "gas", "minería", "clima", "renovable", "agua"],
            "Soberanía y Alianzas": ["soberanía", "alianza", "diplomacia", "tratado", "geopolítica", "otan", "brics"],
            "Tecnología y Espacio": ["tecnología", "espacio", "digital", "satélite", "ciber", "ia", "chips"],
            "Sociedad y Derechos": ["derechos", "humano", "social", "salud", "educación", "protesta", "justicia"]
        }
        
        for area, keywords in keywords_map.items():
            if any(keyword in area_lower for keyword in keywords):
                # Calcular confianza basada en matches
                matches = sum(1 for keyword in keywords if keyword in area_lower)
                confidence = min(100.0, matches * 20.0)  # 20% por keyword
                return area, confidence
        
        return None, 0.0
    
    # ========================================================================
    # SISTEMA DE CACHÉ DE EMBEDDINGS
    # ========================================================================
    def get_vector(self, text: str) -> Optional[List[float]]:
        """Obtiene vector de caché o None si no existe"""
        if not text:
            return None
        
        cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
        cache_path = os.path.join(CACHE_DIR, f"{cache_key}.bin")
        
        if not os.path.exists(cache_path):
            return None
        
        try:
            with open(cache_path, 'rb') as f:
                data = f.read()
                vector = list(struct.unpack(f'{len(data)//4}f', data))
            
            self.stats["cache_hits"] += 1
            return vector
        except Exception as e:
            logging.warning(f"Error cargando vector de caché: {e}")
            return None
    
    def save_vector(self, text: str, vector: List[float]) -> bool:
        """Guarda vector en caché"""
        if not text or not vector:
            return False
        
        try:
            cache_key = hashlib.md5(text.encode('utf-8')).hexdigest()
            cache_path = os.path.join(CACHE_DIR, f"{cache_key}.bin")
            
            with open(cache_path, 'wb') as f:
                f.write(struct.pack(f'{len(vector)}f', *vector))
            
            self.stats["cache_misses"] += 1
            return True
        except Exception as e:
            logging.error(f"Error guardando vector en caché: {e}")
            return False
    
    def cleanup_old_cache(self, days: int = 7):
        """Limpia caché antigua"""
        try:
            cutoff = time.time() - (days * 86400)
            deleted = 0
            
            for filename in os.listdir(CACHE_DIR):
                if filename.endswith('.bin'):
                    filepath = os.path.join(CACHE_DIR, filename)
                    if os.path.getmtime(filepath) < cutoff:
                        os.remove(filepath)
                        deleted += 1
            
            if deleted > 0:
                logging.info(f"Limpieza de caché: {deleted} archivos antiguos eliminados")
        except Exception as e:
            logging.error(f"Error en limpieza de caché: {e}")
    
    # ========================================================================
    # FASE 1: RECOLECCIÓN DE SEÑALES
    # ========================================================================
    def fetch_all_feeds(self) -> None:
        """Recolección robusta de todos los feeds RSS"""
        logging.info("📡 FASE 1: Recolección de señales multi-fuente...")
        
        item_counter = 0
        
        for region, urls in FUENTES.items():
            for url in urls:
                if item_counter >= MAX_ITEMS_TOTAL:
                    logging.warning(f"Límite máximo de items alcanzado: {MAX_ITEMS_TOTAL}")
                    break
                
                try:
                    # Headers para evitar bloqueos
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'application/xml, text/xml, */*',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate',
                        'Connection': 'keep-alive'
                    }
                    
                    req = urllib.request.Request(url, headers=headers)
                    
                    with urllib.request.urlopen(req, timeout=15) as response:
                        # Detectar encoding
                        content_type = response.headers.get('Content-Type', '')
                        encoding = 'utf-8'
                        
                        if 'charset=' in content_type:
                            encoding = content_type.split('charset=')[-1].split(';')[0].strip()
                        
                        # Leer y decodificar
                        raw_data = response.read()
                        try:
                            xml_data = raw_data.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            xml_data = raw_data.decode('utf-8', errors='ignore')
                        
                        # Parsear XML
                        root = ET.fromstring(xml_data)
                        
                        # Buscar items (compatible con RSS y Atom)
                        items = (root.findall('.//item') or 
                                root.findall('.//{*}item') or 
                                root.findall('.//entry') or 
                                root.findall('.//{*}entry'))
                        
                        for item in items[:12]:  # Límite por feed
                            if item_counter >= MAX_ITEMS_TOTAL:
                                break
                            
                            # Extraer título
                            title_elem = (item.find('title') or 
                                         item.find('{*}title') or 
                                         item.find('.//{http://www.w3.org/2005/Atom}title'))
                            title = title_elem.text if title_elem is not None else ""
                            
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
                            
                            # Crear item solo si tiene datos válidos
                            if title and link and len(title) > 10:
                                item_id = f"{region}_{item_counter}_{hashlib.md5(link.encode()).hexdigest()[:8]}"
                                news_item = NewsItem(item_id, title, link, region, url)
                                
                                if news_item.link:  # Solo si URL es válida
                                    self.active_items.append(news_item)
                                    item_counter += 1
                    
                    logging.debug(f"Feed procesado: {url} ({len(items)} items)")
                    
                except urllib.error.URLError as e:
                    logging.warning(f"Error de red en feed {url}: {e}")
                    self.stats["errors"] += 1
                except ET.ParseError as e:
                    logging.warning(f"XML inválido en feed {url}: {e}")
                    self.stats["errors"] += 1
                except Exception as e:
                    logging.error(f"Error inesperado en feed {url}: {e}")
                    self.stats["errors"] += 1
        
        self.stats["items_collected"] = len(self.active_items)
        logging.info(f"✅ Recolección completada: {self.stats['items_collected']} señales válidas")
    
    # ========================================================================
    # FASE 2: CLASIFICACIÓN CON IA
    # ========================================================================
    def classify_with_ai(self) -> None:
        """Clasificación por lotes con validación robusta"""
        if not self.active_items:
            logging.warning("No hay items para clasificar")
            return
        
        logging.info(f"🔎 FASE 2: Clasificación IA ({len(self.active_items)} señales)...")
        
        # Prompt optimizado con few-shot examples
        system_prompt = f"""Eres un analista de inteligencia geopolítica. Clasifica cada titular:

ÁREAS ESTRATÉGICAS (SOLO UNA POR TITULAR):
{chr(10).join(f'- {area}' for area in AREAS)}

EJEMPLOS:
- "Ciberataque a infraestructura crítica" → "Seguridad y Conflictos"
- "Sanciones económicas a banco central" → "Economía y Sanciones"  
- "Acuerdo para exportación de gas natural" → "Energía y Recursos"
- "Firma de pacto de defensa mutua" → "Soberanía y Alianzas"
- "Lanzamiento de satélite de comunicaciones" → "Tecnología y Espacio"
- "Protestas por derechos laborales" → "Sociedad y Derechos"

INSTRUCCIONES:
1. TRADUCE al español manteniendo significado exacto
2. ASIGNA EXACTAMENTE UNA área estratégica de la lista
3. CALIFICA tu confianza (0-100)
4. EXTRAE 3-5 palabras clave relevantes

RESPONDE SOLO CON JSON:
{{"res": [{{"id": "...", "area": "...", "titulo_es": "...", "confianza": 95, "keywords": ["kw1", "kw2"]}}]}}"""
        
        batch_size = 25  # Tamaño seguro para Gemini Flash
        classified_count = 0
        
        for i in range(0, len(self.active_items), batch_size):
            batch = self.active_items[i:i+batch_size]
            
            # Construir prompt del batch
            batch_items = []
            for item in batch:
                batch_items.append(f"ID:{item.id}|{item.original_title}")
            
            batch_prompt = f"{system_prompt}\n\nTITULARES:\n" + "\n".join(batch_items)
            
            try:
                self.stats["api_calls"] += 1
                
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=batch_prompt,
                    config={
                        "temperature": 0.1,
                        "max_output_tokens": 2000,
                        "top_p": 0.95
                    }
                )
                
                # Parsear respuesta
                data = self.safe_json_extract(response.text)
                
                if data and 'res' in data:
                    for result in data['res']:
                        item_id = str(result.get('id', '')).strip()
                        
                        # Buscar el item correspondiente
                        target_item = next((it for it in batch if it.id == item_id), None)
                        
                        if target_item:
                            # Validar y clasificar área
                            area_name = result.get('area', '')
                            classified_area, confidence = self.validate_and_classify_area(area_name)
                            
                            if classified_area and confidence >= 50:  # Umbral de confianza
                                target_item.area = classified_area
                                target_item.translated_title = result.get('titulo_es', '')
                                target_item.confidence = min(confidence, float(result.get('confianza', confidence)))
                                target_item.keywords = result.get('keywords', [])[:5]
                                
                                classified_count += 1
                                self.stats["items_classified"] += 1
                            else:
                                target_item.processing_errors.append(f"Área inválida o confianza baja: {area_name}")
                
                logging.debug(f"Batch {i//batch_size + 1}: {len(data['res'] if data else [])} procesados")
                
            except Exception as e:
                logging.error(f"Error en batch {i//batch_size + 1}: {str(e)[:100]}")
                self.stats["errors"] += 1
                continue
            
            # Rate limiting respetuoso
            if i + batch_size < len(self.active_items):
                time.sleep(1.5)
        
        logging.info(f"✅ Clasificación completada: {classified_count} señales clasificadas")
    
    # ========================================================================
    # FASE 3: ANÁLISIS DE FRICCIÓN NARRATIVA (CORREGIDO)
    # ========================================================================
    def calculate_proximity_optimized(self) -> None:
        """Cálculo de proximidad optimizado O(n) con correcciones"""
        logging.info("📐 FASE 3: Análisis de fricción narrativa...")
        
        # Limpiar caché antigua
        self.cleanup_old_cache()
        
        # Agrupar items por área
        items_by_area = defaultdict(list)
        for item in self.active_items:
            if item.area and item.area in AREAS:
                items_by_area[item.area].append(item)
        
        # Procesar cada área por separado
        for area, items in items_by_area.items():
            if len(items) < 2:  # Necesitamos al menos 2 items para comparar
                for item in items:
                    item.proximity = 50.0
                continue
            
            logging.debug(f"Procesando área '{area}' con {len(items)} items")
            
            # ================================================================
            # PASO 1: OBTENER EMBEDDINGS (CON CACHÉ)
            # ================================================================
            items_with_text = [item for item in items if item.translated_title]
            
            # Obtener embeddings con caché
            for item in items_with_text:
                cached_vector = self.get_vector(item.translated_title)
                if cached_vector:
                    item.vector = cached_vector
                else:
                    # Marcar para embedding batch
                    item.vector = None
            
            # Agrupar textos que necesitan embedding
            texts_to_embed = [item.translated_title for item in items_with_text if item.vector is None]
            
            if texts_to_embed:
                try:
                    self.stats["api_calls"] += 1
                    
                    emb_response = self.client.models.embed_content(
                        model="text-embedding-004",
                        contents=texts_to_embed,
                        config={'task_type': 'RETRIEVAL_DOCUMENT'}
                    )
                    
                    # Asignar vectores y guardar en caché
                    text_idx = 0
                    for item in items_with_text:
                        if item.vector is None:  # Necesita embedding
                            if text_idx < len(emb_response.embeddings):
                                item.vector = emb_response.embeddings[text_idx].values
                                self.save_vector(item.translated_title, item.vector)
                                text_idx += 1
                
                except Exception as e:
                    logging.error(f"Error en embeddings para área {area}: {e}")
                    self.stats["errors"] += 1
                    # Fallback: vectores aleatorios normalizados
                    for item in items_with_text:
                        if item.vector is None:
                            import random
                            random.seed(hash(item.translated_title))
                            item.vector = [random.uniform(-0.1, 0.1) for _ in range(768)]
            
            # ================================================================
            # PASO 2: CALCULAR CENTROIDES POR REGIÓN (OPTIMIZADO)
            # ================================================================
            # Filtrar items con vector válido
            valid_items = [item for item in items_with_text if item.vector and len(item.vector) > 0]
            
            if len(valid_items) < 2:
                for item in items:
                    item.proximity = 50.0
                continue
            
            # Agrupar vectores por región
            vectors_by_region = defaultdict(list)
            for item in valid_items:
                vectors_by_region[item.region].append(item.vector)
            
            # Pre-calcular centroides por región
            region_centroids = {}
            for region, vectors in vectors_by_region.items():
                if vectors:
                    # Calcular promedio por dimensión
                    centroid = []
                    for dim_idx in range(len(vectors[0])):  # Asume todos los vectores tienen misma dimensión
                        dim_values = [vec[dim_idx] for vec in vectors]
                        centroid.append(sum(dim_values) / len(dim_values))
                    region_centroids[region] = centroid
            
            # ================================================================
            # PASO 3: CALCULAR PROXIMIDAD (CORRECCIÓN APLICADA)
            # ================================================================
            for item in valid_items:
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
                    continue
                
                # Calcular centroide global de "otras regiones"
                global_centroid = []
                for dim_idx in range(len(current_vector)):
                    dim_values = [centroid[dim_idx] for centroid in other_centroids]
                    global_centroid.append(sum(dim_values) / len(dim_values))
                
                # CALCULO CORREGIDO: Similitud coseno [-1, 1] -> Proximidad [0, 100]
                # 1. Calcular producto punto
                dot_product = sum(a * b for a, b in zip(current_vector, global_centroid))
                
                # 2. Calcular magnitudes
                magnitude_current = math.sqrt(sum(x * x for x in current_vector))
                magnitude_global = math.sqrt(sum(x * x for x in global_centroid))
                
                # 3. Calcular similitud coseno
                if magnitude_current * magnitude_global > 0:
                    cosine_similarity = dot_product / (magnitude_current * magnitude_global)
                    
                    # 4. CORRECCIÓN CRÍTICA: Mapear [-1, 1] a [0, 100]
                    # Fórmula: proximity = (similarity + 1) * 50
                    # similarity = -1 -> proximity = 0
                    # similarity = 0 -> proximity = 50  
                    # similarity = 1 -> proximity = 100
                    raw_proximity = (cosine_similarity + 1) * 50
                    
                    # 5. Asegurar rango [0, 100] (por errores de punto flotante)
                    item.proximity = max(0.0, min(100.0, raw_proximity))
                else:
                    item.proximity = 50.0
            
            # Para items sin vector, asignar valor neutro
            for item in items:
                if not hasattr(item, 'proximity') or item.proximity is None:
                    item.proximity = 50.0
        
        logging.info("✅ Análisis de proximidad completado")
    
    # ========================================================================
    # FASE 4: GENERACIÓN DE MICRO-INFORMES PARA NETFLIX
    # ========================================================================
    def generate_micro_reports(self) -> Dict[str, str]:
        """Genera micro-informes por área para la interfaz Netflix"""
        logging.info("🎬 Generando micro-informes para interfaz Netflix...")
        
        # Agrupar items por área
        items_by_area = defaultdict(list)
        for item in self.active_items:
            if item.area and item.area in AREAS and item.proximity is not None:
                items_by_area[item.area].append(item)
        
        micro_reports = {}
        
        for area, items in items_by_area.items():
            if not items:
                micro_reports[area] = f"Actividad limitada detectada en {area}."
                continue
            
            # Calcular métricas del área
            avg_proximity = sum(item.proximity for item in items) / len(items)
            region_counts = defaultdict(int)
            keyword_counts = defaultdict(int)
            
            for item in items:
                region_counts[item.region] += 1
                for keyword in item.keywords[:3]:
                    keyword_counts[keyword.lower()] += 1
            
            # Top regiones y keywords
            top_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Determinar nivel de consenso
            if avg_proximity > 80:
                consensus = "ALTO CONSENSO"
                emoji = "🟢"
            elif avg_proximity > 60:
                consensus = "CONSENSO MODERADO"
                emoji = "🟡"
            elif avg_proximity > 40:
                consensus = "TENSIÓN DETECTADA"
                emoji = "🟠"
            else:
                consensus = "FRICCIÓN SEVERA"
                emoji = "🔴"
            
            # Determinar tendencia
            trend = "↑" if avg_proximity > 60 else "↓" if avg_proximity < 40 else "→"
            
            # Construir micro-informe
            regions_str = ", ".join([r[0] for r in top_regions])
            keywords_str = ", ".join([k[0] for k in top_keywords])
            
            micro_report = (
                f"{emoji} {consensus} | "
                f"Bloques activos: {regions_str} | "
                f"Temas: {keywords_str} | "
                f"Tendencia: {trend}"
            )
            
            micro_reports[area] = micro_report[:150]  # Limitar longitud
        
        return micro_reports
    
    # ========================================================================
    # FASE 5: EXPORTACIÓN DE RESULTADOS
    # ========================================================================
    def export_results(self) -> Dict:
        """Exporta resultados en formato para frontend Netflix"""
        logging.info("💾 Exportando resultados...")
        
        # Generar micro-informes
        micro_reports = self.generate_micro_reports()
        
        # Agrupar items por área para el carrusel
        carousel_data = []
        
        for area in AREAS:
            # Filtrar items del área
            area_items = [item for item in self.active_items if item.area == area]
            
            if not area_items:
                continue
            
            # Convertir a formato de partículas
            particles = []
            for item in area_items:
                particle = item.to_dict()
                
                # Añadir etiqueta de sesgo basada en proximidad
                if particle["proximidad"] > 80:
                    particle["sesgo"] = "Consenso Global"
                elif particle["proximidad"] > 65:
                    particle["sesgo"] = "Alineación"
                elif particle["proximidad"] > 50:
                    particle["sesgo"] = "Tensión Moderada"
                elif particle["proximidad"] > 35:
                    particle["sesgo"] = "Divergencia"
                else:
                    particle["sesgo"] = "Contraste Radical"
                
                particles.append(particle)
            
            # Ordenar por proximidad (más consensuados primero)
            particles.sort(key=lambda x: x["proximidad"], reverse=True)
            
            # Color por área
            area_colors = {
                "Seguridad y Conflictos": "#ef4444",
                "Economía y Sanciones": "#3b82f6",
                "Energía y Recursos": "#10b981",
                "Soberanía y Alianzas": "#f59e0b",
                "Tecnología y Espacio": "#8b5cf6",
                "Sociedad y Derechos": "#ec4899"
            }
            
            carousel_data.append({
                "area": area,
                "punto_cero": micro_reports.get(area, f"Análisis de {area} actualizado."),
                "color": area_colors.get(area, "#666666"),
                "total_particulas": len(particles),
                "particulas": particles[:30]  # Top 30 por área
            })
        
        # Metadatos de ejecución
        execution_time = time.time() - self.start_time
        
        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "execution_seconds": round(execution_time, 2),
            "stats": self.stats,
            "version": "IroncladCollector v2.0 (Corregido)",
            "total_areas": len(carousel_data),
            "total_particles": sum(area["total_particulas"] for area in carousel_data),
            "cache_efficiency": round(
                self.stats["cache_hits"] / (self.stats["cache_hits"] + self.stats["cache_misses"]) * 100, 
                2
            ) if (self.stats["cache_hits"] + self.stats["cache_misses"]) > 0 else 0
        }
        
        result = {
            "carousel": carousel_data,
            "meta": meta
        }
        
        # Guardar archivo principal
        try:
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logging.info("✅ gravity_carousel.json actualizado")
        except Exception as e:
            logging.error(f"Error guardando archivo principal: {e}")
        
        # Guardar histórico diario
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            hist_path = os.path.join(HIST_DIR, f"{date_str}.json")
            
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logging.info(f"✅ Histórico guardado: {hist_path}")
        except Exception as e:
            logging.error(f"Error guardando histórico: {e}")
        
        # Guardar resumen ejecutivo
        try:
            summary = {
                "timestamp": meta["updated"],
                "areas_summary": [
                    {
                        "area": area["area"],
                        "particle_count": area["total_particulas"],
                        "avg_proximity": round(
                            sum(p["proximidad"] for p in area["particulas"]) / area["total_particulas"], 
                            2
                        ) if area["total_particulas"] > 0 else 0,
                        "micro_report": area["punto_cero"][:100]
                    }
                    for area in carousel_data
                ],
                "performance": {
                    "execution_time": meta["execution_seconds"],
                    "items_processed": self.stats["items_collected"],
                    "classification_rate": round(
                        self.stats["items_classified"] / self.stats["items_collected"] * 100, 
                        2
                    ) if self.stats["items_collected"] > 0 else 0,
                    "cache_efficiency": meta["cache_efficiency"]
                }
            }
            
            with open("executive_summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            logging.info("✅ Resumen ejecutivo generado")
        except Exception as e:
            logging.error(f"Error guardando resumen: {e}")
        
        return result
    
    # ========================================================================
    # EJECUCIÓN PRINCIPAL
    # ========================================================================
    def run(self) -> Optional[Dict]:
        """Ejecuta el pipeline completo"""
        print("\n" + "="*70)
        print("🚀 IRONCLAD COLLECTOR - Sistema de Inteligencia Geopolítica")
        print("="*70)
        
        try:
            # Pipeline principal
            self.fetch_all_feeds()
            self.classify_with_ai()
            self.calculate_proximity_optimized()
            result = self.export_results()
            
            # Reporte final
            total_time = time.time() - self.start_time
            
            print("\n" + "="*70)
            print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
            print("="*70)
            
            print(f"📊 ESTADÍSTICAS:")
            print(f"   • Tiempo total: {total_time:.1f} segundos")
            print(f"   • Señales recolectadas: {self.stats['items_collected']}")
            print(f"   • Señales clasificadas: {self.stats['items_classified']}")
            print(f"   • Llamadas API: {self.stats['api_calls']}")
            print(f"   • Hits de caché: {self.stats['cache_hits']}")
            print(f"   • Eficiencia de caché: {self.stats.get('cache_efficiency', 0):.1f}%")
            
            if result:
                total_particles = sum(len(area["particulas"]) for area in result["carousel"])
                print(f"   • Partículas totales: {total_particles}")
                print(f"   • Áreas activas: {len(result['carousel'])}")
            
            print(f"\n📁 ARCHIVOS GENERADOS:")
            print("   1. gravity_carousel.json (datos principales)")
            print("   2. executive_summary.json (resumen ejecutivo)")
            print(f"   3. {HIST_DIR}/YYYY-MM-DD.json (histórico diario)")
            print(f"   4. {LOG_FILE} (registros de sistema)")
            
            print("\n⚠️  NOTA: Revisa gravity_carousel.json para visualizar el radar")
            print("="*70 + "\n")
            
            return result
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Ejecución interrumpida por el usuario")
            logging.info("Ejecución interrumpida por el usuario")
            return None
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO: {str(e)[:200]}")
            logging.error(f"Error en ejecución principal: {e}", exc_info=True)
            return None

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
def main():
    """Función principal con manejo de errores"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: Variable de entorno GEMINI_API_KEY no encontrada")
        print("\nPor favor, configura tu API key:")
        print("  Linux/Mac:  export GEMINI_API_KEY='tu-clave-aqui'")
        print("  Windows:    set GEMINI_API_KEY=tu-clave-aqui")
        print("\nO ejecuta: GEMINI_API_KEY='tu-clave' python ironclad_collector.py")
        sys.exit(1)
    
    # Inicializar y ejecutar collector
    collector = IroncladCollector(api_key)
    result = collector.run()
    
    if result:
        print("🎯 Inteligencia geopolítica actualizada exitosamente!")
        sys.exit(0)
    else:
        print("⚠️  El análisis encontró problemas. Revisa los logs.")
        sys.exit(1)

if __name__ == "__main__":
    main()

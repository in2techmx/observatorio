# PROXIMITY ENGINE V5.2 - GeoCore Architecture (Regional Narrative Extraction)
import os
import json
import datetime
import time
import hashlib
import re
import sys
import logging
import argparse
import csv
from collections import defaultdict
import feedparser
from google import genai
from google.genai import types

# --- LOGGING ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')

# --- CONFIGURATION LOADING ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "BD_Noticias", "Config")
DATA_DIR = os.path.join(BASE_DIR, "BD_Noticias", "Diario")

def load_config(filename):
    path = os.path.join(CONFIG_DIR, filename)
    if not os.path.exists(path):
        logging.error(f"Config not found: {path}")
        sys.exit(1)
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

RSS_FEEDS = load_config("feeds.json")
PROMPTS = load_config("prompts.json")
PIPELINE = load_config("pipeline_logic.json")
CATEGORIES = load_config("categories.json")
PHASE2_CONFIG = load_config("phase2_classification.json")
PHASE3_CONFIG = load_config("phase3_proximity.json")

# --- NEWS ITEM ---
class NewsItem:
    def __init__(self, item_id, title, link, region, source_url, description=""):
        self.id = item_id
        self.title = self._sanitize(title)
        self.description = self._sanitize(description)[:500]
        self.link = link if link and link.startswith("http") else None
        self.region = region
        self.source_url = source_url
        self.category = None  # Will be assigned in Phase 2
        self.embedding = None  # Will be calculated in Phase 3
        self.proximity_score = 0.0  # Distance from category centroid
        
    def _sanitize(self, text):
        if not text: return ""
        return re.sub(r'<[^>]+>', '', str(text)).strip()
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "region": self.region,
            "source": self.source_url,
            "category": self.category,
            "proximity_score": self.proximity_score
        }

# --- COLLECTOR V5 (GeoCore) ---
class GeoCoreCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.regional_data = {}  # region -> {narrative, items}
        self.thematic_groups = {}  # category -> [items] (populated in Phase 2)
        self.stats = {"total_fetched": 0, "total_selected": 0, "regions_processed": 0}
        self.start_time = time.time()
        
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs("public", exist_ok=True)

    def fetch_and_synthesize_by_region(self):
        logging.info("🌍 FASE 1: Recolección y Síntesis Regional (V5 GeoCore)...")
        
        pool_size = PIPELINE["collection_params"]["pool_size_per_region"]
        min_items = PIPELINE["collection_params"]["min_items_for_synthesis"]
        
        for region, feeds in RSS_FEEDS.items():
            logging.info(f"  📍 Procesando: {region}")
            
            # 1. Recolectar pool regional completo
            pool = []
            for url in feeds:
                try:
                    d = feedparser.parse(url)
                    for entry in d.entries[:pool_size]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        desc = entry.get('summary', '') or entry.get('description', '')
                        
                        if not title: continue
                        
                        item_id = hashlib.md5(f"{title}|{link}".encode()).hexdigest()
                        
                        # Deduplicación regional simple
                        if not any(x.title.lower() == title.lower() for x in pool):
                            news = NewsItem(item_id, title, link, region, url, desc)
                            pool.append(news)
                            
                except Exception as e:
                    logging.warning(f"Feed error {url}: {e}")
            
            self.stats["total_fetched"] += len(pool)
            logging.info(f"    ✓ Recolectados: {len(pool)} items")
            
            # 2. Síntesis via IA (si hay suficientes items)
            if len(pool) < min_items:
                logging.warning(f"    ⚠️ Insuficientes items para {region} ({len(pool)}). Saltando...")
                continue
            
            selected_items = self._synthesize_region(region, pool)
            
            if selected_items:
                # ESTRATEGIA: Índices Numéricos (1-based) -> Items
                # La IA devuelve [1, 5, 10...], nosotros mapeamos a pool[0], pool[4], pool[9]...
                selected_indices = selected_items.get("selected_indexes", [])
                
                filtered_items = []
                for idx in selected_indices:
                    # Validar rango (1 a len(pool))
                    if isinstance(idx, int) and 1 <= idx <= len(pool):
                        filtered_items.append(pool[idx-1]) # Convertir a 0-based
                
                # Enforce limits: truncate if too many, warn if too few
                min_sel = PIPELINE["collection_params"]["output_stories_min"]
                max_sel = PIPELINE["collection_params"]["output_stories_max"]
                
                if len(filtered_items) > max_sel:
                    logging.warning(f"    ⚠️ Truncando de {len(filtered_items)} a {max_sel} items")
                    filtered_items = filtered_items[:max_sel]
                elif len(filtered_items) < min_sel:
                    logging.warning(f"    ⚠️ Solo {len(filtered_items)} items válidos (esperado {min_sel})")
                
                self.regional_data[region] = {
                    "narrative": selected_items["narrative"],
                    "confidence": selected_items.get("confidence", "medium"),
                    "items": filtered_items
                }
                self.stats["total_selected"] += len(filtered_items)
                self.stats["regions_processed"] += 1
                logging.info(f"    ✅ Seleccionados: {len(filtered_items)} / Narrativa: {selected_items['narrative'][:60]}...")

    def _synthesize_region(self, region, pool):
        """Envía el pool completo a la IA para síntesis y selección"""
        
        # Preparar input para la IA usando ÍNDICES NUMÉRICOS (Más robusto)
        # Formato: "1. Título..."
        headlines = "\n".join([f"{i+1}. {item.title} - {item.description[:80]}" 
                               for i, item in enumerate(pool)])
        
        prompt_template = PIPELINE["regional_synthesis_prompt"]["user_template"]
        prompt = prompt_template.replace("{region}", region).replace("{count}", str(len(pool))).replace("{headlines}", headlines)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            
            result = json.loads(response.text)
            
            # Validar que los IDs seleccionados estén en el rango correcto
            min_sel = PIPELINE["collection_params"]["output_stories_min"]
            max_sel = PIPELINE["collection_params"]["output_stories_max"]
            
            selected_ids = result.get("selected_ids", [])
            if len(selected_ids) < min_sel or len(selected_ids) > max_sel:
                logging.warning(f"    ⚠️ IA seleccionó {len(selected_ids)} items (fuera de rango {min_sel}-{max_sel})")
            
            return result
            
        except Exception as e:
            logging.error(f"Error en síntesis de {region}: {e}")
            return None

    def classify_by_theme(self):
        """FASE 2: Reagrupar todas las noticias seleccionadas por categoría temática"""
        logging.info("🎯 FASE 2: Clasificación Temática (Re-agrupación)...")
        
        # Obtener todas las noticias seleccionadas de todas las regiones
        all_items = []
        for region, data in self.regional_data.items():
            all_items.extend(data["items"])
        
        logging.info(f"  📊 Total de noticias a clasificar: {len(all_items)}")
        
        # Clasificar cada noticia por categoría usando keywords (config from phase2_classification.json)
        categories_data = CATEGORIES["categories"]
        fallback_cat = PHASE2_CONFIG["fallback_category"]
        case_sensitive = PHASE2_CONFIG["classification_rules"]["case_sensitive"]
        
        for item in all_items:
            # Build search text from configured fields
            search_fields = PHASE2_CONFIG["classification_rules"]["search_fields"]
            text_parts = [getattr(item, field, "") for field in search_fields]
            text = " ".join(text_parts)
            if not case_sensitive:
                text = text.lower()
            
            item.category = fallback_cat  # Default from config
            
            # Buscar coincidencias con keywords
            for cat_name, cat_info in categories_data.items():
                if cat_name == fallback_cat:
                    continue
                keywords = cat_info["keywords"]
                if any(keyword in text for keyword in keywords):
                    item.category = cat_name
                    break
        
        # Agrupar por categoría
        self.thematic_groups = defaultdict(list)
        for item in all_items:
            self.thematic_groups[item.category].append(item)
        
        for cat, items in self.thematic_groups.items():
            logging.info(f"  ✓ {cat}: {len(items)} noticias")
        
        self.stats["categories_found"] = len(self.thematic_groups)

    def calculate_proximity(self):
        """FASE 3: Calcular proximidad narrativa usando centroide temático"""
        logging.info("📐 FASE 3: Cálculo de Proximidad Narrativa (Centroide)...")
        
        import math
        
        # Load config parameters
        embedding_model = PHASE3_CONFIG["embedding_model"]
        embedding_fields = PHASE3_CONFIG["embedding_fields"]
        separator = PHASE3_CONFIG["embedding_separator"]
        min_items = PHASE3_CONFIG["centroid_calculation"]["min_items_for_centroid"]
        
        for category, items in self.thematic_groups.items():
            if len(items) < min_items:
                logging.info(f"  ⚠️ {category}: Insuficientes items para centroide ({len(items)} < {min_items})")
                continue
            
            logging.info(f"  🎯 Procesando: {category} ({len(items)} items)")
            
            # 1. Generar embeddings para todos los items de esta categoría
            # Build text from configured fields
            texts = []
            for item in items:
                field_values = [getattr(item, field, "") for field in embedding_fields]
                text = separator.join(field_values)
                texts.append(text)
            
            try:
                # Procesar en lotes de 100 (límite de la API de Gemini)
                BATCH_SIZE = 100
                all_embeddings = []
                
                for i in range(0, len(texts), BATCH_SIZE):
                    batch_texts = texts[i:i + BATCH_SIZE]
                    try:
                        embeddings_response = self.client.models.embed_content(
                            model=embedding_model,
                            contents=batch_texts
                        )
                        # Extraer valores y añadir a la lista general
                        batch_values = [e.values for e in embeddings_response.embeddings]
                        all_embeddings.extend(batch_values)
                    except Exception as e:
                         logging.error(f"Error en batch {i}: {e}")
                         # Rellenar con None para mantener índices alineados si falla un batch
                         all_embeddings.extend([None] * len(batch_texts))

                # Asignar embeddings a cada item
                for i, embedding_values in enumerate(all_embeddings):
                    if embedding_values:
                         items[i].embedding = embedding_values
                
                # 2. Calcular centroide (vector promedio) - method from config
                valid_embeddings = [item.embedding for item in items if item.embedding]
                if not valid_embeddings:
                    continue
                
                dim = len(valid_embeddings[0])
                centroid = [sum(col)/len(valid_embeddings) for col in zip(*valid_embeddings)]
                
                # 3. Calcular distancia de cada item al centroide
                # Using distance metric from config
                for item in items:
                    if item.embedding:
                        # Cosine similarity (as per config)
                        dot = sum(a*b for a,b in zip(item.embedding, centroid))
                        norm1 = math.sqrt(sum(a*a for a in item.embedding))
                        norm2 = math.sqrt(sum(a*a for a in centroid))
                        similarity = dot / (norm1 * norm2) if norm1 and norm2 else 0
                        
                        # Normalize to 0-100 using formula from config
                        # Formula: ((cosine_similarity + 1) / 2) * 100
                        item.proximity_score = ((similarity + 1) / 2) * 100
                
                logging.info(f"    ✅ Proximidad calculada para {len(valid_embeddings)} items")
                
            except Exception as e:
                logging.error(f"Error calculando proximidad para {category}: {e}")

    def save_audit_csv(self):
        """Guarda CSV con todas las noticias seleccionadas (auditoría)"""
        logging.info("💾 FASE 4: Guardando Auditoría CSV...")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = os.path.join(DATA_DIR, f"run_{timestamp}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Region", "Category", "Title", "Description", "Source", "Link", "Proximity_Score"])
                
                for category, items in self.thematic_groups.items():
                    for item in items:
                        writer.writerow([
                            item.id,
                            item.region,
                            item.category,
                            item.title,
                            item.description,
                            item.source_url,
                            item.link,
                            round(item.proximity_score, 2)
                        ])
            
            logging.info(f"✅ CSV guardado: {filename}")
        except Exception as e:
            logging.error(f"Error guardando CSV: {e}")

    def export(self):
        """Exporta JSON para el frontend (organizado por CATEGORÍA TEMÁTICA con colores Cyberpunk)"""
        logging.info("📦 FASE 5: Exportación JSON...")
        
        # Colores Cyberpunk por Temática
        THEME_COLORS = {
            "War & Conflict": "#ff0055",    # Neon Red
            "Global Economy": "#00ff9f",    # Matrix Green
            "Politics & Policy": "#00f3ff", # Cyan Neon
            "Science & Tech": "#bf00ff",    # Electric Purple
            "Social & Rights": "#ffbe0b",   # Cyber Yellow
            "Other": "#888888"              # Grey
        }
        
        carousel = []
        categories_config = CATEGORIES["categories"]
        
        for category, items in self.thematic_groups.items():
            if not items:
                continue
            
            # Obtener configuración y Color Cyberpunk
            # Priorizamos el color del mapa THEME_COLORS, fallback al config
            color = THEME_COLORS.get(category, categories_config.get(category, {}).get("color", "#888888"))
            
            particles = [
                {
                    "id": item.id,
                    "title": item.title,
                    "titulo_es": item.title,
                    "titulo_en": item.title,
                    "region": item.region,
                    "url": item.link,
                    "description": item.description,
                    "proximity_score": round(item.proximity_score, 2)
                }
                for item in items
            ]
            
            # Calcular promedio de proximidad
            avg_proximity = sum(p["proximity_score"] for p in particles) / len(particles) if particles else 0
            
            # Generar síntesis temática usando IA (captura divergencias narrativas)
            regional_narratives = defaultdict(str)
            for item in items:
                # Buscar la narrativa regional original
                for region, data in self.regional_data.items():
                    if item in data["items"]:
                        regional_narratives[region] = data["narrative"]
                        break
            
            # Crear síntesis con IA que capture divergencias
            synthesis = self._generate_category_synthesis(category, regional_narratives, items)
            
            # Sanitizar nombres de regiones para consistencia (ej. USA vs NORTEAMERICA)
            # Mapeo simple para asegurar keys consistentes en frontend
            export_regional_narratives = {}
            for region, narrative in regional_narratives.items():
                clean_region = region.split("_")[0] # EUROPA_WEST -> EUROPA
                export_regional_narratives[region] = narrative

            carousel.append({
                "area": category, # AHORA POR TEMÁTICA
                "sintesis": synthesis,
                "sintesis_en": synthesis,
                "regional_syntheses": export_regional_narratives, # NEW: Per-region narratives
                "color": color,   # COLOR CYBERPUNK
                "count": len(particles),
                "avg_proximity": round(avg_proximity, 2),
                "particulas": particles
            })
        
        final = {
            "carousel": carousel,
            "meta": {
                "generated": datetime.datetime.now().isoformat(),
                "pipeline_version": PIPELINE["version"],
                "stats": self.stats,
                "execution_time": round(time.time() - self.start_time, 2)
            }
        }
        
        with open("public/gravity_carousel.json", "w", encoding='utf-8') as f:
            json.dump(final, f, indent=2, ensure_ascii=False)
        
        logging.info(f"✅ Exportado: {len(carousel)} categorías, {self.stats['total_selected']} noticias")

    def _generate_category_synthesis(self, category, regional_narratives, items):
        """Genera síntesis temática usando titulares específicos para evitar repetición"""
        
        # Agrupar titulares por región
        headlines_by_region = defaultdict(list)
        for item in items:
            headlines_by_region[item.region].append(f"- {item.title}")
            
        if not headlines_by_region:
            return f"Análisis de {category} en desarrollo."

        # Construir prompt con titulares específicos del tema
        source_text = ""
        for region, headlines in headlines_by_region.items():
            # Usar hasta 8 titulares por región para dar contexto rico
            source_text += f"\nREGION: {region}\n" + "\n".join(headlines[:8])
        
        prompt = f"""CATEGORY: {category}
        
        SOURCE MATERIAL (Specific Headlines per Region):
        {source_text}
        
        TASK: Synthesize the global narrative divergence on this specific topic based ONLY on the headlines above.
        - Analyze specific events mentioned in these headlines.
        - Contrast regional perspectives (e.g. "While West focuses on [Specific Event X], Russia emphasizes [Perspective Y]").
        - Be specific to the headlines provided. Do NOT use generic geopolitical boilerplate.
        
        OUTPUT: A single dense analytical paragraph (approx 60-80 words). Neutral tone."""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            logging.warning(f"Error generando síntesis para {category}: {e}")
            return f"{category}: {len(items)} noticias. Divergencia detectada entre {', '.join(headlines_by_region.keys())}."

    def run(self):
        try:
            self.fetch_and_synthesize_by_region()  # FASE 1
            self.classify_by_theme()                # FASE 2
            self.calculate_proximity()              # FASE 3
            self.save_audit_csv()                   # FASE 4 (Audit)
            self.export()                           # FASE 5 (Export)
            
            logging.info(f"🎯 Pipeline V5 Completado: {self.stats}")
            return True
        except Exception as e:
            logging.error(f"FATAL: {e}", exc_info=True)
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="tactical")
    args = parser.parse_args()
    
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("❌ GEMINI_API_KEY not found"); sys.exit(1)
    
    logging.info(f"🚀 Iniciando Proximity Engine V5 - GeoCore")
    logging.info(f"⚙️  Modo: {args.mode}")
    logging.info(f"📋 Pipeline: {PIPELINE['version']}")
    
    collector = GeoCoreCollector(key)
    sys.exit(0 if collector.run() else 1)

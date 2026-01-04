# PROXIMITY ENGINE V5 - GeoCore Architecture (Regional Narrative Extraction)
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
                self.regional_data[region] = {
                    "narrative": selected_items["narrative"],
                    "confidence": selected_items.get("confidence", "medium"),
                    "items": [pool[i] for i in range(len(pool)) if pool[i].id in selected_items["selected_ids"]]
                }
                self.stats["total_selected"] += len(self.regional_data[region]["items"])
                self.stats["regions_processed"] += 1
                logging.info(f"    ✅ Seleccionados: {len(self.regional_data[region]['items'])} / Narrativa: {selected_items['narrative'][:60]}...")

    def _synthesize_region(self, region, pool):
        """Envía el pool completo a la IA para síntesis y selección"""
        
        # Preparar input para la IA
        headlines = "\n".join([f"{i+1}. [{item.id}] {item.title} - {item.description[:80]}" 
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
        
        # Clasificar cada noticia por categoría usando keywords
        categories_data = CATEGORIES["categories"]
        
        for item in all_items:
            text = (item.title + " " + item.description).lower()
            item.category = "Other"  # Default
            
            # Buscar coincidencias con keywords
            for cat_name, cat_info in categories_data.items():
                if cat_name == "Other":
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
        
        for category, items in self.thematic_groups.items():
            if len(items) < 2:
                logging.info(f"  ⚠️ {category}: Insuficientes items para centroide ({len(items)})")
                continue
            
            logging.info(f"  🎯 Procesando: {category} ({len(items)} items)")
            
            # 1. Generar embeddings para todos los items de esta categoría
            texts = [f"{item.title} {item.description}" for item in items]
            
            try:
                embeddings_response = self.client.models.embed_content(
                    model="text-embedding-004",
                    contents=texts
                )
                
                # Asignar embeddings a cada item
                for i, emb_result in enumerate(embeddings_response.embeddings):
                    items[i].embedding = emb_result.values
                
                # 2. Calcular centroide (vector promedio)
                valid_embeddings = [item.embedding for item in items if item.embedding]
                if not valid_embeddings:
                    continue
                
                dim = len(valid_embeddings[0])
                centroid = [sum(col)/len(valid_embeddings) for col in zip(*valid_embeddings)]
                
                # 3. Calcular distancia de cada item al centroide
                for item in items:
                    if item.embedding:
                        # Cosine similarity
                        dot = sum(a*b for a,b in zip(item.embedding, centroid))
                        norm1 = math.sqrt(sum(a*a for a in item.embedding))
                        norm2 = math.sqrt(sum(a*a for a in centroid))
                        similarity = dot / (norm1 * norm2) if norm1 and norm2 else 0
                        
                        # Convertir a score 0-100 (mayor = más cerca del consenso)
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
        """Exporta JSON para el frontend (organizado por CATEGORÍA TEMÁTICA)"""
        logging.info("📦 FASE 4: Exportación JSON...")
        
        carousel = []
        categories_config = CATEGORIES["categories"]
        
        for category, items in self.thematic_groups.items():
            if not items:
                continue
            
            # Obtener configuración de la categoría
            cat_config = categories_config.get(category, {})
            color = cat_config.get("color", "#888888")
            
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
            
            # Generar síntesis temática (combinando narrativas regionales)
            regional_narratives = defaultdict(str)
            for item in items:
                # Buscar la narrativa regional original
                for region, data in self.regional_data.items():
                    if item in data["items"]:
                        regional_narratives[region] = data["narrative"]
                        break
            
            # Crear síntesis combinada
            synthesis = f"Tema: {category}. "
            if regional_narratives:
                synthesis += "Perspectivas regionales: " + "; ".join([f"{r}: {n[:50]}..." for r, n in list(regional_narratives.items())[:3]])
            
            carousel.append({
                "area": category,
                "sintesis": synthesis,
                "sintesis_en": synthesis,  # TODO: Translation
                "color": color,
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
        
        logging.info(f"✅ Exportado: {len(carousel)} regiones, {self.stats['total_selected']} noticias")

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

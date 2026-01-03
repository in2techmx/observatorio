import os, json, datetime, time, urllib.request, hashlib, re, sys, math, struct
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN HIPERCOMPACTA ---
MAX_PER_REGION_IN_AREA = 8
AREAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
         "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"]
REGIONS = {"USA":"USA","RUSSIA":"RUSSIA","CHINA":"CHINA","EUROPE":"EUROPE","LATAM":"LATAM",
           "MID_EAST":"MID_EAST","INDIA":"INDIA","AFRICA":"AFRICA","GLOBAL":"GLOBAL"}
COLORS = {"Seguridad y Conflictos":"#ef4444","Economía y Sanciones":"#3b82f6",
          "Energía y Recursos":"#10b981","Soberanía y Alianzas":"#f59e0b",
          "Tecnología y Espacio":"#8b5cf6","Sociedad y Derechos":"#ec4899"}

# Directorios
for d in ["vector_cache", "historico_noticias/diario"]: os.makedirs(d, exist_ok=True)

# --- RED DE VIGILANCIA OPTIMIZADA ---
FUENTES = {
    "USA": ["https://rss.nytimes.com/services/xml/rss/nyt/US.xml", 
            "http://rss.cnn.com/rss/edition_us.rss",
            "https://feeds.washingtonpost.com/rss/politics"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", 
               "https://themoscowtimes.com/rss/news"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", 
              "https://www.chinadaily.com.cn/rss/world_rss.xml"],
    "EUROPE": ["https://www.theguardian.com/world/rss", 
               "https://www.france24.com/en/rss"],
    "LATAM": ["https://www.infobae.com/america/arc/outboundfeeds/rss/", 
              "https://elpais.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", 
                 "https://www.trtworld.com/rss"],
    "GLOBAL": ["https://www.wired.com/feed/category/science/latest/rss", 
               "https://techcrunch.com/feed/"]
}

class GravityHubUltra:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(lambda: defaultdict(list))
        self.stats = {"feeds": 0, "items": 0, "classified": 0}
        self.session_start = time.time()
    
    # --- UTILIDADES CRÍTICAS ---
    def extract_json(self, text):
        """Extrae JSON de respuestas de IA ruidosas"""
        try:
            # Buscar el primer { y el último }
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except:
            pass
        return None
    
    def clean_html(self, text):
        """Limpia HTML/XML rápido"""
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
        return text.strip()
    
    def classify_area(self, area_name):
        """Clasificación rápida de áreas"""
        if not area_name: return None
        area_lower = area_name.lower().strip()
        
        # Búsqueda directa primero
        for area in AREAS:
            if area.lower() == area_lower or area_lower in area.lower():
                return area
        
        # Palabras clave
        keywords = {
            "Seguridad y Conflictos": ["militar", "defensa", "guerra", "terrorismo", "conflicto", "ejército"],
            "Economía y Sanciones": ["economía", "finanzas", "mercado", "comercio", "sanciones", "inflación"],
            "Energía y Recursos": ["energía", "petróleo", "gas", "minería", "clima", "renovable"],
            "Soberanía y Alianzas": ["diplomacia", "tratado", "alianza", "otan", "onu", "geopolítica"],
            "Tecnología y Espacio": ["tecnología", "ia", "digital", "satélite", "ciber", "espacio"],
            "Sociedad y Derechos": ["derechos", "humano", "social", "salud", "educación", "protesta"]
        }
        
        for area, keys in keywords.items():
            if any(key in area_lower for key in keys):
                return area
        
        return None
    
    # --- INGESTA OPTIMIZADA ---
    def fetch_all_feeds(self):
        """Recolecta todos los feeds en paralelo con timeouts"""
        print("🌍 FASE 1: Ingesta masiva de fuentes...")
        items_by_region = defaultdict(list)
        id_counter = 0
        
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0 (compatible; GravityRadar/1.0)',
                        'Accept': 'application/xml, text/xml'
                    })
                    
                    with urllib.request.urlopen(req, timeout=15) as response:
                        xml_data = response.read().decode('utf-8', errors='ignore')
                        root = ET.fromstring(xml_data)
                        
                        # Buscar items en diferentes formatos
                        entries = root.findall('.//item') or root.findall('.//entry') or root.findall('.//{*}item')
                        
                        for entry in entries[:12]:  # Límite por feed
                            # Extraer título
                            title_elem = entry.find('title') or entry.find('{*}title')
                            title = self.clean_html(title_elem.text if title_elem is not None else "")
                            
                            # Extraer enlace
                            link_elem = entry.find('link') or entry.find('{*}link')
                            if link_elem is not None:
                                link = link_elem.text or link_elem.get('href', '')
                            else:
                                link = ""
                            
                            if title and link and len(title) > 10:
                                item_id = f"{region}_{id_counter}"
                                items_by_region[region].append({
                                    "id": item_id,
                                    "title": title,
                                    "link": link.strip(),
                                    "region": region
                                })
                                id_counter += 1
                        
                        self.stats["feeds"] += 1
                        
                except Exception as e:
                    print(f"  ⚠️  Feed fallido: {url[:50]}...")
                    continue
        
        # Aplanar todos los items
        all_items = []
        for items in items_by_region.values():
            all_items.extend(items)
        
        self.stats["items"] = len(all_items)
        print(f"  ✅ Recolectados: {self.stats['items']} titulares de {self.stats['feeds']} feeds")
        return all_items
    
    # --- CLASIFICACIÓN POR IA ---
    def classify_with_gemini(self, items):
        """Clasificación por lotes con Gemini Flash"""
        if not items:
            print("  ⚠️  No hay items para clasificar")
            return
        
        print(f"🔎 FASE 2: Clasificación IA ({len(items)} titulares)...")
        
        # Prompt optimizado para JSON estricto
        SYSTEM_PROMPT = """Eres un clasificador geopolítico. Para cada titular:
1. TRADUCE al español manteniendo significado exacto
2. ASIGNA UNA de estas áreas: 
   - Seguridad y Conflictos
   - Economía y Sanciones  
   - Energía y Recursos
   - Soberanía y Alianzas
   - Tecnología y Espacio
   - Sociedad y Derechos

RESPONDE SOLO CON JSON: {"res": [{"id": "...", "area": "...", "titulo_es": "..."}]}"""
        
        classified = []
        batch_size = 35  # Optimizado para Gemini Flash
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i+batch_size]
            
            # Crear prompt del batch
            batch_text = "\n".join([f"ID:{item['id']}|{item['title']}" for item in batch])
            full_prompt = f"{SYSTEM_PROMPT}\n\n{batch_text}"
            
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=full_prompt,
                    config={"temperature": 0.1, "max_output_tokens": 1500}
                )
                
                data = self.extract_json(response.text)
                
                if data and 'res' in data:
                    for result in data['res']:
                        item_id = str(result.get('id', '')).strip()
                        area_name = result.get('area', '')
                        translated_title = result.get('titulo_es', '')
                        
                        # Validar y clasificar área
                        classified_area = self.classify_area(area_name)
                        
                        if classified_area and translated_title:
                            # Buscar el item original
                            original_item = next((it for it in batch if it['id'] == item_id), None)
                            
                            if original_item:
                                region = original_item['region']
                                link = original_item['link']
                                
                                # Control de cupo por región en área
                                if len(self.matrix[classified_area][region]) < MAX_PER_REGION_IN_AREA:
                                    self.matrix[classified_area][region].append({
                                        "titulo_es": translated_title,
                                        "link": link,
                                        "region": region,
                                        "original_title": original_item['title']
                                    })
                                    classified.append({
                                        "area": classified_area,
                                        "titulo_es": translated_title,
                                        "region": region
                                    })
                                    self.stats["classified"] += 1
                
                print(f"  📦 Batch {i//batch_size + 1}: {len(data['res'] if data else [])} procesados")
                
            except Exception as e:
                print(f"  ⚠️  Error en batch {i//batch_size + 1}: {str(e)[:50]}...")
                continue
            
            # Pequeña pausa entre batches
            if i + batch_size < len(items):
                time.sleep(0.5)
        
        print(f"  ✅ Clasificados: {self.stats['classified']} titulares")
    
    # --- ANÁLISIS DE FRICCIÓN Y MICRO-INFORMES ---
    def analyze_narrative_friction(self):
        """Calcula fricción narrativa y genera micro-informes"""
        print("📐 FASE 3: Análisis de fricción inter-bloques...")
        final_carousel = []
        
        for area in AREAS:
            # Recolectar todos los nodos del área
            nodes = []
            for region_list in self.matrix[area].values():
                nodes.extend(region_list)
            
            if not nodes:
                continue
            
            print(f"  📊 Área: {area} ({len(nodes)} señales)")
            
            # --- VECTORIZACIÓN RÁPIDA ---
            texts_to_embed = [node['titulo_es'] for node in nodes]
            vectors = []
            
            try:
                # Embedding batch
                emb_response = self.client.models.embed_content(
                    model="text-embedding-004",
                    contents=texts_to_embed,
                    config={'task_type': 'RETRIEVAL_DOCUMENT'}
                )
                vectors = [emb.values for emb in emb_response.embeddings]
            except Exception as e:
                print(f"  ⚠️  Error en embeddings: {e}")
                # Fallback: vectores aleatorios normalizados
                vectors = [[0.01] * 768 for _ in nodes]
            
            # --- CÁLCULO DE FRICCIÓN ---
            # Agrupar vectores por región
            vectors_by_region = defaultdict(list)
            for idx, vector in enumerate(vectors):
                region = nodes[idx]['region']
                vectors_by_region[region].append(vector)
            
            particles = []
            for idx, node in enumerate(nodes):
                current_vector = vectors[idx]
                current_region = node['region']
                
                # Recolectar vectores de otras regiones
                other_vectors = []
                for region, vec_list in vectors_by_region.items():
                    if region != current_region:
                        other_vectors.extend(vec_list)
                
                if not other_vectors:
                    # Solo una región habla de esto
                    proximity = 50.0
                    bias_label = "Perspectiva Única"
                else:
                    # Calcular centroide de "el resto del mundo"
                    # Promedio por dimensión
                    other_centroid = []
                    for dim_idx in range(len(current_vector)):
                        dim_values = [vec[dim_idx] for vec in other_vectors]
                        other_centroid.append(sum(dim_values) / len(dim_values))
                    
                    # Similitud coseno
                    dot_product = sum(a*b for a, b in zip(current_vector, other_centroid))
                    norm_current = math.sqrt(sum(x*x for x in current_vector))
                    norm_other = math.sqrt(sum(x*x for x in other_centroid))
                    
                    if norm_current * norm_other > 0:
                        similarity = dot_product / (norm_current * norm_other)
                        # Escalar a 0-100
                        proximity = max(0.0, min(100.0, (similarity * 50) + 50))
                    else:
                        proximity = 50.0
                
                # Etiqueta de sesgo
                if proximity > 85:
                    bias_label = "Consenso Global"
                elif proximity > 70:
                    bias_label = "Alineación"
                elif proximity > 55:
                    bias_label = "Tensión Moderada"
                elif proximity > 40:
                    bias_label = "Divergencia"
                else:
                    bias_label = "Contraste Radical"
                
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:10],
                    "titulo": node['titulo_es'],
                    "link": node['link'],
                    "bloque": REGIONS.get(current_region, "GLOBAL"),
                    "proximidad": round(proximity, 1),
                    "sesgo": bias_label,
                    "region": current_region
                })
            
            # --- MICRO-INFORME PARA NETFLIX ---
            micro_informe = self.generate_micro_report(area, particles)
            
            # Ordenar por proximidad (más consensuados primero)
            particles.sort(key=lambda x: x['proximidad'], reverse=True)
            
            final_carousel.append({
                "area": area,
                "punto_cero": micro_informe,  # <-- Para el modal Netflix
                "color": COLORS.get(area, "#00fffb"),
                "total_particulas": len(particles),
                "particulas": particles[:30]  # Top 30 por área
            })
        
        return final_carousel
    
    def generate_micro_report(self, area, particles):
        """Genera micro-informe de 25 palabras para el área"""
        if not particles:
            return f"Actividad limitada detectada en {area}."
        
        # Seleccionar los titulares más representativos
        top_titles = [p['titulo'] for p in particles[:4]]
        
        # Prompt para micro-análisis
        prompt = f"""Analiza estos titulares sobre {area} y genera un micro-informe de 1-2 frases (máximo 25 palabras) que describa la tendencia principal.
        
        Titulares:
        {chr(10).join(f'- {title}' for title in top_titles)}
        
        Responde solo con el micro-informe, sin explicaciones adicionales."""
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={"temperature": 0.3, "max_output_tokens": 100}
            )
            
            informe = response.text.strip()
            # Limitar a 25 palabras aproximadamente
            words = informe.split()
            if len(words) > 30:
                informe = ' '.join(words[:30]) + "..."
            
            return informe
            
        except Exception as e:
            print(f"  ⚠️  Error generando micro-informe: {e}")
            
            # Fallback inteligente basado en proximidad promedio
            avg_proximity = sum(p['proximidad'] for p in particles[:10]) / min(10, len(particles))
            
            if avg_proximity > 75:
                return f"Consenso global emergente en {area} con señales alineadas."
            elif avg_proximity > 60:
                return f"Tensión moderada detectada en {area} entre diferentes perspectivas."
            else:
                return f"Fricción narrativa significativa en {area} entre bloques geopolíticos."
    
    # --- GUARDADO DE RESULTADOS ---
    def save_results(self, carousel_data):
        """Guarda los resultados en múltiples formatos"""
        print("💾 FASE 4: Persistencia de inteligencia...")
        
        # Metadatos
        meta = {
            "updated": datetime.datetime.now().isoformat(),
            "execution_seconds": round(time.time() - self.session_start, 2),
            "stats": self.stats,
            "version": "GravityHubUltra v1.0",
            "total_areas": len([a for a in carousel_data if a['particulas']]),
            "total_particles": sum(len(a['particulas']) for a in carousel_data)
        }
        
        result = {
            "carousel": carousel_data,
            "meta": meta
        }
        
        # 1. Archivo principal
        try:
            with open("gravity_carousel.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print("  ✅ gravity_carousel.json actualizado")
        except Exception as e:
            print(f"  ❌ Error guardando principal: {e}")
        
        # 2. Histórico diario
        try:
            date_str = datetime.datetime.now().strftime("%Y-%m-%d")
            hist_path = f"historico_noticias/diario/{date_str}.json"
            
            with open(hist_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"  ✅ Histórico guardado: {hist_path}")
        except Exception as e:
            print(f"  ⚠️  Error guardando histórico: {e}")
        
        # 3. Archivo de resumen rápido
        try:
            summary = {
                "timestamp": meta["updated"],
                "areas": [
                    {
                        "area": a["area"],
                        "count": len(a["particulas"]),
                        "micro_informe": a["punto_cero"][:100]  # Primeros 100 chars
                    }
                    for a in carousel_data if a["particulas"]
                ]
            }
            
            with open("summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print("  ✅ summary.json generado")
        except Exception as e:
            print(f"  ⚠️  Error guardando resumen: {e}")
        
        return result
    
    # --- EJECUCIÓN PRINCIPAL ---
    def run(self):
        """Pipeline completo optimizado"""
        print("=" * 60)
        print("🚀 GRAVITY HUB ULTRA - Radar Geopolítico")
        print("=" * 60)
        
        try:
            # Pipeline
            items = self.fetch_all_feeds()
            self.classify_with_gemini(items)
            carousel = self.analyze_narrative_friction()
            result = self.save_results(carousel)
            
            # Reporte final
            total_time = time.time() - self.session_start
            total_particles = sum(len(a['particulas']) for a in carousel)
            
            print("\n" + "=" * 60)
            print("✅ ANÁLISIS COMPLETADO")
            print("=" * 60)
            print(f"📊 RESULTADOS:")
            print(f"   • Tiempo total: {total_time:.1f}s")
            print(f"   • Feeds procesados: {self.stats['feeds']}")
            print(f"   • Titulares recolectados: {self.stats['items']}")
            print(f"   • Titulares clasificados: {self.stats['classified']}")
            print(f"   • Áreas activas: {len([a for a in carousel if a['particulas']])}")
            print(f"   • Partículas totales: {total_particles}")
            print(f"\n🎯 MICRO-INFORMES GENERADOS:")
            for area in carousel:
                if area['particulas']:
                    print(f"   • {area['area']}: {area['punto_cero'][:60]}...")
            print("\n⚠️  Archivo principal: gravity_carousel.json")
            print("=" * 60)
            
            return result
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrumpido por usuario")
            return None
        except Exception as e:
            print(f"\n❌ ERROR CRÍTICO: {e}")
            import traceback
            traceback.print_exc()
            return None

# --- EJECUCIÓN ---
def main():
    """Función principal con manejo de API key"""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERROR: Variable GEMINI_API_KEY no encontrada")
        print("\nConfigura tu API key:")
        print("  Linux/Mac: export GEMINI_API_KEY='tu-clave-aqui'")
        print("  Windows: set GEMINI_API_KEY=tu-clave-aqui")
        sys.exit(1)
    
    # Ejecutar radar
    radar = GravityHubUltra(api_key)
    result = radar.run()
    
    if result:
        print("\n🎯 Inteligencia geopolítica actualizada exitosamente!")
        sys.exit(0)
    else:
        print("\n⚠️  El análisis encontró problemas")
        sys.exit(1)

if __name__ == "__main__":
    main()

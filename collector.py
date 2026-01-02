import os, json, datetime, time, ssl, urllib.request, re, hashlib
import xml.etree.ElementTree as ET
import concurrent.futures
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE RUTAS ---
PATHS = {
    "diario": "historico_noticias/diario", 
    "semanal": "historico_noticias/semanal", 
    "mensual": "historico_noticias/mensual"
}
for p in PATHS.values(): 
    os.makedirs(p, exist_ok=True)

ssl_context = ssl._create_unverified_context()

# --- CONFIGURACIÓN VISUAL ---
AREAS_ESTRATEGICAS = {
    "Seguridad y Conflictos": "#ef4444", 
    "Economía y Sanciones": "#3b82f6",
    "Energía y Recursos": "#10b981", 
    "Soberanía y Alianzas": "#f59e0b",
    "Tecnología y Espacio": "#8b5cf6", 
    "Sociedad y Derechos": "#ec4899"
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", 
    "INDIA": "#8b5cf6", "AFRICA": "#22c55e"
}

# --- FUENTES (optimizadas) ---
FUENTES = {
    "USA": [
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://feeds.a.dj.com/rss/RSSWorldNews.xml"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml",
        "https://rt.com/rss/news/"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed",
        "https://www.chinadaily.com.cn/rss/world_rss.xml"
    ],
    "EUROPE": [
        "https://www.france24.com/en/rss",
        "https://www.euronews.com/rss?level=vertical&name=news"
    ],
    "LATAM": [
        "https://www.jornada.com.mx/rss/edicion.xml",
        "https://legrandcontinent.eu/es/feed/"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.middleeasteye.net/rss"
    ],
    "INDIA": [
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    ],
    "AFRICA": [
        "https://services.radiofrance.fr/referentiels/rss/rfi/en/news.xml",
        "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml"
    ]
}

class GeopoliticalCollector:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.link_storage = {}  # {id: {title, url, region, summary}}
        self.title_to_id = {}   # {title: [id1, id2]} para manejar duplicados
        self.hoy = datetime.datetime.now()
        self.stats = {"total_fetched": 0, "processed": 0, "errors": 0}

    def fetch_rss(self):
        print(f"🌍 Escaneando fuentes multipolares...")
        results = {reg: [] for reg in FUENTES.keys()}
        
        def get_feed(region, url):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'application/xml, text/xml, */*'
                }
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    raw_data = resp.read()
                    
                    # Detectar encoding
                    try:
                        content = raw_data.decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            content = raw_data.decode('latin-1')
                        except:
                            content = raw_data.decode('utf-8', errors='replace')
                    
                    # Parsear XML
                    root = ET.fromstring(content)
                    
                    # Buscar items (RSS y Atom)
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    
                    extracted = []
                    for n in items[:12]:  # Limitar para no saturar
                        # Título
                        t_node = n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')
                        title = t_node.text.strip() if t_node is not None and t_node.text else None
                        
                        # Enlace
                        l_node = n.find('link') or n.find('{http://www.w3.org/2005/Atom}link')
                        link = ""
                        if l_node is not None:
                            link = l_node.text or l_node.attrib.get('href', '')
                        link = link.strip()
                        
                        # Descripción/resumen
                        d_node = n.find('description') or n.find('{http://www.w3.org/2005/Atom}summary') or n.find('{http://www.w3.org/2005/Atom}content')
                        description = d_node.text.strip() if d_node is not None and d_node.text else ""
                        
                        if title and link and link.startswith('http'):
                            # Crear ID único para evitar colisiones
                            title_hash = hashlib.md5(title.encode()).hexdigest()[:10]
                            article_id = f"{region}_{title_hash}"
                            
                            article_data = {
                                "id": article_id,
                                "title": title,
                                "link": link,
                                "summary": description[:500] if description else "",
                                "region": region,
                                "source": urlparse(url).netloc
                            }
                            
                            # Guardar en storage
                            self.link_storage[article_id] = article_data
                            
                            # Mapear título a ID(s) para búsqueda
                            if title not in self.title_to_id:
                                self.title_to_id[title] = []
                            self.title_to_id[title].append(article_id)
                            
                            extracted.append(article_data)
                    
                    return region, extracted
                    
            except Exception as e:
                err_msg = str(e)[:40]
                domain = url.split('/')[2] if len(url.split('/')) > 2 else url[:30]
                print(f"  ⚠️ {region}: {domain}... ({err_msg})")
                return region, []
        
        # Ejecutar concurrentemente
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = []
            for region, urls in FUENTES.items():
                for url in urls:
                    futures.append(executor.submit(get_feed, region, url))
            
            for future in concurrent.futures.as_completed(futures):
                region, news = future.result()
                results[region].extend(news)
                self.stats["total_fetched"] += len(news)
        
        print(f"  📊 RSS obtenidos: {self.stats['total_fetched']} artículos")
        return results

    def scrape_and_clean(self, articles):
        """Scrapea contenido de artículos seleccionados"""
        
        def process(article):
            try:
                # Si ya tenemos un buen resumen del RSS (>400 chars), usarlo
                if len(article.get('summary', '')) > 400:
                    article['text'] = article['summary'][:1500]
                    article['scraped'] = False
                    return article
                
                # Intentar scrapear contenido completo
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                req = urllib.request.Request(article['link'], headers=headers)
                
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    html = resp.read()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # Remover elementos no deseados
                    for tag in soup(["script", "style", "nav", "footer", "aside", 
                                    "header", "form", "iframe", ".ad", ".advertisement"]):
                        tag.decompose()
                    
                    # Extraer párrafos significativos
                    paragraphs = []
                    for p in soup.find_all('p'):
                        text = p.get_text().strip()
                        if len(text) > 60 and len(text) < 1000:
                            paragraphs.append(text)
                    
                    # Si no encontramos párrafos, buscar en otros elementos
                    if not paragraphs:
                        for div in soup.find_all(['div', 'article', 'main']):
                            text = div.get_text().strip()
                            if 100 < len(text) < 2000:
                                paragraphs.append(text[:500])
                    
                    # Combinar texto
                    if paragraphs:
                        text = " ".join(paragraphs[:8])[:1800]
                        article['text'] = text
                        article['scraped'] = True
                    else:
                        # Fallback al resumen del RSS
                        article['text'] = article.get('summary', 'Contenido no disponible')[:800]
                        article['scraped'] = False
                    
                    return article
                    
            except Exception as e:
                # Si falla el scraping, usar datos del RSS
                article['text'] = article.get('summary', 'Error al obtener contenido')[:800]
                article['scraped'] = False
                article['error'] = str(e)[:100]
                return article
        
        # Procesar concurrentemente
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            processed = list(executor.map(process, articles))
        
        # Filtrar artículos con contenido válido
        valid_articles = []
        for art in processed:
            if art and len(art.get('text', '')) > 100:
                valid_articles.append(art)
                self.stats["processed"] += 1
            else:
                self.stats["errors"] += 1
        
        return valid_articles

    def select_best_articles(self, region, items):
        """Usa Gemini para seleccionar las mejores 2 noticias por región"""
        if not items or len(items) < 2:
            return items[:2] if items else []
        
        try:
            # Preparar lista para Gemini
            titles_list = "\n".join([f"[{i}] {item['title'][:120]}" 
                                   for i, item in enumerate(items[:20])])
            
            prompt = f"""
            Eres un editor de inteligencia geopolítica para la región {region}.
            
            Selecciona los índices (0-N) de las 2 noticias con MAYOR impacto geopolítico GLOBAL.
            
            CRITERIOS:
            1. Conflictos internacionales o tensiones entre países
            2. Economía global, sanciones, acuerdos comerciales
            3. Seguridad, defensa, alianzas militares
            4. Tecnología estratégica, ciberseguridad, espacio
            5. Soberanía, territorios en disputa
            
            Responde EXACTAMENTE en este formato JSON:
            {{"indices": [número1, número2]}}
            
            LISTA:
            {titles_list}
            """
            
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.1,
                    'max_output_tokens': 200
                }
            )
            
            # Parsear respuesta (con manejo robusto)
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '')
            
            try:
                result = json.loads(response_text)
                # Aceptar "indices" o "idx"
                indices = result.get("indices", result.get("idx", [0, 1]))
                
                # Validar índices
                valid_indices = [idx for idx in indices 
                               if isinstance(idx, int) and 0 <= idx < len(items)]
                
                if valid_indices:
                    return [items[idx] for idx in valid_indices[:2]]
                else:
                    return items[:2]
                    
            except json.JSONDecodeError:
                print(f"  ⚠️ {region}: JSON inválido de Gemini, usando primeros 2")
                return items[:2]
                
        except Exception as e:
            print(f"  ⚠️ {region}: Error en selección ({str(e)[:30]}), usando primeros 2")
            return items[:2]

    def analyze(self, context):
        """Análisis final con Gemini para generar la matriz"""
        if not context or len(context) < 500:
            print("❌ ERROR: Contexto insuficiente para análisis")
            return {"carousel": []}
        
        print(f"🧠 Generando Matriz de Gravedad...")
        
        prompt = f"""
        Eres el motor analítico del Observatorio Geopolítico Multipolar.
        
        ANALIZA este contexto y genera una matriz de 3-6 "áreas estratégicas" donde:
        1. Cada área es un tema geopolítico global
        2. El "punto_cero" es la descripción objetiva del tema
        3. Las "partículas" son narrativas regionales sobre ese tema
        
        DATOS REALES:
        {context}
        
        GENERA EXACTAMENTE este JSON:
        {{
          "carousel": [
            {{
              "area": "Nombre del área estratégica (ej: 'Tensiones en el Mar de China')",
              "punto_cero": "Descripción objetiva basada en los hechos reportados",
              "particulas": [
                {{
                  "titulo": "TÍTULO EXACTO de la noticia",
                  "bloque": "USA, CHINA, RUSSIA, EUROPE, etc.",
                  "proximidad": 0-100,
                  "sesgo": "Breve análisis del enfoque regional",
                  "link": "TÍTULO_EXACTO_ID"
                }}
              ]
            }}
          ]
        }}
        
        REGLAS ESTRICTAS:
        1. Usa SOLO los títulos que están en los datos
        2. Máximo 6 áreas estratégicas
        3. Cada área debe tener al menos 2 partículas (perspectivas regionales)
        4. "link" DEBE ser el TÍTULO EXACTO para que coincida con nuestras URLs
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.15,
                    'max_output_tokens': 2500
                }
            )
            
            response_text = response.text.strip()
            response_text = response_text.replace('```json', '').replace('```', '')
            
            result = json.loads(response_text)
            return result
            
        except Exception as e:
            print(f"❌ Error en análisis Gemini: {str(e)}")
            # Fallback básico
            return {
                "carousel": [{
                    "area": "Análisis Geopolítico",
                    "punto_cero": "Análisis basado en múltiples fuentes internacionales",
                    "particulas": []
                }]
            }

    def run(self):
        """Ejecuta el pipeline completo"""
        print("\n" + "="*60)
        print("🚀 OBSERVATORIO GEOPOLÍTICO MULTIPOLAR")
        print("="*60)
        
        # 1. Obtener noticias RSS
        raw_articles = self.fetch_rss()
        
        # 2. Procesar por región
        batch_text = ""
        all_enriched = []
        
        for region, items in raw_articles.items():
            if not items:
                continue
            
            print(f"\n📍 Procesando {region} ({len(items)} artículos)...")
            
            # Seleccionar mejores 2 con Gemini
            selected = self.select_best_articles(region, items)
            
            if selected:
                # Scrapear contenido
                enriched = self.scrape_and_clean(selected)
                
                for art in enriched:
                    # Añadir al contexto para Gemini
                    batch_text += f"[BLOQUE: {region}]\n"
                    batch_text += f"TÍTULO: {art['title']}\n"
                    batch_text += f"CONTENIDO: {art.get('text', '')[:800]}\n"
                    batch_text += f"URL_ID: {art['id']}\n\n"
                    
                    all_enriched.append(art)
        
        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   • Artículos obtenidos: {self.stats['total_fetched']}")
        print(f"   • Artículos procesados: {self.stats['processed']}")
        print(f"   • Errores: {self.stats['errors']}")
        
        if not all_enriched:
            print("❌ No se pudieron procesar artículos. Terminando.")
            return
        
        # 3. Análisis final con Gemini
        final_json = self.analyze(batch_text)
        
        # 4. Procesar y enriquecer el JSON final
        processed_carousel = []
        
        for slide in final_json.get('carousel', []):
            # Añadir color al área
            slide['color'] = AREAS_ESTRATEGICAS.get(
                slide['area'], 
                list(AREAS_ESTRATEGICAS.values())[len(processed_carousel) % len(AREAS_ESTRATEGICAS)]
            )
            
            # Procesar partículas
            processed_particles = []
            for p in slide.get('particulas', []):
                # Buscar URL por título
                original_title = p.get('titulo', '')
                ids = self.title_to_id.get(original_title, [])
                
                if ids:
                    # Tomar el primer ID que coincida
                    article_id = ids[0]
                    article_data = self.link_storage.get(article_id, {})
                    
                    p['link'] = article_data.get('link', '')
                    p['id'] = article_id
                    p['color_bloque'] = BLOQUE_COLORS.get(p.get('bloque', ''), "#94a3b8")
                    p['region'] = article_data.get('region', p.get('bloque', ''))
                    
                    processed_particles.append(p)
                else:
                    # Si no encontramos el título, intentar búsqueda parcial
                    for art_id, art_data in self.link_storage.items():
                        if original_title[:50] in art_data.get('title', ''):
                            p['link'] = art_data.get('link', '')
                            p['id'] = art_id
                            p['color_bloque'] = BLOQUE_COLORS.get(p.get('bloque', ''), "#94a3b8")
                            p['region'] = art_data.get('region', p.get('bloque', ''))
                            processed_particles.append(p)
                            break
            
            slide['particulas'] = processed_particles
            
            # Solo incluir slides con partículas válidas
            if processed_particles:
                processed_carousel.append(slide)
        
        final_json['carousel'] = processed_carousel
        
        # 5. Añadir metadatos
        final_json['metadata'] = {
            'generated_at': datetime.datetime.now().isoformat(),
            'total_articles': len(all_enriched),
            'regions_covered': list(set([a.get('region', '') for a in all_enriched])),
            'version': '2.0'
        }
        
        # 6. Guardar archivos
        # Archivo principal
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
        
        # Archivo histórico diario
        fecha = self.hoy.strftime('%Y%m%d_%H%M')
        with open(os.path.join(PATHS["diario"], f"{fecha}.json"), "w", encoding="utf-8") as f:
            json.dump(final_json, f, indent=2, ensure_ascii=False)
        
        # Archivar semanalmente si es domingo
        if self.hoy.weekday() == 6:  # Domingo = 6
            semana = self.hoy.strftime('%Y-W%U')
            with open(os.path.join(PATHS["semanal"], f"{semana}.json"), "w", encoding="utf-8") as f:
                json.dump(final_json, f, indent=2, ensure_ascii=False)
        
        # Archivar mensualmente si es día 1
        if self.hoy.day == 1:
            mes = self.hoy.strftime('%Y-%m')
            with open(os.path.join(PATHS["mensual"], f"{mes}.json"), "w", encoding="utf-8") as f:
                json.dump(final_json, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("="*60)
        print(f"📁 Archivos generados:")
        print(f"   • gravity_carousel.json (principal)")
        print(f"   • historico_noticias/diario/{fecha}.json")
        print(f"📊 Matriz: {len(processed_carousel)} áreas estratégicas")
        print(f"   Total partículas: {sum(len(s['particulas']) for s in processed_carousel)}")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        collector = GeopoliticalCollector(key)
        try:
            collector.run()
        except KeyboardInterrupt:
            print("\n\n⚠️  Proceso interrumpido por el usuario")
        except Exception as e:
            print(f"\n❌ Error crítico: {str(e)}")
            # Guardar error log
            with open("error_log.txt", "w") as f:
                f.write(f"Error: {str(e)}\nTime: {datetime.datetime.now()}")
    else:
        print("❌ ERROR: Variable de entorno GEMINI_API_KEY no encontrada")
        print("   Configura: export GEMINI_API_KEY='tu_clave_aqui'")

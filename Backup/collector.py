import os, json, datetime, urllib.request, ssl, re, time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN TÉCNICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

# --- FUENTES ESTRATÉGICAS (3+ POR REGIÓN) ---
# Mapeado estricto a las 7 Regiones del Observatorio V2
FUENTES = {
    "USA": [
        "https://www.npr.org/rss/rss.php?id=1004", 
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://api.washingtontimes.com/rss/headlines/news/world/",
        "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"
    ],
    "RUSSIA": [
        "https://tass.com/rss/v2.xml", 
        "https://rt.com/rss/news/",
        "https://en.interfax.ru/rss/",
        "https://themoscowtimes.com/rss/news"
    ],
    "CHINA": [
        "https://www.scmp.com/rss/91/feed", 
        "http://www.ecns.cn/rss/rss.xml",
        "https://www.globaltimes.cn/rss/index.xml",
        "http://www.xinhuanet.com/english/rss/world.xml"
    ],
    "EUROPE": [
        "https://www.france24.com/en/rss", 
        "https://www.dw.com/xml/rss-en-all",
        "https://www.euronews.com/rss?level=vertical&name=news",
        "https://www.theguardian.com/world/rss"
    ],
    "LATAM": [
        "https://www.jornada.com.mx/rss/edicion.xml", 
        "https://www.clarin.com/rss/mundo/",
        "https://www.infobae.com/america/rss/",
        "https://elpais.com/rss/elpais/americas.xml"
    ],
    "MID_EAST": [
        "https://www.aljazeera.com/xml/rss/all.xml", 
        "https://www.trtworld.com/rss",
        "https://www.timesofisrael.com/feed/",
        "https://www.arabnews.com/rss.xml"
    ],
    "INDIA": [ 
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", 
        "https://www.thehindu.com/news/national/feeder/default.rss",
        "https://zeenews.india.com/rss/india-national-news.xml",
        "https://idsa.in/rss.xml"
    ]
}

def clean_html(html_content):
    """Deep Scraping: Limpieza profunda de HTML para extraer solo texto relevante."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        # Eliminar ruido
        for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "ad", "iframe"]):
            noisy.decompose()
        
        # Extraer párrafos sustantivos (> 60 caracteres)
        paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 60]
        
        # Tomar los primeros 6 párrafos o 2500 caracteres
        text = " ".join(paragraphs[:6])
        return re.sub(r'\s+', ' ', text).strip()[:2500]
    except:
        return ""

def fetch_rss_items(url, limit=5):
    """Descarga y parsea RSS con manejo robusto de errores."""
    items_found = []
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
            xml_data = resp.read()
            # Intento 1: Parseo directo
            try:
                root = ET.fromstring(xml_data)
            except:
                # Intento 2: Decode manual
                root = ET.fromstring(xml_data.decode('utf-8', errors='ignore'))
            
            # Soportar RSS <item> y Atom <entry>
            nodes = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for node in nodes[:limit]:
                t_node = node.find('title') or node.find('{http://www.w3.org/2005/Atom}title')
                l_node = node.find('link') or node.find('{http://www.w3.org/2005/Atom}link')
                
                title = t_node.text.strip() if t_node is not None and t_node.text else "Sin Título"
                
                # Manejo de Link (Atributo href o texto interno)
                link = ""
                if l_node is not None:
                    link = l_node.attrib.get('href') if l_node.attrib.get('href') else l_node.text
                
                if link:
                    items_found.append({"title": title, "link": link.strip()})
                    
    except Exception as e:
        print(f"   [!] Error en fuente {url[:40]}...: {str(e)[:50]}")
    
    return items_found

def get_full_content(url):
    """Wrapper para obtener contenido limpio de una URL."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
            return clean_html(resp.read())
    except:
        return ""

def collect():
    print("\n" + "═"*70 + "\n🛰️  OBSERVATORIO V2: INICIANDO ESCANEO GLOBAL\n" + "═"*70)
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR CRÍTICO: Variable de entorno GEMINI_API_KEY no encontrada.")
        return

    client = genai.Client(api_key=api_key)
    accumulated_context = ""
    stats = {"scanned": 0, "processed": 0}

    # 1. RECOLECCIÓN (FASE DE INGESTA)
    for region, urls in FUENTES.items():
        print(f"\n🌍 Escaneando Región: {region}...")
        region_pool = []
        
        for url in urls:
            items = fetch_rss_items(url, limit=4) # Top 4 por fuente
            region_pool.extend(items)
            stats["scanned"] += len(items)
        
        if not region_pool:
            continue

        # 2. TRIAJE IA (CAPA 1: SELECCIÓN)
        # Pedimos a Gemini que seleccione las 2 más relevantes geopolíticamente para ahorrar tokens
        list_str = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(region_pool)])
        prompt_triaje = f"""
        Actúa como Editor Jefe de Inteligencia {region}. 
        De esta lista, selecciona los índices (0-N) de las 2 noticias con mayor impacto geopolítico global (Conflictos, Economía, Alianzas).
        Responde SOLO JSON: {{"indices": [x, y]}}
        LISTA:
        {list_str}
        """
        
        try:
            res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_triaje, config={'response_mime_type': 'application/json'})
            indices = json.loads(res.text.strip().replace('```json', '').replace('```', '')).get("indices", [])
        except:
            indices = [0, 1] # Fallback
            
        # 3. EXTRACCIÓN PROFUNDA (FASE DE ENTENDIMIENTO)
        for idx in indices:
            if idx < len(region_pool):
                news = region_pool[idx]
                print(f"   -> Procesando: {news['title'][:50]}...")
                content = get_full_content(news['link'])
                if content:
                    accumulated_context += f"REGION: {region} | TÍTULO: {news['title']} | LINK: {news['link']} | TEXTO: {content}\n\n"
                    stats["processed"] += 1

    # 4. SÍNTESIS GLOBAL (CAPA 2: MOTOR DE INFERENCIA V2)
    print(f"\n🧠 PROCESANDO CONTEXTO ({stats['processed']} artículos)... Generando Matriz de Gravedad...")
    
    prompt_final = """
    Eres el motor 'Global Gravity Index'. Tu objetivo es analizar las noticias globales y estructurarlas para el Observatorio V2.
    
    TAREA:
    1. Identifica 5-7 "Eventos/Narrativas" transversales que aparezcan en múltiples regiones.
    2. Para cada evento, analiza CÓMO lo cubre cada región (Perspectiva).
    3. Identifica "Puntos Ciegos" (Regiones que NO cubren el tema o lo ignoran activamente).
    
    GENERA EL SIGUIENTE JSON EXACTO:
    [
        {
            "id": 1,
            "title": "Título conciso del Evento Global",
            "category": "Una de: Economía, Conflicto, Tecnología, Clima, Sociedad, Soberanía",
            "regions_coverage": ["LISTA DE REGIONES QUE CUBREN EL TEMA (IDs: USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM)"],
            "blind_spots": ["LISTA DE REGIONES QUE IGNORAN EL TEMA"],
            "perspectives": {
                "USA": { "weight": (1-10 Intensidad), "synthesis": "Resumen de 30 palabras sobre el enfoque de USA...", "keyword": "Palabra Clave" },
                ... (repetir para cada región QUE CUBRA el tema. Si es blind spot, NO incluir aquí)
            },
            "blind_spot_analysis": "Frase analítica sobre por qué las regiones del blind_spot lo estarían ignorando (hipótesis basada en su Razón de Estado)."
        }
    ]
    
    REGLAS:
    - No inventes noticias. Usa solo el CONTEXTO PROPORCIONADO.
    - Si una región no tiene noticias sobre el tema, DEBE ir a 'blind_spots'.
    - El JSON debe ser válido.
    
    CONTEXTO:
    """ + accumulated_context

    try:
        res = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt_final,
            config={'response_mime_type': 'application/json', 'temperature': 0.1}
        )
        
        data = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        
        # Guardar resultado
        with open("latest_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print("\n✅ ÉXITO: 'latest_news.json' generado correctamente.")
        print(f"   Eventos detectados: {len(data)}")
        for ev in data:
            print(f"   - {ev['title']} ({len(ev['regions_coverage'])} Regiones, {len(ev['blind_spots'])} Vacíos)")
            
    except Exception as e:
        print(f"\n❌ Error en generación final: {e}")

if __name__ == "__main__":
    collect()

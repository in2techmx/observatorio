import os, json, datetime, urllib.request, ssl, re, time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN ESTRATÉGICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

CATEGORIAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio"]
BLOQUE_COLORS = {
    "USA": "#3b82f6", "EUROPE": "#fde047", "RUSSIA": "#ef4444", 
    "CHINA": "#f97316", "LATAM": "#d946ef", "MID_EAST": "#10b981", "INDIA": "#8b5cf6",
    "AFRICA": "#22c55e" # Nuevo color para África
}

# --- RED DE FUENTES (Actualizado con África y 3 fuentes por región) ---
FUENTES = {
    "USA": ["https://www.npr.org/rss/rss.php?id=1004", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "https://api.washingtontimes.com/rss/headlines/news/world/"],
    "RUSSIA": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/", "https://en.interfax.ru/rss/"],
    "CHINA": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml", "https://www.globaltimes.cn/rss/index.xml"],
    "EUROPE": ["https://www.france24.com/en/rss", "https://www.dw.com/xml/rss-en-all", "https://www.euronews.com/rss?level=vertical&name=news"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "MID_EAST": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss", "https://www.timesofisrael.com/feed/"],
    "INDIA": ["https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "https://www.thehindu.com/news/national/feeder/default.rss", "https://zeenews.india.com/rss/india-national-news.xml"],
    "AFRICA": ["https://www.africanews.com/feeds/rss", "https://allafrica.com/tools/headlines/rdf/latestnews/index.xml", "https://www.theafricareport.com/feed/"] # Nuevas fuentes para África
}

def clean_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "ad"]):
            noisy.decompose()
        paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 60]
        return " ".join(paragraphs[:6]).strip()[:2000]
    except: return ""

def collect():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    contexto_final = ""
    link_backup = {} # Memoria para evitar links dummy
    
    for bloque, urls in FUENTES.items():
        print(f"🌍 Escaneando {bloque}...")
        region_pool = []
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    nodes = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    for n in nodes[:5]:
                        t = (n.find('title') or n.find('{http://www.w3.org/2005/Atom}title')).text
                        l_node = n.find('link') or n.find('{http://www.w3.org/2005/Atom}link')
                        l = l_node.attrib.get('href') if (l_node is not None and l_node.attrib) else (l_node.text if l_node is not None else "")
                        if t and l: region_pool.append({"title": t.strip(), "link": l.strip()})
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue

        # Triaje IA de 2 artículos por bloque
        if region_pool:
            list_str = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(region_pool)])
            prompt_triaje = f"Selecciona los índices de las 2 noticias más relevantes para {bloque}. JSON: {{\"indices\": [x, y]}}. LISTA:\n{list_str}"
            try:
                res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_triaje, config={'response_mime_type': 'application/json'})
                indices = json.loads(res.text.strip().replace('```json', '').replace('```', '')).get("indices", [0,1])
                for idx in indices:
                    if idx < len(region_pool):
                        news = region_pool[idx]
                        try:
                            req_article = urllib.request.Request(news['link'], headers=HEADERS)
                            with urllib.request.urlopen(req_article, timeout=10, context=ssl_context) as resp_article:
                                cuerpo = clean_html(resp_article.read())
                                if cuerpo:
                                    link_backup[news['title']] = news['link']
                                    contexto_final += f"REGION: {bloque} | TITULO: {news['title']} | LINK: {news['link']} | TEXTO: {cuerpo}\n\n"
                        except Exception as e:
                            print(f"Error fetching article {news['link']}: {e}")
                            continue
            except Exception as e:
                print(f"Error during AI triaging for {bloque}: {e}")
                continue

    # SÍNTESIS CON MATRIZ DE GRAVEDAD (Proximidad sin Bias)
    prompt_final = f"""
    Eres un motor de cálculo de proximidad narrativa. No opines, calcula distancias.
    1. Define el 'Punto Cero' de cada categoría basándote en los hechos repetidos en la mayoría de las regiones.
    2. Calcula la 'Proximidad' (0-100%) de cada noticia según su desviación de ese Punto Cero.
    
    ESTRUCTURA JSON:
    {{
      "categorias": [
        {{
          "nombre": "Nombre de Categoría",
          "consenso": "Resumen del Punto Cero",
          "particulas": [
            {{ "titulo": "Título", "bloque": "Región", "proximidad": 0-100, "analisis_regional": "Sesgo", "link": "LINK_REAL" }}
          ]
        }}
      ]
    }}
    CONTEXTO: {contexto_final}
    """
    
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_final, config={'response_mime_type': 'application/json', 'temperature': 0.0})
        data = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        
        # AUTO-CORRECCIÓN DE LINKS
        for cat in data['categorias']:
            for p in cat['particulas']:
                if "example" in p['link'] or "URL" in p['link']:
                    p['link'] = link_backup.get(p['titulo'], p['link'])
                p['color_bloque'] = BLOQUE_COLORS.get(p['bloque'], "#ffffff")

        with open("latest_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("✅ Matriz de Gravedad generada y links validados.")
    except Exception as e: print(f"❌ Error: {e}")

if __name__ == "__main__": collect()

import os, json, datetime, urllib.request, ssl, re
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE SEGURIDAD Y HEADERS ---
ssl_context = ssl._create_unverified_context()
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

CATEGORIAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio"]

FUENTES_ESTRATEGICAS = {
    "USA": ["https://www.washingtontimes.com/rss/headlines/news/world/", "https://feeds.aoc.org/reuters/USA"],
    "Rusia": ["https://tass.com/rss/v2.xml", "https://pravda-en.com/rss/"],
    "China": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "Europa": ["https://www.dw.com/en/top-stories/rss", "https://www.france24.com/en/rss"],
    "África": ["https://www.africanews.com/feed/", "https://www.premiumtimesng.com/feed"],
    "LATAM": [
        "https://www.clarin.com/rss/mundo/",
        "https://www.infobae.com/feeds/rss/",
        "https://www.eluniversal.com.mx/rss.xml",
        "https://www.jornada.com.mx/rss/edicion.xml?v=1"
    ],
    "Medio Oriente": [
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.trtworld.com/rss",
        "https://www.hispantv.com/rss/noticias"
    ]
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "Europa": "#fde047", "Rusia": "#ef4444", 
    "China": "#f97316", "LATAM": "#d946ef", "Medio Oriente": "#10b981", "África": "#8b5cf6"
}

def clean_text(text):
    """Elimina URLs, emails y normaliza espacios para optimizar tokens"""
    text = re.sub(r'http\S+', '', text) 
    text = re.sub(r'\S*@\S*\s?', '', text) 
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_pure_content(url):
    """Extrae el cuerpo de la noticia eliminando Ads, Nav y Scripts"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            
            # 1. ELIMINAR RUIDO: Etiquetas no periodísticas
            for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button", "iframe"]):
                noisy.decompose()
            
            # 2. FILTRADO DE PÁRRAFOS: Solo contenido sustancial
            paragraphs = soup.find_all('p')
            news_content = []
            for p in paragraphs:
                txt = p.get_text()
                # Filtrar avisos de cookies o párrafos muy cortos/irrelevantes
                if len(txt) > 70 and not any(x in txt.lower() for x in ["cookie", "subscribe", "follow us"]):
                    news_content.append(txt)
            
            # Unir los párrafos más importantes (primeros 5)
            full_text = " ".join(news_content[:5])
            return clean_text(full_text)[:1400]
    except:
        return "Contenido no accesible."

def collect():
    print("📡 Iniciando Deep Scan (Limpieza de contenido y Ads)...")
    raw_context = ""
    
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read())
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    
                    for item in items[:2]:
                        title_n = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                        title = title_n.text if title_n is not None else ""
                        
                        link_n = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        link = link_n.attrib['href'] if link_n is not None and 'href' in link_n.attrib else (link_n.text if link_n is not None else "")

                        if link and title:
                            print(f"   ∟ Depurando noticia: {title[:45]}...")
                            body = get_pure_content(link)
                            raw_context += f"BLOQUE: {bloque} | TÍTULO: {title} | ARGUMENTOS: {body}\n\n"
                            
                print(f"✅ Fuente depurada: {url[:35]}...")
            except Exception as e:
                print(f"⚠️ Error en fuente: {url[:30]}... {str(e)[:30]}")

    # Análisis de Proximidad con Gemini 2.0 Flash
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    prompt = f"""
    Actúa como un motor de análisis geopolítico multipolar.
    Analiza este CUERPO DE NOTICIAS (limpio de anuncios y ruido):
    {raw_context}

    TAREA:
    1. Agrupa en: {CATEGORIAS}.
    2. Determina el 'Consenso Global' (qué dicen la mayoría de los bloques).
    3. Calcula la Proximidad (0-100) basándote en la semejanza de los ARGUMENTOS del texto.
    4. En 'analisis_regional', describe la disidencia específica de ese bloque frente al consenso.
    5. Usa esta paleta: {BLOQUE_COLORS}.

    RESPONDE SOLO JSON:
    {{
      "categorias": [
        {{
          "nombre": "Nombre de Categoría",
          "consenso": "...",
          "particulas": [
            {{
              "titulo": "...",
              "bloque": "...",
              "proximidad": 80,
              "color_bloque": "#hex",
              "analisis_regional": "...",
              "link": "..."
            }}
          ]
        }}
      ]
    }}
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        data = json.loads(response.text.strip())
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print("✅ Universo geopolítico depurado y actualizado.")
    except Exception as e:
        print(f"❌ Error en el análisis de IA: {e}")

if __name__ == "__main__":
    collect()

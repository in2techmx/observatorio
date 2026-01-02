import os, json, datetime, urllib.request
import xml.etree.ElementTree as ET
from google import genai

# --- CONFIGURACIÓN DE CATEGORÍAS ---
CATEGORIAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio"]

# --- FUENTES ESTRATEGICAS SOLICITADAS ---
FUENTES_ESTRATEGICAS = {
    "USA": [
        "https://www.washingtontimes.com/rss/headlines/news/world/", 
        "https://feeds.aoc.org/reuters/USA"
    ],
    "Rusia": [
        "https://tass.com/rss/v2.xml", 
        "https://pravda-en.com/rss/"
    ],
    "China": [
        "https://www.scmp.com/rss/91/feed", 
        "http://www.ecns.cn/rss/rss.xml"
    ],
    "Europa": [
        "https://www.dw.com/en/top-stories/rss", 
        "https://www.france24.com/en/rss"
    ],
    "África": [
        "https://www.africanews.com/feed/", 
        "https://www.premiumtimesng.com/feed"
    ],
    "LATAM": [
        "https://www.telesurenglish.net/rss/sport.xml",
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

# --- PALETA DE COLORES REGIONALES ---
BLOQUE_COLORS = {
    "USA": "#3b82f6", "Europa": "#fde047", "Rusia": "#ef4444", 
    "China": "#f97316", "LATAM": "#d946ef", "Medio Oriente": "#10b981", "África": "#8b5cf6"
}

def collect():
    print("📡 Iniciando Deep Scan Multipolar...")
    raw_context = ""
    
    # 1. Recolección de noticias
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        for url in urls:
            try:
                # User-Agent para evitar bloqueos
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    xml_data = resp.read()
                    root = ET.fromstring(xml_data)
                    items = root.findall('.//item')
                    # Tomamos las más recientes para no saturar el prompt
                    for item in items[:4]:
                        title = item.find('title').text if item.find('title') is not None else ""
                        desc = item.find('description').text if item.find('description') is not None else ""
                        link = item.find('link').text if item.find('link') is not None else ""
                        raw_context += f"BLOQUE: {bloque} | TÍTULO: {title} | RESUMEN: {desc[:200]} | LINK: {link}\n\n"
            except Exception as e:
                print(f"⚠️ Saltando fuente {url} por error técnico.")

    # 2. Análisis Planetario con Gemini
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    prompt = f"""
    Eres un Analista de Inteligencia Geopolítica de Datos.
    Analiza este cuerpo de noticias para crear un sistema planetario de proximidad narrativa:
    {raw_context}

    REGLAS:
    1. Agrupa las noticias en estas CATEGORÍAS maestras: {CATEGORIAS}.
    2. Define para cada categoría una 'Narrativa de Consenso'.
    3. Para cada noticia (partícula), calcula su 'Proximidad' (0-100) al consenso.
    4. El color debe ser el asignado aquí: {BLOQUE_COLORS}.
    5. 'analisis_regional' debe explicar qué hace a esta noticia diferente o disidente.

    RESPONDE EXCLUSIVAMENTE EN JSON CON ESTA ESTRUCTURA:
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
        
        # Guardar para la web
        with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        # Guardar histórico
        ts = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
        hist_dir = os.path.join(base_dir, "historico_noticias")
        if not os.path.exists(hist_dir): os.makedirs(hist_dir)
        with open(os.path.join(hist_dir, f"analisis_{ts}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        print(f"✅ Éxito: {len(data['categorias'])} cúmulos generados con fuentes globales.")

    except Exception as e:
        print(f"❌ Error en IA: {e}")

if __name__ == "__main__":
    collect()

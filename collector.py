import os, json, datetime, urllib.request, ssl, re, time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN ESTRATÉGICA ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

CATEGORIAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio"]

BLOQUE_COLORS = {
    "USA": "#3b82f6", "Europa": "#fde047", "Rusia": "#ef4444", 
    "China": "#f97316", "LATAM": "#d946ef", "Medio Oriente": "#10b981", "África": "#8b5cf6"
}

FUENTES_ESTRATEGICAS = {
    "USA": ["https://www.washingtontimes.com/rss/headlines/news/world/", "https://www.washingtontimes.com/rss/headlines/news/politics/"],
    "Rusia": ["https://tass.com/rss/v2.xml"],
    "China": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "Europa": ["https://www.france24.com/en/rss", "https://es.euronews.com/rss?level=vertical&name=noticias"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "Medio Oriente": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.hispantv.com/rss/noticias"],
    "África": ["https://www.africanews.com/feed/"]
}

def get_pure_content(url):
    """Extrae el núcleo narrativo (Deep Scraping)"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "ad"]):
                noisy.decompose()
            paragraphs = soup.find_all('p')
            text = " ".join([p.get_text().strip() for p in paragraphs if len(p.get_text()) > 100][:6])
            return re.sub(r'\s+', ' ', text).strip()[:1500]
    except:
        return ""

def triaje_inteligente(client, bloque, pool):
    """La IA filtra 20 titulares y elige los 3 más pesados geopolíticamente"""
    listado = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(pool)])
    prompt = f"""
    Como analista de inteligencia, selecciona los índices de los 3 titulares más estratégicos del bloque '{bloque}'.
    Ignora temas locales, deportes o farándula. Céntrate en poder global.
    LISTA:
    {listado}
    Responde solo JSON: {{"indices": [0, 1, 2]}}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json).get("indices", [])
    except:
        return [0, 1]

def collect():
    print("📡 Iniciando Fase 1: Radar (20 noticias por fuente)...")
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    contexto_final = ""
    
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        pool_bloque = []
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    xml_data = resp.read().decode('utf-8', errors='ignore')
                    root = ET.fromstring(xml_data)
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    for item in items[:20]:
                        t_node = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                        t = t_node.text if t_node is not None else ""
                        l_node = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        l = l_node.attrib.get('href') if l_node is not None and l_node.attrib else (l_node.text if l_node is not None else "")
                        if t and l: pool_bloque.append({"title": t, "link": l})
            except: continue

        if pool_bloque:
            print(f"🧠 Triaje IA para {bloque}...")
            seleccionados = triaje_inteligente(client, bloque, pool_bloque)
            for idx in seleccionados:
                if idx < len(pool_bloque):
                    noticia = pool_bloque[idx]
                    print(f"   ∟ Leyendo cuerpo: {noticia['title'][:40]}...")
                    cuerpo = get_pure_content(noticia['link'])
                    if cuerpo:
                        contexto_final += f"BLOQUE: {bloque} | TÍTULO: {noticia['title']} | LINK: {noticia['link']} | CUERPO: {cuerpo}\n\n"
            time.sleep(1)

    print("🔮 Generando Estructura de Partículas para el Mapa...")
    prompt_final = f"""
    Analiza este universo de datos y genera un JSON para un mapa D3.js:
    {contexto_final}
    
    ESTRUCTURA JSON REQUERIDA:
    {{
      "categorias": [
        {{
          "nombre": "Nombre de la Categoría",
          "consenso": "Resumen del consenso global en 1 frase",
          "particulas": [
            {{
              "titulo": "Título de la noticia",
              "bloque": "Nombre del Bloque (USA, China, etc)",
              "proximidad": 85, 
              "analisis_regional": "Breve análisis del sesgo o enfoque de este bloque sobre el tema",
              "link": "URL original de la noticia",
              "color_bloque": "Usa el color asignado al bloque"
            }}
          ]
        }}
      ]
    }}
    
    Categorías: {CATEGORIAS}.
    Colores: {BLOQUE_COLORS}.
    Responde estrictamente en JSON.
    """
    
    try:
        res = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_final,
            config={'response_mime_type': 'application/json'}
        )
        clean_res = res.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_res)
        
        with open("latest_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("✅ Mapa actualizado: latest_news.json generado con partículas.")
    except Exception as e:
        print(f"❌ Error final: {e}")

if __name__ == "__main__":
    collect()

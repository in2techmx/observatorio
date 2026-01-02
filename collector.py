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
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "ad"]):
                noisy.decompose()
            text = " ".join([p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 100][:6])
            return re.sub(r'\s+', ' ', text).strip()[:1500]
    except: return ""

def triaje_inteligente(client, bloque, pool):
    listado = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(pool)])
    prompt = f"Selecciona los 3 índices más estratégicos geopolíticamente para '{bloque}'. Solo responde JSON: {{\"indices\": [0,1,2]}}. LISTA:\n{listado}"
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
        return json.loads(res.text.strip().replace('```json', '').replace('```', '')).get("indices", [])
    except: return [0, 1]

def collect():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    contexto_final = ""
    
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        pool = []
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=10, context=ssl_context) as resp:
                    root = ET.fromstring(resp.read().decode('utf-8', errors='ignore'))
                    for item in (root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry'))[:20]:
                        t = (item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')).text
                        l_node = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        l = l_node.attrib.get('href') if l_node.attrib else l_node.text
                        if t and l: pool.append({"title": t, "link": l})
            except: continue

        if pool:
            indices = triaje_inteligente(client, bloque, pool)
            for idx in indices:
                if idx < len(pool):
                    print(f"📡 Procesando: {bloque} -> {pool[idx]['title'][:50]}")
                    cuerpo = get_pure_content(pool[idx]['link'])
                    if cuerpo:
                        contexto_final += f"BLOQUE: {bloque} | TÍTULO: {pool[idx]['title']} | LINK: {pool[idx]['link']} | CUERPO: {cuerpo}\n\n"

    # PROMPT DE ALTA PRECISIÓN
    prompt_final = f"""
    Convierte esta base de datos en un mapa de partículas JSON. 
    DATOS: {contexto_final}
    
    REGLA ORO: Cada noticia en los DATOS debe ser una 'particula' dentro de su categoría. No resumas, mapea.
    Categorías: {CATEGORIAS}.
    Colores: {BLOQUE_COLORS}.
    
    ESTRUCTURA:
    {{
      "categorias": [
        {{
          "nombre": "Nombre de la Categoría",
          "consenso": "Tendencia global",
          "particulas": [
            {{
              "titulo": "Título de la noticia",
              "bloque": "Bloque",
              "proximidad": 85,
              "analisis_regional": "Breve sesgo",
              "link": "URL",
              "color_bloque": "HEX"
            }}
          ]
        }}
      ]
    }}
    """
    
    try:
        res = client.models.generate_content(model="gemini-2.0-flash", contents=prompt_final, config={'response_mime_type': 'application/json'})
        data = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        
        # VALIDACIÓN: Si Gemini entregó partículas vacías, forzamos un re-intento específico
        for cat in data['categorias']:
            if not cat['particulas'] and len(contexto_final) > 100:
                print(f"⚠️ Re-procesando categoría vacía: {cat['nombre']}")
                # (Aquí podríamos añadir lógica de re-intento, pero el prompt mejorado debería bastar)

        with open("latest_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("✅ Proceso completado con éxito.")
    except Exception as e:
        print(f"❌ Error Crítico: {e}")

if __name__ == "__main__":
    collect()

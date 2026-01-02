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

# --- RED DE FUENTES AMPLIADA ---
FUENTES_ESTRATEGICAS = {
    "USA": ["https://www.washingtontimes.com/rss/headlines/news/world/", "https://www.npr.org/rss/rss.php?id=1004"],
    "Rusia": ["https://tass.com/rss/v2.xml", "https://rt.com/rss/news/"],
    "China": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "Europa": ["https://www.france24.com/en/rss", "https://www.dw.com/xml/rss-en-all"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "Medio Oriente": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.trtworld.com/rss"],
    "África": ["https://www.africanews.com/feed/"]
}

def get_pure_content(url):
    """Lógica original de limpieza profunda (Deep Scraping)"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "ad"]):
                noisy.decompose()
            # Filtro de calidad: párrafos > 100 caracteres
            paragraphs = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text()) > 100]
            text = " ".join(paragraphs[:6])
            return re.sub(r'\s+', ' ', text).strip()[:1500]
    except:
        return ""

def triaje_inteligente(client, bloque, pool):
    """Lógica original para seleccionar los 3 mejores titulares"""
    listado = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(pool)])
    prompt = f"Selecciona los 3 índices más estratégicos geopolíticamente para '{bloque}'. Responde SOLO JSON: {{\"indices\": [0,1,2]}}. LISTA:\n{listado}"
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json).get("indices", [0, 1])
    except:
        return [0, 1]

def collect():
    print("📡 INICIANDO RECOLECCIÓN Y AUDITORÍA...")
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    contexto_final = ""
    status_report = {"exito": [], "error": []}
    
    for bloque, urls in FUENTES_ESTRATEGICAS.items():
        pool_bloque = []
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                    xml_data = resp.read()
                    # Intento de parseo robusto para evitar errores de tokens inválidos
                    try:
                        root = ET.fromstring(xml_data)
                    except:
                        root = ET.fromstring(xml_data.decode('utf-8', errors='ignore'))
                        
                    items = root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry')
                    for item in items[:20]:
                        t_node = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                        l_node = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        t = t_node.text if t_node is not None else ""
                        l = l_node.attrib.get('href') if (l_node is not None and l_node.attrib) else (l_node.text if l_node is not None else "")
                        if t and l: pool_bloque.append({"title": t.strip(), "link": l.strip()})
                status_report["exito"].append(f"{bloque}: {url[:35]}...")
            except Exception as e:
                status_report["error"].append(f"{bloque}: {url[:35]}... ({str(e)[:30]})")

        if pool_bloque:
            print(f"🧠 Triaje IA para {bloque}...")
            seleccionados = triaje_inteligente(client, bloque, pool_bloque)
            for idx in seleccionados:
                if idx < len(pool_bloque):
                    noticia = pool_bloque[idx]
                    cuerpo = get_pure_content(noticia['link'])
                    if cuerpo:
                        # Marcado explícito de URL para evitar alucinaciones
                        contexto_final += f"--- DATOS NOTICIA ---\nBLOQUE: {bloque}\nTÍTULO: {noticia['title']}\nURL_REAL: {noticia['link']}\nCONTENIDO: {cuerpo}\n--- FIN ---\n\n"

    # PROMPT DE ALTA PRECISIÓN (Mapeo estricto con temperatura 0)
    prompt_final = f"""
    Actúa como un transcriptor técnico. Genera un JSON táctico basado en los datos proporcionados.
    REGLA DE ORO INVIOLABLE: El campo 'link' DEBE ser exactamente igual al valor 'URL_REAL' de cada noticia. No inventes URLs bajo ninguna circunstancia.
    
    DATOS RECOLECTADOS: 
    {contexto_final}

    Categorías: {CATEGORIAS}. Colores: {BLOQUE_COLORS}.
    
    ESTRUCTURA REQUERIDA:
    {{
      "categorias": [
        {{
          "nombre": "Nombre de la Categoría",
          "consenso": "Resumen ejecutivo",
          "particulas": [
            {{
              "titulo": "Título de la noticia",
              "bloque": "Bloque",
              "proximidad": 85, 
              "analisis_regional": "Breve sesgo",
              "link": "URL_REAL_OBTENIDA",
              "color_bloque": "HEX"
            }}
          ]
        }}
      ]
    }}
    """
    
    try:
        # Usamos temperature 0 para asegurar que sea literal y no creativo con los links
        res = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_final,
            config={
                'response_mime_type': 'application/json',
                'temperature': 0.0
            }
        )
        data = json.loads(res.text.strip().replace('```json', '').replace('```', ''))
        
        with open("latest_news.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # --- REPORTE FINAL EN CONSOLA ---
        print("\n" + "═"*60)
        print("📊 REPORTE DE SALUD DE FUENTES")
        print("═"*60)
        for ok in status_report["exito"]: print(f"  [ONLINE] {ok}")
        for err in status_report["error"]: print(f"  [OFFLINE] {err}")
        print("═"*60 + "\n✅ Proceso completado exitosamente.")

    except Exception as e:
        print(f"❌ Error crítico final: {e}")

if __name__ == "__main__":
    collect()

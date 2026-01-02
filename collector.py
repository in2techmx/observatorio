import os, json, datetime, urllib.request, ssl, re, time
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from google import genai

# --- CONFIGURACIÓN DE CONEXIÓN ---
ssl_context = ssl._create_unverified_context()
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

CATEGORIAS = ["Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", "Soberanía y Alianzas", "Tecnología y Espacio"]

FUENTES_ESTRATEGICAS = {
    "USA": ["https://www.washingtontimes.com/rss/headlines/news/world/", "https://www.washingtontimes.com/rss/headlines/news/politics/"],
    "Rusia": ["https://tass.com/rss/v2.xml"],
    "China": ["https://www.scmp.com/rss/91/feed", "http://www.ecns.cn/rss/rss.xml"],
    "Europa": ["https://www.france24.com/en/rss", "https://es.euronews.com/rss?level=vertical&name=noticias"],
    "LATAM": ["https://www.jornada.com.mx/rss/edicion.xml", "https://www.clarin.com/rss/mundo/", "https://www.infobae.com/america/rss/"],
    "Medio Oriente": ["https://www.aljazeera.com/xml/rss/all.xml", "https://www.hispantv.com/rss/noticias"],
    "África": ["https://www.africanews.com/feed/"]
}

BLOQUE_COLORS = {
    "USA": "#3b82f6", "Europa": "#fde047", "Rusia": "#ef4444", 
    "China": "#f97316", "LATAM": "#d946ef", "Medio Oriente": "#10b981", "África": "#8b5cf6"
}

def get_pure_content(url):
    """EXTRAE CUERPO DE NOTICIA: Limpia basura y toma hasta 1500 caracteres"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12, context=ssl_context) as resp:
            soup = BeautifulSoup(resp.read(), 'html.parser')
            # Limpieza quirúrgica de Ads y Nav
            for noisy in soup(["script", "style", "nav", "footer", "header", "aside", "form", "button"]):
                noisy.decompose()
            
            # Captura de párrafos reales
            paragraphs = soup.find_all('p')
            text_parts = [p.get_text().strip() for p in paragraphs if len(p.get_text()) > 100]
            full_text = " ".join(text_parts[:6]) # Tomamos los primeros 6 párrafos densos
            
            # Limpieza de espacios y enlaces
            full_text = re.sub(r'http\S+', '', full_text)
            return re.sub(r'\s+', ' ', full_text).strip()[:1500]
    except:
        return ""

def triaje_inteligente(client, bloque, pool):
    """IA EDITORIAL: Analiza hasta 20 titulares y elige los 3 estratégicos"""
    listado = "\n".join([f"[{i}] {n['title']}" for i, n in enumerate(pool)])
    prompt = f"""
    Eres un Analista Senior de Inteligencia Geopolítica.
    De los siguientes 20 titulares del bloque '{bloque}', selecciona EXACTAMENTE los índices de los 3 que representan mayor impacto estratégico, cambios en el equilibrio de poder o relevancia económica global.
    IGNORA: sucesos locales, deportes, farándula o noticias de interés humano.

    LISTA:
    {listado}

    Responde ESTRICTAMENTE un JSON con este formato: {{"indices": [index1, index2, index3]}}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        # Limpieza básica por si la IA añade texto extra
        clean_json = response.text.strip().replace('```json', '').replace('```', '')
        return json.loads(clean_json).get("indices", [])
    except:
        return [0, 1] # Fallback si falla la criba

def collect():
    print("📡 Fase 1: Escaneo de Radar Geopolítico (20 ítems/fuente)...")
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
                    
                    for item in items[:20]: # Radar de 20 encabezados
                        t_node = item.find('title') or item.find('{http://www.w3.org/2005/Atom}title')
                        t = t_node.text if t_node is not None else ""
                        
                        l_node = item.find('link') or item.find('{http://www.w3.org/2005/Atom}link')
                        l = l_node.attrib.get('href') if l_node is not None and l_node.attrib else (l_node.text if l_node is not None else "")
                        
                        if t and l: pool_bloque.append({"title": t, "link": l})
            except: continue

        if pool_bloque:
            print(f"🧠 IA realizando triaje para {bloque}...")
            seleccionados = triaje_inteligente(client, bloque, pool_bloque)
            
            for idx in seleccionados:
                if idx < len(pool_bloque):
                    noticia = pool_bloque[idx]
                    print(f"   ∟ Extrayendo análisis profundo: {noticia['title'][:50]}...")
                    cuerpo = get_pure_content(noticia['link'])
                    if cuerpo:
                        contexto_final += f"BLOQUE: {bloque} | TÍTULO: {noticia['title']} | CUERPO: {cuerpo}\n\n"
            time.sleep(1) # Pausa estratégica entre bloques

    # --- ANÁLISIS SEMÁNTICO FINAL ---
    print("🔮 Generando Clustering Semántico Final...")
    prompt_final = f"""
    Como motor de inteligencia multipolar, analiza este universo de datos:
    {contexto_final}
    
    Categorías: {CATEGORIAS}.
    TAREAS:
    1. Define el 'Consenso Global' por cada categoría comparando todas las visiones regionales.
    2. Calcula la 'Proximidad' (0-100) según qué tanto se aleja el CUERPO de la noticia de ese consenso.
    3. Explica el sesgo específico del bloque en 'analisis_regional'.
    4. Usa estos colores: {BLOQUE_COLORS}.
    
    Responde solo JSON estricto.
    """
    
    try:
        res = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt_final,
            config={'response_mime_type': 'application/json'}
        )
        clean_res = res.text.strip().replace('```json', '').replace('```', '')
        data = json.loads(clean_res)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print("✅ Observatorio actualizado con inteligencia depurada.")
    except Exception as e:
        print(f"❌ Error crítico en fase final: {e}")

if __name__ == "__main__":
    collect()

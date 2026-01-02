import os
import json
import datetime
import urllib.request
from bs4 import BeautifulSoup # Necesitarás instalar: pip install beautifulsoup4
import xml.etree.ElementTree as ET
from google import genai

def get_deep_news():
    """Descarga titulares y el contenido completo de las noticias"""
    urls = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ]
    data_completa = []
    
    for url in urls:
        try:
            with urllib.request.urlopen(url) as response:
                tree = ET.parse(response)
                root = tree.getroot()
                # Analizamos las 5 noticias más importantes de cada fuente para no saturar
                for item in root.findall('.//item')[:5]:
                    titulo = item.find('title').text
                    link = item.find('link').text
                    
                    # --- DEEP SCRAPING ---
                    try:
                        with urllib.request.urlopen(link) as page:
                            soup = BeautifulSoup(page, 'html.parser')
                            # Buscamos los párrafos de texto (esto varía según el sitio, pero 'p' es estándar)
                            parrafos = soup.find_all('p')
                            contenido = " ".join([p.get_text() for p in parrafos[:8]]) # Leemos los primeros 8 párrafos
                            data_completa.append(f"TITULO: {titulo}\nCONTENIDO: {contenido}\n---")
                    except:
                        data_completa.append(f"TITULO: {titulo} (Sin contenido extra)")
        except Exception as e:
            print(f"Error en fuente {url}: {e}")
            
    return "\n".join(data_completa)

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    client = genai.Client()
    
    print("--- ESCANEANDO PROFUNDIDAD DE NOTICIAS ---")
    contexto_profundo = get_deep_news()

    prompt = f"""
    Eres el motor 'Global Proximity'. Analiza este contexto profundo:
    {contexto_profundo}

    TAREA:
    1. Identifica los 6 ejes de mayor fricción o cercanía geopolítica.
    2. Calcula el 'Grado de Proximidad' (0% conflicto total, 100% alianza total).
    3. Explica por qué ese porcentaje basándote en los detalles del texto analizado.
    
    Responde en JSON:
    [
      {{
        "tematica": "...",
        "descripcion": "...",
        "regiones_activas": [],
        "proximidad": "X%",
        "perspectivas": {{"Actor": "Postura analizada"}}
      }}
    ]
    """

    # ... (El resto del código de guardado se mantiene igual)
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={'response_mime_type': 'application/json'}
        )
        analisis = json.loads(response.text.strip())
        
        with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
            json.dump(analisis, f, indent=4, ensure_ascii=False)
        print("✅ Análisis profundo completado.")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    collect()

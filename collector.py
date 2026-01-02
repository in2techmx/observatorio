import os
import json
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from google import genai

def get_rss_news():
    """Obtiene titulares reales de fuentes globales"""
    # Puedes añadir más fuentes aquí (BBC, Reuters, Al Jazeera, etc.)
    urls = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://www.aljazeera.com/xml/rss/all.xml"
    ]
    titulares = []
    for url in urls:
        try:
            with urllib.request.urlopen(url) as response:
                tree = ET.parse(response)
                root = tree.getroot()
                for item in root.findall('.//item')[:10]: # 10 noticias por fuente
                    titulares.append(item.find('title').text)
        except Exception as e:
            print(f"Error leyendo RSS: {e}")
    return "\n".join(titulares)

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    client = genai.Client()
    noticias_reales = get_rss_news()

    prompt = f"""
    Eres el motor de análisis 'Global Proximity'. 
    Basándote en estas noticias reales de hoy:
    {noticias_reales}

    TAREA:
    1. Agrupa las noticias en 6 ejes geopolíticos clave.
    2. Para cada eje, calcula el 'Grado de Proximidad' (0-100%) entre los bloques implicados (Occidente, Global South, Eurasia, etc.).
    3. Responde ÚNICAMENTE con un array JSON.

    Formato esperado:
    [
      {{
        "tematica": "Título breve",
        "descripcion": "Análisis de fondo",
        "regiones_activas": ["Región A", "Región B"],
        "proximidad": "85%",
        "perspectivas": {{
          "Actor 1": "Postura A",
          "Actor 2": "Postura B"
        }}
      }}
    ]
    """

    analisis = []
    modelos = ["gemini-2.0-flash", "gemini-1.5-flash"] # Usamos los estables

    print("--- INICIANDO ANÁLISIS DE PROXIMIDAD ---")
    
    for modelo in modelos:
        try:
            response = client.models.generate_content(
                model=modelo,
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            raw_text = response.text.strip()
            inicio = raw_text.find("[")
            fin = raw_text.rfind("]") + 1
            analisis = json.loads(raw_text[inicio:fin])
            print(f"✅ ÉXITO: {len(analisis)} ejes de proximidad detectados.")
            break 
        except Exception as e:
            print(f"❌ Error en {modelo}: {e}")

    # --- GUARDADO ---
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    with open(os.path.join(historico_dir, f"analisis_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    print(f"--- PROCESO COMPLETADO ---")

if __name__ == "__main__":
    collect()

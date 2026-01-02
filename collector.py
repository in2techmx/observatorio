import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key: return

    client = genai.Client(api_key=api_key)
    
    analisis = []
    modelo_a_usar = None

    try:
        # PASO 1: Buscar qué modelo tienes realmente disponible
        print("Buscando modelos disponibles en tu cuenta Pro...")
        for m in client.models.list():
            # Buscamos gemini-1.5-pro o gemini-1.5-flash
            if "generateContent" in m.supported_methods:
                modelo_a_usar = m.name
                if "1.5-pro" in m.name: # Preferimos el Pro si aparece
                    break
        
        if not modelo_a_usar:
            raise Exception("No se encontraron modelos de generación de texto en esta cuenta.")

        print(f"✅ Usando modelo detectado: {modelo_a_usar}")

        # PASO 2: Generar contenido con el modelo encontrado
        prompt = "Genera un análisis geopolítico actual en un array JSON de 5 objetos: {'tematica': '...', 'descripcion': '...', 'regiones_activas': [], 'perspectivas': {}}"
        
        response = client.models.generate_content(
            model=modelo_a_usar,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpiador de Markdown
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        analisis = json.loads(raw_text)
        print(f"✅ ¡ÉXITO! Datos generados con {modelo_a_usar}")

    except Exception as e:
        print(f"❌ Error crítico: {e}")
        analisis = [{
            "tematica": "Error de Configuración de API",
            "descripcion": f"La cuenta Pro no reporta modelos disponibles. Detalle: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["SISTEMA"],
            "perspectivas": {"ERROR": "Verificar habilitación de modelo en Google Cloud"}
        }]

    # Guardado para la web
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
    
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump([f"analisis_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')}.json"], f, indent=4)

    print("🚀 Proceso terminado.")

if __name__ == "__main__":
    collect()

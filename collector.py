import os
import json
import datetime
from google import genai

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: No se encontró GEMINI_API_KEY en los Secrets.")
        return

    # 1. Configuración del Cliente
    client = genai.Client(api_key=api_key)
    modelo_a_usar = None

    try:
        # 2. Detección Dinámica del Modelo Pro
        print("Interrogando a la cuenta Pro para listar modelos disponibles...")
        modelos = list(client.models.list())
        
        # Buscamos el mejor modelo disponible que soporte generación de contenido
        for m in modelos:
            if 'generateContent' in m.supported_methods:
                # Preferencia 1: Gemini 1.5 Pro
                if "1.5-pro" in m.name:
                    modelo_a_usar = m.name
                    break
                # Preferencia 2: Gemini 1.5 Flash (si el Pro no aparece)
                elif "1.5-flash" in m.name:
                    modelo_a_usar = m.name

        if not modelo_a_usar:
            print("⚠️ No se detectó modelo Pro en el listado, intentando fallback manual...")
            modelo_a_usar = "gemini-1.5-pro"

        print(f"✅ Objetivo fijado: {modelo_a_usar}")

        # 3. Generación de Contenido
        prompt = """Genera un análisis geopolítico mundial actual para hoy 2026. 
        Responde ÚNICAMENTE con un array JSON (lista de objetos).
        Cada objeto debe tener:
        - "tematica": Título profesional corto.
        - "descripcion": Análisis profundo de 2 frases.
        - "regiones_activas": Lista de regiones (USA, CHINA, RUSSIA, EUROPE, INDIA, MID_EAST, LATAM, AFRICA, UK).
        - "perspectivas": Un objeto con visiones breves.
        Solo devuelve el código JSON puro, sin bloques de texto ni markdown."""

        print(f"Enviando consulta a {modelo_a_usar}...")
        response = client.models.generate_content(
            model=modelo_a_usar,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpieza de posibles etiquetas markdown ```json
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        # Validación de JSON
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        if inicio != -1:
            analisis = json.loads(raw_text[inicio:fin])
            print(f"✅ ¡ÉXITO! Se generaron {len(analisis)} noticias con tecnología Pro.")
        else:
            raise ValueError("La respuesta de la IA no contiene un JSON válido.")

    except Exception as e:
        print(f"❌ FALLO CRÍTICO: {e}")
        # Generar datos de error para no romper la web
        analisis = [{
            "tematica": "Nodo en Sincronización Pro",
            "descripcion": f"El observatorio está ajustando la conexión con el satélite. Detalle: {str(e)[:50]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Reintentando protocolo de enlace..."}
        }]

    # 4. Guardado Sincronizado para Netlify
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    
    # Guardar para la vista principal
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # Guardar en el histórico
    with open(os.path.join(historico_dir, f"analisis_{timestamp}.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    # Actualizar el timeline
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(files[:50], f, indent=4)

    print(f"🚀 Sincronización completa a las {timestamp}. Web lista.")

if __name__ == "__main__":
    collect()

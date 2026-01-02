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
        print("❌ Error: No se encontró GEMINI_API_KEY.")
        return

    client = genai.Client(api_key=api_key)
    modelo_a_usar = "gemini-1.5-pro" # Valor por defecto

    try:
        print("Interrogando a la cuenta Pro...")
        # Intentamos listar para ver si el Pro está disponible
        modelos = client.models.list()
        
        for m in modelos:
            # Acceso seguro a los nombres de los modelos
            nombre_modelo = getattr(m, 'name', str(m))
            if "1.5-pro" in nombre_modelo:
                modelo_a_usar = nombre_modelo
                break
        
        print(f"✅ Objetivo fijado: {modelo_a_usar}")

        prompt = """Genera un análisis geopolítico mundial actual de hoy 2026. 
        Responde ÚNICAMENTE con un array JSON (lista de objetos).
        Cada objeto debe tener:
        - "tematica": Título profesional corto.
        - "descripcion": Análisis profundo de 2 frases.
        - "regiones_activas": Lista de regiones.
        - "perspectivas": Un objeto con visiones breves."""

        print(f"Enviando consulta a {modelo_a_usar}...")
        response = client.models.generate_content(
            model=modelo_a_usar,
            contents=prompt
        )
        
        raw_text = response.text.strip()
        
        # Limpiador de Markdown robusto
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        analisis = json.loads(raw_text[inicio:fin])
        print(f"✅ ¡ÉXITO! Datos generados.")

    except Exception as e:
        print(f"❌ FALLO: {e}")
        analisis = [{
            "tematica": "Sincronización Pro",
            "descripcion": f"Conexión establecida. Validando flujo de datos. Error: {str(e)[:40]}",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["GLOBAL"],
            "perspectivas": {"SISTEMA": "Reintentando..."}
        }]

    # Guardado
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    with open(os.path.join(base_dir, "latest_news.json"), "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)

    with open(os.path.join(base_dir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump([f"analisis_{timestamp}.json"], f, indent=4)

    print(f"🚀 Proceso terminado a las {timestamp}")

if __name__ == "__main__":
    collect()

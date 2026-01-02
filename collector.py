import os
from google import genai

def collect():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ ERROR: No hay API Key en Secrets.")
        return

    client = genai.Client(api_key=api_key)
    
    print("--- INICIO DE DIAGNÓSTICO PRO ---")
    try:
        # Le pedimos a Google la lista de modelos permitidos para TU llave
        print("Listando modelos disponibles para tu API Key...")
        for m in client.models.list():
            print(f"✅ Modelo encontrado: {m.name} | Soporta: {m.supported_methods}")
            
    except Exception as e:
        print(f"❌ Error al listar modelos: {e}")
        print("\nPosibles causas:")
        print("1. La API Key no tiene permisos de 'Generative AI Viewer'.")
        print("2. Estás usando Vertex AI de Google Cloud y falta configurar el Proyecto.")

    print("--- FIN DE DIAGNÓSTICO ---")

if __name__ == "__main__":
    collect()

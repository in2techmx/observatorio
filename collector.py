import os
import json
import datetime

def collect():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    historico_dir = os.path.join(base_dir, "historico_noticias")
    
    if not os.path.exists(historico_dir):
        os.makedirs(historico_dir)

    # --- SIMULACIÓN DE SEGURIDAD (Asegúrate de que 'analisis' tenga datos) ---
    # Aquí es donde Gemini genera la lista. 
    # Si por algún motivo Gemini falla, NO dejaremos el archivo vacío.
    analisis = [] # <--- Aquí debe caer el resultado de tu IA
    
    # REFUERZO: Si la IA falló o devolvió algo vacío, usamos un aviso visual
    if not analisis or len(analisis) == 0:
        analisis = [{
            "tematica": "Sincronización de Inteligencia",
            "descripcion": "El observatorio está procesando la señal. Los archivos base han sido creados con éxito.",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "regiones_activas": ["USA", "EUROPE"],
            "perspectivas": {"USA": "Señal detectada.", "EUROPE": "Analizando divergencia..."}
        }]

    # 1. GUARDAR LATEST_NEWS.JSON (Lo hacemos primero para asegurar la web)
    latest_path = os.path.join(base_dir, "latest_news.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno()) # Fuerza el guardado físico

    # 2. GUARDAR HISTÓRICO
    timestamp_str = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
    filename = f"analisis_{timestamp_str}.json"
    historico_path = os.path.join(historico_dir, filename)
    with open(historico_path, "w", encoding="utf-8") as f:
        json.dump(analisis, f, indent=4, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 3. ACTUALIZAR TIMELINE.JSON
    files = sorted([f for f in os.listdir(historico_dir) if f.startswith('analisis_')], reverse=True)
    timeline_path = os.path.join(base_dir, "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(files, f, indent=4)
        f.flush()
        os.fsync(f.fileno())

    print(f"Éxito: Se escribieron {len(analisis)} bloques en {latest_path}")

if __name__ == "__main__":
    collect()

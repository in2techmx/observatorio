# Prompt ultra-estricto para Gemini 2.5
    prompt = """Eres un analista geopolítico de élite en 2026. 
    Tu tarea es generar un informe en formato JSON puro.
    NO escribas introducciones ni conclusiones. SOLO el JSON.
    
    Estructura exacta (Array de objetos):
    [
      {
        "tematica": "Título corto",
        "descripcion": "Análisis de 2 frases máximo",
        "regiones_activas": ["Región 1", "Región 2"],
        "perspectivas": {"Actor": "Breve visión"}
      }
    ]
    Genera 5 noticias actuales de hoy."""

    # ... dentro del bucle de modelos ...
    try:
        response = client.models.generate_content(
            model=modelo,
            contents=prompt,
            # Añadimos configuración de respuesta para forzar JSON
            config={'response_mime_type': 'application/json'}
        )
        
        raw_text = response.text.strip()
        
        # Limpiador ultra-reforzado
        if "```json" in raw_text:
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            raw_text = raw_text.split("```")[1].split("```")[0].strip()

        # Aseguramos que empiece por [ y termine por ]
        inicio = raw_text.find("[")
        fin = raw_text.rfind("]") + 1
        
        if inicio != -1:
            analisis = json.loads(raw_text[inicio:fin])
            # ... resto del código ...

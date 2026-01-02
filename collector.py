# Configuración del cliente
    client = genai.Client(api_key=api_key)
    
    # Lista de posibles nombres para cuentas Pro (en orden de probabilidad)
    model_options = [
        "gemini-1.5-pro-002",  # Versión específica de producción
        "gemini-1.5-pro",      # Versión estándar
        "gemini-1.5-flash"     # Respaldo de alta velocidad
    ]

    analisis = []
    exito = False

    for model_id in model_options:
        if exito: break
        try:
            print(f"Intentando conexión con: {model_id}...")
            response = client.models.generate_content(
                model=model_id,
                contents=prompt
            )
            raw_text = response.text.strip()
            
            # Limpieza de JSON
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            
            inicio = raw_text.find("[")
            fin = raw_text.rfind("]") + 1
            
            if inicio != -1:
                analisis = json.loads(raw_text[inicio:fin])
                print(f"✅ ¡CONECTADO! Usando {model_id}")
                exito = True
        except Exception as e:
            print(f"❌ {model_id} rechazado: {str(e)[:50]}")
            continue

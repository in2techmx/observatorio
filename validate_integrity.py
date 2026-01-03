import json, sys, os

try:
    if not os.path.exists('gravity_carousel.json'):
        sys.exit(1)
        
    with open('gravity_carousel.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'carousel' not in data or not isinstance(data['carousel'], list):
        print('❌ Error: Falta array carousel')
        sys.exit(1)
    
    total = sum(len(a.get('particulas', [])) for a in data['carousel'])
    
    print(f'✅ JSON Válido. Áreas: {len(data["carousel"])}, Partículas: {total}')
    
    # --- AQUÍ ESTÁ EL FRENO DE EMERGENCIA ---
    if total == 0:
        print('⛔ ALERTA ROJA: El JSON está vacío (0 partículas). Cancelando despliegue para proteger la web.')
        sys.exit(1) # Esto fuerza el error y detiene el proceso
    # ----------------------------------------

except Exception as e:
    print(f'❌ JSON Corrupto: {e}')
    sys.exit(1)

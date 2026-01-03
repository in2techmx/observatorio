import json, sys, os
try:
    if not os.path.exists('gravity_carousel.json'): sys.exit(1)
    with open('gravity_carousel.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    if 'carousel' not in data or not isinstance(data['carousel'], list):
        print('❌ Error: Estructura inválida'); sys.exit(1)
    total = sum(len(a.get('particulas', [])) for a in data['carousel'])
    print(f'✅ JSON Válido. Áreas: {len(data["carousel"])}, Partículas: {total}')
except Exception as e:
    print(f'❌ Error: {e}'); sys.exit(1)

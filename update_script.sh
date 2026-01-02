#!/bin/bash
set -e  # Salir inmediatamente si ocurre un error

echo "🚀 Iniciando actualización del observatorio..."

# Configuración Git
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 1. Sincronizar con el repositorio remoto de forma agresiva
echo "📡 Sincronizando con GitHub..."
git fetch origin main
git reset --hard origin main

# 2. Asegurar que existen los directorios
echo "📁 Creando estructura de directorios..."
mkdir -p historico_noticias/diario
mkdir -p historico_noticias/semanal
mkdir -p historico_noticias/mensual

# 3. Crear archivos esenciales si no existen (Garantiza que git add no falle)
echo "📄 Verificando archivos esenciales..."
if [ ! -f manifest.json ]; then
    echo '{"diario": [], "semanal": [], "mensual": []}' > manifest.json
    echo "✅ manifest.json creado"
fi

if [ ! -f gravity_carousel.json ]; then
    echo '{"carousel": []}' > gravity_carousel.json
    echo "✅ gravity_carousel.json creado"
fi

# 4. Ejecutar el collector Python
echo "🐍 Ejecutando análisis de noticias..."
# Instalamos dependencias por si acaso no están en el entorno
pip install google-genai beautifulsoup4 --quiet
python collector.py || echo "⚠️ El collector tuvo un problema, pero intentaremos archivar..."

# 5. Archivar resultados
# Nota: Asumimos que tu collector genera 'gravity_carousel.json'
if [ -f "gravity_carousel.json" ]; then
    TODAY=$(date +"%Y-%m-%d")
    echo "📦 Archivando datos del día ($TODAY)..."
    cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
    
    # Archivo semanal (Domingo = 7 o 0)
    if [ $(date +%u) -eq 7 ]; then
        WEEK=$(date +"%Y-W%U")
        cp gravity_carousel.json "historico_noticias/semanal/news_${WEEK}.json"
    fi
    
    # Archivo mensual (Día 1)
    if [ $(date +%d) -eq 01 ]; then
        MONTH=$(date +"%Y-%m")
        cp gravity_carousel.json "historico_noticias/mensual/news_${MONTH}.json"
    fi
fi

# 6. Preparar commit
echo "📎 Agregando cambios al área de preparación..."
git add gravity_carousel.json
git add manifest.json
git add historico_noticias/  # Agrega todas las subcarpetas de una vez

# 7. Hacer commit solo si hay cambios reales
if git diff --staged --quiet; then
    echo "📭 No hay cambios significativos para subir."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌐 Actualización estratégica: $TIMESTAMP [Bot]"
    echo "🚀 Enviando a GitHub..."
    git push origin main --force
    echo "✅ Actualización completada exitosamente!"
fi

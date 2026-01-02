#!/bin/bash
set -e  # Detener el script si ocurre cualquier error

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE SINCRONIZACIÓN"
echo "===================================================="

# 1. CONFIGURACIÓN DE IDENTIDAD
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZACIÓN RADICAL (Soluciona el error de los 18 commits)
echo "[1/4] Reseteando repositorio a la versión de la nube..."
git fetch origin main
# El reset --hard elimina cualquier discrepancia con el servidor
git reset --hard origin main
git checkout main

# 3. INFRAESTRUCTURA Y PREVENCIÓN DE ERRORES
echo "[2/4] Asegurando archivos esenciales..."
mkdir -p historico_noticias/{diario,semanal,mensual}

# Creamos archivos base si no existen para que 'git add' nunca falle
if [ ! -f manifest.json ]; then
    echo '{"diario": [], "semanal": [], "mensual": []}' > manifest.json
fi
if [ ! -f gravity_carousel.json ]; then
    echo '{"carousel": []}' > gravity_carousel.json
fi

# 4. EJECUCIÓN DEL MOTOR (Python)
echo "[3/4] Ejecutando collector.py..."
pip install google-genai beautifulsoup4 --quiet
python collector.py || echo "⚠️ Advertencia: El collector falló, se usarán datos previos."

# 5. ARCHIVADO Y CARGA
echo "[4/4] Preparando commit y subida..."

# Si el collector generó el archivo, lo guardamos en el histórico
if [ -f "gravity_carousel.json" ]; then
    TODAY=$(date +"%Y-%m-%d")
    cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
fi

# Agregamos los archivos de forma segura
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Solo subir si hay cambios reales
if git diff --staged --quiet; then
    echo "📭 Sin cambios nuevos."
else
    git commit -m "🌍 Actualización Geopolítica: $(date +'%Y-%m-%d %H:%M')"
    git push origin main --force
    echo "✅ PROCESO COMPLETADO CON ÉXITO"
fi

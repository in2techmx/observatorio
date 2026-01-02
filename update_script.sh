#!/bin/bash
set -e  # Detener el script si ocurre cualquier error

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE SINCRONIZACIÓN TOTAL"
echo "===================================================="

# 1. CONFIGURACIÓN DE IDENTIDAD
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZACIÓN RADICAL (Soluciona el error de los commits desfasados)
echo "[1/4] Reseteando repositorio a la versión de la nube..."
# Traemos los datos frescos del servidor
git fetch origin main
# Forzamos al repositorio local a ser EXACTAMENTE igual al de la nube
git reset --hard origin/main
git checkout main

# 3. INFRAESTRUCTURA Y PREVENCIÓN DE ERRORES 'PATHSPEC'
echo "[2/4] Asegurando archivos esenciales..."
# Creamos las carpetas si no existen
mkdir -p historico_noticias/diario
mkdir -p historico_noticias/semanal
mkdir -p historico_noticias/mensual

# Creamos archivos base si no existen para que 'git add' nunca falle aunque falle Python
if [ ! -f manifest.json ]; then
    echo '{"diario": [], "semanal": [], "mensual": []}' > manifest.json
fi
if [ ! -f gravity_carousel.json ]; then
    echo '{"carousel": []}' > gravity_carousel.json
fi

# 4. EJECUCIÓN DEL MOTOR (Python)
echo "[3/4] Ejecutando collector.py..."
# Aseguramos que las librerías estén presentes
pip install google-genai beautifulsoup4 --quiet
# Ejecutamos el script de inteligencia. Si falla, el script sigue adelante.
python collector.py || echo "⚠️ Advertencia: El collector falló, se intentará subir lo que haya."

# 5. ARCHIVADO Y CARGA FINAL
echo "[4/4] Preparando commit y subida..."

# Si el collector generó el archivo hoy, lo guardamos en la carpeta histórica
if [ -f "gravity_carousel.json" ]; then
    TODAY=$(date +"%Y-%m-%d")
    cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
fi

# Agregamos los archivos de forma segura. Ya no darán error porque los aseguramos arriba.
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Solo subir si hay cambios reales detectados por Git
if git diff --staged --quiet; then
    echo "📭 No se detectaron cambios nuevos en los datos."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌍 Actualización Geopolítica: $TIMESTAMP [Bot]"
    # Push forzado para garantizar que la web se actualice sobre cualquier conflicto
    git push origin main --force
    echo "===================================================="
    echo "✅ PROCESO COMPLETADO CON ÉXITO"
    echo "===================================================="
fi

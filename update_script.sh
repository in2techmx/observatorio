#!/bin/bash
set -e  # Detener el script si ocurre cualquier error

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE SINCRONIZACIÓN TOTAL"
echo "===================================================="

# 1. CONFIGURACIÓN DE IDENTIDAD
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZACIÓN RADICAL
echo "[1/4] Reseteando repositorio a la versión de la nube..."
# Traemos los metadatos actualizados del servidor
git fetch origin main

# CORRECCIÓN AQUÍ: Usamos 'origin/main' (con barra) para evitar el error de argumento ambiguo
git reset --hard origin/main
git checkout main

# 3. INFRAESTRUCTURA Y PREVENCIÓN DE ERRORES 'PATHSPEC'
echo "[2/4] Asegurando archivos esenciales..."
mkdir -p historico_noticias/diario
mkdir -p historico_noticias/semanal
mkdir -p historico_noticias/mensual

# Garantizamos que los archivos existan para que 'git add' no falle jamás
if [ ! -f manifest.json ]; then
    echo '{"diario": [], "semanal": [], "mensual": []}' > manifest.json
fi
if [ ! -f gravity_carousel.json ]; then
    echo '{"carousel": []}' > gravity_carousel.json
fi

# 4. EJECUCIÓN DEL MOTOR (Python)
echo "[3/4] Ejecutando collector.py..."
# Aseguramos librerías (GitHub Actions limpia el entorno en cada corrida)
pip install google-genai beautifulsoup4 --quiet

# Ejecutamos el collector. El '|| true' evita que el script de Bash muera si Python falla.
python collector.py || echo "⚠️ Advertencia: El collector falló, se intentará subir lo que haya."

# 5. ARCHIVADO Y CARGA FINAL
echo "[4/4] Preparando commit y subida..."

# Si el collector tuvo éxito y generó el archivo, lo guardamos en histórico diario
if [ -f "gravity_carousel.json" ]; then
    TODAY=$(date +"%Y-%m-%d")
    cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
fi

# Agregamos los archivos al área de preparación (staging)
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Solo hacemos el push si hay cambios reales detectados
if git diff --staged --quiet; then
    echo "📭 No se detectaron cambios nuevos."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌍 Actualización Geopolítica: $TIMESTAMP [Bot]"
    
    # Push forzado para limpiar el desfase de commits acumulados
    git push origin main --force
    echo "===================================================="
    echo "✅ PROCESO COMPLETADO CON ÉXITO"
    echo "===================================================="
fi

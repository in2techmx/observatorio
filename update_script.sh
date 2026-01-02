#!/bin/bash
set -e  # Detener en primer error

echo "========================================"
echo "🤖 INTELLIGENCE-BOT - OBSERVATORIO UPDATE"
echo "========================================"

# 1. CONFIGURACIÓN GIT
echo "[1/5] Configurando Git..."
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZAR CON REMOTO
echo "[2/5] Sincronizando repositorio..."
git fetch origin main

# Forzar branch main y limpiar cualquier desfase
git checkout -B main origin/main

# 3. VERIFICAR/CREAR ARCHIVOS ESENCIALES
echo "[3/5] Verificando archivos esenciales..."

# manifest.json
if [ ! -f manifest.json ]; then
    echo "  ↪ Creando manifest.json..."
    cat > manifest.json << EOF
{
  "project": "Observatorio Geopolítico Multipolar",
  "version": "2.0.0",
  "updated_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "data_sources": ["RSS International"],
  "update_frequency": "6h"
}
EOF
fi

# gravity_carousel.json
if [ ! -f gravity_carousel.json ]; then
    echo "  ↪ Creando gravity_carousel.json..."
    echo '{"carousel": [], "last_updated": null}' > gravity_carousel.json
fi

# Crear directorios históricos
mkdir -p historico_noticias/{diario,semanal,mensual}

# 4. EJECUTAR COLECTOR
echo "[4/5] Ejecutando análisis..."
if [ -f "collector.py" ]; then
    # Instalación rápida de dependencias para el entorno de GitHub
    pip install google-genai beautifulsoup4 --quiet
    python collector.py || echo "  ⚠️ Collector terminó con errores"
else
    echo "  ⚠️ collector.py no encontrado"
fi

# 5. ARCHIVAR Y COMMIT
echo "[5/5] Preparando commit..."

# NOTA IMPORTANTE: Si tu collector genera 'gravity_carousel.json' directamente, 
# usamos ese para el histórico.
if [ -f "gravity_carousel.json" ]; then
    echo "  ↪ Archivando datos..."
    TODAY=$(date +"%Y-%m-%d_%H%M")
    cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
    
    # Lógica Semanal (Domingos)
    if [ $(date +%u) -eq 7 ]; then
        cp gravity_carousel.json "historico_noticias/semanal/news_$(date +%V).json"
    fi
fi

# Agregar archivos con verificación
echo "  ↪ Agregando archivos..."
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/  # Esto agrega todo el contenido de las carpetas

# Verificar si hay cambios reales
if git diff --staged --quiet; then
    echo "  📭 No hay cambios para commit"
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌍 Actualización Observatorio: $TIMESTAMP"
    git push origin main --force
    echo "✅ ACTUALIZACIÓN COMPLETADA"
fi

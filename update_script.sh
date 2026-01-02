#!/bin/bash
set -e  # Salir si ocurre un error

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE ACTUALIZACIÓN TOTAL"
echo "===================================================="

# 1. CONFIGURACIÓN DE IDENTIDAD
echo "[1/6] Configurando Git..."
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZACIÓN RADICAL (Soluciona el error de commits desfasados)
echo "[2/6] Reseteando repositorio a la versión de la nube..."
git fetch origin main
# Usamos origin/main con barra para evitar el error de "argumento ambiguo"
git reset --hard origin/main
git checkout main

# 3. INFRAESTRUCTURA Y PREVENCIÓN DE ERRORES 'PATHSPEC'
echo "[3/6] Verificando directorios y archivos base..."
mkdir -p historico_noticias/{diario,semanal,mensual}

# Crear manifest.json preventivo si no existe
if [ ! -f manifest.json ]; then
    echo "  ↪ Creando manifest.json preventivo..."
    echo '{
      "project": "Observatorio Geopolítico",
      "updated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }' > manifest.json
fi

# Crear gravity_carousel.json preventivo si no existe
if [ ! -f gravity_carousel.json ]; then
    echo "  ↪ Creando gravity_carousel.json preventivo..."
    echo '{"articles": [], "last_updated": null}' > gravity_carousel.json
fi

# 4. EJECUCIÓN DEL MOTOR (Python)
echo "[4/6] Ejecutando análisis Python..."
# Instalamos dependencias por si el entorno está limpio
pip install google-genai beautifulsoup4 --quiet

if [ -f "collector.py" ]; then
    # Ejecutar collector. Usamos '|| true' para que el script no muera si falla la IA
    python collector.py || echo "  ⚠️ Advertencia: El collector falló, se usará la base existente."
else
    echo "  ❌ Error: No se encontró collector.py"
    exit 1
fi

# 5. LÓGICA DE ARCHIVADO HISTÓRICO
echo "[5/6] Organizando archivos históricos..."
# Verificamos si Python generó el archivo actualizado
if [ -f "gravity_carousel.json" ]; then
    FECHA_HOY=$(date +"%Y-%m-%d")
    HORA_HOY=$(date +"%H%M")
    
    # Guardar copia en diario
    echo "  ↪ Archivando en histórico diario..."
    cp gravity_carousel.json "historico_noticias/diario/${FECHA_HOY}_${HORA_HOY}.json"
    
    # Si es domingo (7), guardar en semanal
    if [ $(date +%u) -eq 7 ]; then
        cp gravity_carousel.json "historico_noticias/semanal/semana_$(date +%V).json"
    fi
    
    # Si es día 01, guardar en mensual
    if [ $(date +%d) -eq 01 ]; then
        cp gravity_carousel.json "historico_noticias/mensual/mes_$(date +%m).json"
    fi
fi

# 6. COMMIT Y SUBIDA FINAL
echo "[6/6] Preparando commit y push..."

# Agregamos los archivos de forma segura
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Solo subir si hay cambios detectados
if git diff --staged --quiet; then
    echo "📭 No se detectaron cambios nuevos para subir."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌍 Actualización Geopolítica: $TIMESTAMP [Bot]"
    
    echo "🚀 Enviando cambios a GitHub..."
    # Force push para limpiar el historial desfasado definitivamente
    git push origin main --force
    echo "===================================================="
    echo "✅ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE"
    echo "===================================================="
fi

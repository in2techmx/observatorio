#!/bin/bash
set -e

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE SINCRONIZACIÓN"
echo "===================================================="

# 1. CONFIGURAR GIT
echo "[1/6] Configurando Git..."
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# En GitHub Actions el remote ya viene configurado por el checkout
# Solo nos aseguramos de estar en la rama correcta
git fetch origin main

# 2. SINCRONIZACIÓN RADICAL (Limpia desfases de commits)
echo "[2/6] Sincronizando branch local..."
git reset --hard origin/main
git checkout main

# 3. INFRAESTRUCTURA (CRÍTICO)
echo "[3/6] Verificando estructura de archivos..."
mkdir -p historico_noticias/{diario,semanal,mensual}

# Asegurar que manifest.json existe para evitar error 128 de Git
if [ ! -f manifest.json ]; then
    echo "  ↪ Creando manifest.json preventivo..."
    echo '{
      "project": "Observatorio Geopolítico",
      "updated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }' > manifest.json
fi

# Asegurar que gravity_carousel.json existe
if [ ! -f gravity_carousel.json ]; then
    echo "  ↪ Creando gravity_carousel.json preventivo..."
    echo '{"articles": [], "last_updated": null}' > gravity_carousel.json
fi

# 4. EJECUTAR COLECTOR (Python)
echo "[4/6] Ejecutando análisis..."
# Aseguramos dependencias
pip install google-genai beautifulsoup4 --quiet

if [ -f "collector.py" ] && [ -n "$GEMINI_API_KEY" ]; then
    echo "  ↪ Ejecutando collector.py..."
    if python collector.py 2>&1 | tee collector.log; then
        echo "  ✅ Collector ejecutado exitosamente"
    else
        echo "  ⚠️ Collector terminó con errores, revisando últimas líneas:"
        tail -n 10 collector.log
    fi
    
    # 5. ARCHIVADO DE RESULTADOS
    # Tu Python genera gravity_carousel.json, lo usamos para el histórico
    if [ -f "gravity_carousel.json" ]; then
        echo "  ↪ Archivando datos..."
        TODAY=$(date +"%Y%m%d_%H%M")
        cp gravity_carousel.json "historico_noticias/diario/${TODAY}.json"
    fi
else
    echo "  ⚠️ Saltando collector: No hay API key o falta collector.py"
fi

# 6. COMMIT Y PUSH SEGURO
echo "[5/6] Preparando commit..."

# Agregamos todo el contenido
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Verificar si hay cambios reales antes de subir
if git diff --cached --quiet; then
    echo "  📭 No hay cambios detectados. Terminando."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    echo "  💾 Creando commit: $TIMESTAMP"
    git commit -m "🌐 Actualización automática: $TIMESTAMP" --quiet

    echo "[6/6] Enviando a GitHub..."
    # Intentar push normal, si falla (por cambios remotos), hacer rebase
    if git push origin main; then
        echo "  ✅ Push exitoso"
    else
        echo "  ⚠️ Push rechazado, sincronizando y reintentando..."
        git pull --rebase origin main
        git push origin main
    fi
fi

# Limpieza de archivos temporales
rm -f collector.log 2>/dev/null || true

echo "===================================================="
echo "✅ SINCRONIZACIÓN COMPLETADA EXITOSAMENTE"
echo "===================================================="

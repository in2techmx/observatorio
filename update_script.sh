#!/bin/bash
set -e  # Detener el script si ocurre cualquier error

echo "===================================================="
echo "🤖 INTELLIGENCE-BOT: PROCESO DE SINCRONIZACIÓN"
echo "===================================================="

# 1. CONFIGURACIÓN DE IDENTIDAD
echo "[1/6] Configurando identidad del bot..."
git config --global user.name "Intelligence-Bot"
git config --global user.email "bot@github.com"

# 2. SINCRONIZACIÓN RADICAL (Solución al desfase de commits)
echo "[2/6] Sincronizando con el repositorio remoto..."
git fetch origin main
# El reset --hard origin/main elimina el error de "18 commits atrasados"
git reset --hard origin/main
git checkout main

# 3. INFRAESTRUCTURA DE ARCHIVOS (Evita error fatal 128)
echo "[3/6] Asegurando estructura de directorios..."
mkdir -p historico_noticias/{diario,semanal,mensual}

# Crear archivos preventivos: si no existen, el comando 'git add' fallaría
if [ ! -f manifest.json ]; then
    echo "  ↪ Creando manifest.json preventivo..."
    echo '{
      "project": "Observatorio Geopolítico",
      "updated": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
    }' > manifest.json
fi

if [ ! -f gravity_carousel.json ]; then
    echo "  ↪ Creando gravity_carousel.json preventivo..."
    echo '{"articles": [], "last_updated": null}' > gravity_carousel.json
fi

# 4. EJECUCIÓN DEL MOTOR (Python)
echo "[4/6] Ejecutando análisis Python..."
# Instalamos librerías necesarias en el entorno de GitHub Actions
pip install google-genai beautifulsoup4 --quiet

if [ -f "collector.py" ]; then
    # Ejecutamos el collector. El '|| true' permite que el script siga aunque la IA falle
    python collector.py || echo "  ⚠️ Advertencia: El collector tuvo un problema, se usará la base existente."
else
    echo "  ❌ Error: No se encontró collector.py en la raíz."
    exit 1
fi

# 5. ARCHIVADO HISTÓRICO
echo "[5/6] Organizando archivos históricos..."
if [ -f "gravity_carousel.json" ]; then
    FECHA=$(date +"%Y-%m-%d")
    HORA=$(date +"%H%M")
    cp gravity_carousel.json "historico_noticias/diario/${FECHA}_${HORA}.json"
    echo "  ✓ Copia diaria creada: ${FECHA}_${HORA}.json"
fi

# 6. COMMIT Y SUBIDA FINAL
echo "[6/6] Preparando commit y push..."

# Agregamos los archivos de forma segura (ya existen gracias al paso 3)
git add manifest.json
git add gravity_carousel.json
git add historico_noticias/

# Solo hacer push si hay cambios reales detectados por Git
if git diff --staged --quiet; then
    echo "📭 No hay cambios nuevos para subir."
else
    TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
    git commit -m "🌍 Actualización Geopolítica: $TIMESTAMP [Bot]"
    
    echo "🚀 Enviando cambios a GitHub..."
    # Force push para garantizar que la rama main se limpie del desfase
    git push origin main --force
    echo "===================================================="
    echo "✅ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE"
    echo "===================================================="
fi

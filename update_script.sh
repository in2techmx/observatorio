# 2. SINCRONIZAR CON REMOTO (FORZADO)
echo "[2/5] Reseteando repositorio a la versión de la nube..."
# Esto elimina el error de "18 commits atrás" instantáneamente
git fetch origin main
git reset --hard origin main

# 3. VERIFICAR/CREAR ARCHIVOS ESENCIALES
echo "[3/5] Asegurando existencia de archivos..."
# Si el collector no los crea, los creamos vacíos para que git add no de error fatal
if [ ! -f manifest.json ]; then
    echo '{"diario": [], "semanal": [], "mensual": []}' > manifest.json
fi
if [ ! -f gravity_carousel.json ]; then
    echo '{"carousel": []}' > gravity_carousel.json
fi

# 4. EJECUTAR COLECTOR
echo "[4/5] Ejecutando análisis Python..."
python collector.py || echo "⚠️ El collector falló, pero el script continuará"

# 5. ARCHIVAR Y COMMIT
echo "[5/5] Preparando commit y subida..."

# Usamos git add con rutas de carpetas, no con archivos específicos si no estamos seguros
git add manifest.json
git add gravity_carousel.json
if [ -d "historico_noticias" ]; then
    git add historico_noticias/
fi

# Hacer commit solo si hay algo nuevo
if git diff --staged --quiet; then
    echo "📭 No hay cambios detectados."
else
    git commit -m "🌍 Actualización Observatorio: $(date +'%Y-%m-%d %H:%M')"
    # Push forzado para sobreescribir el historial desfasado
    git push origin main --force
fi

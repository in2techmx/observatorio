# 🌍 Global News Proximity | Observatorio Geopolítico

**Versión:** 2.4 (Historical Edition)  
**Estado:** Operativo (Autónomo)  
**Motor de IA:** Google Gemini 1.5 Flash  

## 🛰️ Visión General
Global News Proximity es un sistema de monitoreo autónomo que recolecta, analiza y sintetiza la divergencia narrativa de 18 fuentes de noticias globales. 
A diferencia de un lector de noticias tradicional, este observatorio mide la "proximidad" o "distancia" entre las narrativas de diferentes bloques geopolíticos.



---

## 🏗️ Arquitectura del Sistema

El proyecto opera en un ciclo de tres capas de inteligencia:

1.  **Capa de Flujo (Horaria):** El bot recolecta datos de 9 regiones y genera un análisis de proximidad inmediato.
2.  **Capa Temporal (Slider):** Permite al usuario "viajar al pasado" reciente para observar cómo evolucionó una narrativa específica.
3.  **Capa de Síntesis (Maestra):** Procesos semanales y mensuales que comprimen los datos en registros históricos de neutralidad regional.

---

## 🛠️ Stack Tecnológico
* **Frontend:** React 18 + Tailwind CSS + Framer Motion.
* **Backend (Automation):** Python 3.9 + GitHub Actions.
* **Inteligencia Artificial:** Gemini SDK (Análisis de sentimientos y temáticas).
* **Hosting:** Netlify (CI/CD continuo).

---

## 📁 Estructura del Repositorio
* `/historico_noticias`: Archivos JSON con el pulso horario (última semana).
* `/archivos_maestros`: Síntesis semanales y mensuales de alta densidad.
* `collector.py`: El cerebro encargado de la recolección y la limpieza.
* `index.html`: Interfaz cinematográfica de usuario.

---

## ⚙️ Configuración de Seguridad
Para mantener la autonomía del sistema en este repositorio privado, asegúrate de tener configurado:
* `GEMINI_API_KEY`: Ubicada en *Settings > Secrets > Actions*.
* **Permisos de Workflow:** "Read and write permissions" activados en la configuración de GitHub Actions.

---

> **Nota de Neutralidad:** Este sistema no unifica opiniones; su propósito es evidenciar la fragmentación de la verdad global mediante la separación estricta de perspectivas regionales.

import os, json, datetime, logging, statistics
from collections import defaultdict, Counter
from google import genai

class StrategicAggregatorPro:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        
    def load_week_data(self, days_back=7):
        """Carga y analiza datos de la última semana completa"""
        end_date = datetime.datetime.now() - datetime.timedelta(days=1)  # Excluir hoy
        dates = [(end_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d") 
                for i in range(days_back)]
        
        week_data = []
        metrics_by_area = defaultdict(lambda: {
            'proximities': [],
            'regions': Counter(),
            'keywords': Counter(),
            'titles': []
        })
        
        for date in dates:
            path = os.path.join("historico_noticias/diario", f"{date}.json")
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        week_data.append(data)
                        
                        # Extraer métricas por área
                        for area in data.get('carousel', []):
                            area_name = area['area']
                            metrics = metrics_by_area[area_name]
                            
                            # Promedio de proximidad del día
                            if area['particulas']:
                                day_avg = sum(p['proximidad'] for p in area['particulas']) / len(area['particulas'])
                                metrics['proximities'].append(day_avg)
                            
                            # Conteo de regiones y keywords
                            for particle in area['particulas'][:8]:  # Top 8 por día
                                metrics['regions'][particle['bloque']] += 1
                                for kw in particle.get('keywords', [])[:3]:
                                    metrics['keywords'][kw.lower()] += 1
                                metrics['titles'].append(particle['titulo'])
                except Exception as e:
                    logging.warning(f"Error procesando {date}: {e}")
        
        return week_data, metrics_by_area
    
    def calculate_week_metrics(self, metrics_by_area):
        """Calcula métricas agregadas por área"""
        area_summaries = {}
        
        for area_name, metrics in metrics_by_area.items():
            if not metrics['proximities']:
                continue
                
            # Tendencia de consenso
            if len(metrics['proximities']) >= 2:
                trend = statistics.mean(metrics['proximities'][-3:]) - statistics.mean(metrics['proximities'][:3])
                trend_dir = "↑" if trend > 5 else "↓" if trend < -5 else "→"
            else:
                trend_dir = "→"
            
            # Top regiones y keywords
            top_regions = [r[0] for r in metrics['regions'].most_common(3)]
            top_keywords = [k[0] for k in metrics['keywords'].most_common(5)]
            
            # Nivel de consenso semanal
            avg_prox = statistics.mean(metrics['proximities'])
            if avg_prox > 75:
                consensus_level = "ALTO CONSENSO"
                emoji = "🟢"
            elif avg_prox > 60:
                consensus_level = "CONSENSO MODERADO"
                emoji = "🟡"
            elif avg_prox > 45:
                consensus_level = "TENSIÓN DETECTADA"
                emoji = "🟠"
            else:
                consensus_level = "FRICCIÓN SEVERA"
                emoji = "🔴"
            
            area_summaries[area_name] = {
                'consensus_avg': round(avg_prox, 1),
                'consensus_level': consensus_level,
                'emoji': emoji,
                'trend': trend_dir,
                'top_regions': top_regions,
                'top_keywords': top_keywords,
                'signal_count': sum(metrics['regions'].values()),
                'sample_titles': metrics['titles'][:5]  # Para contexto de IA
            }
        
        return area_summaries
    
    def build_analysis_prompt(self, area_summaries):
        """Construye prompt estructurado para análisis semanal"""
        
        prompt_sections = []
        
        for area_name, summary in area_summaries.items():
            section = f"""
### {area_name}
**Nivel de Consenso:** {summary['emoji']} {summary['consensus_level']} ({summary['consensus_avg']}%)
**Tendencia Semanal:** {summary['trend']}
**Bloques Más Activos:** {', '.join(summary['top_regions'])}
**Temas Principales:** {', '.join(summary['top_keywords'])}
**Señales Analizadas:** {summary['signal_count']}

**Muestras Representativas:**
{chr(10).join(f"- {title}" for title in summary['sample_titles'])}
"""
            prompt_sections.append(section)
        
        full_prompt = f"""# ANÁLISIS SEMANAL GEOPOLÍTICO - SÍNTESIS ESTRATÉGICA

Eres el Director de Inteligencia del Proximity Hub. Analiza los datos agregados de la última semana y genera un reporte estratégico.

## CONTEXTO OPERACIONAL:
- Período: Últimos 7 días completos (excluyendo hoy)
- Metodología: Análisis de fricción narrativa inter-bloques
- Métrica Clave: Proximidad (0-100%) indica nivel de consenso entre bloques geopolíticos

## DATOS POR ÁREA ESTRATÉGICA:
{chr(10).join(prompt_sections)}

## REQUERIMIENTOS DEL INFORME:

### 1. RESUMEN EJECUTIVO (Máximo 150 palabras)
- Estado general del consenso geopolítico
- Áreas de mayor estabilidad/inestabilidad
- Cambios significativos vs semana anterior

### 2. DINÁMICAS DE PODER POR BLOQUE
- Análisis específico de USA, RUSSIA, CHINA, EUROPE
- Posicionamientos divergentes/convergentes
- Movimientos estratégicos detectados

### 3. PUNTOS DE FRICCIÓN CRÍTICA
- Top 3 tensiones emergentes
- Potenciales escaladas
- Áreas con riesgo de conflicto

### 4. RECOMENDACIONES DE VIGILANCIA
- 5 señales a monitorear la próxima semana
- Predicción de temas emergentes
- Alertas tempranas recomendadas

### 5. IMPLICACIONES ESTRATÉGICAS
- Impacto en alianzas internacionales
- Consecuencias económicas potenciales
- Escenarios prospectivos (optimista/neutral/pesimista)

**TONO:** Analítico, objetivo, basado en datos. Evitar especulación sin fundamento.
**FORMATO:** Markdown profesional con secciones claras. Usar bullet points para listas."""
        
        return full_prompt
    
    def generate_weekly_report(self, area_summaries):
        """Genera el reporte semanal usando Gemini"""
        prompt = self.build_analysis_prompt(area_summaries)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-1.5-pro",  # Mejor para análisis complejo
                contents=prompt,
                config={
                    "temperature": 0.3,
                    "max_output_tokens": 3000,
                    "top_p": 0.95
                }
            )
            
            return response.text
        except Exception as e:
            logging.error(f"Error generando reporte: {e}")
            return None
    
    def save_weekly_report(self, report_markdown, area_summaries):
        """Guarda el reporte en múltiples formatos"""
        hoy = datetime.datetime.now()
        week_id = f"semana_{hoy.strftime('%U_%Y')}"
        
        # 1. JSON completo con metadatos
        report_data = {
            "sintesis_estrategica": report_markdown,
            "resumen_ejecutivo": self.extract_executive_summary(report_markdown),
            "metricas_semanales": area_summaries,
            "meta": {
                "generado": hoy.isoformat(),
                "periodo_id": week_id,
                "fecha_inicio": (hoy - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
                "fecha_fin": (hoy - datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
                "modelo_ia": "gemini-1.5-pro",
                "version": "StrategicAggregatorPro v2.0"
            }
        }
        
        # Guardar JSON
        os.makedirs("historico_noticias/semanal", exist_ok=True)
        json_path = f"historico_noticias/semanal/{week_id}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # Guardar Markdown (para lectura humana)
        md_path = f"historico_noticias/semanal/{week_id}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(report_markdown)
        
        # Guardar resumen para el frontend
        summary_path = "historico_noticias/semanal/ultimo_resumen.json"
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "ultimo_reporte": week_id,
                "fecha": hoy.strftime("%Y-%m-%d"),
                "resumen": report_data["resumen_ejecutivo"],
                "areas_analizadas": len(area_summaries)
            }, f, indent=2, ensure_ascii=False)
        
        return json_path, md_path
    
    def extract_executive_summary(self, full_report):
        """Extrae el resumen ejecutivo del reporte completo"""
        lines = full_report.split('\n')
        summary_lines = []
        in_summary = False
        
        for line in lines:
            if "RESUMEN EJECUTIVO" in line.upper():
                in_summary = True
                continue
            if in_summary and line.strip().startswith('##'):
                break
            if in_summary and line.strip():
                summary_lines.append(line.strip())
        
        return ' '.join(summary_lines[:200])  # Limitar longitud
    
    def run(self):
        """Ejecuta el pipeline completo de agregación semanal"""
        print("🔍 Iniciando análisis semanal estratégico...")
        
        # 1. Cargar datos
        week_data, metrics_by_area = self.load_week_data()
        
        if not week_data:
            print("⚠️ No hay datos históricos suficientes para análisis semanal")
            return
        
        # 2. Calcular métricas
        area_summaries = self.calculate_week_metrics(metrics_by_area)
        
        if not area_summaries:
            print("⚠️ No se pudieron calcular métricas semanales")
            return
        
        print(f"✅ Datos procesados: {len(area_summaries)} áreas, {len(week_data)} días")
        
        # 3. Generar reporte
        print("🧠 Generando síntesis estratégica con IA...")
        report_markdown = self.generate_weekly_report(area_summaries)
        
        if not report_markdown:
            print("❌ Error generando reporte")
            return
        
        # 4. Guardar resultados
        json_path, md_path = self.save_weekly_report(report_markdown, area_summaries)
        
        print(f"📊 Reporte semanal generado exitosamente")
        print(f"   • JSON: {json_path}")
        print(f"   • Markdown: {md_path}")
        print(f"   • Áreas analizadas: {len(area_summaries)}")
        print(f"   • Días considerados: {len(week_data)}")
        
        # 5. Imprimir resumen
        for area, summary in area_summaries.items():
            print(f"   • {area}: {summary['consensus_avg']}% consenso ({summary['trend']})")

if __name__ == "__main__":
    import sys
    
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY no configurada")
        sys.exit(1)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Ejecutar agregador
    aggregator = StrategicAggregatorPro(api_key)
    aggregator.run()

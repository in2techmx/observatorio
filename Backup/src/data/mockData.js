export const REGIONS = {
    USA: { id: 'USA', name: 'USA', color: 'var(--region-usa)' },
    CHINA: { id: 'CHINA', name: 'China', color: 'var(--region-china)' },
    RUSSIA: { id: 'RUSSIA', name: 'Russia', color: 'var(--region-russia)' },
    EUROPE: { id: 'EUROPE', name: 'Europa', color: 'var(--region-europe)' },
    INDIA: { id: 'INDIA', name: 'India', color: 'var(--region-india)' },
    MID_EAST: { id: 'MID_EAST', name: 'Medio Oriente', color: 'var(--region-mideast)' },
    LATAM: { id: 'LATAM', name: 'LATAM', color: 'var(--region-latam)' },
};

export const PILLARS = [
    'Conflicto', 'Economía', 'Clima', 'Tecnología', 'Recursos', 'Derechos'
];

export const EVENTS = [
    {
        id: 1,
        title: "Acuerdo Libre Comercio Unión Africana - Mercosur",
        category: "Economía",
        global_convergence: 35, // Low convergence = High divergence
        regions_coverage: {
            LATAM: 9,
            CHINA: 6,
            RUSSIA: 6,
            USA: 1,
            EUROPE: 1,
            INDIA: 4,
            MID_EAST: 3
        },
        perspectives: {
            CHINA: { synthesis: "Un paso hacia la des-dolarización de los mercados emergentes.", keyword: "Des-dolarización" },
            LATAM: { synthesis: "Oportunidad histórica para la soberanía de recursos.", keyword: "Soberanía" },
            USA: { synthesis: "Preocupación por la influencia china en el Atlántico Sur.", keyword: "Influencia China" },
            EUROPE: { synthesis: "Silencio relativo. Enfoque menor en estándares ambientales.", keyword: "Estándares" },
            RUSSIA: { synthesis: "Fortalecimiento del eje multipolar lejos de sanciones.", keyword: "Multipolaridad" },
            INDIA: { synthesis: "Observando modelos de cooperación Sur-Sur.", keyword: "Cooperación" },
            MID_EAST: { synthesis: "Diversificación de rutas comerciales.", keyword: "Rutas" }
        },
        blind_spot_analysis: "Mientras el eje Sur-Sur consolida un bloque comercial, los medios occidentales enfocan en volatilidad de bolsas locales."
    },
    {
        id: 2,
        title: "Nueva Regulación Global de IA (G20)",
        category: "Tecnología",
        global_convergence: 85, // High convergence
        regions_coverage: {
            LATAM: 5,
            CHINA: 9,
            RUSSIA: 8,
            USA: 9,
            EUROPE: 10,
            INDIA: 7,
            MID_EAST: 6
        },
        perspectives: {
            EUROPE: { synthesis: "Protección de derechos fundamentales y ética.", keyword: "Ética" },
            CHINA: { synthesis: "Control estatal para estabilidad social.", keyword: "Seguridad" },
            USA: { synthesis: "No sobre-regular para mantener liderazgo en innovación.", keyword: "Innovación" },
            RUSSIA: { synthesis: "IA como herramienta de defensa soberana.", keyword: "Soberanía Digital" },
            LATAM: { synthesis: "Riesgo de colonialismo de datos.", keyword: "Colonialismo" },
            INDIA: { synthesis: "IA para el desarrollo y servicios públicos.", keyword: "Desarrollo" },
            MID_EAST: { synthesis: "Inversión masiva en infraestructura propia.", keyword: "Infraestructura" }
        },
        blind_spot_analysis: "Consenso en regulación, pero divergencia en el objetivo: Control (China) vs Ética (UE) vs Mercado (USA)."
    },
    {
        id: 3,
        title: "Crisis de Agua en el Cuerno de África",
        category: "Clima",
        global_convergence: 15,
        regions_coverage: {
            LATAM: 2,
            CHINA: 4,
            RUSSIA: 1,
            USA: 3,
            EUROPE: 5,
            INDIA: 2,
            MID_EAST: 8
        },
        perspectives: {
            MID_EAST: { synthesis: "Impacto directo en seguridad alimentaria regional.", keyword: "Hambruna" },
            EUROPE: { synthesis: "Llamado a ayuda humanitaria urgente.", keyword: "Ayuda" },
            USA: { synthesis: "Reportes menores en secciones científicas.", keyword: "Sequía" },
            CHINA: { synthesis: "Proyectos de irrigación como solución.", keyword: "Infraestructura" },
            RUSSIA: { synthesis: "Mínima cobertura.", keyword: "Silencio" },
            LATAM: { synthesis: "Comparación con sequías locales.", keyword: "Clima" },
            INDIA: { synthesis: "Solidaridad con el sur global.", keyword: "Solidaridad" }
        },
        blind_spot_analysis: "Crisis humanitaria masiva ignorada por el Norte Global, tratada como nota al pie climática."
    }
];

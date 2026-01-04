import React from 'react';
import { motion } from 'framer-motion';

const MethodologyModal = ({ onClose, language = 'EN' }) => {
    const t = {
        title: language === 'EN' ? "METHODOLOGY: PROXIMITY INDEX" : "METODOLOGÍA: ÍNDICE DE PROXIMIDAD",
        intro: language === 'EN'
            ? "The Proximity Score (0-10) is a calculated metric indicating the relevance and immediacy of a geopolitical signal relative to strategic interests."
            : "El Puntaje de Proximidad (0-10) es una métrica calculada que indica la relevancia e inmediatez de una señal geopolítica en relación con intereses estratégicos.",
        factors: [
            {
                title: language === 'EN' ? "1. GEOPOLITICAL WEIGHT" : "1. PESO GEOPOLÍTICO",
                desc: language === 'EN'
                    ? "Regions with active conflicts or high strategic value (e.g., Indo-Pacific, Eastern Europe) receive higher base weights."
                    : "Regiones con conflictos activos o alto valor estratégico (ej. Indo-Pacífico, Europa del Este) reciben pesos base más altos."
            },
            {
                title: language === 'EN' ? "2. KEYWORD RESONANCE" : "2. RESONANCIA DE PALABRAS CLAVE",
                desc: language === 'EN'
                    ? "Signals containing critical terms (e.g., 'Nuclear', 'Sanctions', 'Treaty') trigger multipliers."
                    : "Señales que contienen términos críticos (ej. 'Nuclear', 'Sanciones', 'Tratado') activan multiplicadores."
            },
            {
                title: language === 'EN' ? "3. TEMPORAL DECAY" : "3. DECAIMIENTO TEMPORAL",
                desc: language === 'EN'
                    ? "Scores degrade over time. Fresh signals (<24h) maintain peak scores; older signals fade to the perimeter."
                    : "Los puntajes se degradan con el tiempo. Señales frescas (<24h) mantienen puntajes pico; las antiguas se desvanecen hacia el perímetro."
            }
        ],
        formula: language === 'EN' ? "FORMULA" : "FÓRMULA",
        close: language === 'EN' ? "CLOSE PROTOCOL" : "CERRAR PROTOCOLO"
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
        >
            <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                className="w-full max-w-2xl bg-black border border-cyan-500/50 rounded-2xl overflow-hidden shadow-[0_0_50px_rgba(6,182,212,0.2)]"
            >
                {/* Header */}
                <div className="bg-cyan-900/20 p-6 border-b border-cyan-500/30 flex justify-between items-center">
                    <h2 className="text-2xl font-black text-cyan-400 tracking-tighter uppercase flex items-center gap-3">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.384-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
                        {t.title}
                    </h2>
                    <button onClick={onClose} className="text-gray-500 hover:text-white transition-colors">
                        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                    </button>
                </div>

                {/* Content */}
                <div className="p-8 space-y-8">
                    <p className="text-gray-300 font-mono text-sm leading-relaxed border-l-2 border-cyan-500 pl-4">
                        {t.intro}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {t.factors.map((f, i) => (
                            <div key={i} className="bg-white/5 p-4 rounded-lg border border-white/10">
                                <h3 className="text-xs font-bold text-cyan-400 mb-2">{f.title}</h3>
                                <p className="text-[10px] text-gray-400 leading-normal">{f.desc}</p>
                            </div>
                        ))}
                    </div>

                    <div className="bg-black border border-gray-800 p-4 rounded font-mono text-xs text-gray-500 text-center">
                        <span className="text-gray-300 font-bold block mb-2">{t.formula}</span>
                        (RegionWeight × KeywordMultiplier) - (HoursSince × DecayRate) = <span className="text-cyan-400 font-bold">PROXIMITY</span>
                    </div>
                </div>

                {/* Footer */}
                <div className="p-4 bg-gray-900 border-t border-white/5 text-center">
                    <button
                        onClick={onClose}
                        className="text-xs font-bold text-black bg-cyan-500 hover:bg-cyan-400 px-6 py-2 rounded uppercase tracking-widest transition-colors"
                    >
                        {t.close}
                    </button>
                </div>
            </motion.div>
        </motion.div>
    );
};

export default MethodologyModal;

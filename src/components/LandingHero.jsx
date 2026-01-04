import React from 'react';
import { motion } from 'framer-motion';

const LandingHero = ({ language = 'EN', toggleLanguage, onOpenMethodology }) => {
    // Dictionary
    const t = {
        subtitle: language === 'EN' ? "Global Intelligence Observatory" : "Observatorio de Inteligencia Global",
        desc: language === 'EN'
            ? "Decentralized monitoring of geopolitical signals. Tracking convergence across 7 strategic regions."
            : "Monitoreo descentralizado de señales geopolíticas. Rastreando la convergencia en 7 regiones estratégicas.",
        steps: {
            scan: language === 'EN' ? "1. SCAN" : "1. ESCANEAR",
            scanDesc: language === 'EN' ? "Scan the horizon for high-priority signal clusters." : "Escanea el horizonte buscando grupos de señales de alta prioridad.",
            select: language === 'EN' ? "2. SELECT" : "2. SELECCIONAR",
            selectDesc: language === 'EN' ? "Select a category to view the tactical radar." : "Selecciona una categoría para ver el radar táctico.",
            analyze: language === 'EN' ? "3. ANALYZE" : "3. ANALIZAR",
            analyzeDesc: language === 'EN' ? "Analyze the proximity score and synthesized intelligence." : "Analiza el puntaje de proximidad y la inteligencia sintetizada."
        },
        reports: {
            weekly: language === 'EN' ? "WEEKLY REPORT" : "REPORTE SEMANAL",
            monthly: language === 'EN' ? "MONTHLY REPORT" : "REPORTE MENSUAL",
            method: language === 'EN' ? "METHODOLOGY" : "METODOLOGÍA"
        }
    };

    return (
        <div className="relative w-full h-auto py-8 md:py-10 flex flex-col md:flex-row items-center justify-between px-6 md:px-12 border-b border-white/10 overflow-hidden bg-black z-50 gap-6 md:gap-0">
            {/* Background Effects */}
            <div className="absolute inset-0 z-0 pointer-events-none">
                <div className="absolute top-[-50%] left-[20%] w-[30vw] h-[30vw] bg-cyan-500/10 rounded-full blur-[80px]" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
            </div>

            {/* Left: Title & Slogan */}
            <div className="z-10 flex flex-col justify-center max-w-2xl text-center md:text-left">
                <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-5xl md:text-8xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-b from-white to-white/50 mb-2 select-none leading-none font-display">
                        PROXIMITY
                    </h1>
                </motion.div>
                <div className="flex flex-col gap-2 mt-1">
                    <p className="text-sm md:text-base text-cyan-400 font-bold tracking-[0.3em] uppercase glow-text">
                        {t.subtitle}
                    </p>
                    <p className="text-[10px] md:text-xs text-gray-500 font-mono leading-relaxed max-w-lg block">
                        {t.desc}
                    </p>
                    {/* Tactical Report Buttons */}
                    <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 mt-4">
                        <button className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 hover:border-cyan-500 hover:bg-cyan-500/10 transition-all rounded text-[10px] font-mono tracking-widest text-cyan-400 uppercase group">
                            <svg className="w-3 h-3 group-hover:animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                            {t.reports.weekly}
                        </button>
                        <button className="flex items-center gap-2 px-3 py-2 bg-white/5 border border-white/10 hover:border-magenta-500 hover:bg-magenta-500/10 transition-all rounded text-[10px] font-mono tracking-widest text-magenta-400 uppercase group">
                            <svg className="w-3 h-3 group-hover:animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
                            {t.reports.monthly}
                        </button>
                        <button
                            onClick={onOpenMethodology}
                            className="flex items-center gap-2 px-3 py-2 bg-transparent border border-gray-700 hover:border-gray-400 hover:bg-gray-800 transition-all rounded text-[10px] font-mono tracking-widest text-gray-400 hover:text-white uppercase group ml-2"
                        >
                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                            {t.reports.method}
                        </button>
                    </div>
                </div>
            </div>

            {/* Right: Steps & Language */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="z-10 flex flex-col items-end gap-6"
            >
                {/* Language Toggle */}
                <button
                    onClick={toggleLanguage}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 cursor-pointer transition-all active:scale-95 mb-2"
                >
                    <span className={`text-[10px] font-bold ${language === 'EN' ? 'text-cyan-400' : 'text-gray-500'}`}>EN</span>
                    <div className="h-3 w-[1px] bg-white/20"></div>
                    <span className={`text-[10px] font-bold ${language === 'ES' ? 'text-cyan-400' : 'text-gray-500'}`}>ES</span>
                </button>

                {/* 3 Instructional Tiles */}
                <div className="flex gap-3">
                    {[
                        { title: t.steps.scan, desc: t.steps.scanDesc, color: "text-cyan-400", border: "border-cyan-500/30" },
                        { title: t.steps.select, desc: t.steps.selectDesc, color: "text-magenta-400", border: "border-magenta-500/30" },
                        { title: t.steps.analyze, desc: t.steps.analyzeDesc, color: "text-emerald-400", border: "border-emerald-500/30" }
                    ].map((step, i) => (
                        <div key={i} className={`flex flex-col justify-start w-32 h-32 bg-black/50 backdrop-blur-sm border ${step.border} rounded-lg p-4 hover:bg-white/5 transition-colors group`}>
                            <span className={`text-[10px] font-bold ${step.color} mb-2 group-hover:scale-105 transition-transform block`}>{step.title}</span>
                            <span className="text-[9px] text-gray-400 leading-relaxed font-mono block">{step.desc}</span>
                        </div>
                    ))}
                </div>
            </motion.div>
        </div>
    );
};

export default LandingHero;

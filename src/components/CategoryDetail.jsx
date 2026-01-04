import React, { useState } from 'react';
import RadarView from './RadarView';
import NewsList from './NewsList';
import { motion } from 'framer-motion';

const CategoryDetail = ({ category, events, synthesis, onSelectNews, onClose, language = 'EN', categoryTranslations }) => {
    const [hoveredId, setHoveredId] = useState(null);
    const [filterRegion, setFilterRegion] = useState(null); // New: Filter by region

    if (!category) return null;

    // Translation Helpers
    const isEn = language === 'EN';
    const t = {
        signals: isEn ? "SIGNALS DETECTED" : "SEÑALES DETECTADAS",
        briefing: isEn ? "Specialist Briefing" : "Informe de Especialista",
        radarTitle: isEn ? "Proximity Radar" : "Radar de Proximidad",
        feedTitle: isEn ? "Intelligence Feed" : "Señales en Tiempo Real",
        center: isEn ? "CENTER" : "CENTRO",
        centerDesc: isEn ? "High Convergence" : "Alta Convergencia",
        perimeter: isEn ? "PERIMETER" : "PERÍMETRO",
        perimeterDesc: isEn ? "Weak Signals" : "Señales Débiles",
        filteringBy: isEn ? "FILTERING BY:" : "FILTRANDO POR:",
        clearFilter: isEn ? "CLEAR" : "BORRAR"
    };

    // Resolve Category Name
    const categoryName = categoryTranslations?.[category]?.[language.toLowerCase()] || category;

    // Resolve Synthesis Text
    const synthesisText = typeof synthesis === 'object' ? synthesis[language.toLowerCase()] : synthesis;

    // Filter Events
    const filteredEvents = filterRegion
        ? events.filter(e => e.country === filterRegion || e.region === filterRegion)
        : events;

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.3 }}
            className="fixed inset-0 z-50 bg-black/95 backdrop-blur-2xl flex flex-col overflow-hidden h-screen"
        >
            {/* Header Bar */}
            <div className="flex items-center justify-between px-6 md:px-8 py-4 md:py-6 border-b border-white/10 bg-black/50 shrink-0 z-10">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onClose}
                        className="p-2 -ml-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors group"
                        title={isEn ? "Back" : "Volver"}
                    >
                        <svg className="w-6 h-6 group-hover:-translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" /></svg>
                    </button>
                    <div>
                        <h2 className="text-2xl md:text-5xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 uppercase font-display">
                            {categoryName}
                        </h2>
                        <div className="flex items-center gap-3 mt-1">
                            <span className="text-[10px] font-mono text-cyan-500 tracking-widest uppercase">
                                // {filteredEvents.length} {t.signals}
                            </span>
                            {filterRegion && (
                                <span className="flex items-center gap-1 text-[10px] font-mono text-white bg-cyan-900/30 px-2 py-0.5 rounded border border-cyan-500/30">
                                    {t.filteringBy} {filterRegion}
                                    <button onClick={() => setFilterRegion(null)} className="ml-2 hover:text-cyan-400">
                                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                    </button>
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                <button
                    onClick={onClose}
                    className="p-3 rounded-full hover:bg-red-500/10 text-gray-500 hover:text-red-500 transition-colors border border-transparent hover:border-red-500/50"
                    title="Close"
                >
                    <svg className="w-5 h-5 md:w-6 md:h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
            </div>

            {/* Scrollable Content Container - Responsive Logic */}
            {/* 2. Main Content Grid */}
            <div className="flex-1 overflow-y-auto md:overflow-hidden p-6 md:p-8 grid grid-cols-1 md:grid-cols-2 gap-8 relative">

                {/* TOP BRIEF (Mobile: Stacked first, Desktop: Absolute top or span-2? 
                   User said "Brief arriba". In a 2-col layout, "Top" implies spanning both cols or being outside grid. 
                   Let's put it OUTSIDE the grid, just below Header, if we want full width top. 
                   OR make grid-cols-1 md:grid-cols-2 and put Brief in a col-span-2 div first.
                */}
                <div className="md:col-span-2 mb-4">
                    <div className="bg-gradient-to-r from-cyan-900/20 to-transparent border-l-4 border-cyan-500 p-6 rounded-r-xl">
                        <h3 className="text-xs font-bold text-cyan-400 mb-2 uppercase tracking-widest">
                            {language === 'EN' ? 'INTELLIGENCE BRIEF' : 'INFORME DE INTELIGENCIA'}
                        </h3>
                        <p className="text-lg md:text-xl text-gray-200 font-light leading-relaxed font-mono">
                            {/* Strict Language Toggle for Synthesis */}
                            {(typeof synthesis === 'object' ? synthesis[language.toLowerCase()] : synthesis) || (language === 'EN' ? "No briefing available." : "No hay informe disponible.")}
                        </p>
                    </div>
                </div>

                {/* LEFT: RADAR (Interactive) */}
                <div className="relative h-[400px] md:h-full flex flex-col items-center justify-center p-4 bg-white/5 rounded-2xl border border-white/10 order-2 md:order-1">
                    <RadarView
                        events={events}
                        onNodeClick={onSelectNews}
                        language={language}
                    />
                    {/* Overlay Instruction */}
                    <div className="absolute bottom-4 left-4 text-[10px] text-gray-500 font-mono">
                        {language === 'EN' ? "CLICK NODE TO INSPECT" : "CLIC EN NODO PARA INSPECCIONAR"}
                    </div>
                </div>

                {/* RIGHT: NEWS FEED (Scrollable) */}
                <div className="flex flex-col h-full overflow-hidden order-3 md:order-2">
                    <h3 className="text-xs font-bold text-gray-500 mb-4 flex items-center gap-2 px-2 shrink-0">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
                        {language === 'EN' ? 'INCOMING SIGNALS' : 'SEÑALES ENTRANTES'}
                        <span className="text-cyan-500">[{events.length}]</span>
                    </h3>

                    <div className="flex-1 overflow-y-auto space-y-3 pr-2 custom-scrollbar pb-20 md:pb-0">
                        {events.map((event) => (
                            <div
                                key={event.id}
                                onClick={() => onSelectNews(event)}
                                className="group relative p-4 bg-black/40 border border-white/10 hover:border-cyan-500/50 hover:bg-cyan-900/10 rounded-lg cursor-pointer transition-all"
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <span className="text-[10px] font-bold text-cyan-400 bg-cyan-900/30 px-2 py-0.5 rounded uppercase tracking-wider">
                                        {event.region || "GLOBAL"}
                                    </span>
                                    <span className="text-[10px] text-gray-500 font-mono">
                                        {Math.round(event.proximity_score * 10)}% PROX
                                    </span>
                                </div>
                                <h4 className="text-sm font-medium text-gray-200 group-hover:text-white leading-snug mb-2">
                                    {language === 'EN' ? (event.titulo_en || event.title) : (event.titulo_es || event.title)}
                                </h4>
                                <div className="flex items-center justify-between text-[10px] text-gray-600 font-mono">
                                    <span>{new Date().toLocaleDateString()}</span>
                                    <span className="group-hover:text-cyan-400 transition-colors">&gt;&gt; READ</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default CategoryDetail;

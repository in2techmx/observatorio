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
            {/* Mobile: Standard vertical scroll. Desktop: Flex row that fits screen (if content allows) or scrolls internally */}
            <div className="flex-1 overflow-y-auto custom-scrollbar bg-black/90 w-full">
                <div className="container mx-auto px-4 md:px-8 py-8 h-full flex flex-col">

                    {/* Specialist Analysis Block */}
                    {synthesisText && !filterRegion && (
                        <div className="mb-8 md:mb-12 p-6 border-l-4 border-cyan-500 bg-white/5 rounded-r-xl backdrop-blur-md shadow-lg shrink-0">
                            <h4 className="text-xs uppercase font-bold tracking-[0.2em] text-cyan-400 mb-3 flex items-center gap-2">
                                <span className="relative flex h-2 w-2">
                                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                                    <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
                                </span>
                                {t.briefing}
                            </h4>
                            <div className="prose prose-invert prose-sm max-w-none">
                                <p className="text-gray-200 font-mono leading-relaxed whitespace-pre-line text-sm md:text-base border-l border-white/10 pl-4">
                                    {synthesisText}
                                </p>
                            </div>
                        </div>
                    )}

                    {/* Main Content Layout - Desktop: Side-by-Side / Mobile: Stacked */}
                    <div className="flex flex-col xl:flex-row gap-8 lg:gap-12 items-start justify-center flex-1">

                        {/* Block 1: The Radar (LEFT) - Pure Black Background */}
                        <div className="flex-1 flex flex-col items-center w-full min-h-[400px] xl:h-auto xl:sticky xl:top-0 p-6 bg-black rounded-3xl border border-white/20 shadow-[0_0_30px_rgba(0,0,0,0.8)] shrink-0">
                            <h3 className="text-xs uppercase tracking-[0.2em] text-cyan-400 mb-8 flex items-center gap-2">
                                <svg className="w-4 h-4 animate-spin-slow" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                                {t.radarTitle}
                            </h3>
                            <div className="w-full max-w-[500px] aspect-square relative group">
                                {/* Subtle center glow, but mostly black */}
                                <div className="absolute inset-0 bg-cyan-500/5 rounded-full blur-3xl opacity-50" />
                                <RadarView
                                    events={events} // Pass full events to radar to show all context
                                    hoveredId={hoveredId}
                                    onHover={setHoveredId}
                                    language={language}
                                    onRegionSelect={setFilterRegion} // Pass handler
                                    selectedRegion={filterRegion} // Pass state
                                />
                            </div>
                            <div className="mt-8 flex gap-8 text-[10px] text-gray-500 font-mono text-center">
                                <div>
                                    <span className="block text-white font-bold mb-1">{t.center}</span>
                                    {t.centerDesc}
                                </div>
                                <div>
                                    <span className="block text-white font-bold mb-1">{t.perimeter}</span>
                                    {t.perimeterDesc}
                                </div>
                            </div>
                        </div>

                        {/* Block 2: The List (RIGHT) - Glass Cards */}
                        <div className="flex-1 w-full xl:max-w-2xl xl:h-full xl:overflow-y-auto custom-scrollbar pr-2">
                            <h3 className="text-xs uppercase tracking-[0.2em] text-gray-400 mb-6 pl-2 flex items-center gap-2 sticky top-0 bg-black/90 pb-4 z-10 backdrop-blur-sm">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" /></svg>
                                {t.feedTitle}
                            </h3>
                            <div className="bg-transparent space-y-2 pb-12">
                                <NewsList
                                    events={filteredEvents} // Pass filtered events
                                    hoveredId={hoveredId}
                                    onHover={setHoveredId}
                                    onSelect={onSelectNews}
                                    language={language}
                                />
                            </div>
                        </div>

                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default CategoryDetail;

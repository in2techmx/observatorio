import React, { useState } from 'react';
import RadarView from './RadarView';
import { motion } from 'framer-motion';
import { REGION_COLORS } from '../constants/regions';

const CategoryDetail = ({ category, events = [], synthesis = "", regionalSyntheses = {}, onSelectNews, onClose, language = 'EN', categoryTranslations }) => {
    const [selectedRadarId, setSelectedRadarId] = useState(null);
    const [selectedRegion, setSelectedRegion] = useState(null);

    // Helper to clean URL
    const tryParseDomain = (url) => {
        try {
            return new URL(url).hostname.replace('www.', '');
        } catch (e) {
            return "";
        }
    };

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
    // Filter Events SAFE
    const safeEvents = Array.isArray(events) ? events : [];
    const filteredEvents = filterRegion
        ? safeEvents.filter(e => e && (e.country === filterRegion || e.region === filterRegion))
        : safeEvents;

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
            <div className="flex-1 overflow-hidden p-4 md:p-6 grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6 relative">

                {/* DYNAMIC TOP PANEL: BRIEFING OR INSPECTION */}
                <div className="md:col-span-2 min-h-[120px] shrink-0">
                    <div className={`h-full border-l-4 pl-4 py-3 rounded-r-lg transition-all duration-300 ${selectedRadarId
                        ? 'bg-gradient-to-r from-gray-900 via-gray-900/50 to-transparent border-white'
                        : 'bg-gradient-to-r from-cyan-900/10 to-transparent border-cyan-500'}`}>

                        {selectedRadarId ? (
                            // === INSPECTION MODE (Selected Item) ===
                            (() => {
                                const item = events.find(e => e.id === selectedRadarId);
                                const regionColor = REGION_COLORS[item.region] || "#fff";
                                return (
                                    <div className="animate-in fade-in slide-in-from-top-2 duration-300">
                                        <div className="flex items-center gap-3 mb-2">
                                            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded text-black uppercase tracking-widest"
                                                style={{ backgroundColor: regionColor }}>
                                                TARGET LOCKED: {item.region}
                                            </span>
                                            <div className="h-[1px] flex-1 bg-white/20"></div>
                                            <span className="text-[10px] text-gray-400 font-mono">
                                                CENTROID PROXIMITY: {Math.round(item.proximity_score * 10)}% | BIAS: {item.sesgo || 'NEUTRAL'}
                                            </span>
                                        </div>

                                        <h3 className="text-lg md:text-xl font-bold text-white leading-tight mb-2 font-display">
                                            {language === 'EN' ? (item.titulo_en || item.title) : (item.titulo_es || item.title)}
                                        </h3>

                                        <div className="flex flex-wrap gap-4 text-xs text-gray-300 font-sans">
                                            {item.snippet && (
                                                <p className="max-w-4xl opacity-90 border-l-2 border-white/20 pl-2 italic">
                                                    "{item.snippet}"
                                                </p>
                                            )}

                                            <div className="flex flex-wrap gap-2 mt-1">
                                                {(item.keywords || []).slice(0, 5).map((kw, i) => (
                                                    <span key={i} className="text-[9px] border border-white/20 px-1.5 rounded text-gray-400 font-mono">
                                                        #{kw}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })()
                        ) : (
                            // === BRIEFING MODE (Global or Regional) ===
                            (() => {
                                // Determine content: Regional or Global
                                const activeNarrative = (selectedRegion && regionalSyntheses && regionalSyntheses[selectedRegion])
                                    ? regionalSyntheses[selectedRegion]
                                    : (typeof synthesis === 'object' ? synthesis[language.toLowerCase()] : synthesis);

                                const title = selectedRegion
                                    ? `${language === 'EN' ? 'REGIONAL INTEL' : 'INTEL REGIONAL'}: ${selectedRegion}`
                                    : (language === 'EN' ? 'INTELLIGENCE BRIEF' : 'INFORME DE INTELIGENCIA');

                                return (
                                    <>
                                        <div className="flex items-baseline gap-3 mb-1">
                                            <h3 className={`text-[10px] font-bold uppercase tracking-widest ${selectedRegion ? 'text-purple-400' : 'text-cyan-400'}`}>
                                                {title}
                                            </h3>
                                            <div className={`h-[1px] flex-1 ${selectedRegion ? 'bg-purple-900/30' : 'bg-cyan-900/30'}`}></div>
                                        </div>
                                        <p className="text-sm md:text-base text-gray-300 font-light leading-snug font-sans max-w-5xl animate-in fade-in">
                                            {activeNarrative || (language === 'EN' ? "No briefing available." : "No hay informe disponible.")}
                                        </p>
                                    </>
                                );
                            })()
                        )}
                    </div>
                </div>

                {/* LEFT: RADAR (Interactive) */}
                <div className="relative h-[300px] md:h-full flex flex-col items-center justify-center p-2 bg-white/5 rounded-xl border border-white/5 order-2 md:order-1 overflow-hidden">
                    <RadarView
                        events={events}
                        onNodeClick={onSelectNews} // Legacy prop
                        language={language}
                        hoveredId={hoveredId}
                        selectedNodeId={selectedRadarId}
                        onNodeSelect={setSelectedRadarId}
                        selectedRegion={selectedRegion}
                        onRegionSelect={setSelectedRegion}
                    />
                    {/* Radar Legend/Status */}
                    <div className="absolute bottom-2 left-4 text-[9px] font-mono text-white/30 pointer-events-none">
                        RADAR_STATUS: ACTIVE<br />
                        SCANNING_SECTOR: {filterRegion || "GLOBAL"}
                    </div>
                </div>

                {/* RIGHT: NEWS FEED (Scrollable) */}
                <div className="flex flex-col h-full overflow-hidden order-3 md:order-2">
                    <h3 className="text-[10px] font-bold text-gray-500 mb-2 flex items-center gap-2 px-2 shrink-0 uppercase tracking-wider">
                        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" /></svg>
                        {language === 'EN' ? 'INCOMING SIGNALS' : 'SEÑALES ENTRANTES'}
                        <span className="text-cyan-500">[{events.length}]</span>
                    </h3>

                    <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar pb-20 md:pb-0">
                        {filteredEvents.map((event) => {
                            // Resolve Color
                            const regionColor = REGION_COLORS[event.region] || REGION_COLORS["GLOBAL"] || "#fff";
                            const isSelected = hoveredId === event.id || selectedRadarId === event.id;

                            return (
                                <div
                                    key={event.id}
                                    onClick={() => setSelectedRadarId(event.id)}
                                    onMouseEnter={() => setHoveredId(event.id)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    // Dynamic Style: Border and Background follow Region Color
                                    className={`group relative p-4 bg-black/40 border rounded-md cursor-pointer transition-all duration-200 flex flex-col gap-2`}
                                    style={{
                                        borderColor: isSelected ? regionColor : 'rgba(255,255,255,0.05)',
                                        backgroundColor: isSelected ? `${regionColor}10` : 'rgba(0,0,0,0.4)',
                                        boxShadow: isSelected ? `0 0 15px ${regionColor}20` : 'none'
                                    }}
                                >
                                    {/* Header: Region & Score */}
                                    <div className="flex justify-between items-start">
                                        <span
                                            className="text-[9px] font-bold px-1.5 rounded uppercase tracking-wider"
                                            style={{
                                                color: regionColor,
                                                backgroundColor: `${regionColor}20`,
                                                border: `1px solid ${regionColor}40`
                                            }}
                                        >
                                            {event.region || "GLOBAL"}
                                        </span>
                                        <span className={`text-[9px] font-mono ${isSelected ? 'text-white' : 'text-gray-600'}`}>
                                            PROX: {Math.round(event.proximity_score * 10)}%
                                        </span>
                                    </div>

                                    {/* Title */}
                                    <h4 className={`text-sm font-bold leading-tight ${isSelected ? 'text-white' : 'text-gray-200'}`}>
                                        {language === 'EN' ? (event.titulo_en || event.title) : (event.titulo_es || event.title)}
                                    </h4>

                                    {/* Snippet / Synthesis */}
                                    {event.snippet && (
                                        <p
                                            className="text-xs text-gray-400 leading-snug line-clamp-3 font-sans border-l-2 pl-2"
                                            style={{ borderColor: `${regionColor}40` }}
                                        >
                                            {event.snippet}
                                        </p>
                                    )}

                                    {/* Footer: Metadata & Source Link */}
                                    <div className="flex items-center justify-between text-[10px] text-gray-500 font-mono mt-1 pt-2 border-t border-white/5">
                                        <div className="flex gap-2">
                                            <span>{new Date().toLocaleDateString()}</span>
                                            {event.source_url && (
                                                <span className="truncate max-w-[100px]" style={{ color: isSelected ? regionColor : undefined }}>
                                                    {tryParseDomain(event.source_url)}
                                                </span>
                                            )}
                                        </div>

                                        <a
                                            href={event.source_url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                            className="flex items-center gap-1 transition-colors uppercase tracking-wider hover:underline"
                                            style={{ color: isSelected ? regionColor : undefined }}
                                        >
                                            [ {language === 'EN' ? 'SOURCE' : 'FUENTE'} ]
                                            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                                        </a>

                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onSelectNews(event);
                                            }}
                                            className="font-bold ml-4 border-b border-white/20 transition-colors"
                                            style={{
                                                color: isSelected ? '#fff' : regionColor,
                                                borderColor: isSelected ? regionColor : undefined
                                            }}
                                        >
                                            &gt;&gt; {language === 'EN' ? 'ANALYZE' : 'ANALIZAR'}
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default CategoryDetail;

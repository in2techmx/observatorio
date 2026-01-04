import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Radio } from 'lucide-react';
import RadarView from './RadarView';
import NewsList from './NewsList';

const CategoryDeck = ({ category, events, synthesis, onSelectNews }) => {
    const [isExpanded, setIsExpanded] = useState(false);
    const [hoveredId, setHoveredId] = useState(null);

    // Calculate average intensity for the 'preview' stats
    const avgScore = (events.reduce((acc, curr) => acc + curr.proximity_score, 0) / events.length).toFixed(1);

    return (
        <section className="w-full mb-4 group">
            {/* Deck Header (Always Visible) */}
            <div
                onClick={() => setIsExpanded(!isExpanded)}
                className={`
                    w-full p-6 flex items-center justify-between cursor-pointer
                    border-l-4 transition-all duration-300
                    ${isExpanded
                        ? 'bg-gradient-to-r from-white/10 to-transparent border-cyan-500'
                        : 'hover:bg-white/5 border-transparent hover:border-gray-600'
                    }
                `}
            >
                <div className="flex items-center gap-4">
                    <h2 className="text-2xl font-bold tracking-tighter text-white uppercase">{category}</h2>
                    <span className="text-xs text-gray-500 font-mono border border-gray-700 px-2 py-0.5 rounded-full">
                        {events.length} SIGNALS
                    </span>
                </div>

                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] text-gray-500 uppercase tracking-widest">Avg Gravity</span>
                        <div className="flex items-center gap-1">
                            <Radio size={14} className={avgScore > 7 ? "text-red-500 animate-pulse" : "text-gray-500"} />
                            <span className="font-mono text-lg font-bold text-gray-300">{avgScore}</span>
                        </div>
                    </div>

                    <button className={`p-2 rounded-full transition-all ${isExpanded ? 'bg-white text-black' : 'bg-white/10 text-white group-hover:bg-white group-hover:text-black'}`}>
                        {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
                    </button>
                </div>
            </div>

            {/* AI Narrative Synthesis Banner */}
            {synthesis && (
                <div className="px-6 pb-4 -mt-2">
                    <div className="text-sm font-mono text-cyan-300/80 border-l-2 border-cyan-500 pl-4 italic">
                        "{synthesis}"
                    </div>
                </div>
            )}

            {/* Expanded Content (Simple Render) */}
            {isExpanded && (
                <div className="relative z-20 bg-zinc-900/50 min-h-[500px] border-t border-white/10 border-b border-white/5 mx-4 md:mx-12 transition-all duration-300 backdrop-blur-sm">
                    <div className="p-8 h-full">
                        <div className="flex flex-col md:flex-row gap-8 items-center md:items-start justify-center h-full">

                            {/* Block 1: The Radar */}
                            <div className="flex-1 flex flex-col items-center w-full min-h-[400px]">
                                <h3 className="text-xs uppercase tracking-[0.2em] text-cyan-400 mb-6 flex items-center gap-2">
                                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping" />
                                    Radar de Proximidad
                                </h3>
                                <RadarView
                                    events={events}
                                    hoveredId={hoveredId}
                                    onHover={setHoveredId}
                                />
                                <p className="text-[10px] text-gray-500 mt-4 max-w-xs text-center">
                                    Los nodos centrales (Radio Interno) representan alta convergencia geopolítica. Los nodos externos son señales débiles o aisladas.
                                </p>
                            </div>

                            {/* Divider */}
                            <div className="hidden md:block w-px bg-white/10 h-[400px] mx-4" />

                            {/* Block 2: The List */}
                            <div className="flex-1 w-full md:max-w-xl min-h-[400px]">
                                <h3 className="text-xs uppercase tracking-[0.2em] text-gray-500 mb-6">
                                    Feed de Inteligencia
                                </h3>
                                <NewsList
                                    events={events}
                                    hoveredId={hoveredId}
                                    onHover={setHoveredId}
                                    onSelect={onSelectNews}
                                />
                            </div>

                        </div>
                    </div>
                </div>
            )}
        </section>
    );
};

export default CategoryDeck;

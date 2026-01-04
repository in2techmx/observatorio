import React, { useState } from 'react';
import RadarView from './RadarView';
import NewsList from './NewsList';
import { motion } from 'framer-motion';

const CategoryDetail = ({ category, events, synthesis, onSelectNews }) => {
    const [hoveredId, setHoveredId] = useState(null);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
            className="relative z-20 w-full bg-black/40 border-t border-white/10 backdrop-blur-xl min-h-[600px]"
        >
            {/* Header / Synthesis Strip */}
            <div className="w-full border-b border-white/5 bg-white/5">
                <div className="container mx-auto px-6 py-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                    <div>
                        <h2 className="text-3xl font-bold tracking-tighter text-white uppercase">{category}</h2>
                        <span className="text-xs font-mono text-cyan-400 border border-cyan-900/50 bg-cyan-900/10 px-2 py-0.5 rounded">
                            {events.length} SIGNALS DETECTED
                        </span>
                    </div>

                    {/* Specialist Analysis Block */}
                    {synthesis && (
                        <div className="mt-6 p-4 border-l-2 border-cyan-500 bg-cyan-900/10 max-w-4xl rounded-r-lg">
                            <h4 className="text-[10px] uppercase font-bold tracking-[0.2em] text-cyan-400 mb-2 flex items-center gap-2">
                                <span className="w-2 h-2 bg-cyan-500 rounded-sm animate-pulse" />
                                Specialist Briefing
                            </h4>
                            <p className="text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-line">
                                {synthesis}
                            </p>
                        </div>
                    )}
                </div>
            </div>
        </div>

            {/* Main Content Area */ }
    <div className="container mx-auto px-6 py-8">
        <div className="flex flex-col xl:flex-row gap-12 items-start justify-center">

            {/* Block 1: The Radar */}
            <div className="flex-1 flex flex-col items-center w-full min-h-[500px] p-6 bg-black/20 rounded-2xl border border-white/5">
                <h3 className="text-xs uppercase tracking-[0.2em] text-cyan-400 mb-8 flex items-center gap-2">
                    <div className="w-1.5 h-1.5 bg-cyan-400 rounded-full animate-ping" />
                    Radar de Proximidad
                </h3>
                <div className="scale-110">
                    <RadarView
                        events={events}
                        hoveredId={hoveredId}
                        onHover={setHoveredId}
                    />
                </div>
                <p className="text-[10px] text-gray-500 mt-8 max-w-xs text-center leading-relaxed">
                    Los nodos centrales (Radio Interno) representan alta convergencia geopolítica. Los nodos externos son señales débiles o aisladas.
                </p>
            </div>

            {/* Block 2: The List */}
            <div className="flex-1 w-full xl:max-w-2xl min-h-[500px]">
                <h3 className="text-xs uppercase tracking-[0.2em] text-gray-500 mb-6 pl-2">
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
        </motion.div >
    );
};

export default CategoryDetail;

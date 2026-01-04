import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Globe } from 'lucide-react';

const NewsList = ({ events, hoveredId, onHover, onSelect }) => {
    return (
        <div className="flex flex-col gap-3 h-[600px] overflow-y-auto pr-2 custom-scrollbar pb-20">
            {events.map((ev) => {
                const isHovered = hoveredId === ev.id;

                // Parse domain for display
                const domain = ev.source_url ? new URL(ev.source_url).hostname.replace('www.', '') : 'External Source';

                return (
                    <motion.div
                        key={ev.id}
                        layoutId={`card-${ev.id}`}
                        onMouseEnter={() => onHover(ev.id)}
                        onMouseLeave={() => onHover(null)}
                        onClick={() => onSelect(ev)}
                        className={`
                            relative p-5 rounded-xl border cursor-pointer transition-all duration-300 group
                            ${isHovered
                                ? 'bg-zinc-900 border-cyan-500/50 shadow-[0_0_20px_rgba(6,182,212,0.1)]'
                                : 'bg-black/40 border-white/5 hover:bg-zinc-900/40 hover:border-white/20'
                            }
                        `}
                    >
                        <div className="flex justify-between items-start mb-3">
                            <div className="flex items-center gap-2">
                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${isHovered ? 'bg-cyan-900/20 text-cyan-400 border-cyan-500/30' : 'bg-white/5 text-gray-500 border-white/10'}`}>
                                    {ev.country}
                                </span>
                                <span className="text-[9px] text-gray-600 font-mono flex items-center gap-1">
                                    <Globe size={10} /> {domain}
                                </span>
                            </div>
                            <span className={`text-[10px] font-mono ${isHovered ? 'text-cyan-400' : 'text-gray-600'}`}>
                                {Number(ev.proximity_score).toFixed(2)}
                            </span>
                        </div>

                        <h3 className={`text-sm font-semibold leading-snug mb-3 ${isHovered ? 'text-white' : 'text-gray-400'}`}>
                            {ev.title}
                        </h3>

                        {/* Always show analysis/commentary in list view (specialist inputs) */}
                        <div className={`text-xs overflow-hidden border-l-2 pl-3 ${isHovered ? 'border-cyan-500/50 text-gray-300' : 'border-white/10 text-gray-500'}`}>
                            <p className="line-clamp-3 leading-relaxed italic">
                                "{ev.analysis || "No sufficient data for deep analysis."}"
                            </p>
                        </div>

                        {isHovered && (
                            <div className="mt-3 flex justify-end">
                                <div className="flex items-center gap-1 text-cyan-400 text-[9px] uppercase font-bold tracking-widest animate-pulse">
                                    Read Intelligence <ArrowRight size={10} />
                                </div>
                            </div>
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
};

export default NewsList;

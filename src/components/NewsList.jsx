import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Globe } from 'lucide-react';

const NewsList = ({ events, hoveredId, onHover, onSelect }) => {
    return (
        <div className="flex flex-col gap-2 h-[400px] overflow-y-auto pr-2 custom-scrollbar">
            {events.map((ev) => {
                const isHovered = hoveredId === ev.id;

                return (
                    <motion.div
                        key={ev.id}
                        layoutId={`card-${ev.id}`}
                        onMouseEnter={() => onHover(ev.id)}
                        onMouseLeave={() => onHover(null)}
                        onClick={() => onSelect(ev)}
                        className={`
                            relative p-4 rounded-xl border cursor-pointer transition-all duration-300 group
                            ${isHovered
                                ? 'bg-white/10 border-cyan-500/50 shadow-[0_0_15px_rgba(6,182,212,0.15)]'
                                : 'bg-white/5 border-transparent hover:bg-white/10'
                            }
                        `}
                    >
                        <div className="flex justify-between items-start mb-2">
                            <div className="flex items-center gap-2">
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${isHovered ? 'bg-cyan-500 text-black' : 'bg-white/10 text-gray-400'}`}>
                                    {ev.country}
                                </span>
                            </div>
                            <span className={`text-xs font-mono ${isHovered ? 'text-cyan-400' : 'text-gray-500'}`}>
                                PROX: {ev.proximity_score}
                            </span>
                        </div>

                        <h3 className={`text-sm font-semibold leading-tight mb-2 ${isHovered ? 'text-white' : 'text-gray-300'}`}>
                            {ev.title}
                        </h3>

                        {isHovered && (
                            <motion.div
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="text-xs text-gray-400 overflow-hidden"
                            >
                                <p className="line-clamp-2 mb-2">{ev.analysis}</p>
                                <div className="flex items-center gap-1 text-cyan-400 text-[10px] uppercase font-bold tracking-widest">
                                    Deep Dive <ArrowRight size={12} />
                                </div>
                            </motion.div>
                        )}
                    </motion.div>
                );
            })}
        </div>
    );
};

export default NewsList;

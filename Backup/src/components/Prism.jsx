import React from 'react';
import { motion } from 'framer-motion';
import Bubble from './Bubble';
import { REGIONS } from '../data/mockData';

const Prism = ({ event }) => {
    if (!event) return <div className="flex items-center justify-center h-full text-gray-500">Selecciona un evento</div>;

    const regionKeys = Object.keys(REGIONS);
    const radius = 220; // Distance from center

    return (
        <div className="relative w-full h-[600px] flex items-center justify-center overflow-hidden">
            {/* Central Node: The Neutral Fact */}
            <motion.div
                className="z-20 glass-panel p-6 w-64 text-center z-10"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
            >
                <div className="text-xs text-accent uppercase tracking-widest mb-2">Evento Global</div>
                <h2 className="text-xl font-bold text-white mb-2">{event.title}</h2>
                <div className="w-full bg-gray-700 h-1 mt-2 rounded-full overflow-hidden">
                    <div
                        className="bg-white h-full transition-all duration-1000"
                        style={{ width: `${event.global_convergence}%` }}
                    />
                </div>
                <div className="text-[10px] text-gray-400 mt-1 flex justify-between">
                    <span>Divergencia</span>
                    <span>Convergencia ({event.global_convergence}%)</span>
                </div>
            </motion.div>

            {/* Orbiting Bubbles */}
            {regionKeys.map((key, index) => {
                const region = REGIONS[key];
                const data = event.perspectives[key];
                const angle = (index / regionKeys.length) * 2 * Math.PI - (Math.PI / 2); // Start from top
                const x = Math.cos(angle) * radius;
                const y = Math.sin(angle) * radius;

                return (
                    <div
                        key={key}
                        className="absolute flex items-center justify-center"
                        style={{
                            left: `calc(50% + ${x}px - 90px)`, // 90px is half bubble width
                            top: `calc(50% + ${y}px - 90px)`
                        }}
                    >
                        <Bubble region={region} data={data} />

                        {/* Connection Line (Optional, maybe too messy with glass) */}
                        <svg className="absolute top-1/2 left-1/2 w-[500px] h-[500px] -translate-x-1/2 -translate-y-1/2 pointer-events-none -z-10 opacity-20">
                            <line
                                x1="50%"
                                y1="50%"
                                x2={`${50 + (x / 2.5)}%`} // Draw line towards bubble center
                                y2={`${50 + (y / 2.5)}%`}
                                stroke="white"
                                strokeWidth="1"
                            />
                        </svg>
                    </div>
                );
            })}
        </div>
    );
};

export default Prism;

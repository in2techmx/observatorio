import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { REGIONS, PILLARS } from '../data/mockData';

const Heatmap = () => {
    const [hoveredCell, setHoveredCell] = useState(null);

    // Mock intensity generation (0-10)
    // In a real app, this comes from the "Volume Transregional" calculation
    const getIntensity = (pillar, regionId) => {
        // Hash based on strings to be deterministic but look random
        const val = (pillar.length + regionId.length) % 11;
        return val;
    };

    const getCellColor = (intensity) => {
        // 0 is silence (dark), 10 is bright
        if (intensity < 2) return 'rgba(255, 255, 255, 0.05)'; // Silence
        // Heatmap gradient
        return `rgba(100, 108, 255, ${intensity / 10})`;
    };

    return (
        <div className="w-full h-full p-8 flex flex-col glass-panel">
            <h3 className="text-2xl font-bold mb-6 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
                Mapa de Silencios
            </h3>

            <div className="flex-1 grid gap-2" style={{
                gridTemplateColumns: `auto repeat(${PILLARS.length}, 1fr)`,
                gridTemplateRows: `repeat(${Object.keys(REGIONS).length + 1}, 1fr)`
            }}>
                {/* Header Row */}
                <div className="p-2"></div> {/* Corner */}
                {PILLARS.map(pillar => (
                    <div key={pillar} className="flex items-center justify-center p-2 text-xs font-bold text-gray-400 uppercase tracking-wider">
                        {pillar}
                    </div>
                ))}

                {/* Rows */}
                {Object.keys(REGIONS).map(regionKey => {
                    const region = REGIONS[regionKey];
                    return (
                        <React.Fragment key={regionKey}>
                            {/* Region Label */}
                            <div className="flex items-center justify-start p-2 font-bold text-sm" style={{ color: region.color }}>
                                {region.name}
                            </div>

                            {/* Cells */}
                            {PILLARS.map((pillar, index) => {
                                // Make it dynamic/random for demo
                                const intensity = (getIntensity(pillar, regionKey) + index) % 10;
                                const isSilence = intensity < 3;

                                return (
                                    <motion.div
                                        key={`${regionKey}-${pillar}`}
                                        className="relative rounded-lg cursor-pointer border border-transparent hover:border-white/20"
                                        style={{
                                            background: getCellColor(intensity),
                                            boxShadow: isSilence ? 'none' : `0 0 ${intensity * 2}px ${region.color}40`
                                        }}
                                        whileHover={{ scale: 1.05, zIndex: 10 }}
                                        onMouseEnter={() => setHoveredCell({ region: region.name, pillar, intensity, isSilence })}
                                        onMouseLeave={() => setHoveredCell(null)}
                                    >
                                        {isSilence && (
                                            <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity duration-300">
                                                <span className="text-[10px] text-gray-500 font-mono">SILENCIO</span>
                                            </div>
                                        )}
                                    </motion.div>
                                );
                            })}
                        </React.Fragment>
                    );
                })}
            </div>

            {/* Info Panel / Tooltip Area */}
            <div className="h-24 mt-4 glass-panel p-4 flex items-center justify-center text-center">
                <AnimatePresence mode="wait">
                    {hoveredCell ? (
                        <motion.div
                            key="tooltip"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -10 }}
                            className="text-sm"
                        >
                            <div className="font-bold text-lg mb-1">
                                {hoveredCell.region} <span className="text-gray-500">×</span> {hoveredCell.pillar}
                            </div>
                            {hoveredCell.isSilence ? (
                                <div className="text-red-400 flex items-center gap-2 justify-center">
                                    <span>⚠️ Alerta de Punto Ciego</span>
                                    <span className="text-gray-400 text-xs">Este tema es vital globalmente pero {hoveredCell.region} lo ignora.</span>
                                </div>
                            ) : (
                                <div className="text-blue-300">
                                    Intensidad de Cobertura: {hoveredCell.intensity}/10 — Tema dominante.
                                </div>
                            )}
                        </motion.div>
                    ) : (
                        <motion.div
                            key="default"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 0.5 }}
                            className="text-gray-500 text-sm italic"
                        >
                            Explora la matriz para detectar patrones de silencio.
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
};

export default Heatmap;

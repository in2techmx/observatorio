import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const RadarView = ({ events, hoveredId, onHover }) => {
    const [selectedNodeId, setSelectedNodeId] = useState(null);

    // Canvas config
    const size = 400;
    const center = size / 2;
    const maxRadius = size / 2 - 20;

    // Helper: Map proximity (0-10) to radius (inverse relationship: 10 is center, 0 is edge)
    // Proximity 10 -> r = 0
    // Proximity 0  -> r = maxRadius
    const getCoordinates = (score, index, total) => {
        const radius = maxRadius * (1 - (score / 10)); // 10 score = 0 radius (center)
        const angle = (index * (360 / total) - 90) * (Math.PI / 180); // Spread evenly
        return {
            x: center + radius * Math.cos(angle),
            y: center + radius * Math.sin(angle),
            r: radius
        };
    };

    const selectedEvent = events.find(e => e.id === selectedNodeId);

    return (
        <div className="relative w-[400px] h-[400px] flex items-center justify-center">
            {/* Click background to deselect */}
            <svg
                width={size}
                height={size}
                className="overflow-visible"
                onClick={() => setSelectedNodeId(null)}
            >
                {/* Radar Grid Circles */}
                {[0.2, 0.4, 0.6, 0.8, 1].map((scale, i) => (
                    <circle
                        key={i}
                        cx={center}
                        cy={center}
                        r={maxRadius * scale}
                        fill="none"
                        stroke="white"
                        strokeOpacity={0.05}
                        strokeDasharray="4 4"
                        pointerEvents="none"
                    />
                ))}

                {/* Crosshairs */}
                <line x1={center} y1={0} x2={center} y2={size} stroke="white" strokeOpacity={0.05} pointerEvents="none" />
                <line x1={0} y1={center} x2={size} y2={center} stroke="white" strokeOpacity={0.05} pointerEvents="none" />

                {/* Center Gravity Well */}
                <circle cx={center} cy={center} r={5} fill="#06b6d4" className="animate-pulse" opacity="0.5" pointerEvents="none" />

                {/* Nodes */}
                {events.map((ev, i) => {
                    const coords = getCoordinates(ev.proximity_score, i, events.length);
                    const isHovered = hoveredId === ev.id;
                    const isSelected = selectedNodeId === ev.id;

                    return (
                        <g
                            key={ev.id}
                            onMouseEnter={() => onHover(ev.id)}
                            onMouseLeave={() => onHover(null)}
                            onClick={(e) => {
                                e.stopPropagation();
                                setSelectedNodeId(isSelected ? null : ev.id);
                            }}
                            className="cursor-pointer transition-all duration-300"
                        >
                            {/* Connector Line to Center (optional aesthetic) */}
                            {(isHovered || isSelected) && (
                                <line
                                    x1={center}
                                    y1={center}
                                    x2={coords.x}
                                    y2={coords.y}
                                    stroke="#06b6d4"
                                    strokeWidth="1"
                                    strokeOpacity="0.3"
                                />
                            )}

                            <motion.circle
                                cx={coords.x}
                                cy={coords.y}
                                r={isSelected ? 6 : (isHovered ? 8 : 4)}
                                fill={isSelected ? "#ec4899" : (isHovered ? "#06b6d4" : "white")}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: i * 0.1, type: "spring" }}
                            />

                            {/* Alert Ring for selected */}
                            {isSelected && (
                                <circle
                                    cx={coords.x}
                                    cy={coords.y}
                                    r={10}
                                    fill="none"
                                    stroke="#ec4899"
                                    strokeWidth={2}
                                />
                            )}

                            {/* Proximity Halo for hover */}
                            {isHovered && !isSelected && (
                                <motion.circle
                                    cx={coords.x}
                                    cy={coords.y}
                                    r={12}
                                    fill="transparent"
                                    stroke="#06b6d4"
                                    strokeWidth={1}
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1.5, opacity: 0 }}
                                    transition={{ repeat: Infinity, duration: 1.5 }}
                                />
                            )}
                        </g>
                    );
                })}
            </svg>

            {/* Mini Info Card Overlay */}
            <AnimatePresence>
                {selectedEvent && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/90 border border-cyan-500/30 p-4 rounded-xl z-20 w-max max-w-[250px] text-center backdrop-blur-md shadow-2xl"
                    >
                        <div className="text-[10px] text-gray-500 uppercase tracking-widest mb-1">{selectedEvent.country}</div>
                        <h4 className="text-sm font-bold text-white mb-2 leading-tight">{selectedEvent.title}</h4>
                        <div className="inline-block bg-white/10 px-2 py-0.5 rounded text-[10px] font-mono text-cyan-400">
                            PROX: {selectedEvent.proximity_score}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default RadarView;

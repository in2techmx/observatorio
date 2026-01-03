import React from 'react';
import { motion } from 'framer-motion';

const RadarView = ({ events, hoveredId, onHover }) => {
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

    return (
        <div className="relative w-[400px] h-[400px] flex items-center justify-center">
            <svg width={size} height={size} className="overflow-visible">
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
                    />
                ))}

                {/* Crosshairs */}
                <line x1={center} y1={0} x2={center} y2={size} stroke="white" strokeOpacity={0.05} />
                <line x1={0} y1={center} x2={size} y2={center} stroke="white" strokeOpacity={0.05} />

                {/* Center Gravity Well */}
                <circle cx={center} cy={center} r={5} fill="#06b6d4" className="animate-pulse" opacity="0.5" />

                {/* Nodes */}
                {events.map((ev, i) => {
                    const coords = getCoordinates(ev.proximity_score, i, events.length);
                    const isHovered = hoveredId === ev.id;

                    return (
                        <g
                            key={ev.id}
                            onMouseEnter={() => onHover(ev.id)}
                            onMouseLeave={() => onHover(null)}
                            className="cursor-pointer transition-all duration-300"
                        >
                            {/* Connector Line to Center (optional aesthetic) */}
                            {isHovered && (
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
                                r={isHovered ? 8 : 4}
                                fill={isHovered ? "#06b6d4" : "white"}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: i * 0.1, type: "spring" }}
                            />

                            {/* Proximity Halo */}
                            {isHovered && (
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

            {/* Hover Tooltip Overlay */}
            {/* We can do this in HTML overlay for better text rendering */}
        </div>
    );
};

export default RadarView;

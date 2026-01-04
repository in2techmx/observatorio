import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { REGION_COLORS, REGION_ANGLES } from '../constants/regions';

const RadarView = ({ events, hoveredId, onHover, language = 'EN', onRegionSelect, selectedRegion, selectedNodeId, onNodeSelect }) => {
    // Internal state removed, controlled via props now
    // const [selectedNodeId, setSelectedNodeId] = useState(null);

    // Canvas config
    const size = 400;
    const center = size / 2;
    const maxRadius = size / 2 - 20;

    // Use imported constants for consistent coloring logic
    const regionColors = REGION_COLORS;
    const regionAngles = REGION_ANGLES;

    // Translations

    // Translations
    const t = {
        regions: {
            "NORTEAMERICA": language === 'EN' ? "N. AMERICA" : "N. AMÉRICA",
            "LATINOAMERICA": "LATAM",
            "EUROPA": language === 'EN' ? "EUROPE" : "EUROPA",
            "ASIA_PACIFICO": language === 'EN' ? "ASIA PAC." : "ASIA PAC.",
            "MEDIO_ORIENTE": language === 'EN' ? "M. EAST" : "O. MEDIO",
            "RUSIA_CIS": language === 'EN' ? "RUSSIA" : "RUSIA",
            "AFRICA": language === 'EN' ? "AFRICA" : "ÁFRICA",
            "GLOBAL": "GLOBAL"
        },
        tap: language === 'EN' ? "Tap for details" : "Tocar para ver más",
        unknown: language === 'EN' ? "Unknown Source" : "Fuente Desconocida",
        keywords: language === 'EN' ? "Keywords" : "Claves"
    };

    // PHYSICS ENGINE ----------------
    const [layout, setLayout] = useState([]);

    useEffect(() => {
        if (!events.length) return;

        let nodes = events.map(ev => {
            const baseAngleDeg = regionAngles[ev.region] || regionAngles[ev.country] || (Math.random() * 360);
            const jitter = (Math.random() - 0.5) * 40;
            const angleRad = (baseAngleDeg + jitter) * (Math.PI / 180);
            // Proximity Score (0-10) - ensure numeric
            const score = Number(ev.proximity_score || ev.proximidad || 0);
            const r = maxRadius * (1 - (score / 10));

            return {
                id: ev.id,
                x: center + r * Math.cos(angleRad),
                y: center + r * Math.sin(angleRad),
                r: r,
                angle: angleRad,
                data: ev,
                vx: 0,
                vy: 0
            };
        });

        // Simple Force Simulation
        const iterations = 120;
        const repelStrength = 5;
        const nodeRadius = 8;

        for (let k = 0; k < iterations; k++) {
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const distSq = dx * dx + dy * dy;
                    const minDist = nodeRadius * 2.5;

                    if (distSq < minDist * minDist && distSq > 0) {
                        const dist = Math.sqrt(distSq);
                        const force = (minDist - dist) / dist * repelStrength * 0.1;
                        const fx = dx * force;
                        const fy = dy * force;
                        nodes[i].x += fx;
                        nodes[i].y += fy;
                        nodes[j].x -= fx;
                        nodes[j].y -= fy;
                    }
                }
            }
            // Constrain to Radial Orbit
            for (let i = 0; i < nodes.length; i++) {
                const dx = nodes[i].x - center;
                const dy = nodes[i].y - center;
                const currentAngle = Math.atan2(dy, dx);
                nodes[i].x = center + nodes[i].r * Math.cos(currentAngle);
                nodes[i].y = center + nodes[i].r * Math.sin(currentAngle);
            }
        }
        setLayout(nodes);
    }, [events]);

    const selectedEvent = events.find(e => e.id === selectedNodeId);

    // Bilingual title helper for selected event
    const getSelectedTitle = () => {
        if (!selectedEvent) return "";
        return language === 'EN'
            ? (selectedEvent.titulo_en || selectedEvent.original_title || selectedEvent.title)
            : (selectedEvent.titulo_es || selectedEvent.translated_title || selectedEvent.title);
    };

    return (
        <div className="relative w-full max-w-[400px] aspect-square flex items-center justify-center">
            {/* Click background to deselect */}
            <svg
                viewBox={`0 0 ${size} ${size}`}
                width="100%"
                height="100%"
                className="overflow-visible"
                onClick={() => onNodeSelect(null)} // Deselect on bg click
            >
                {/* 1. TACTICAL GRID LAYER */}
                <defs>
                    <radialGradient id="radarRadial" cx="0.5" cy="0.5" r="0.5">
                        <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.1" />
                        <stop offset="100%" stopColor="#000" stopOpacity="0" />
                    </radialGradient>
                    <filter id="neonGlow">
                        <feGaussianBlur stdDeviation="2.5" result="coloredBlur" />
                        <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                        </feMerge>
                    </filter>
                </defs>

                {/* Background Glow */}
                <circle cx={center} cy={center} r={maxRadius} fill="url(#radarRadial)" opacity="0.4" />

                {/* Radar Scan Animation */}
                <motion.g
                    animate={{ rotate: 360 }}
                    transition={{
                        repeat: Infinity,
                        duration: 8,
                        ease: "linear"
                    }}
                    style={{ originX: "50%", originY: "50%" }}
                >
                    <g opacity="0.5">
                        <path d={`M${center},${center} L${center},0 A${center},${center} 0 0,1 ${size},${center} L${center},${center}`} fill="url(#radarRadial)" opacity="0.2" />
                        <line x1={center} y1={center} x2={center} y2={0} stroke="#22d3ee" strokeWidth="1" />
                    </g>
                </motion.g>

                {/* Concentric Rings (Tactical) */}
                {[0.2, 0.4, 0.6, 0.8, 1].map((scale, i) => (
                    <circle
                        key={i}
                        cx={center}
                        cy={center}
                        r={maxRadius * scale}
                        fill="none"
                        stroke={i === 4 ? "#06b6d4" : "#1e293b"} // Cyan Outer, Slate Inner
                        strokeWidth={i === 4 ? 2 : 1}
                        strokeOpacity={i === 4 ? 1 : 0.4}
                        strokeDasharray={i === 4 ? "0" : "2 2"} // Micro-dashed inner rings
                        filter={i === 4 ? "url(#neonGlow)" : "none"}
                        pointerEvents="none"
                    />
                ))}

                {/* Crosshairs & Ticks */}
                <line x1={center} y1={20} x2={center} y2={size - 20} stroke="#06b6d4" strokeWidth={0.5} strokeOpacity={0.3} pointerEvents="none" />
                <line x1={20} y1={center} x2={size - 20} y2={center} stroke="#06b6d4" strokeWidth={0.5} strokeOpacity={0.3} pointerEvents="none" />

                {/* 45 degree lines */}
                <line x1={center - maxRadius} y1={center - maxRadius} x2={center + maxRadius} y2={center + maxRadius} stroke="#06b6d4" strokeWidth={0.5} strokeOpacity={0.1} />
                <line x1={center + maxRadius} y1={center - maxRadius} x2={center - maxRadius} y2={center + maxRadius} stroke="#06b6d4" strokeWidth={0.5} strokeOpacity={0.1} />


                {/* Region Labels (Perimeter) - CLICKABLE & GLOWING */}
                {Object.entries(regionAngles).map(([region, angle]) => {
                    const labelText = t.regions[region] || region;
                    const hasEvents = events.some(e => e.region === region || e.country === region);
                    if (!hasEvents) return null;

                    const rad = angle * (Math.PI / 180);
                    const labelR = maxRadius + 25; // Push out slightly
                    const x = center + labelR * Math.cos(rad);
                    const y = center + labelR * Math.sin(rad);

                    const isSelected = selectedRegion === region;

                    return (
                        <g key={region} onClick={(e) => {
                            e.stopPropagation();
                            if (onRegionSelect) onRegionSelect(isSelected ? null : region);
                        }} className="cursor-pointer">
                            {/* Connector Line */}
                            <line
                                x1={center + (maxRadius + 5) * Math.cos(rad)}
                                y1={center + (maxRadius + 5) * Math.sin(rad)}
                                x2={center + (maxRadius + 15) * Math.cos(rad)}
                                y2={center + (maxRadius + 15) * Math.sin(rad)}
                                stroke={isSelected ? "#22d3ee" : "#334155"}
                                strokeWidth={isSelected ? 2 : 1}
                            />

                            <text
                                x={x}
                                y={y}
                                fill={isSelected ? "#22d3ee" : regionColors[region]}
                                fontSize={isSelected ? "11" : "9"} // Larger font
                                textAnchor="middle"
                                alignmentBaseline="middle"
                                opacity={isSelected ? "1" : "0.7"}
                                className={`uppercase tracking-widest font-mono font-bold transition-all duration-300 ${isSelected ? 'animate-pulse' : 'hover:opacity-100'}`}
                                style={{
                                    textShadow: isSelected ? "0 0 10px #22d3ee" : "none",
                                    fontFamily: 'Rajdhani'
                                }}
                            >
                                {labelText}
                            </text>
                        </g>

                    );
                })}

                {/* Nodes - NEON ORBS */}
                {layout.map((node, i) => {
                    const { x, y } = node;
                    const ev = node.data;
                    const isHovered = hoveredId === ev.id;
                    const isSelected = selectedNodeId === ev.id;
                    const nodeColor = regionColors[ev.region] || regionColors[ev.country] || "white";

                    return (
                        <g
                            key={ev.id}
                            onMouseEnter={() => onHover(ev.id)}
                            onMouseLeave={() => onHover(null)}
                            onClick={(e) => {
                                e.stopPropagation();
                                onNodeSelect(isSelected ? null : ev.id);
                            }}
                            className="cursor-pointer transition-all duration-300"
                        >
                            {(isHovered || isSelected) && (
                                <line
                                    x1={center}
                                    y1={center}
                                    x2={x}
                                    y2={y}
                                    stroke={nodeColor}
                                    strokeWidth="1"
                                    strokeOpacity="0.8"
                                    strokeDasharray="2 2"
                                />
                            )}

                            {/* Glow halo */}
                            <circle
                                cx={x} cy={y}
                                r={isSelected ? 10 : (isHovered ? 8 : 2)}
                                fill={nodeColor}
                                opacity="0.3"
                                filter="url(#neonGlow)"
                            />

                            <motion.circle
                                cx={x}
                                cy={y}
                                r={isSelected ? 4 : (isHovered ? 5 : 2.5)}
                                fill={isSelected ? "#fff" : nodeColor}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: i * 0.02, type: "spring" }}
                                stroke={isSelected ? nodeColor : "none"}
                                strokeWidth={isSelected ? 2 : 0}
                            />
                        </g>
                    );
                })}
            </svg>

            {/* Mini Info Card Overlay - GLASS TACTICAL */}
            <AnimatePresence>
                {selectedEvent && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.9 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black/80 backdrop-blur-xl border border-white/20 p-4 rounded-none z-20 w-[280px] text-center shadow-[0_0_30px_rgba(0,0,0,0.8)]"
                        style={{
                            borderTop: `2px solid ${regionColors[selectedEvent.region]}`,
                            clipPath: "polygon(0 0, 100% 0, 100% 90%, 95% 100%, 0 100%)" // Tactical Shape
                        }}
                    >
                        <div className="flex justify-between items-center mb-2 border-b border-white/10 pb-2">
                            <span className="text-[10px] font-bold uppercase tracking-widest font-mono" style={{ color: regionColors[selectedEvent.region] }}>
                                {t.regions[selectedEvent.region] || selectedEvent.region}
                            </span>
                            <span className="text-[9px] text-gray-400 font-mono">
                                ID: {selectedEvent.id.toString().slice(-4)}
                            </span>
                        </div>
                        <h4 className="text-sm font-bold text-white mb-2 leading-tight text-left font-sans">
                            {getSelectedTitle()}
                        </h4>

                        <div className="flex justify-between items-center mt-2">
                            <span className="text-[9px] text-cyan-500 font-mono animate-pulse">
                                ● LIVE SATELLITE
                            </span>
                            <span className="text-[9px] text-gray-500 font-mono cursor-pointer border-b border-dotted border-gray-600">
                                {t.tap}
                            </span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default RadarView;

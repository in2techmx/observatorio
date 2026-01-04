import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const RadarView = ({ events, hoveredId, onHover, language = 'EN', onRegionSelect, selectedRegion }) => {
    const [selectedNodeId, setSelectedNodeId] = useState(null);

    // Canvas config
    const size = 400;
    const center = size / 2;
    const maxRadius = size / 2 - 20;

    // Regional Color Palette
    const regionColors = {
        "USA": "#3b82f6",     // Blue
        "RUSSIA": "#ef4444",  // Red
        "CHINA": "#eab308",   // Yellow
        "EUROPE": "#8b5cf6",  // Purple
        "MID_EAST": "#f97316",// Orange
        "LATAM": "#10b981",   // Green
        "AFRICA": "#14b8a6",  // Teal
        "INDIA": "#f43f5e",   // Rose
        "GLOBAL": "#9ca3af"   // Gray
    };

    const regionAngles = {
        "USA": 30,
        "LATAM": 90,
        "EUROPE": 150,
        "RUSSIA": 210,
        "CHINA": 270,
        "MID_EAST": 330,
        "AFRICA": 120,
        "INDIA": 300,
        "GLOBAL": 0
    };

    // Translations
    const t = {
        regions: {
            "USA": language === 'EN' ? "USA" : "EE.UU",
            "RUSSIA": language === 'EN' ? "RUSSIA" : "RUSIA",
            "CHINA": "CHINA",
            "EUROPE": language === 'EN' ? "EUROPE" : "EUROPA",
            "MID_EAST": language === 'EN' ? "M. EAST" : "O. MEDIO",
            "LATAM": "LATAM",
            "AFRICA": language === 'EN' ? "AFRICA" : "ÁFRICA",
            "INDIA": "INDIA",
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
            const baseAngleDeg = regionAngles[ev.country] || regionAngles[ev.region] || (Math.random() * 360);
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
                onClick={() => setSelectedNodeId(null)}
            >
                {/* Radar Grid Circles - MAX Visibility */}
                {[0.2, 0.4, 0.6, 0.8, 1].map((scale, i) => (
                    <circle
                        key={i}
                        cx={center}
                        cy={center}
                        r={maxRadius * scale}
                        fill="none"
                        stroke={i === 4 ? "#06b6d4" : "#333"} // Outer ring cyan, inner rings dark gray/white
                        strokeWidth={i === 4 ? 2 : 1}
                        strokeOpacity={i === 4 ? 1 : 0.5} // High contrast
                        strokeDasharray={i === 4 ? "0" : "4 4"}
                        pointerEvents="none"
                    />
                ))}

                {/* Crosshairs - High Visibility */}
                <line x1={center} y1={0} x2={center} y2={size} stroke="#333" strokeWidth={1} strokeOpacity={0.5} pointerEvents="none" />
                <line x1={0} y1={center} x2={size} y2={center} stroke="#333" strokeWidth={1} strokeOpacity={0.5} pointerEvents="none" />

                {/* Region Labels (Perimeter) - CLICKABLE */}
                {Object.entries(regionAngles).map(([region, angle]) => {
                    const labelText = t.regions[region] || region;
                    // Check if region has data
                    const hasEvents = events.some(e => e.country === region);
                    if (!hasEvents) return null;

                    const rad = angle * (Math.PI / 180);
                    const labelR = maxRadius + 20;
                    const x = center + labelR * Math.cos(rad);
                    const y = center + labelR * Math.sin(rad);

                    const isSelected = selectedRegion === region;

                    return (
                        <text
                            key={region}
                            x={x}
                            y={y}
                            fill={isSelected ? "#22d3ee" : regionColors[region]}
                            fontSize={isSelected ? "10" : "8"}
                            textAnchor="middle"
                            alignmentBaseline="middle"
                            opacity={isSelected ? "1" : "0.7"}
                            className="uppercase tracking-widest font-mono font-bold cursor-pointer transition-all duration-300 hover:opacity-100"
                            onClick={(e) => {
                                e.stopPropagation();
                                if (onRegionSelect) onRegionSelect(isSelected ? null : region);
                            }}
                            style={{ filter: isSelected ? "drop-shadow(0 0 5px cyan)" : "none" }}
                        >
                            {labelText}
                        </text>
                    );
                })}

                {/* Center Gravity Well */}
                <circle cx={center} cy={center} r={5} fill="#06b6d4" className="animate-pulse" opacity="0.8" pointerEvents="none" />

                {/* Nodes */}
                {layout.map((node, i) => {
                    const { x, y } = node;
                    const ev = node.data;
                    const isHovered = hoveredId === ev.id;
                    const isSelected = selectedNodeId === ev.id;
                    const nodeColor = regionColors[ev.country] || "white";

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
                            {(isHovered || isSelected) && (
                                <line
                                    x1={center}
                                    y1={center}
                                    x2={x}
                                    y2={y}
                                    stroke={nodeColor}
                                    strokeWidth="1"
                                    strokeOpacity="0.5"
                                />
                            )}
                            <motion.circle
                                cx={x}
                                cy={y}
                                r={isSelected ? 6 : (isHovered ? 8 : 4)}
                                fill={isSelected ? nodeColor : (isHovered ? nodeColor : nodeColor)}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: i * 0.05, type: "spring" }}
                            />
                            {isSelected && (
                                <circle
                                    cx={x}
                                    cy={y}
                                    r={10}
                                    fill="none"
                                    stroke={nodeColor}
                                    strokeWidth={2}
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
                        className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-black border border-white/20 p-4 rounded-xl z-20 w-[280px] text-center shadow-2xl"
                        style={{ borderColor: regionColors[selectedEvent.country] }}
                    >
                        <div className="flex justify-between items-center mb-2 border-b border-white/10 pb-2">
                            <span className="text-[10px] font-bold uppercase tracking-widest" style={{ color: regionColors[selectedEvent.country] }}>
                                {t.regions[selectedEvent.country] || selectedEvent.country}
                            </span>
                            <span className="text-[10px] text-gray-400 font-mono">
                                {selectedEvent.source_url ? new URL(selectedEvent.source_url).hostname.replace('www.', '') : t.unknown}
                            </span>
                        </div>
                        <h4 className="text-sm font-bold text-white mb-2 leading-tight text-left">
                            {getSelectedTitle()}
                        </h4>

                        <p className="text-[10px] text-gray-400 text-left mb-3 line-clamp-3 leading-relaxed">
                            {selectedEvent.analysis
                                ? selectedEvent.analysis
                                : (selectedEvent.keywords && selectedEvent.keywords.length > 0)
                                    ? `${t.keywords}: ${selectedEvent.keywords.join(', ')}`
                                    : (selectedEvent.snippet || "")
                            }
                        </p>

                        <div className="flex justify-between items-center mt-2">
                            <div className="inline-block bg-white/10 px-2 py-0.5 rounded text-[10px] font-mono" style={{ color: regionColors[selectedEvent.country] }}>
                                PROX: {Number(selectedEvent.proximity_score || selectedEvent.proximidad || 0).toFixed(2)}
                            </div>
                            <span className="text-[9px] text-gray-500">{t.tap}</span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default RadarView;

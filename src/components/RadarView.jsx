import React, { useState, useEffect } from 'react';
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
    // PHYSICS ENGINE ----------------
    const [layout, setLayout] = useState([]);

    // 1. Initialize Layout with calculated positions
    // This runs whenever 'events' changes. We calculate the target "ideal" position
    // based strictly on proximity (radius) and region (angle).
    useEffect(() => {
        if (!events.length) return;

        const regionAngles = {
            "USA": 30, // Top Right
            "LATAM": 90, // Bottom Right
            "EUROPE": 150, // Bottom Left
            "RUSSIA": 210, // Left
            "CHINA": 270, // Top Left
            "MID_EAST": 330, // Top
            "AFRICA": 120,
            "INDIA": 300,
            "GLOBAL": 0
        };

        // Initial placement with Jitter
        let nodes = events.map(ev => {
            const baseAngleDeg = regionAngles[ev.country] || regionAngles[ev.region] || (Math.random() * 360);
            const jitter = (Math.random() - 0.5) * 40; // +/- 20 degrees jitter
            const angleRad = (baseAngleDeg + jitter) * (Math.PI / 180);

            // STRICT RADIUS: Derived from Proximity Score (0-10) -> NOW 0-10 (from App.jsx) or 0-100?
            // App.jsx divides by 10. So ev.proximity_score is 0-10.
            // If Collector outputs 0-100.
            // Let's rely on Proximity Score being 0-10.
            // If Proximity is 0 (Divergent) -> Radius Max.
            // If Proximity is 10 (Core) -> Radius 0.

            // Fix: Check if range is 0-10 or 0-100. 
            // Collector exports 0-100. App.jsx divides by 10. So it is 0-10.
            // BUT, if score was small (e.g. 1.5%), App.jsx gave 0.15.
            // Radius = maxRadius * (1 - 0.015). Almost max.

            // Visual Fix: Spread them out more. 
            // Instead of linear 1-score/10, let's use a non-linear visual spread?
            // No, backend already did cubic. Let's trust the backend score.

            const r = maxRadius * (1 - (ev.proximity_score / 10));

            return {
                id: ev.id,
                x: center + r * Math.cos(angleRad),
                y: center + r * Math.sin(angleRad),
                r: r, // Target radius
                angle: angleRad,
                data: ev,
                vx: 0,
                vy: 0
            };
        });

        // 2. Simple Force Simulation (Iterative Solver)
        // We run a fixed number of iterations to "relax" the layout immediately
        // preventing visual jitter during render.
        const iterations = 120;
        const repelStrength = 5;
        const nodeRadius = 8; // Assumed visual size

        for (let k = 0; k < iterations; k++) {
            // A. Apply Repulsion (Collision Avoidance)
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const dx = nodes[i].x - nodes[j].x;
                    const dy = nodes[i].y - nodes[j].y;
                    const distSq = dx * dx + dy * dy;
                    const minDist = nodeRadius * 2.5; // Minimum separate distance

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

            // B. Constrain to Radial Orbit (The "Gravity" of the Logic)
            // Nodes must stay at their specific 'r' distance from center.
            // We project them back onto their specific radius circle.
            for (let i = 0; i < nodes.length; i++) {
                const dx = nodes[i].x - center;
                const dy = nodes[i].y - center;
                const currentAngle = Math.atan2(dy, dx);

                // Strict adherence to calculated proximity radius
                nodes[i].x = center + nodes[i].r * Math.cos(currentAngle);
                nodes[i].y = center + nodes[i].r * Math.sin(currentAngle);
            }
        }

        setLayout(nodes);
    }, [events]);

    const selectedEvent = events.find(e => e.id === selectedNodeId);

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
                {/* Radar Grid Circles */}
                {[0.2, 0.4, 0.6, 0.8, 1].map((scale, i) => (
                    <circle
                        key={i}
                        cx={center}
                        cy={center}
                        r={maxRadius * scale}
                        fill="none"
                        stroke="white"
                        strokeOpacity={0.15} // Increased opacity from 0.05
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
                {layout.map((node, i) => {
                    // Coordinates come from our physics engine now
                    const { x, y } = node;
                    const ev = node.data;
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
                                    x2={x}
                                    y2={y}
                                    stroke="#06b6d4"
                                    strokeWidth="1"
                                    strokeOpacity="0.3"
                                />
                            )}

                            <motion.circle
                                cx={x}
                                cy={y}
                                r={isSelected ? 6 : (isHovered ? 8 : 4)}
                                fill={isSelected ? "#ec4899" : (isHovered ? "#06b6d4" : "white")}
                                initial={{ scale: 0, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                transition={{ delay: i * 0.1, type: "spring" }}
                            />

                            {/* Alert Ring for selected */}
                            {isSelected && (
                                <circle
                                    cx={x}
                                    cy={y}
                                    r={10}
                                    fill="none"
                                    stroke="#ec4899"
                                    strokeWidth={2}
                                />
                            )}

                            {/* Proximity Halo for hover */}
                            {isHovered && !isSelected && (
                                <motion.circle
                                    cx={x}
                                    cy={y}
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

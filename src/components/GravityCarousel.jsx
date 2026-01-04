import React, { useEffect, useRef, useState } from 'react';
import { motion, useAnimationFrame, useMotionValue, useTransform, wrap, useMotionValueEvent } from 'framer-motion';

const GravityCarousel = ({ categories, selectedCategory, onSelect, language = 'EN', categoryTranslations }) => {
    // 1. Metric Config
    const CARD_WIDTH = 260;
    const GAP = 32; // gap-8
    const ITEM_WIDTH = CARD_WIDTH + GAP;
    const TOTAL_WIDTH = categories.length * ITEM_WIDTH;

    // 2. Motion Setup
    const containerRef = useRef(null);
    const x = useMotionValue(0);
    const [isHovered, setIsHovered] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // Dictionaries
    const uiText = {
        center: language === 'EN' ? 'CENTER' : 'CENTRO',
        perimeter: language === 'EN' ? 'PERIMETER' : 'PERÍMETRO',
        drag: language === 'EN' ? 'DRAG TO SCAN' : 'DESLIZA PARA EXPLORAR'
    };

    // 3. Animation Loop
    useAnimationFrame((t, delta) => {
        if (!isHovered && !isDragging) {
            // Speed of auto-scroll - SLOWER per request
            const moveBy = -0.02 * delta;
            x.set(x.get() + moveBy);
        }

        // Seamless loop logic for direct x motion value
        const currentX = x.get();
        const minX = -TOTAL_WIDTH;
        const maxX = 0;

        if (currentX < minX) {
            x.set(currentX + TOTAL_WIDTH);
        } else if (currentX > maxX) {
            x.set(currentX - TOTAL_WIDTH);
        }
    });

    return (
        <div
            className="w-full overflow-hidden py-8 relative cursor-grab active:cursor-grabbing group"
            ref={containerRef}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* UI Tech Decals */}
            <div className="absolute top-2 left-0 w-full flex justify-between px-12 pointer-events-none opacity-40">
                <span className="text-[10px] font-mono text-cyan-500 tracking-[0.2em]">{uiText.perimeter}</span>
                <span className="text-[10px] font-mono text-cyan-500 tracking-[0.2em]">{uiText.center}</span>
                <span className="text-[10px] font-mono text-cyan-500 tracking-[0.2em]">{uiText.perimeter}</span>
            </div>

            {/* Draggable Track */}
            <motion.div
                className="flex items-center gap-8 pl-[50vw]"
                style={{ x }}
                drag="x"
                dragConstraints={{ left: -TOTAL_WIDTH * 2, right: TOTAL_WIDTH }}
                onDragStart={() => setIsDragging(true)}
                onDragEnd={() => setIsDragging(false)}
            >
                {/* Loop 3 times for seamless infinite feel */}
                {[...categories, ...categories, ...categories].map((cat, i) => {
                    const isSelected = selectedCategory === cat;
                    // Color Logic
                    const colorMap = {
                        "Seguridad y Conflictos": "#ef4444",
                        "Economía y Sanciones": "#3b82f6",
                        "Energía y Recursos": "#10b981",
                        "Soberanía y Alianzas": "#f59e0b",
                        "Tecnología y Espacio": "#8b5cf6",
                        "Sociedad y Derechos": "#ec4899"
                    };
                    const color = colorMap[cat] || "#fff";

                    // Translation
                    const displayName = categoryTranslations?.[cat]?.[language.toLowerCase()] || cat;

                    return (
                        <motion.div
                            key={`${cat}-${i}`}
                            onClick={() => !isDragging && onSelect(cat)}
                            whileHover={{ scale: 1.05, filter: "brightness(1.2)" }}
                            className={`
                                relative flex-shrink-0 w-[280px] h-[180px] rounded-xl 
                                border transition-all duration-500 group overflow-hidden
                                backdrop-blur-md select-none flex flex-col items-center justify-center
                                ${isSelected
                                    ? 'z-20 bg-black/80 border-cyan-400 shadow-[0_0_50px_rgba(34,211,238,0.3)]'
                                    : 'bg-white/5 border-white/10 hover:border-cyan-500/50 hover:bg-black/40 hover:shadow-[0_0_30px_rgba(6,182,212,0.15)]'
                                }
                            `}
                        >
                            {/* Neon Glow Gradient Backend */}
                            <div className={`absolute inset-0 bg-gradient-to-br from-${isSelected ? 'cyan-500/20' : 'transparent'} to-transparent opacity-50`} />

                            {/* Card Content */}
                            <div className="relative z-10 p-6 text-center">
                                {/* Decorative Icon Line */}
                                <div className="w-[1px] h-8 bg-gradient-to-b from-transparent via-cyan-500 to-transparent mx-auto mb-4 opacity-50"></div>

                                <h3 className={`font-black text-2xl uppercase tracking-tighter leading-none mb-2 ${isSelected ? 'text-white drop-shadow-[0_0_10px_rgba(255,255,255,0.8)]' : 'text-gray-400 group-hover:text-white'}`}>
                                    {displayName}
                                </h3>

                                {isSelected && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="text-[10px] font-mono text-cyan-400 tracking-[0.3em] font-bold"
                                    >
                                        // SIGNAL_LOCKED
                                    </motion.div>
                                )}
                            </div>

                            {/* Tech Borders */}
                            <div className={`absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-0 transition-opacity duration-500 ${isSelected ? 'opacity-100' : 'group-hover:opacity-50'}`}></div>
                            <div className={`absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-0 transition-opacity duration-500 ${isSelected ? 'opacity-100' : 'group-hover:opacity-50'}`}></div>

                            {/* Corner Accents */}
                            <div className="absolute top-2 left-2 w-2 h-2 border-t border-l border-white/30"></div>
                            <div className="absolute top-2 right-2 w-2 h-2 border-t border-r border-white/30"></div>
                            <div className="absolute bottom-2 left-2 w-2 h-2 border-b border-l border-white/30"></div>
                            <div className="absolute bottom-2 right-2 w-2 h-2 border-b border-r border-white/30"></div>
                        </motion.div>
                    );
                })}
            </motion.div>

            {/* Hint */}
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-[9px] text-gray-600 font-mono tracking-widest pointer-events-none">
                [{uiText.drag}]
            </div>
        </div>
    );
};

export default GravityCarousel;

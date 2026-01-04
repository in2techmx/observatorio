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
                            whileHover={{ scale: 1.05, filter: "brightness(1.5)" }}
                            className={`
                                relative flex-shrink-0 w-[260px] h-[160px] rounded-xl 
                                border-2 transition-all duration-300 group overflow-hidden
                                backdrop-blur-xl select-none
                                ${isSelected
                                    ? 'scale-110 border-white shadow-[0_0_60px_rgba(255,255,255,0.4)] z-10 bg-black'
                                    : 'opacity-100 bg-white/5 border-white/20 hover:border-white/60 hover:shadow-[0_0_30px_rgba(255,255,255,0.1)]'
                                }
                            `}
                            style={{
                                borderColor: isSelected ? color : (isSelected ? 'white' : 'rgba(255,255,255,0.2)'),
                                boxShadow: isSelected ? `0 0 50px ${color}80` : 'none'
                            }}
                        >
                            {/* Card Content */}
                            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                                {/* Icon/Graphic placeholder */}
                                <div className={`w-2 h-2 rounded-full mb-3 shadow-[0_0_10px_currentColor]`} style={{ color }}></div>

                                <h3 className={`font-black text-lg uppercase tracking-tight leading-tight ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                                    {displayName}
                                </h3>

                                {isSelected && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="mt-2 text-[10px] font-mono text-cyan-400 tracking-widest bg-black/50 px-2 py-1 rounded"
                                    >
                                        ACTIVE FEED
                                    </motion.div>
                                )}
                            </div>

                            {/* Tech Lines */}
                            <div className="absolute top-2 right-2 w-4 h-[1px] bg-white/30"></div>
                            <div className="absolute bottom-2 left-2 w-4 h-[1px] bg-white/30"></div>
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

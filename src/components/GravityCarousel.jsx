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
            ref={containerRef}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            // Fade Mask: Desktop only (md:mask-image). Mobile is full width.
            className="w-full overflow-hidden py-8 relative cursor-grab active:cursor-grabbing group md:[mask-image:linear-gradient(to_right,transparent_0%,black_10%,black_90%,transparent_100%)]"
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
                {[...categories, ...categories, ...categories].map((catItem, i) => {
                    // catItem is now { name: "Category Name", count: 12 }
                    const catName = catItem.name;
                    const catCount = catItem.count || 0;

                    const isSelected = selectedCategory === catName;

                    // Distinct Color Logic - EXPANDED PALETTE
                    const colorMap = {
                        "Seguridad y Conflictos": "#ef4444",      // Red-500
                        "Economía y Sanciones": "#3b82f6",        // Blue-500
                        "Energía y Recursos": "#10b981",          // Emerald-500
                        "Soberanía y Alianzas": "#f59e0b",        // Amber-500
                        "Tecnología y Espacio": "#8b5cf6",        // Violet-500
                        "Sociedad y Derechos": "#ec4899",         // Pink-500
                        "Desconocido": "#64748b"                  // Slate-500
                    };
                    const color = colorMap[catName] || "#fff";

                    // Translation
                    const displayName = categoryTranslations?.[catName]?.[language.toLowerCase()] || catName;

                    return (
                        <motion.div
                            key={`${catName}-${i}`}
                            onClick={() => !isDragging && onSelect(catName)}
                            whileHover={{ scale: 1.05, filter: "brightness(1.2)" }}
                            className={`
                                relative flex-shrink-0 w-[280px] h-[180px] rounded-xl 
                                border transition-all duration-500 group overflow-hidden
                                backdrop-blur-md select-none flex flex-col items-center justify-center
                                ${isSelected
                                    ? 'z-20 bg-black/90 border-transparent' // Border handled by style
                                    : 'bg-white/5 border-white/10 hover:bg-black/40'
                                }
                            `}
                            style={{
                                borderColor: isSelected ? color : undefined,
                                boxShadow: isSelected ? `0 0 40px ${color}60` : undefined
                            }}
                        >
                            {/* Neon Glow Gradient Backend - DYNAMIC COLOR */}
                            <div className="absolute inset-0 opacity-20" style={{ background: `linear-gradient(to bottom right, ${color}, transparent)` }} />

                            {/* Card Content */}
                            <div className="relative z-10 p-6 text-center w-full">
                                {/* Decorative Icon Line */}
                                <div className="w-[1px] h-8 bg-gradient-to-b from-transparent to-transparent mx-auto mb-4 opacity-80"
                                    style={{ backgroundImage: `linear-gradient(to bottom, transparent, ${color}, transparent)` }}
                                ></div>

                                <h3 className={`font-black text-2xl uppercase tracking-tighter leading-none mb-3 ${isSelected ? 'text-white' : 'text-gray-400 group-hover:text-white'}`}
                                    style={{ textShadow: isSelected ? `0 0 20px ${color}80` : 'none' }}
                                >
                                    {displayName}
                                </h3>

                                {/* Signal Count Badge */}
                                <div className="inline-flex items-center gap-2 px-2 py-1 rounded border border-white/10 bg-black/40 backdrop-blur-sm">
                                    <div className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: color }}></div>
                                    <span className="text-[10px] font-mono tracking-widest text-gray-300">
                                        {catCount} {language === 'EN' ? 'SIGNALS' : 'SEÑALES'}
                                    </span>
                                </div>

                                {isSelected && (
                                    <motion.div
                                        layoutId="activeTab"
                                        className="mt-4 text-[9px] font-mono tracking-[0.3em] font-bold absolute bottom-2 left-0 right-0"
                                        style={{ color: color }}
                                    >
                                        // LOCKED
                                    </motion.div>
                                )}
                            </div>

                            {/* Tech Borders - DYNAMIC COLOR */}
                            <div className="absolute top-0 left-0 w-full h-[2px] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                                style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
                            />
                            <div className="absolute bottom-0 left-0 w-full h-[2px] opacity-0 transition-opacity duration-500 group-hover:opacity-100"
                                style={{ background: `linear-gradient(90deg, transparent, ${color}, transparent)` }}
                            />

                            {/* Corner Accents */}
                            <div className="absolute top-2 left-2 w-2 h-2 border-t border-l border-white/30"></div>
                            <div className="absolute top-2 right-2 w-2 h-2 border-t border-r border-white/30"></div>
                            <div className="absolute bottom-2 left-2 w-2 h-2 border-b border-l border-white/30"></div>
                            <div className="absolute bottom-2 right-2 w-2 h-2 border-b border-r border-white/30"></div>
                        </motion.div>
                    );
                })}
            </motion.div>

        </div>
    );
};

export default GravityCarousel;

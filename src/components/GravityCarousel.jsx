import React, { useEffect, useRef, useState } from 'react';
import { motion, useAnimationFrame, useMotionValue, useTransform, wrap } from 'framer-motion';

const GravityCarousel = ({ categories, selectedCategory, onSelect }) => {
    // 1. Neon Colors
    const neonColors = ["cyan", "fuchsia", "violet", "lime", "rose", "emerald", "amber"];
    const getCategoryColor = (index) => {
        const colorName = neonColors[index % neonColors.length];
        const map = {
            "cyan": "rgb(34, 211, 238)",
            "fuchsia": "rgb(232, 121, 249)",
            "violet": "rgb(167, 139, 250)",
            "lime": "rgb(190, 242, 100)",
            "rose": "rgb(251, 113, 133)",
            "emerald": "rgb(52, 211, 153)",
            "amber": "rgb(251, 191, 36)"
        };
        return map[colorName];
    };

    // 2. Metric Config
    const CARD_WIDTH = 260;
    const GAP = 32; // gap-8
    const ITEM_WIDTH = CARD_WIDTH + GAP;
    const TOTAL_WIDTH = categories.length * ITEM_WIDTH;

    // 3. Motion Setup
    const baseX = useMotionValue(0);
    const [isHovered, setIsHovered] = useState(false);
    const [isDragging, setIsDragging] = useState(false);

    // 4. Animation Loop
    useAnimationFrame((t, delta) => {
        if (!isHovered && !isDragging) {
            // Speed of auto-scroll - SLOWER per request
            const moveBy = -0.02 * delta;
            baseX.set(baseX.get() + moveBy);
        }
    });

    // 5. Seamless Loop Logic
    const x = useTransform(baseX, v => {
        return `${((v % TOTAL_WIDTH) - TOTAL_WIDTH) % TOTAL_WIDTH}px`;
    });

    const handleDragStart = () => setIsDragging(true);
    const handleDragEnd = () => setIsDragging(false);

    return (
        <div
            className="relative w-full overflow-hidden py-8 bg-black/90 border-b border-white/5 z-30"
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
        >
            {/* Fade Edges */}
            <div className="absolute top-0 left-0 h-full w-32 bg-gradient-to-r from-black via-black/80 to-transparent z-10 pointer-events-none" />
            <div className="absolute top-0 right-0 h-full w-32 bg-gradient-to-l from-black via-black/80 to-transparent z-10 pointer-events-none" />

            {/* Note: User asked to leave initial explanation, which is in LandingHero. 
                But if we need space here, we can remove the "Select Sector" pulse text if redundant. 
                Keeping straightforward layout. */}

            {/* Draggable Track */}
            <motion.div
                className="flex gap-8 px-8 items-center cursor-grab active:cursor-grabbing"
                style={{ x, width: TOTAL_WIDTH * 3 }}
                drag="x"
                dragConstraints={{ left: -TOTAL_WIDTH * 2, right: 0 }}
                onDragStart={handleDragStart}
                onDragEnd={handleDragEnd}
                onDrag={(event, info) => {
                    baseX.set(baseX.get() + info.delta.x);
                }}
            >
                {/* Render 3 Sets for infinite illusion */}
                {[...categories, ...categories, ...categories].map((cat, index) => {
                    const uniqueKey = `cat-${index}`;
                    const originalIndex = index % categories.length;
                    const isSelected = selectedCategory === cat.name;
                    const color = getCategoryColor(originalIndex);

                    return (
                        <motion.div
                            key={uniqueKey}
                            onClick={() => !isDragging && onSelect(cat.name)}
                            whileHover={{ scale: 1.05, filter: "brightness(1.5)" }}
                            className={`
                                relative flex-shrink-0 w-[260px] h-[160px] rounded-xl 
                                border-2 transition-all duration-300 group overflow-hidden
                                backdrop-blur-xl select-none
                                ${isSelected
                                    ? 'scale-110 border-white shadow-[0_0_60px_rgba(255,255,255,0.4)] z-10 bg-black' // Stronger selected glow
                                    : 'opacity-100 bg-white/5 border-white/20 hover:border-white/60 hover:shadow-[0_0_30px_rgba(255,255,255,0.1)]' // Clearer glass effect
                                }
                            `}
                            style={{
                                borderColor: isSelected ? color : (isSelected ? 'white' : 'rgba(255,255,255,0.2)'),
                                boxShadow: isSelected ? `0 0 50px ${color}80` : 'none' // Enhanced color glow
                            }}
                        >
                            {/* Visual Effects */}
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-30" />
                            <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-90" />

                            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center z-10">
                                <div
                                    className="w-2 h-2 rounded-full mb-3 shadow-[0_0_15px_currentColor]"
                                    style={{ backgroundColor: color, boxShadow: `0 0 20px ${color}` }}
                                />
                                <h3
                                    className="text-xl font-black uppercase tracking-wider leading-none"
                                    style={{
                                        color: isSelected ? 'white' : '#e5e7eb',
                                        textShadow: isSelected ? `0 0 25px ${color}` : '0 0 10px rgba(0,0,0,0.8)'
                                    }}
                                >
                                    {cat.name}
                                </h3>
                                <span className={`text-[10px] mt-2 font-mono tracking-widest ${isSelected ? 'text-white' : 'text-gray-400'}`}>
                                    {cat.count} NODES
                                </span>
                            </div>

                            {isSelected && (
                                <motion.div
                                    layoutId="activeBar"
                                    className="absolute bottom-0 left-0 w-full h-1"
                                    style={{ backgroundColor: color, boxShadow: `0 0 20px ${color}` }}
                                />
                            )}
                        </motion.div>
                    );
                })}
            </motion.div>
        </div>
    );
};

export default GravityCarousel;

import React, { useEffect, useRef, useState } from 'react';
import { motion, useAnimation, useMotionValue } from 'framer-motion';

const GravityCarousel = ({ categories, selectedCategory, onSelect }) => {
    // Generate distinct neon colors for sections if not passed via props
    const neonColors = [
        "cyan", "fuchsia", "violet", "lime", "rose", "emerald", "amber"
    ];

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

    return (
        <div className="relative w-full overflow-hidden py-8 bg-black/90 border-b border-white/5 z-30">
            {/* Fade Edges */}
            <div className="absolute top-0 left-0 h-full w-24 bg-gradient-to-r from-black to-transparent z-10 pointer-events-none" />
            <div className="absolute top-0 right-0 h-full w-24 bg-gradient-to-l from-black to-transparent z-10 pointer-events-none" />

            <div className="flex items-center justify-center mb-6">
                <h3 className="text-[10px] uppercase tracking-[0.4em] text-gray-500 animate-pulse">Select Sector to Decrypt</h3>
            </div>

            {/* Scroll Container - Auto-roll implemented via CSS animation in index.css if needed, 
                but for now we depend on the user manual scroll or we add a ticker effect.
                User asked for "auto-roll slow". Let's try a CSS ticker approach or just allow manual for interaction.
                Actually, a slow JS auto-scroll is better for "Netflix style" which usually is static until interaction.
                But user explicitly said "auto-roll despacio". 
                
                Let's use a marquee animation container.
            */}
            <div className="relative flex overflow-x-hidden group">
                {/* Rolling Track */}
                <motion.div
                    className="flex gap-8 px-8 items-center"
                    animate={{ x: [0, -1000] }} // Simple infinite scroll logic requires duplicating items
                    transition={{
                        x: { repeat: Infinity, duration: 60, ease: "linear" }
                    }}
                    // Pause on hover
                    whileHover={{ animationPlayState: "paused" }}
                    style={{ minWidth: "200%" }}
                >
                    {/* Render Double for infinite loop illusion */}
                    {[...categories, ...categories].map((cat, index) => {
                        const isSelected = selectedCategory === cat.name;
                        const color = getCategoryColor(index % categories.length);
                        // Make unique key for duplicates
                        const uniqueKey = `${cat.name}-${index}`;

                        return (
                            <motion.div
                                key={uniqueKey}
                                onClick={() => onSelect(cat.name)}
                                whileHover={{ scale: 1.05, filter: "brightness(1.2)" }}
                                className={`
                                    relative flex-shrink-0 w-[260px] h-[150px] rounded-xl cursor-pointer 
                                    border transition-all duration-500 group overflow-hidden
                                    backdrop-blur-sm
                                    ${isSelected
                                        ? 'scale-110 border-white shadow-[0_0_40px_rgba(255,255,255,0.1)] z-10 bg-black'
                                        : 'opacity-70 grayscale hover:grayscale-0 hover:opacity-100 bg-zinc-900/30 border-white/10'
                                    }
                                `}
                                style={{
                                    borderColor: isSelected ? color : 'rgba(255,255,255,0.1)',
                                    boxShadow: isSelected ? `0 0 30px ${color}40` : 'none'
                                }}
                            >
                                {/* Scanline Effect */}
                                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20" />
                                <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-80" />

                                {/* Content */}
                                <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center z-10">
                                    <div
                                        className="w-1.5 h-1.5 rounded-full mb-3 shadow-[0_0_10px_currentColor]"
                                        style={{ backgroundColor: color, boxShadow: `0 0 15px ${color}` }}
                                    />
                                    <h3
                                        className="text-lg font-bold uppercase tracking-wider leading-none"
                                        style={{
                                            color: isSelected ? 'white' : 'gray',
                                            textShadow: isSelected ? `0 0 20px ${color}` : 'none'
                                        }}
                                    >
                                        {cat.name}
                                    </h3>
                                    <span className="text-[9px] mt-2 font-mono text-gray-500 tracking-widest">
                                        {cat.count} NODES
                                    </span>
                                </div>

                                {/* Active Indicator Bar */}
                                {isSelected && (
                                    <motion.div
                                        layoutId="activeBar"
                                        className="absolute bottom-0 left-0 w-full h-0.5"
                                        style={{ backgroundColor: color, boxShadow: `0 0 10px ${color}` }}
                                    />
                                )}
                            </motion.div>
                        );
                    })}
                </motion.div>
            </div>
        </div>
    );
};

export default GravityCarousel;

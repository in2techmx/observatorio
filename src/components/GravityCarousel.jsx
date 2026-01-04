import React, { useEffect, useRef, useState } from 'react';
import { motion, useAnimation, useMotionValue } from 'framer-motion';

const CAR_WIDTH = 300;
const GAP = 20;

const GravityCarousel = ({ categories, selectedCategory, onSelect }) => {
    const [width, setWidth] = useState(0);
    const carouselRef = useRef();
    const x = useMotionValue(0);
    const controls = useAnimation();

    // Auto-scroll definition
    useEffect(() => {
        if (carouselRef.current) {
            setWidth(carouselRef.current.scrollWidth - carouselRef.current.offsetWidth);
        }
    }, [categories]);

    // Simple marquee effect? Or distinct cards?
    // User asked for "netflix card roll" "auto roll slow motion".
    // Let's do a marquee that CAN be dragged, but auto-plays.

    return (
        <div className="relative w-full overflow-hidden py-12 bg-gradient-to-b from-black via-black/90 to-black/50 border-b border-white/5 z-30">
            {/* Fade Edges */}
            <div className="absolute top-0 left-0 h-full w-20 bg-gradient-to-r from-black to-transparent z-10 pointer-events-none" />
            <div className="absolute top-0 right-0 h-full w-20 bg-gradient-to-l from-black to-transparent z-10 pointer-events-none" />

            <div className="flex items-center justify-center mb-4">
                <h3 className="text-[10px] uppercase tracking-[0.3em] text-cyan-500/50">Select Sector</h3>
            </div>

            {/* Scroll Container */}
            <div className="flex justify-center overflow-x-auto no-scrollbar snap-x snap-mandatory px-[30vw]">
                {/* We map categories. If it's short, maybe duplicate? */}
                <div className="flex gap-8 py-8 items-center">
                    {categories.map((cat, index) => {
                        const isSelected = selectedCategory === cat.name;

                        return (
                            <motion.div
                                key={cat.name}
                                layoutId={cat.name}
                                onClick={() => onSelect(cat.name)}
                                className={`
                                    relative flex-shrink-0 w-[240px] h-[140px] rounded-xl cursor-pointer snap-center
                                    border transition-all duration-500 group overflow-hidden
                                    ${isSelected
                                        ? 'scale-125 border-cyan-400 shadow-[0_0_30px_rgba(34,211,238,0.2)] z-10 bg-zinc-800'
                                        : 'scale-100 border-white/10 hover:border-white/30 bg-zinc-900/50 opacity-60 hover:opacity-100 grayscale hover:grayscale-0'
                                    }
                                `}
                            >
                                {/* Background Gradient/Image Placeholder */}
                                <div className={`absolute inset-0 bg-gradient-to-br ${isSelected ? 'from-cyan-900/40 to-black' : 'from-white/5 to-black'}`} />

                                <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center">
                                    <div className={`w-2 h-2 rounded-full mb-3 ${isSelected ? 'bg-cyan-400' : 'bg-gray-600'}`} />
                                    <h3 className={`text-base font-bold uppercase tracking-wider leading-tight ${isSelected ? 'text-white' : 'text-gray-400'}`}>
                                        {cat.name}
                                    </h3>
                                    <span className="text-[10px] mt-2 font-mono text-gray-500">
                                        {cat.count} Signals
                                    </span>
                                </div>

                                {/* Active Indicator Bar */}
                                {isSelected && (
                                    <motion.div
                                        layoutId="activeBar"
                                        className="absolute bottom-0 left-0 w-full h-1 bg-cyan-400"
                                    />
                                )}
                            </motion.div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default GravityCarousel;

import React from 'react';
import { motion } from 'framer-motion';

const LandingHero = () => {
    return (
        <div className="relative w-full h-[25vh] md:h-[20vh] flex items-center justify-between px-6 md:px-12 border-b border-white/10 overflow-hidden bg-black z-50">
            {/* Background Effects */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-50%] left-[20%] w-[30vw] h-[30vw] bg-cyan-500/10 rounded-full blur-[80px]" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
            </div>

            {/* Left: Title */}
            <div className="z-10 flex flex-col justify-center">
                <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-300 to-gray-500 font-display">
                        PROXIMITY
                    </h1>
                </motion.div>
                <p className="text-xs text-gray-400 font-light mt-1 tracking-wide uppercase">
                    Global Intelligence Observatory
                </p>
            </div>

            {/* Right: Micro-Legend (Horizontal) */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="z-10 hidden md:flex items-center gap-6"
            >
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 backdrop-blur-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
                    <span className="text-[10px] uppercase text-gray-300 tracking-wider font-bold">Category Decks</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 backdrop-blur-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-magenta-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]"></div>
                    <span className="text-[10px] uppercase text-gray-300 tracking-wider font-bold">Gravity Score (1-10)</span>
                </div>
            </motion.div>
        </div>
    );
};

export default LandingHero;

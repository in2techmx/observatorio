import React from 'react';
import { motion } from 'framer-motion';

const LandingHero = ({ language = 'EN', toggleLanguage }) => {
    // Dictionary
    const t = {
        subtitle: language === 'EN' ? "Global Intelligence Observatory" : "Observatorio de Inteligencia Global",
        desc: language === 'EN'
            ? "Decentralized monitoring of geopolitical signals. Tracking convergence across 7 strategic regions."
            : "Monitoreo descentralizado de señales geopolíticas. Rastreando la convergencia en 7 regiones estratégicas.",
        legend1: language === 'EN' ? "Category Decks" : "Decks de Categoría",
        legend2: language === 'EN' ? "Gravity Score (1-10)" : "Puntaje de Gravedad (1-10)"
    };

    return (
        <div className="relative w-full h-[25vh] md:h-[20vh] flex items-center justify-between px-6 md:px-12 border-b border-white/10 overflow-hidden bg-black z-50">
            {/* Background Effects */}
            <div className="absolute inset-0 z-0">
                <div className="absolute top-[-50%] left-[20%] w-[30vw] h-[30vw] bg-cyan-500/10 rounded-full blur-[80px]" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10"></div>
            </div>

            {/* Left: Title & Explanation */}
            <div className="z-10 flex flex-col justify-center max-w-2xl">
                <motion.div
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.6 }}
                >
                    <h1 className="text-3xl md:text-5xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-300 to-gray-500 font-display">
                        PROXIMITY
                    </h1>
                </motion.div>
                <div className="flex flex-col gap-1 mt-2">
                    <p className="text-xs text-cyan-500 font-bold tracking-widest uppercase">
                        {t.subtitle}
                    </p>
                    <p className="text-[10px] md:text-xs text-gray-400 font-mono leading-relaxed max-w-md hidden md:block">
                        {t.desc}
                    </p>
                </div>
            </div>

            {/* Right: Micro-Legend & Language Toggle */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4 }}
                className="z-10 flex items-center gap-6"
            >
                {/* Language Toggle */}
                <button
                    onClick={toggleLanguage}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 hover:bg-white/10 cursor-pointer transition-all active:scale-95"
                >
                    <span className={`text-[10px] font-bold ${language === 'EN' ? 'text-cyan-400' : 'text-gray-500'}`}>EN</span>
                    <div className="h-3 w-[1px] bg-white/20"></div>
                    <span className={`text-[10px] font-bold ${language === 'ES' ? 'text-cyan-400' : 'text-gray-500'}`}>ES</span>
                </button>

                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 backdrop-blur-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)]"></div>
                    <span className="text-[10px] uppercase text-gray-300 tracking-wider font-bold">{t.legend1}</span>
                </div>
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 border border-white/5 backdrop-blur-sm">
                    <div className="w-1.5 h-1.5 rounded-full bg-magenta-400 shadow-[0_0_8px_rgba(232,121,249,0.8)]"></div>
                    <span className="text-[10px] uppercase text-gray-300 tracking-wider font-bold">{t.legend2}</span>
                </div>
            </motion.div>
        </div>
    );
};

export default LandingHero;

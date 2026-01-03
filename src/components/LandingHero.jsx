import React from 'react';
import { motion } from 'framer-motion';

const LandingHero = () => {
    return (
        <div className="relative w-full h-[80vh] flex flex-col justify-center items-start px-12 md:px-24 overflow-hidden">
            {/* Background Effects */}
            <div className="absolute inset-0 bg-black z-0">
                <div className="absolute top-[-20%] right-[-10%] w-[60vw] h-[60vw] bg-cyan-500/10 rounded-full blur-[120px] animate-pulse" />
                <div className="absolute bottom-[-10%] left-[-10%] w-[40vw] h-[40vw] bg-magenta-500/10 rounded-full blur-[100px]" />
                <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20"></div>
            </div>

            <div className="z-10 max-w-3xl">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8 }}
                >
                    <h1 className="text-7xl md:text-8xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-white via-gray-200 to-gray-500 mb-6 font-display">
                        GLOBAL <br /> GRAVITY
                    </h1>
                </motion.div>

                <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.4, duration: 0.8 }}
                    className="text-xl md:text-2xl text-gray-400 font-light mb-12 max-w-2xl leading-relaxed"
                >
                    Observatorio de Inteligencia Geopolítica V2.
                    <br />
                    <span className="text-cyan-400 font-medium">Decodificando el caos global</span> a través de la proximidad narrativa.
                </motion.p>

                {/* Legend / Methodology */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.8 }}
                    className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-white/5 backdrop-blur-md p-6 rounded-2xl border border-white/10"
                >
                    <div className="p-4 rounded-xl hover:bg-white/5 transition-colors group">
                        <div className="w-10 h-10 mb-3 rounded-full bg-cyan-500/20 flex items-center justify-center text-cyan-400">
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                        </div>
                        <h3 className="text-white font-bold mb-1 group-hover:text-cyan-400 transition-colors">The Decks</h3>
                        <p className="text-xs text-gray-400">Las noticias se organizan por vectores de impacto: Economía, Salud, Política, Sociedad.</p>
                    </div>

                    <div className="p-4 rounded-xl hover:bg-white/5 transition-colors group">
                        <div className="w-10 h-10 mb-3 rounded-full bg-magenta-500/20 flex items-center justify-center text-magenta-400">
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        </div>
                        <h3 className="text-white font-bold mb-1 group-hover:text-magenta-400 transition-colors">Proximity Score</h3>
                        <p className="text-xs text-gray-400">
                            <span className="font-bold text-white">Gravedad (1-10)</span>.
                            Cuanto más cerca del centro del radar, mayor es la tracción global del evento.
                        </p>
                    </div>

                    <div className="p-4 rounded-xl hover:bg-white/5 transition-colors group">
                        <div className="w-10 h-10 mb-3 rounded-full bg-yellow-500/20 flex items-center justify-center text-yellow-400">
                            <svg xmlns="http://www.w3.org/2000/svg" className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                        </div>
                        <h3 className="text-white font-bold mb-1 group-hover:text-yellow-400 transition-colors">Deep Dive</h3>
                        <p className="text-xs text-gray-400">Haz clic en cualquier nodo o tarjeta para acceder al análisis de inteligencia completo.</p>
                    </div>
                </motion.div>
            </div>

            {/* Scroll Indicator */}
            <div className="absolute bottom-10 left-1/2 transform -translate-x-1/2 flex flex-col items-center animate-bounce">
                <span className="text-[10px] uppercase tracking-[0.2em] text-gray-500 mb-2">Scroll to Monitor</span>
                <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 14l-7 7m0 0l-7-7m7 7V3" /></svg>
            </div>
        </div>
    );
};

export default LandingHero;

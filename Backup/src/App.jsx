import React, { useState } from 'react';
import Prism from './components/Prism';
import Heatmap from './components/Heatmap';
import { EVENTS } from './data/mockData';
import { motion, AnimatePresence } from 'framer-motion';

function App() {
    const [selectedEventId, setSelectedEventId] = useState(EVENTS[0].id);
    const [currentView, setCurrentView] = useState('monitor');
    const selectedEvent = EVENTS.find(e => e.id === selectedEventId);

    return (
        <div className="min-h-screen text-white font-inter overflow-hidden flex flex-col">
            {/* Header */}
            <header className="p-6 flex justify-between items-center z-50">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-400 to-blue-600 animate-pulse"></div>
                    <h1 className="text-2xl font-bold tracking-tight">GLOBAL <span className="font-light opacity-70">GRAVITY</span></h1>
                </div>
                <nav className="flex gap-6 text-sm uppercase tracking-widest text-gray-400">
                    <button
                        onClick={() => setCurrentView('monitor')}
                        className={`hover:text-white transition-colors ${currentView === 'monitor' ? 'text-white font-bold shadow-white drop-shadow-md' : ''}`}
                    >
                        Monitor
                    </button>
                    <button
                        onClick={() => setCurrentView('alerts')}
                        className={`hover:text-white transition-colors ${currentView === 'alerts' ? 'text-white font-bold shadow-white drop-shadow-md' : ''}`}
                    >
                        Alertas
                    </button>
                    <button
                        onClick={() => setCurrentView('export')}
                        className={`hover:text-white transition-colors ${currentView === 'export' ? 'text-white font-bold shadow-white drop-shadow-md' : ''}`}
                    >
                        Exportar
                    </button>
                </nav>
            </header>

            {/* Main Content Container */}
            <main className="flex-1 flex gap-8 p-8 pt-0 h-[calc(100vh-100px)] relative">

                {/* View: MONITOR */}
                {currentView === 'monitor' && (
                    <>
                        {/* Left Column: The Noise (Prism + Feed) */}
                        <section className="flex-1 flex flex-col gap-6 relative">
                            {/* Feed Selector (Floating List) */}
                            <div className="h-48 overflow-y-auto glass-panel p-4 pr-2 custom-scrollbar space-y-3">
                                <h2 className="text-xs uppercase text-gray-500 mb-2 font-bold tracking-wider">Señales Detectadas (24h)</h2>
                                {EVENTS.map(ev => (
                                    <div
                                        key={ev.id}
                                        onClick={() => setSelectedEventId(ev.id)}
                                        className={`p-3 rounded-xl cursor-pointer transition-all border border-transparent hover:bg-white/5 ${selectedEventId === ev.id ? 'bg-white/10 border-white/20 shadow-lg' : 'opacity-60 hover:opacity-100'
                                            }`}
                                    >
                                        <div className="flex justify-between items-start mb-1">
                                            <span className="text-[10px] bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full uppercase">{ev.category}</span>
                                            <span className="text-[10px] text-gray-400">{ev.global_convergence}% Conv.</span>
                                        </div>
                                        <h3 className="text-sm font-semibold leading-snug">{ev.title}</h3>
                                    </div>
                                ))}
                            </div>

                            {/* Prism Visualization */}
                            <div className="flex-1 glass-panel relative flex flex-col">
                                <div className="absolute top-4 left-4 z-10">
                                    <h2 className="text-sm uppercase text-gray-400 tracking-wider">Prisma de Perspectivas</h2>
                                </div>
                                <div className="flex-1 relative">
                                    <AnimatePresence mode="wait">
                                        <motion.div
                                            key={selectedEventId}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            exit={{ opacity: 0, scale: 1.05 }}
                                            transition={{ duration: 0.4 }}
                                            className="w-full h-full"
                                        >
                                            <Prism event={selectedEvent} />
                                        </motion.div>
                                    </AnimatePresence>
                                </div>

                                {/* Blind Spot Analysis Footer */}
                                <div className="p-4 border-t border-white/5 bg-black/20">
                                    <div className="flex items-start gap-3">
                                        <span className="text-xl">👁️</span>
                                        <div>
                                            <h4 className="text-xs font-bold uppercase text-red-400 mb-1">Análisis de Punto Ciego</h4>
                                            <p className="text-sm text-gray-300 italic">
                                                "{selectedEvent?.blind_spot_analysis}"
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* Right Column: The Silence (Heatmap) */}
                        <section className="flex-1 flex flex-col">
                            <Heatmap />
                        </section>
                    </>
                )}

                {/* View: ALERTS */}
                {currentView === 'alerts' && (
                    <div className="flex-1 glass-panel p-12 flex flex-col items-center justify-center text-center">
                        <div className="p-8 bg-red-500/10 rounded-full mb-6">
                            <span className="text-6xl">⚠️</span>
                        </div>
                        <h2 className="text-3xl font-bold mb-4">Alertas de Puntos Ciegos</h2>
                        <p className="max-w-md text-gray-400 mb-8">
                            Se han detectado 3 narrativas críticas con alta divergencia regional que requieren atención inmediata.
                        </p>
                        <div className="w-full max-w-2xl space-y-4">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="p-4 bg-white/5 rounded-lg border border-white/10 text-left flex items-start gap-4">
                                    <div className="w-2 h-2 rounded-full bg-red-500 mt-2"></div>
                                    <div>
                                        <h4 className="font-bold">Divergencia Crítica: Tratado del Ártico #{i}</h4>
                                        <p className="text-sm text-gray-400">Silencio total en medios occidentales vs. Cobertura masiva en BRICS.</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* View: EXPORT */}
                {currentView === 'export' && (
                    <div className="flex-1 glass-panel p-12 flex flex-col items-center justify-center text-center">
                        <div className="p-8 bg-blue-500/10 rounded-full mb-6">
                            <span className="text-6xl">📥</span>
                        </div>
                        <h2 className="text-3xl font-bold mb-4">Exportar Informe</h2>
                        <p className="max-w-md text-gray-400 mb-8">
                            Generar reporte PDF con el análisis de convergencia y mapas de calor actuales.
                        </p>
                        <div className="flex gap-4">
                            <button className="px-6 py-3 bg-white text-black font-bold rounded-lg hover:bg-gray-200 transition-colors">
                                Descargar PDF
                            </button>
                            <button className="px-6 py-3 border border-white/20 rounded-lg hover:bg-white/5 transition-colors">
                                Exportar CSV
                            </button>
                        </div>
                    </div>
                )}

            </main>
        </div>
    );
}

export default App;

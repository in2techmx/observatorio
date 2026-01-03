import React from 'react';
import { motion } from 'framer-motion';
import { X, Globe, Share2, ExternalLink } from 'lucide-react';

const NewsCard = ({ event, onClose }) => {
    if (!event) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={onClose}
                className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />

            <motion.div
                layoutId={`card-${event.id}`}
                initial={{ opacity: 0, scale: 0.9, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9, y: 20 }}
                className="relative w-full max-w-2xl bg-[#0f0f0f] border border-white/10 rounded-2xl overflow-hidden shadow-2xl z-10"
            >
                {/* Header Image / Gradient */}
                <div className="h-32 bg-gradient-to-r from-cyan-900 via-blue-900 to-purple-900 relative overflow-hidden">
                    <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-30 mix-blend-overlay"></div>
                    <div className="absolute bottom-4 left-6">
                        <span className="text-[10px] bg-white text-black font-bold px-2 py-1 rounded uppercase tracking-wider mb-2 inline-block">
                            {event.category}
                        </span>
                        <h2 className="text-2xl font-bold text-white leading-tight shadow-md">{event.title}</h2>
                    </div>
                    <button
                        onClick={onClose}
                        className="absolute top-4 right-4 p-2 bg-black/20 hover:bg-black/40 rounded-full transition-colors text-white"
                    >
                        <X size={20} />
                    </button>
                </div>

                <div className="p-8">
                    {/* Metadata Bar */}
                    <div className="flex items-center gap-6 mb-8 text-sm text-gray-400 border-b border-white/5 pb-4">
                        <div className="flex items-center gap-2">
                            <Globe size={16} className="text-cyan-400" />
                            <span>{event.country}</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <div className={`w-2 h-2 rounded-full ${event.proximity_score > 7 ? 'bg-red-500 animate-pulse' : 'bg-green-500'}`} />
                            <span>Gravity Score: <strong className="text-white">{event.proximity_score}/10</strong></span>
                        </div>
                    </div>

                    {/* Main Analysis */}
                    <div className="prose prose-invert max-w-none">
                        <h3 className="text-lg font-bold text-gray-100 mb-2">Análisis de Inteligencia</h3>
                        <p className="text-gray-300 leading-relaxed text-base mb-6">
                            {event.analysis}
                        </p>
                    </div>

                    {/* Perspective Matrix (if available) */}
                    {event.perspectives && (
                        <div className="mb-8">
                            <h4 className="text-xs font-bold uppercase text-gray-500 tracking-widest mb-3">Intensidad Regional</h4>
                            <div className="flex gap-2 flex-wrap">
                                {Object.entries(event.perspectives).map(([region, data]) => (
                                    <div key={region} className="bg-white/5 px-3 py-2 rounded border border-white/5 flex items-center gap-2">
                                        <span className="text-xs font-bold text-gray-300">{region}</span>
                                        <div className="h-1 w-12 bg-gray-700 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-cyan-500"
                                                style={{ width: `${(data.weight / 10) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-3 mt-8 pt-4 border-t border-white/5">
                        <button className="flex items-center gap-2 px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
                            <Share2 size={16} /> Compartir
                        </button>
                        <a
                            href={event.url}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-2 px-6 py-2 bg-white text-black font-bold rounded-lg hover:bg-cyan-50 rounded-lg transition-all"
                        >
                            Leer Fuente Original <ExternalLink size={16} />
                        </a>
                    </div>
                </div>
            </motion.div>
        </div>
    );
};

export default NewsCard;

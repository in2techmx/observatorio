import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { FileText, X, Clock, Calendar } from 'lucide-react';

const ArchivePanel = ({ onClose }) => {
    const [briefs, setBriefs] = useState(null);
    const [selectedBrief, setSelectedBrief] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('./briefs.json')
            .then(res => res.json())
            .then(data => {
                setBriefs(data.reports || {});
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load briefs", err);
                setLoading(false);
            });
    }, []);

    // Helper to format key (e.g. M1-2026 -> Enero 2026 approx, or just raw)
    const formatKey = (key) => {
        if (key.startsWith('M')) return `Monthly Report: ${key}`;
        if (key.startsWith('W')) return `Weekly Report: ${key}`;
        return key;
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4"
        >
            <div className="bg-zinc-900 w-full max-w-4xl h-[80vh] rounded-2xl border border-white/10 shadow-2xl flex overflow-hidden">

                {/* Sidebar: List of Reports */}
                <div className="w-1/3 border-r border-white/5 bg-black/40 flex flex-col">
                    <div className="p-4 border-b border-white/5 flex justify-between items-center">
                        <h3 className="text-xs uppercase tracking-[0.2em] text-cyan-500 font-bold">
                            Intelligence Archives
                        </h3>
                    </div>
                    <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-2">
                        {loading && <div className="p-4 text-xs text-gray-500">Decrypting archives...</div>}

                        {!loading && briefs && Object.entries(briefs).length === 0 && (
                            <div className="p-4 text-xs text-gray-500">No historical data declassified yet.</div>
                        )}

                        {!loading && briefs && Object.values(briefs).sort((a, b) => new Date(b.date) - new Date(a.date)).map((report) => (
                            <div
                                key={report.id}
                                onClick={() => setSelectedBrief(report)}
                                className={`p-3 rounded-lg cursor-pointer border transition-all ${selectedBrief?.id === report.id ? 'bg-cyan-900/20 border-cyan-500/50 text-white' : 'bg-transparent border-transparent hover:bg-white/5 text-gray-400'}`}
                            >
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-[10px] font-mono border border-white/10 px-1 rounded uppercase bg-black">
                                        {report.type}
                                    </span>
                                    <span className="text-[10px] text-gray-600 flex items-center gap-1">
                                        <Clock size={10} /> {new Date(report.date).toLocaleDateString()}
                                    </span>
                                </div>
                                <h4 className="text-xs font-bold truncate">
                                    {formatKey(report.id)}
                                </h4>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Main Content: Reader */}
                <div className="flex-1 flex flex-col relative bg-[url('https://grainy-gradients.vercel.app/noise.svg')] bg-opacity-10">
                    <div className="absolute top-4 right-4 z-10">
                        <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-full text-gray-400 hover:text-white transition-colors">
                            <X size={20} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-y-auto custom-scrollbar p-8">
                        {selectedBrief ? (
                            <motion.div
                                key={selectedBrief.id}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="max-w-xl mx-auto"
                            >
                                <div className="mb-6 pb-6 border-b border-white/10">
                                    <span className="text-cyan-500 font-mono text-xs uppercase tracking-widest block mb-2">
                                        // DECLASSIFIED DOCUMENT
                                    </span>
                                    <h2 className="text-2xl font-bold text-white mb-2">
                                        {formatKey(selectedBrief.id)}
                                    </h2>
                                    <p className="text-xs text-gray-500 font-mono">
                                        ID: {selectedBrief.id} | TYPE: {selectedBrief.type}
                                    </p>
                                </div>

                                <div className="prose prose-invert prose-sm font-serif leading-relaxed text-gray-300 whitespace-pre-line">
                                    {selectedBrief.content}
                                </div>

                                <div className="mt-12 pt-6 border-t border-white/5 text-center">
                                    <img src="/api/placeholder/100/30" alt="Signature" className="h-8 mx-auto opacity-30 invert" />
                                    <p className="text-[10px] text-gray-600 font-mono mt-2 uppercase tracking-widest">
                                        Authorized by Gravity Strategic Command
                                    </p>
                                </div>
                            </motion.div>
                        ) : (
                            <div className="h-full flex items-center justify-center text-gray-600 flex-col gap-4">
                                <FileText size={48} className="opacity-20" />
                                <p className="text-xs uppercase tracking-widest">Select a file to review</p>
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </motion.div>
    );
};

export default ArchivePanel;

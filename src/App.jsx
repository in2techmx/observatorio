import React, { useState, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import CategoryDeck from './components/CategoryDeck';
import NewsCard from './components/NewsCard';
import mockData from './data/mockCarousel.json';

function App() {
    const [selectedNews, setSelectedNews] = useState(null);

    // Group data by category dynamically
    const categories = useMemo(() => {
        const groups = {};
        mockData.forEach(event => {
            if (!groups[event.category]) {
                groups[event.category] = [];
            }
            groups[event.category].push(event);
        });
        return groups;
    }, []);

    return (
        <div className="min-h-screen bg-black text-white font-sans selection:bg-cyan-500 selection:text-black overflow-x-hidden">

            {/* 1. HERO SECTION (Explanation) */}
            <LandingHero />

            {/* 2. MAIN CONTENT (The Decks) */}
            <main className="relative z-10 -mt-20 pb-20 space-y-2">
                <div className="px-6 md:px-12 mb-4">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500">
                        Monitor de Inteligencia en Tiempo Real
                    </h3>
                </div>

                {Object.entries(categories).map(([category, events]) => (
                    <CategoryDeck
                        key={category}
                        category={category}
                        events={events}
                        onSelectNews={setSelectedNews}
                    />
                ))}
            </main>

            {/* 3. FOOTER */}
            <footer className="py-12 border-t border-white/5 text-center text-gray-600 text-sm">
                <p>Observatorio V2 &copy; 2026. Powered by Gemini 2.0 Flash.</p>
            </footer>

            {/* 4. MODALS */}
            <AnimatePresence>
                {selectedNews && (
                    <NewsCard
                        event={selectedNews}
                        onClose={() => setSelectedNews(null)}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

export default App;

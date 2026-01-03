import React, { useState, useEffect, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import CategoryDeck from './components/CategoryDeck';
import NewsCard from './components/NewsCard';

function App() {
    const [selectedNews, setSelectedNews] = useState(null);
    const [eventsData, setEventsData] = useState([]);
    const [loading, setLoading] = useState(true);

    // Fetch real data from gravity_carousel.json
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('./gravity_carousel.json');
                const text = await response.text();
                // Handle potential trailing commas or minor JSON errors if needed, but assuming valid JSON for now
                const json = JSON.parse(text);

                if (json.carousel) {
                    // ADAPTER: Transform nested carousel structure to flat events list expected by components
                    // Structure: { carousel: [ { area: "Name", particulas: [...] } ] }
                    const flatEvents = json.carousel.flatMap(categoryBlock => {
                        return (categoryBlock.particulas || []).map(p => ({
                            ...p,
                            category: categoryBlock.area, // Map 'area' to 'category'
                            proximity_score: (p.proximidad / 10).toFixed(1) // Map 0-100 to 0-10
                        }));
                    });
                    setEventsData(flatEvents);
                }
            } catch (error) {
                console.error("Failed to load gravity data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Group data by category dynamically
    const categories = useMemo(() => {
        const groups = {};
        eventsData.forEach(event => {
            if (!groups[event.category]) {
                groups[event.category] = [];
            }
            groups[event.category].push(event);
        });
        return groups;
    }, [eventsData]);

    if (loading) {
        return <div className="min-h-screen bg-black text-white flex items-center justify-center">Initializing Gravity Link...</div>;
    }

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

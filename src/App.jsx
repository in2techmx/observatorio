import React, { useState, useEffect, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import GravityCarousel from './components/GravityCarousel';
import CategoryDetail from './components/CategoryDetail';
import NewsCard from './components/NewsCard';

function App() {
    const [selectedNews, setSelectedNews] = useState(null);
    const [events, setEvents] = useState([]);
    const [meta, setMeta] = useState(null);
    const [syntheses, setSyntheses] = useState({}); // Store synthesis per category
    const [loading, setLoading] = useState(true);

    // Fetch real data from gravity_carousel.json
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('./gravity_carousel.json');
                const text = await response.text();
                // Handle potential trailing commas or minor JSON errors if needed, but assuming valid JSON for now
                const data = JSON.parse(text);

                if (data.carousel) {
                    // ADAPTER: Transform nested carousel structure to flat events list expected by components
                    // Structure: { carousel: [ { area: "Name", particulas: [...] } ] }
                    const adaptedEvents = data.carousel.flatMap(categoryBlock => {
                        return (categoryBlock.particulas || []).map(p => ({
                            id: p.id,
                            title: p.titulo, // Map Spanish key to English prop
                            link: p.link,
                            country: p.bloque,
                            source_url: p.link,
                            proximity_score: p.proximidad / 10, // Map 0-100 to 0-10
                            category: categoryBlock.area,
                            analysis: (p.keywords || []).join(', ') + ". " + (p.sesgo || ""), // Fallback content
                            keywords: p.keywords
                        }));
                    });

                    // Create a map of synthesis per category
                    const synthesisMap = {};
                    data.carousel.forEach(cat => {
                        synthesisMap[cat.area] = cat.sintesis;
                    });

                    setEvents(adaptedEvents);
                    setMeta(data.meta || {});
                    setSyntheses(synthesisMap); // New state for synthesis
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
        events.forEach(event => {
            if (!groups[event.category]) {
                groups[event.category] = [];
            }
            groups[event.category].push(event);
        });
        return groups;
    }, [events]);

    if (loading) {
        return <div className="min-h-screen bg-black text-white flex items-center justify-center">Initializing Gravity Link...</div>;
    }

    return (
        <div className="min-h-screen bg-black text-white font-sans selection:bg-cyan-500 selection:text-black">

            {/* 1. HERO SECTION (Explanation) */}
            <LandingHero />

            {/* 2. MAIN CONTENT (The Decks) */}
            <main id="main-monitor" className="relative z-10 -mt-20 pb-20 space-y-2">
                <div className="px-6 md:px-12 mb-4">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-gray-500">
                        Monitor de Inteligencia en Tiempo Real
                    </h3>
                </div>

                {Object.entries(categories).map(([category, categoryEvents]) => (
                    <CategoryDeck
                        key={category}
                        category={category}
                        events={categoryEvents}
                        synthesis={syntheses[category]}
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

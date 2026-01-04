import React, { useState, useEffect, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import GravityCarousel from './components/GravityCarousel';
import CategoryDetail from './components/CategoryDetail';
import ArchivePanel from './components/ArchivePanel';

function App() {
    const [selectedNews, setSelectedNews] = useState(null);
    const [events, setEvents] = useState([]);
    const [meta, setMeta] = useState(null);
    const [syntheses, setSyntheses] = useState({});
    // State for the new Carousel Navigation
    const [selectedCategory, setSelectedCategory] = useState(null);
    // State for Archives
    const [showArchives, setShowArchives] = useState(false);

    // Fetch real data from gravity_carousel.json
    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('./gravity_carousel.json');
                const text = await response.text();
                const data = JSON.parse(text);

                if (data.carousel) {
                    // ADAPTER: Transform nested carousel structure to flat events list
                    const adaptedEvents = data.carousel.flatMap(categoryBlock => {
                        return (categoryBlock.particulas || []).map(p => ({
                            id: p.id,
                            title: p.titulo,
                            link: p.link,
                            country: p.bloque,
                            source_url: p.link,
                            proximity_score: p.proximidad / 10, // Map 0-100 to 0-10 for Radar
                            category: categoryBlock.area,
                            analysis: (p.keywords || []).join(', ') + ". " + (p.sesgo || ""),
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
                    setSyntheses(synthesisMap);
                }
            } catch (error) {
                console.error("Failed to load gravity data:", error);
            }
        };

        fetchData();
    }, []);

    // Select the first category by default - REMOVED per user request
    // Initial state is "Overview" (Carousel only)
    /*
    useEffect(() => {
        if (events.length > 0 && !selectedCategory) {
            // Find unique categories order
            const uniqueCats = [...new Set(events.map(e => e.category))];
            if (uniqueCats.length > 0) setSelectedCategory(uniqueCats[0]);
        }
    }, [events, selectedCategory]);
    */

    // Prepare data for Carousel (Category Name + Count)
    const categoriesList = useMemo(() => {
        const counts = {};
        events.forEach(e => { counts[e.category] = (counts[e.category] || 0) + 1; });
        // Use syntheses keys to ensure consistent order if preferred, or events
        return Object.keys(syntheses).length > 0
            ? Object.keys(syntheses).map(cat => ({ name: cat, count: counts[cat] || 0 }))
            : [...new Set(events.map(e => e.category))].map(cat => ({ name: cat, count: counts[cat] || 0 }));
    }, [events, syntheses]);

    // Filter events for selected category
    const activeEvents = useMemo(() => {
        return selectedCategory ? events.filter(e => e.category === selectedCategory) : [];
    }, [selectedCategory, events]);


    return (
        <div className="min-h-screen bg-black text-white font-sans selection:bg-cyan-500 selection:text-black">

            {/* 1. HERO SECTION */}
            <LandingHero />

            {/* 2. MAIN NAV INTERFACE (Gravity Stream) */}
            <div id="main-monitor" className="relative min-h-screen bg-black -mt-10 z-10">

                {/* A. Horizontal 3D Carousel (Sticky Header) */}
                <div className="sticky top-0 z-40 bg-black/80 backdrop-blur-md border-b border-white/10 shadow-2xl">
                    <GravityCarousel
                        categories={categoriesList}
                        selectedCategory={selectedCategory}
                        onSelect={setSelectedCategory}
                    />
                </div>

                {/* B. Active Category Detailed View */}
                <div className="relative z-0 min-h-[800px] pt-4 pb-20 bg-gradient-to-b from-black to-zinc-900">
                    <AnimatePresence mode="wait">
                        {selectedCategory && (
                            <CategoryDetail
                                key={selectedCategory}
                                category={selectedCategory}
                                events={activeEvents}
                                synthesis={syntheses[selectedCategory]}
                                onSelectNews={setSelectedNews}
                            />
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* 3. FOOTER */}
            <footer className="py-12 border-t border-white/5 text-center text-gray-600 text-sm bg-black flex flex-col items-center gap-4">
                <button
                    onClick={() => setShowArchives(true)}
                    className="text-xs uppercase tracking-[0.2em] text-cyan-900 hover:text-cyan-400 transition-colors border border-transparent hover:border-cyan-900/30 px-4 py-2 rounded-full"
                >
                    [ ACCESS CLASSIFIED ARCHIVES ]
                </button>
                <p>Observatorio V2 &copy; 2026. Powered by Gemini 2.0 Flash.</p>
            </footer>

            {/* 4. MODALS */}
            <AnimatePresence>
                {selectedNews && (
                    <NewsCard
                        event={events.find(e => e.id === selectedNews)}
                        onClose={() => setSelectedNews(null)}
                    />
                )}
                )}
            </AnimatePresence>

            {/* 5. ARCHIVES PANEL */}
            <AnimatePresence>
                {showArchives && (
                    <ArchivePanel onClose={() => setShowArchives(false)} />
                )}
            </AnimatePresence>
        </div>
    );
}

export default App;

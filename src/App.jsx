import React, { useState, useEffect, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import GravityCarousel from './components/GravityCarousel';
import CategoryDetail from './components/CategoryDetail';
import ArchivePanel from './components/ArchivePanel';
import NewsCard from './components/NewsCard'; // Ensure NewsCard is imported

function App() {
    // UI State
    const [loading, setLoading] = useState(true);
    const [titleLoading, setTitleLoading] = useState(true);
    const [language, setLanguage] = useState('EN');
    const [showArchives, setShowArchives] = useState(false);
    const [isOverlayOpen, setIsOverlayOpen] = useState(false);

    // Data State
    const [events, setEvents] = useState([]);
    const [meta, setMeta] = useState(null);
    const [syntheses, setSyntheses] = useState({});

    // Selection State
    const [selectedCategory, setSelectedCategory] = useState(null);
    const [selectedNews, setSelectedNews] = useState(null);

    // Translations
    const CATEGORY_TRANSLATIONS = {
        "Seguridad y Conflictos": { es: "Seguridad y Conflictos", en: "Security & Conflict" },
        "Economía y Sanciones": { es: "Economía y Sanciones", en: "Economy & Sanctions" },
        "Energía y Recursos": { es: "Energía y Recursos", en: "Energy & Resources" },
        "Soberanía y Alianzas": { es: "Soberanía y Alianzas", en: "Sovereignty & Alliances" },
        "Tecnología y Espacio": { es: "Tecnología y Espacio", en: "Tech & Space" },
        "Sociedad y Derechos": { es: "Sociedad y Derechos", en: "Society & Rights" },
        "Desconocido": { es: "Desconocido", en: "Unknown" }
    };

    const toggleLanguage = () => {
        setLanguage(prev => prev === 'EN' ? 'ES' : 'EN');
    };

    // Fetch real data from gravity_carousel.json
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Simulate cosmic link delay for effect
                await new Promise(r => setTimeout(r, 1500));

                const response = await fetch('./gravity_carousel.json');
                if (!response.ok) throw new Error("Failed to fetch data");

                const text = await response.text();
                const data = JSON.parse(text);

                if (data.carousel) {
                    // ADAPTER: Transform nested carousel structure to flat events list
                    const adaptedEvents = data.carousel.flatMap(categoryBlock => {
                        return (categoryBlock.particulas || []).map(p => ({
                            id: p.id,
                            title: p.titulo, // Default to original for safety
                            titulo_en: p.titulo_en, // Capture bilingual fields for components to use
                            titulo_es: p.titulo_es,
                            link: p.link,
                            country: p.bloque,
                            region: p.bloque || p.region, // Handle inconsistent naming
                            source_url: p.link,
                            proximity_score: p.proximidad / 10, // Map 0-100 to 0-10 for Radar
                            category: categoryBlock.area,
                            analysis: (p.keywords || []).join(', ') + ". " + (p.sesgo || ""),
                            keywords: p.keywords,
                            snippet: p.snippet
                        }));
                    });

                    // Create a map of synthesis per category (handling bilingual object or string fallback)
                    const synthesisMap = {};
                    data.carousel.forEach(cat => {
                        // Backend now sends sintesis (es) and sintesis_en
                        // Map structure: string or object
                        if (cat.sintesis_en) {
                            synthesisMap[cat.area] = {
                                en: cat.sintesis_en,
                                es: cat.sintesis
                            };
                        } else {
                            synthesisMap[cat.area] = cat.sintesis; // Fallback legacy
                        }
                    });

                    setEvents(adaptedEvents);
                    setMeta(data.meta || {});
                    setSyntheses(synthesisMap);
                }
            } catch (error) {
                console.error("Failed to load gravity data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

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

    // Handlers
    const handleCategorySelect = (category) => {
        setSelectedCategory(category);
        setIsOverlayOpen(true);
    };

    const handleCloseOverlay = () => {
        setIsOverlayOpen(false);
        setSelectedCategory(null);
    };

    return (
        <div className="relative w-full min-h-screen bg-black text-white font-sans selection:bg-cyan-500/30 overflow-hidden">

            {/* Header / Hero with Language Toggle */}
            <LandingHero
                language={language}
                toggleLanguage={toggleLanguage}
            />

            {/* Main Content: Carousel */}
            <div className="relative z-10 flex flex-col items-center justify-center h-[75vh]">
                {loading ? (
                    <div className="flex flex-col items-center gap-4">
                        <div className="w-16 h-16 border-4 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin"></div>
                        <p className="text-cyan-500 font-mono text-sm animate-pulse">
                            {language === 'EN' ? 'INITIALIZING SATELLITE LINK...' : 'INICIALIZANDO ENLACE SATELITAL...'}
                        </p>
                    </div>
                ) : (
                    <GravityCarousel
                        categories={categoriesList} // Pass full array of objects {name, count}
                        selectedCategory={selectedCategory}
                        onSelect={handleCategorySelect}
                        language={language}
                        categoryTranslations={CATEGORY_TRANSLATIONS}
                    />
                )}
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

            {/* 4. DETAILS OVERLAY */}
            <AnimatePresence>
                {isOverlayOpen && selectedCategory && (
                    <CategoryDetail
                        category={selectedCategory}
                        events={activeEvents}
                        synthesis={syntheses[selectedCategory]}
                        onSelectNews={setSelectedNews}
                        onClose={handleCloseOverlay}
                        language={language}
                        categoryTranslations={CATEGORY_TRANSLATIONS}
                    />
                )}
            </AnimatePresence>

            {/* 5. MODALS */}
            <AnimatePresence>
                {selectedNews && (
                    <NewsCard
                        event={selectedNews}
                        onClose={() => setSelectedNews(null)}
                        language={language}
                    />
                )}
            </AnimatePresence>

            {/* 6. ARCHIVES PANEL */}
            <AnimatePresence>
                {showArchives && (
                    <ArchivePanel onClose={() => setShowArchives(false)} />
                )}
            </AnimatePresence>
        </div>
    );
}

export default App;

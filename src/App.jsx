import React, { useState, useEffect, useMemo } from 'react';
import { AnimatePresence } from 'framer-motion';
import LandingHero from './components/LandingHero';
import GravityCarousel from './components/GravityCarousel';
import CategoryDetail from './components/CategoryDetail';
import ArchivePanel from './components/ArchivePanel';
import NewsCard from './components/NewsCard';
import MethodologyModal from './components/MethodologyModal'; // Imported

function App() {
    // UI State
    const [loading, setLoading] = useState(true);
    const [titleLoading, setTitleLoading] = useState(true);
    const [language, setLanguage] = useState('EN');
    const [showArchives, setShowArchives] = useState(false);
    const [isOverlayOpen, setIsOverlayOpen] = useState(false);
    const [showMethodology, setShowMethodology] = useState(false); // New State

    // Data State
    const [events, setEvents] = useState([]);
    const [meta, setMeta] = useState(null);
    const [syntheses, setSyntheses] = useState({});

    // Selection State
    const [selectedCategory, setSelectedCategory] = useState(null);
    const [selectedNews, setSelectedNews] = useState(null);

    // Translations
    const CATEGORY_TRANSLATIONS = {
        "War & Conflict": { es: "Guerra y Conflictos", en: "War & Conflict" },
        "Global Economy": { es: "Economía Global", en: "Global Economy" },
        "Politics & Policy": { es: "Política y Gobierno", en: "Politics & Policy" },
        "Science & Tech": { es: "Ciencia y Tecnología", en: "Science & Tech" },
        "Social & Rights": { es: "Sociedad y Derechos", en: "Social & Rights" },
        "Other": { es: "Otros Temas", en: "Other Topics" }
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

                    // Create a map of synthesis AND COLORS per category
                    const categoryMetaMap = {};
                    data.carousel.forEach(cat => {
                        // Backend now sends sintesis (es) and sintesis_en
                        // Map structure: string or object
                        const synthesis = cat.sintesis_en ? {
                            en: cat.sintesis_en,
                            es: cat.sintesis
                        } : cat.sintesis;

                        categoryMetaMap[cat.area] = {
                            synthesis,
                            color: cat.color // Capture color from backend
                        };
                    });

                    setEvents(adaptedEvents);
                    setMeta(data.meta || {});
                    setSyntheses(categoryMetaMap); // Now stores {synthesis, color}
                }
            } catch (error) {
                console.error("Failed to load gravity data:", error);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    // Prepare data for Carousel (Category Name + Count + Color)
    const categoriesList = useMemo(() => {
        const counts = {};
        events.forEach(e => { counts[e.category] = (counts[e.category] || 0) + 1; });

        // Use syntheses keys which now have the metadata
        return Object.keys(syntheses).map(catKey => ({
            name: catKey,
            count: counts[catKey] || 0,
            color: syntheses[catKey]?.color // Pass the color!
        }));
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
                onOpenMethodology={() => setShowMethodology(true)}
            />

            {/* Main Content: Carousel */}
            {/* Lifted up: h-[65vh] instead of 75vh, and removed flex-col centering to let it sit naturally below header */}
            <div className="relative z-10 flex flex-col items-center justify-start pt-12 md:justify-center md:pt-0 h-[65vh] md:h-[75vh]">
                {loading ? (
                    <div className="flex flex-col items-center gap-4 mt-12 md:mt-0">
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
            <footer className="py-8 md:py-12 border-t border-white/5 text-center text-gray-600 text-sm bg-black flex flex-col items-center gap-4 absolute bottom-0 w-full">
                <button
                    onClick={() => setShowArchives(true)}
                    className="text-xs uppercase tracking-[0.2em] text-cyan-900 hover:text-cyan-400 transition-colors border border-transparent hover:border-cyan-900/30 px-4 py-2 rounded-full"
                >
                    [ ACCESS CLASSIFIED ARCHIVES ]
                </button>
                <p className="text-[10px] md:text-sm">Observatorio V2 &copy; 2026. Powered by Gemini 2.0 Flash.</p>
            </footer>

            {/* 4. DETAILS OVERLAY */}
            <AnimatePresence>
                {isOverlayOpen && selectedCategory && (
                    <CategoryDetail
                        category={selectedCategory}
                        events={activeEvents}
                        synthesis={syntheses[selectedCategory]?.synthesis} // Access nested synthesis property
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

            {/* 7. METHODOLOGY MODAL */}
            <AnimatePresence>
                {showMethodology && (
                    <MethodologyModal
                        onClose={() => setShowMethodology(false)}
                        language={language}
                    />
                )}
            </AnimatePresence>
        </div>
    );
}

export default App;

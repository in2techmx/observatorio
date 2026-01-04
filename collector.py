# SCRIPT DE RECOLECCIÓN DE NOTICIAS - PROXIMITY ENGINE V4 (Rich Data + Regional Dedupe)
import os
import json
import datetime
import time
import urllib.request
import hashlib
import re
import sys
import math
import struct
import logging
import argparse
import csv
from collections import defaultdict
import feedparser
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')

# --- CONFIGURATION (LOADED EXTERNALLY) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "BD_Noticias", "Config")
DATA_DIR = os.path.join(BASE_DIR, "BD_Noticias", "Diario")

def load_json_config(filename):
    try:
        path = os.path.join(CONFIG_DIR, filename)
        if not os.path.exists(path):
            # Fallback for CI/CD if dir structure slightly different
            logging.error(f"FATAL: Config file not found: {path}")
            sys.exit(1)
            
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"FATAL: Could not load config {filename}: {e}")
        sys.exit(1)

RSS_FEEDS = load_json_config("feeds.json")
PROMPTS = load_json_config("prompts.json")

# --- CATEGORIES ---
CATEGORIES = {
    "War & Conflict": ["war", "military", "attack", "defense", "strike", "weapon", "gaza", "ukraine", "israel", "russia", "hamas", "idf", "putin", "zelensky", "nato", "missile", "drone", "casualties", "ceasefire", "hostage", "bombing", "troops", "invade", "nuclear"],
    "Global Economy": ["economy", "market", "finance", "stock", "trade", "inflation", "rate", "bank", "currency", "oil", "gas", "energy", "supply", "debt", "gdp", "rececssion", "investment", "tax", "budget", "crypto", "fed", "ecb", "opec"],
    "Politics & Policy": ["politics", "election", "vote", "congress", "senate", "parliament", "leader", "president", "minister", "law", "bill", "court", "policy", "campaign", "party", "democrat", "republican", "tory", "labour", "polls", "scandal", "diplomacy", "summit", "treaty"],
    "Science & Tech": ["technology", "science", "space", "ai", "cyber", "internet", "cern", "nasa", "spacex", "apple", "google", "microsoft", "chip", "quantum", "robot", "pharma", "vaccine", "climate", "energy", "fusion", "biotech"],
    "Social & Rights": ["society", "rights", "protest", "strike", "labor", "health", "education", "immigration", "border", "refugee", "human", "women", "culture", "art", "media"],
    "Other": []
}

FETCH_LIMIT = 50 # Default (Tactical)

class NewsItem:
    def __init__(self, item_id, title, link, region, source_url, description=""):
        self.id = item_id
        self.original_title = self._sanitize(title)
        self.description = self._sanitize(description)[:500]
        self.link = link if self._valid_url(link) else None
        self.region = region
        self.source_url = source_url
        self.category = None # Will be assigned by AI or keyword
        
        # Computed fields
        self.embedding = None
        self.proximity_score = 0.0
        
        # Audit fields
        self.audit_tags = [] # e.g., ["keyword_fallback", "ai_classified"]

    def _sanitize(self, text):
        if not text: return ""
        # Remove HTML tags specifically
        clean = re.sub(r'<[^>]+>', '', str(text))
        return clean.strip()
    
    def _valid_url(self, url):
        return url and url.startswith("http")

class IroncladCollectorPro:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.active_items = []
        self.stats = {"fetched": 0, "classified": 0, "vectors": 0, "errors": 0}
        self.start_time = time.time()
        
        # Create output dirs
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs("public", exist_ok=True)
        os.makedirs("vector_cache", exist_ok=True)

    def fetch_signals(self):
        logging.info(f"📡 FASE 1: Recolección (Límite: {FETCH_LIMIT})...")
        cnt = 0
        
        for region, feeds in RSS_FEEDS.items():
            for url in feeds:
                try:
                    d = feedparser.parse(url)
                    for entry in d.entries[:FETCH_LIMIT]:
                        title = entry.get('title', '')
                        link = entry.get('link', '')
                        
                        # Extract description (RSS often uses 'summary' or 'description')
                        desc = entry.get('summary', '') or entry.get('description', '')
                        
                        if not title: continue
                        
                        # ID Generation
                        raw_id = f"{title}|{link}"
                        item_id = hashlib.md5(raw_id.encode()).hexdigest()
                        
                        # Regional Deduplication Logic
                        # Only check if this title exists WITHIN this region
                        region_items = [x for x in self.active_items if x.region == region]
                        
                        if not self.is_duplicate(title, region_items):
                            news = NewsItem(item_id, title, link, region, url, desc)
                            self.active_items.append(news)
                            cnt += 1
                        else:
                            # Audit: Track discarded duplicates? (Optional, maybe too verbose)
                            pass
                            
                except Exception as e:
                    logging.warning(f"Feed error {url}: {e}")
        
        self.stats["fetched"] = cnt
        logging.info(f"✅ Recolectados {cnt} items únicos (Regional Dedupe Active).")

    def is_duplicate(self, title, existing_items):
        # Ultra-simple Jaccard or exact match for speed
        t_clean = title.lower().strip()
        for item in existing_items:
            if t_clean == item.original_title.lower().strip(): return True
            # TODO: Add fuzzy logic here if needed via specialized module
        return False

    def run_triage(self):
        logging.info(f"🔎 FASE 2: Clasificación IA ({len(self.active_items)} items)...")
        
        # Batching for Gemini
        batch_size = 15
        items_to_classify = [x for x in self.active_items if not x.category]
        batches = [items_to_classify[i:i + batch_size] for i in range(0, len(items_to_classify), batch_size)]

        for batch in batches:
            try:
                self._classify_batch_ai(batch)
            except Exception as e:
                logging.error(f"Error Batch IA: {e}")
                logging.info(f"🛡️ Fallback recuperó {len(batch)} noticias.")
                self._classify_batch_keyword(batch)
                
        self.stats["classified"] = len(self.active_items)

    def _classify_batch_ai(self, batch):
        cat_list = ", ".join(CATEGORIES.keys())
        # Provide Title + Description for better context
        items_str = json.dumps([{"id": x.id, "text": f"{x.original_title} - {x.description[:100]}"} for x in batch])
        
        prompt = PROMPTS["CLASSIFY_USER"].replace("[catlist]", cat_list) + f"\n\nITEMS: {items_str}"
        
        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json")
        )
        
        try:
            res = json.loads(response.text)
            results = res.get("results", [])
            
            res_map = {r["id"]: r["category"] for r in results}
            
            for item in batch:
                if item.id in res_map:
                    item.category = res_map[item.id]
                    item.audit_tags.append("AI_class")
                else:
                    self._classify_single_keyword(item)
                    
        except json.JSONDecodeError:
            raise Exception("Invalid JSON from AI")

    def _classify_batch_keyword(self, batch):
        for item in batch:
            self._classify_single_keyword(item)

    def _classify_single_keyword(self, item):
        txt = (item.original_title + " " + item.description).lower()
        item.category = "Other"
        item.audit_tags.append("keyword_fallback")
        
        for cat, keywords in CATEGORIES.items():
            if any(k in txt for k in keywords):
                item.category = cat
                break

    def compute_vectors_and_proximity(self):
        logging.info("A FASE 3: Generación de Vectores y Proximidad (Global vs Regional)...")
        # For V4, we use a simpler text-embedding-004 approach for speed/quality
        
        texts = [x.original_title for x in self.active_items]
        if not texts: return

        # 1. Batch Embed all titles
        # In a real heavy production, we'd batch this. For <2000 items, one go implies multiple calls but managed by lib?
        # Let's batch manually to be safe.
        BATCH_EMBED = 100
        
        for i in range(0, len(self.active_items), BATCH_EMBED):
            batch = self.active_items[i:i+BATCH_EMBED]
            batch_texts = [x.original_title for x in batch]
            
            try:
                embeddings = self.client.models.embed_content(
                    model="text-embedding-004",
                    contents=batch_texts,
                )
                # Parse embeddings object
                for j, emb_result in enumerate(embeddings.embeddings):
                    batch[j].embedding = emb_result.values
            except Exception as e:
                logging.error(f"Embed Error: {e}")
        
        # 2. Compute Global Consensus (Centroid)
        valid_vecs = [x.embedding for x in self.active_items if x.embedding]
        if not valid_vecs: return
        
        dim = len(valid_vecs[0])
        centroid = [sum(col)/len(valid_vecs) for col in zip(*valid_vecs)]
        
        # 3. Compute Distance
        for item in self.active_items:
            if item.embedding:
                item.proximity_score = self._cosine_similarity(item.embedding, centroid)
                self.stats["vectors"] += 1

    def _cosine_similarity(self, v1, v2):
        dot = sum(a*b for a,b in zip(v1, v2))
        norm1 = math.sqrt(sum(a*a for a in v1))
        norm2 = math.sqrt(sum(a*a for a in v2))
        return dot / (norm1 * norm2) if norm1 and norm2 else 0

    def generate_narrative_syntheses(self):
        logging.info("🧠 FASE 4: Síntesis Narrativa Regional...")
        self.syntheses = {}
        
        # Group by Category + Region for synthesis
        # We want distinct regional voices
        
        synthesis_tasks = [] # (region, category, [items])
        
        # For the carousel, we organize by Category primarily, but we need the synthesis to be rich.
        # Let's synthesize by (Category + Region) then merge?
        # Or simpler: For each Category, generate ONE synthesis that mentions regional clashes.
        # PROMPT says: "Synthesize a coherent 'Situation Report' that captures the dominant narrative of this region."
        
        # Let's grab the TOP 5 categories by volume
        cat_counts = defaultdict(int)
        for i in self.active_items: cat_counts[i.category] += 1
        top_cats = sorted(cat_counts, key=cat_counts.get, reverse=True)[:5]
        
        final_syntheses = {} # cat -> text
        
        for cat in top_cats:
            cat_items = [x for x in self.active_items if x.category == cat]
            # Group these items by region
            region_map = defaultdict(list)
            for x in cat_items: region_map[x.region].append(x)
            
            # Select representative items from each region
            representative_headlines = []
            for reg, items in region_map.items():
                # Pick top 3 most "proximal" (central) or just first 3?
                # Let's pick 3 diverse ones
                top3 = items[:3]
                for x in top3:
                    representative_headlines.append(f"[{reg}] {x.original_title} | {x.description[:100]}")
            
            text_block = "\n".join(representative_headlines)
            
            # Send to AI
            task_prompt = PROMPTS["NARRATIVE_SYSTEM"].replace("{region}", "GLOBAL/MULTI-REGIONAL")
            user_msg = f"CATEGORY: {cat}\n\n{text_block}"
            
            try:
                resp = self.client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents=task_prompt + "\n\n" + user_msg
                )
                final_syntheses[cat] = resp.text.strip()
            except Exception as e:
                final_syntheses[cat] = "Analysis pending..."

        self.syntheses = final_syntheses

    def save_audit_csv(self):
        logging.info("💾 FASE 6: Guardando Auditoría (Excel)...")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        filename = os.path.join(DATA_DIR, f"run_{timestamp}.csv")
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f: # utf-8-sig for Excel
                writer = csv.writer(f)
                writer.writerow(["ID", "Region", "Category", "Source", "Title", "Description", "Proximity", "Tags"])
                
                for item in self.active_items:
                    writer.writerow([
                        item.id,
                        item.region,
                        item.category,
                        item.source_url,
                        item.original_title,
                        item.description,
                        f"{item.proximity_score:.4f}",
                        "|".join(item.audit_tags)
                    ])
            logging.info(f"✅ Auditoría guardada: {filename}")
        except Exception as e:
            logging.error(f"Error saving CSV: {e}")

    def export(self):
        logging.info("📦 FASE 7: Exportación JSON para Frontend...")
        
        # Group for Carousel
        carousel = []
        for cat, synthesis in self.syntheses.items():
            items = [x for x in self.active_items if x.category == cat]
            
            # Map items to particles
            particles = []
            for x in items:
                particles.append({
                    "id": x.id,
                    "title": x.original_title,
                    "titulo_es": x.original_title, # Duplicate for now
                    "titulo_en": x.original_title,
                    "region": x.region,
                    "proximity_score": x.proximity_score,
                    "url": x.link
                })
            
            # Meta metrics
            avg = sum(p["proximity_score"] for p in particles) / len(particles) if particles else 0
            
            carousel.append({
                "area": cat,
                "sintesis": synthesis,
                "sintesis_en": synthesis, # Placeholder for translation
                "count": len(items),
                "avg_proximity": avg,
                "particulas": particles
            })
            
        final = {
            "carousel": carousel, 
            "meta": {"generated": datetime.datetime.now().isoformat()}
        }
        
        with open("public/gravity_carousel.json", "w", encoding='utf-8') as f:
            json.dump(final, f, indent=2)

    def run(self):
        try:
            self.fetch_signals()
            self.run_triage()
            self.compute_vectors_and_proximity()
            self.generate_narrative_syntheses()
            self.save_audit_csv() # NEW: Audit Step
            self.export()
            return True
        except Exception as e:
            logging.error(f"FATAL: {e}", exc_info=True)
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="tactical")
    args = parser.parse_args()
    
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("Set GEMINI_API_KEY"); sys.exit(1)
        
    col = IroncladCollectorPro(key)
    col.run()

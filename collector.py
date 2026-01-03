import os, json, datetime, time, urllib.request, hashlib, re, sys, math, unicodedata
import xml.etree.ElementTree as ET
from collections import defaultdict
from google import genai

# --- CONFIGURACIÓN ---
AREAS_ESTRATEGICAS = [
    "Seguridad y Conflictos", "Economía y Sanciones", "Energía y Recursos", 
    "Soberanía y Alianzas", "Tecnología y Espacio", "Sociedad y Derechos"
]

NORMALIZER_REGIONS = {
    "USA": "USA", "RUSSIA": "RUSSIA", "CHINA": "CHINA", "EUROPE": "EUROPE", 
    "LATAM": "LATAM", "MID_EAST": "MID_EAST", "INDIA": "INDIA", "AFRICA": "AFRICA", "GLOBAL": "GLOBAL"
}

# [Mantenemos el diccionario FUENTES previo]

class CollectorV29_5:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)
        self.matrix = defaultdict(list)
        self.vault = {}
        self.raw_list = []

    def clean_text(self, text):
        if not text: return ""
        text = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', text, flags=re.DOTALL)
        return re.sub(r'<[^>]+>', '', text).strip()

    def fuzzy_match_area(self, area_name):
        if not area_name: return None
        def normalize(s):
            return "".join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')
        target = normalize(area_name)
        for official in AREAS_ESTRATEGICAS:
            if target in normalize(official) or normalize(official) in target:
                return official
        return None

    def run(self):
        # --- PASO 1: INGESTA ---
        print("🌍 PASO 1: Ingesta e Indexación...")
        id_counter = 0
        for region, urls in FUENTES.items():
            for url in urls:
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        root = ET.fromstring(response.read())
                        items = root.findall('.//item') or root.findall('.//{*}entry')
                        for n in items[:30]:
                            title_elem = n.find('title') or n.find('{*}title')
                            link_elem = n.find('link') or n.find('{*}link')
                            if title_elem is None: continue
                            
                            title = self.clean_text(title_elem.text)
                            link = (link_elem.text if link_elem is not None and link_elem.text else link_elem.attrib.get('href', '') if link_elem is not None else f"no-link-{id_counter}").strip()
                            desc_node = n.find('description') or n.find('{*}summary')
                            snippet = self.clean_text(desc_node.text if desc_node is not None else "")
                            
                            nid = str(id_counter)
                            self.vault[nid] = {"link": link, "region": region, "snippet": snippet}
                            self.raw_list.append({"id": nid, "title": title})
                            id_counter += 1
                except: continue
        print(f"✅ Bóveda: {len(self.vault)} registros.")

        # --- PASO 2: TRIAJE CON VALIDACIÓN DE ID ---
        print("\n🔎 PASO 2: Triaje por IDs (Validación Estricta)...")
        batch_size = 45
        for i in range(0, len(self.raw_list), batch_size):
            batch = self.raw_list[i:i+batch_size]
            prompt = f"Clasifica en {AREAS_ESTRATEGICAS}. Responde JSON: {{'res': [{{'id': '...', 'area': '...', 'titulo_es': '...'}}]}}\n" + \
                     "\n".join([f"ID:{x['id']}|{x['title']}" for x in batch])
            try:
                res = self.client.models.generate_content(model="gemini-2.0-flash", contents=prompt, config={'response_mime_type': 'application/json'})
                # Manejo de JSON inválido
                raw_json = res.text.strip()
                data = json.loads(raw_json[raw_json.find('{'):raw_json.rfind('}')+1])
                
                for c in data.get('res', []):
                    clean_id = str(c.get('id')).strip() # Limpieza de ID
                    matched = self.fuzzy_match_area(c.get('area'))
                    
                    if matched and clean_id in self.vault:
                        meta = self.vault[clean_id]
                        self.matrix[matched].append({
                            "titulo_es": c['titulo_es'], "link": meta['link'], "region": meta['region'],
                            "analysis_base": f"{c['titulo_es']}. {meta['snippet']}"
                        })
            except Exception as e:
                print(f"   ⚠️ Error batch: {e}")

        # --- VERIFICACIÓN DE MATRIZ VACÍA ---
        print("\n📊 ESTADO DE MATRIZ:")
        total_nodes = 0
        for area in AREAS_ESTRATEGICAS:
            count = len(self.matrix[area])
            total_nodes += count
            print(f"   - {area}: {count} noticias")

        if total_nodes == 0:
            print("⚠️ MATRIZ VACÍA. Activando Fallback de Emergencia...")
            self.matrix[AREAS_ESTRATEGICAS[0]].append({
                "titulo_es": "Flujo de datos en mantenimiento", "link": "#", "region": "GLOBAL",
                "analysis_base": "Sin datos disponibles en este ciclo."
            })

        # --- PASO 3: TRIANGULACIÓN CON LOG DE PROGRESO ---
        print("\n📐 PASO 3: Triangulación Vectorial...")
        final_carousel = []
        for area in AREAS_ESTRATEGICAS:
            nodes = self.matrix.get(area, [])
            if not nodes: continue
            
            print(f"   🚀 Procesando [{area}]...")
            node_vectors = []
            try:
                node_vectors = self.client.models.embed_content(model="text-embedding-004", content=[n['analysis_base'] for n in nodes], config={'task_type': 'RETRIEVAL_DOCUMENT'}).embeddings
                node_vectors = [v.values for v in node_vectors]
            except Exception as e:
                print(f"   ❌ Fallo Embeddings en {area}: {e}. Usando proximidad fija.")
                node_vectors = [[0.1] * 768 for _ in nodes] # Vector dummy

            # Cálculo de centroide
            dim = len(node_vectors[0])
            centroid = [sum(v[j] for v in node_vectors)/len(node_vectors) for j in range(dim)]
            
            particles = []
            for idx, node in enumerate(nodes):
                # Similitud Coseno
                v = node_vectors[idx]
                dot = sum(a*b for a,b in zip(v, centroid))
                n1, n2 = math.sqrt(sum(a*a for a in v)), math.sqrt(sum(b*b for b in centroid))
                sim = dot / (n1 * n2) if n1*n2 > 0 else 0
                prox = round(max(0, min(100, (sim - 0.75) * 400)), 1) if len(nodes) > 1 else 100.0
                
                particles.append({
                    "id": hashlib.md5(node['link'].encode()).hexdigest()[:8],
                    "titulo": node['titulo_es'], "link": node['link'], 
                    "bloque": NORMALIZER_REGIONS.get(node['region'], "GLOBAL"), 
                    "proximidad": prox, "metodo": "Vector Analysis",
                    "sesgo": "Alineada" if prox > 80 else "Divergente"
                })
            
            final_carousel.append({
                "area": area, "punto_cero": f"Resumen estratégico de {area}", 
                "color": self.get_color(area), "particulas": particles[:15]
            })

        # --- VERIFICACIÓN DE ARCHIVO FINAL ---
        with open("gravity_carousel.json", "w", encoding="utf-8") as f:
            json.dump({"carousel": final_carousel}, f, indent=2, ensure_ascii=False)
        
        if os.path.exists("gravity_carousel.json") and os.path.getsize("gravity_carousel.json") > 0:
            print(f"✅ ÉXITO: gravity_carousel.json generado ({os.path.getsize('gravity_carousel.json')} bytes)")
        else:
            print("❌ ERROR CRÍTICO: El archivo final no existe o está vacío.")

    def get_color(self, a):
        return {"Seguridad y Conflictos": "#ef4444", "Economía y Sanciones": "#3b82f6", "Energía y Recursos": "#10b981", "Soberanía y Alianzas": "#f59e0b", "Tecnología y Espacio": "#8b5cf6", "Sociedad y Derechos": "#ec4899"}.get(a, "#fff")

if __name__ == "__main__":
    key = os.environ.get("GEMINI_API_KEY")
    if key: CollectorV29_5(key).run()

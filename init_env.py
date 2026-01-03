#!/usr/bin/env python3
import os, sys, tempfile

def initialize_environment():
    print("🛠️ Inicializando entorno de Proximity Engine...")
    required_dirs = ["vector_cache", "historico_noticias/diario", "historico_noticias/semanal"]
    
    for directory in required_dirs:
        try:
            # Si existe como archivo y no como carpeta, lo borramos
            if os.path.exists(directory) and not os.path.isdir(directory):
                os.remove(directory)
            
            os.makedirs(directory, mode=0o777, exist_ok=True)
            
            # Test de escritura
            test_file = os.path.join(directory, ".test_write")
            with open(test_file, 'w') as f: f.write("test")
            os.remove(test_file)
            print(f"✅ {directory}: OK")
            
        except Exception as e:
            print(f"❌ {directory}: Error - {e}")
            if directory == "vector_cache":
                temp_dir = tempfile.mkdtemp(prefix="v_cache_")
                with open(".proximity_env", 'w') as f: f.write(f"CACHE_DIR={temp_dir}\n")
                print(f"   📁 Fallback temporal: {temp_dir}")
    return True

if __name__ == "__main__":
    initialize_environment()
    sys.exit(0)

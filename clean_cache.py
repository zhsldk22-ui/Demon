import os
import shutil
import sys

def clean_pycache(path):
    for root, dirs, files in os.walk(path):
        if '__pycache__' in dirs:
            pycache_path = os.path.join(root, '__pycache__')
            print(f"Removing {pycache_path}")
            try:
                shutil.rmtree(pycache_path)
            except OSError as e:
                print(f"Error removing {pycache_path}: {e}", file=sys.stderr)

if __name__ == "__main__":
    clean_pycache('.')

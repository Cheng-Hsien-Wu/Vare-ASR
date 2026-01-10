
import os
import subprocess
import shutil
import sys
import ctranslate2
import faster_whisper 

def run_flet_pack_official():
    """
    Final Release Build Strategy - OFFICIAL FLET PACK
    
    Since 'torch' is NOT in the environment (vare_asr_3_10), 
    we don't need 'exclude-module torch' or custom PyInstaller hacks.
    We can use the standard 'flet pack' command which handles Icons perfectly.
    
    Pre-requisites:
    - Environment MUST NOT have torch installed.
    - System MUST have NVIDIA CUDA Toolkit (for CTranslate2 dependencies).
    """
    print("="*60)
    print("📦  Starting 'flet pack' (Official Mode - Torch Free)")
    print("="*60)
    
    # Pre-clean
    if os.path.exists("dist"):
        try:
            shutil.rmtree("dist")
            print("🧹  Cleaned old dist")
        except: pass

    # 1. Locate Critical Packages for explicit bundling
    # Even with flet pack, we often need to tell it where data files are.
    ct2_dir = os.path.dirname(ctranslate2.__file__)
    fw_dir = os.path.dirname(faster_whisper.__file__)
    
    print(f"🔎  Bundling CTranslate2: {ct2_dir}")
    print(f"🔎  Bundling Faster-Whisper: {fw_dir}")
    
    # 2. Construct flet pack command
    # flet pack main.py --icon ... --add-data ...
    
    cmd = [
        "flet", "pack", "main.py",
        "--name", "Vare",
        "--icon", "assets/icon.png", # Flet pack handles png->ico conversion!
        "--copyright", "Copyright (C) 2026 Cheng-Hsien Wu",
        "--product-name", "Vare",
        "--product-version", "0.5.1",
        
        # Data
        "--add-data", "assets;assets",
        "--add-data", "locales;locales", 
        "--add-data", f"{ct2_dir};ctranslate2", 
        "--add-data", f"{fw_dir};faster_whisper", 
        
        # Hidden Imports (Safety net)
        "--hidden-import", "flet",
        "--hidden-import", "faster_whisper",
        "--hidden-import", "ctranslate2",
        "--hidden-import", "tokenizers",
        "--hidden-import", "huggingface_hub",
        "--hidden-import", "scipy",
        "--hidden-import", "numpy",
        "--hidden-import", "pydantic",
        "--hidden-import", "engineio.async_drivers.threading",
        "--hidden-import", "filelock",
        "--hidden-import", "uvicorn",
        "--hidden-import", "websockets",
        "--hidden-import", "google.generativeai",
        "--hidden-import", "anthropic",
        "--hidden-import", "openai",
        "--hidden-import", "PIL"
    ]
    
    print(f"▶️  Command: {' '.join(cmd)}")
    
    # 3. Run
    # Shell=True to find 'flet' in path
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print("\n" + "="*60)
        print("✅  Pack Success!")
        print("="*60)
        print("📁  Output location: dist/Vare.exe (or dist/Vare dir)")
    else:
        print("\n❌  Pack Failed.")

if __name__ == "__main__":
    run_flet_pack_official()

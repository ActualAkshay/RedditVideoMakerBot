import os
from os.path import exists
import shutil
from utils.console import print_step, print_substep

def cleanup():
    """Deletes assets in assets/temp
    """
    temp_path = "./assets/temp"
    print_step("Removing temporary files 🗑")
    if exists(temp_path):
        file_count = sum(len(files) for _, _, files in os.walk(temp_path))
        shutil.rmtree(temp_path)
    print_substep(f"Removed {file_count} temporary files 🗑")


"""
Colab environment setup utilities.
Call setup_colab() as the first cell in every notebook.
"""
import os
import sys

DRIVE_PROJECT_PATH = "/content/drive/MyDrive/potato-defect-finetuning"


def setup_colab(project_path: str = DRIVE_PROJECT_PATH):
    """
    Mounts Google Drive and adds the project's src/ folder to sys.path
    so notebooks can `import` from src modules.

    Returns the project root path for convenience.
    """
    try:
        from google.colab import drive
        drive.mount('/content/drive', force_remount=False)
        print("Drive mounted.")
    except ImportError:
        print("Not running in Colab — skipping Drive mount (assuming local repo).")

    src_path = os.path.join(project_path, "src")
    if src_path not in sys.path:
        sys.path.append(src_path)
        print(f"Added to sys.path: {src_path}")

    if not os.path.exists(project_path):
        print(f"WARNING: project path does not exist yet: {project_path}")
        print("Create the folder structure in Drive before continuing.")
    else:
        print(f"Project root: {project_path}")

    return project_path


def ensure_folders(project_path: str = DRIVE_PROJECT_PATH):
    """
    Creates the standard project folder structure if it doesn't exist.
    Safe to run multiple times.
    """
    folders = [
        "data/raw", "data/processed", "data/splits",
        "src/data", "src/models", "src/training",
        "src/evaluation", "src/pipeline", "src/utils",
        "notebooks", "configs",
        "checkpoints/linear_probe", "checkpoints/full_finetune", "checkpoints/lora",
        "experiments", "report", "tests",
    ]
    for folder in folders:
        path = os.path.join(project_path, folder)
        os.makedirs(path, exist_ok=True)
    print(f"Folder structure ensured under: {project_path}")


def gpu_check():
    """Prints GPU info if available."""
    import torch
    if torch.cuda.is_available():
        print(f"GPU available: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    else:
        print("No GPU detected — check Colab runtime type (Runtime > Change runtime type > GPU).")
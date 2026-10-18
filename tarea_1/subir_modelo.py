"""Sube el modelo final (sin checkpoints ni estado del optimizador) a Hugging Face Hub.

Uso:  HF_TOKEN=... python subir_modelo.py [carpeta_del_modelo]   (por defecto: modelo/)
"""
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_HF = "gabriela-pozo/noticias-pe-distilbert"
OBLIGATORIOS = ["config.json", "model.safetensors", "etiquetas.json"]
TOKENIZER = ["tokenizer.json", "tokenizer_config.json", "vocab.txt", "special_tokens_map.json"]

token = os.environ.get("HF_TOKEN")
if not token:
    sys.exit("Error: define la variable de entorno HF_TOKEN con un token de escritura de Hugging Face.")

carpeta = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "modelo")
if "checkpoint" in carpeta.as_posix():
    sys.exit(f"Error: {carpeta} es un checkpoint; guarda el modelo final con trainer.save_model().")

faltan = [f for f in OBLIGATORIOS if not (carpeta / f).is_file()]
tokenizer = [f for f in TOKENIZER if (carpeta / f).is_file()]
if faltan or not tokenizer:
    sys.exit(f"Error: en {carpeta} faltan {faltan or 'los archivos del tokenizer'}.")

api = HfApi(token=token)
api.create_repo(REPO_HF, exist_ok=True)
api.upload_folder(
    repo_id=REPO_HF,
    folder_path=carpeta,
    allow_patterns=OBLIGATORIOS + tokenizer,
    commit_message="Modelo final DistilBERT para noticias peruanas",
)
print(f"Listo: https://huggingface.co/{REPO_HF}")

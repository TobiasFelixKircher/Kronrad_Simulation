import yaml
from pathlib import Path

# Standardpfad zur YAML-Datei
pfad = Path("parameter.yaml")

# Lade die Parameter beim Import
if not pfad.exists():
    raise FileNotFoundError(f"Parameterdatei nicht gefunden: {pfad}")

try:
    with open(pfad, "r") as f:
        parameter = yaml.safe_load(f)
except yaml.YAMLError as e:
    raise ValueError(f"Fehler beim Parsen der YAML-Datei: {e}")
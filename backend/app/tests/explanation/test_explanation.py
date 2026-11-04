import json
from pathlib import Path
from app.services.explanation import ExplanationGenerator

def main():
    # Détermination dynamique du chemin vers mock_data.json
    # BASE_DIR pointe vers le dossier 'app'
    base_dir = Path(__file__).resolve().parents[2]
    json_path = base_dir / "services" / "data" / "mock_data.json"

    # Chargement du Mock JSON
    with open(json_path, "r", encoding="utf-8") as f:
        mock_payload = json.load(f)

    generator = ExplanationGenerator()
    results = generator.explain(mock_payload)

    print("=== 🇫🇷 EXPLICATION FRANÇAIS ===")
    print(results["fr"])
    print("\n=== 🇲🇦 EXPLICATION DARIJA ===")
    print(results["darija"])

if __name__ == "__main__":
    main()
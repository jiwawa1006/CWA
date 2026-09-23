import json
from pathlib import Path


def test_sample_json_exists():
  sample_file = Path(__file__).parent / "sample_weather.json"
  assert sample_file.exists()
  with open(sample_file, "r", encoding="utf-8") as f:
    data = json.load(f)
  assert data["success"] == "true"
  assert "records" in data

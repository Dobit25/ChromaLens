import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

def test_t09_segmentation_eval_schema_compliance(tmp_path):
    output_json = tmp_path / "result.json"
    
    # Run the script in auto-rate mode to bypass prompts
    cmd = [
        sys.executable,
        str(ROOT / "scripts/t09_segmentation_eval.py"),
        "--auto-rate", "3",
        "--output", str(output_json.resolve())
    ]
    
    # Needs to be run from ROOT
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    assert result.returncode == 0, f"Script failed: {result.stderr}"
    
    assert output_json.exists(), "Output JSON was not created"
    
    import jsonschema
    
    # Validate against schema
    schema_path = ROOT / "evaluation/schema/t09-result.schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
        
    with open(output_json, "r", encoding="utf-8") as f:
        instance = json.load(f)
        
    # This will raise ValidationError if invalid
    jsonschema.validate(instance=instance, schema=schema)
    
    assert instance["result_status"] == "PARTIAL", "Should be PARTIAL because some assets are TO_BE_ACQUIRED"
    
    # Check that IoU is NOT_APPLICABLE for unannotated cases
    for metric in instance["metrics"]:
        if metric["name"] == "segmentation_iou":
            assert metric["status"] == "NOT_APPLICABLE"
            assert metric["value"] is None

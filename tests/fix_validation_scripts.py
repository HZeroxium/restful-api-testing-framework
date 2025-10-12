"""
Script to fix validation scripts with incorrect status_code access.
"""

import sys
from pathlib import Path
import json

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


def fix_validation_scripts():
    """Fix validation scripts in the dataset."""

    dataset_id = "44358bba-f96c-448d-894d-24474f269bd9"
    scripts_file = Path(f"data/datasets/{dataset_id}/validation_scripts.json")

    if not scripts_file.exists():
        print(f"Validation scripts file not found: {scripts_file}")
        return

    # Read current scripts
    with open(scripts_file, "r") as f:
        data = json.load(f)

    scripts_dict = data.get("scripts", {})
    scripts = list(scripts_dict.values())
    print(f"Found {len(scripts)} validation scripts")

    fixed_count = 0

    for script in scripts:
        original_code = script["validation_code"]
        fixed_code = original_code

        # Fix response.status_code -> response.get('status_code')
        if "response.status_code" in original_code:
            fixed_code = fixed_code.replace(
                "response.status_code", "response.get('status_code')"
            )
            print(
                f"Fixed script {script['name']}: response.status_code -> response.get('status_code')"
            )
            fixed_count += 1

        # Fix response.get('status') -> response.get('status_code') for consistency
        if "response.get('status')" in original_code:
            fixed_code = fixed_code.replace(
                "response.get('status')", "response.get('status_code')"
            )
            print(
                f"Fixed script {script['name']}: response.get('status') -> response.get('status_code')"
            )
            fixed_count += 1

        # Update the script if it was fixed
        if fixed_code != original_code:
            script["validation_code"] = fixed_code
            print(f"Updated validation code for: {script['name']}")

    if fixed_count > 0:
        # Write back the fixed scripts
        with open(scripts_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Fixed {fixed_count} validation scripts and saved to {scripts_file}")
    else:
        print("No scripts needed fixing")


if __name__ == "__main__":
    fix_validation_scripts()

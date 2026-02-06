import toml
import json
import os

def convert_toml_to_json(toml_path, json_path, is_user_db=False):
    """
    Reads a TOML file and writes it to a JSON file.
    """
    try:
        # Check if source file exists
        if not os.path.exists(toml_path):
            print(f"Error: Source file not found at {toml_path}")
            return

        # Read TOML
        with open(toml_path, 'r', encoding='utf-8') as f:
            data = toml.load(f)

        # Structure adjustment for user_db to match the example provided
        # The example user_db.json wraps the content in a "data" key.
        if is_user_db:
            # Check if 'surroundings' is missing in TOML but present in JSON example
            # If the TOML doesn't have it, we might need to mock it or leave it as is if exact match isn't required.
            # Based on the prompt, it seems we just want to convert the existing TOML content.
            # However, looking at the user_db.json example, it has a top-level "data" key.
            # The user_db.toml starts directly with [device].
            final_data = {"data": data}
            
            # The example user_db.json also has a "surroundings" key inside "data".
            # If it's not in the TOML, we should probably add a placeholder or check if it needs to be merged.
            # Since the prompt asks to modify the format *of* the TOML files *into* JSON, 
            # I will wrap the TOML content in "data" to match the structure of user_db.json.
        else:
            # For db.toml (assumed to correspond to db.json), usually the structure is flat lists/dicts.
            final_data = data

        # Ensure directory exists
        os.makedirs(os.path.dirname(json_path), exist_ok=True)

        # Write JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        
        print(f"Successfully converted {toml_path} to {json_path}")

    except Exception as e:
        print(f"Error converting {toml_path}: {str(e)}")

# Define paths
base_path = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/tau2/domains/telecom"
output_base_path = "/mnt/shared-storage-user/lvyaxing/Agent_Honesty/tau2-bench/data/tau2/domains/telecom"

# Define file pairs
files_to_convert = [
    {
        "toml": os.path.join(base_path, "user_db.toml"),
        "json": os.path.join(output_base_path, "user_db.json"),
        "is_user_db": True
    },
    {
        "toml": os.path.join(base_path, "db.toml"),
        "json": os.path.join(output_base_path, "db.json"),
        "is_user_db": False
    }
]

# Install toml if missing (not strictly possible inside script but good for user awareness)
# pip install toml

# Run conversion
if __name__ == "__main__":
    for file_info in files_to_convert:
        convert_toml_to_json(file_info["toml"], file_info["json"], file_info["is_user_db"])
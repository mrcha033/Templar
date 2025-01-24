import yaml
import json

# Load the YAML file
with open('tuning.yaml', 'r', encoding='utf-8') as yaml_file:
    data = yaml.safe_load(yaml_file)

# Open a new JSONL file for writing
with open('tuning.jsonl', 'w', encoding='utf-8') as jsonl_file:
    for item in data:
        # Create a JSON object for each input-output pair
        json_object = {
            "messages": [
                {"role": "user", "content": item["input"]},
                {"role": "assistant", "content": item["output"]}
            ]
        }
        # Write the JSON object to the file as a new line
        jsonl_file.write(json.dumps(json_object, ensure_ascii=False) + "\n")
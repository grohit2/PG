import json

def post_process_data(data):
    """
    Post-processes the data to remove units from the "range" field and strip extra white spaces.

    Args:
        data (dict): The dictionary containing patient details and test results.

    Returns:
        dict: The modified data dictionary with updated "range" fields.
    """
    for test in data.get("tests", []):
        for detail in test.get("details", []):
            # Get and strip "range" and "units"
            range_str = detail.get("range", "").strip()
            units = detail.get("units", "").strip()
            
            # Remove units if "range" ends with them
            if range_str.endswith(units):
                range_str = range_str[:-len(units)].strip()
            
            # Update the "range" field
            detail["range"] = range_str
    
    return data

def read_and_process_json(file_path):
    """
    Reads JSON data from a file, processes it, and returns the modified data.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        dict: The processed data dictionary.
    """
    try:
        # Read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        # Process the data
        processed_data = post_process_data(data)
        return processed_data
    
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: The file {file_path} contains invalid JSON.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
        return None
    
def save_processed_data(data, output_file_path):
    """
    Saves the processed data to a new JSON file.

    Args:
        data (dict): The processed data to save.
        output_file_path (str): Path to the output JSON file.
    """
    try:
        with open(output_file_path, 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Processed data saved to {output_file_path}")
    except Exception as e:
        print(f"Error saving processed data: {str(e)}")

if __name__ == "__main__":
    # File path as provided
    file_path = "/Users/rohitgarlapati/Documents/GitHub/PG/data_scraping/patient_data.json"
    
    # Read and process the data
    processed_data = read_and_process_json(file_path)
    
    if processed_data:
        # Optional: Save the processed data to a new file
        output_file_path = "/Users/rohitgarlapati/Documents/GitHub/PG/data_scraping/processed_patient_data.json"
        save_processed_data(processed_data, output_file_path)
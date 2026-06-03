import json
import os

def read_history(file_path: str = 'history.json') -> list:
    """
    Reads calculation history from a specified JSON file.

    Args:
        file_path (str): The path to the JSON file. Defaults to 'history.json'.

    Returns:
        list: A list of calculation records. If the file does not exist or is empty,
              an empty list is returned.
    """
    if not os.path.exists(file_path):
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Handle empty file case
            content = f.read()
            if not content:
                return []
            # Reset file pointer and load JSON
            f.seek(0)
            data = json.load(f)
            if not isinstance(data, list):
                # If file content is not a list, return empty list
                return []
            return data
    except json.JSONDecodeError:
        # Handle malformed JSON
        return []
    except Exception as e:
        # Catch any other unexpected errors during read
        print(f"An error occurred while reading {file_path}: {e}")
        return []

def write_history(data: list, file_path: str = 'history.json') -> None:
    """
    Writes calculation history to a specified JSON file.

    Args:
        data (list): The list of calculation records to write.
        file_path (str): The path to the JSON file. Defaults to 'history.json'.

    Returns:
        None.
    """
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        print(f"An error occurred while writing to {file_path}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during write
        print(f"An unexpected error occurred during write to {file_path}: {e}")

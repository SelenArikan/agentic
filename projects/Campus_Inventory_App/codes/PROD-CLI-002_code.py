import json
import os
import sys


def load_products(file_path: str) -> list:
    """
    Reads product data from the specified JSON file.

    If the file does not exist or is malformed, an empty list is returned.
    Errors are printed to stderr.

    Args:
        file_path (str): The full path to the products.json file.

    Returns:
        list: A list of product dictionaries, or an empty list if an error occurs
              or the file does not exist/is empty.
    """
    if not os.path.exists(file_path):
        # print(f"INFO: Product data file not found at '{file_path}'. Returning empty list.", file=sys.stderr)
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
            # Ensure the loaded data is a list, if not, treat as malformed
            if not isinstance(products, list):
                print(f"ERROR: Product data in '{file_path}' is not a list. Returning empty list.", file=sys.stderr)
                return []
            return products
    except json.JSONDecodeError as e:
        print(f"ERROR: Malformed JSON in '{file_path}': {e}. Returning empty list.", file=sys.stderr)
        return []
    except IOError as e:
        print(f"ERROR: Could not read product data file '{file_path}': {e}. Returning empty list.", file=sys.stderr)
        return []
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while loading products from '{file_path}': {e}. Returning empty list.", file=sys.stderr)
        return []


def save_products(file_path: str, products: list) -> None:
    """
    Writes a list of product data to the specified JSON file.

    Ensures the directory for the file exists. Errors are printed to stderr.

    Args:
        file_path (str): The full path to the products.json file.
        products (list): A list of product dictionaries to be saved.

    Returns:
        None
    """
    dir_path = os.path.dirname(file_path)
    if dir_path:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            print(f"ERROR: Could not create directory '{dir_path}': {e}. Cannot save products.", file=sys.stderr)
            return

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"ERROR: Could not write product data to file '{file_path}': {e}.", file=sys.stderr)
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while saving products to '{file_path}': {e}.", file=sys.stderr)

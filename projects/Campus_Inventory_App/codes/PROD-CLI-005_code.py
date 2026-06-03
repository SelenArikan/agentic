# filename: product_storage.py
import json
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_PRODUCTS = [
    {"id": "P001", "name": "Laptop Pro X", "category": "Electronics", "price": 1200.0, "description": "High performance laptop."},
    {"id": "P002", "name": "Wireless Mouse", "category": "Electronics", "price": 25.5, "description": "Ergonomic wireless mouse."},
    {"id": "P003", "name": "Coffee Mug", "category": "Home Goods", "price": 10.0, "description": "Ceramic coffee mug."},
    {"id": "P004", "name": "Mechanical Keyboard", "category": "Electronics", "price": 99.99, "description": "Tactile mechanical keyboard for typing."},
    {"id": "P005", "name": "Desk Lamp", "category": "Home Goods", "price": 45.0, "description": "Adjustable LED desk lamp."}
]

def load_products(file_path: str) -> list[dict]:
    """
    Loads product data from the specified JSON file.
    Handles file not found and JSON decoding errors.

    Args:
        file_path (str): The path to the JSON file containing product data.

    Returns:
        list[dict]: A list of product dictionaries. Returns default data if file
                    is not found, an empty list on decoding errors, or the loaded data.
    """
    products = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, list):
                logger.warning("Product data file contains invalid format (not a list). Overwriting with default data.")
                save_products(file_path, DEFAULT_PRODUCTS) # Overwrite with default if malformed
                return DEFAULT_PRODUCTS
            products = data
    except FileNotFoundError:
        logger.info(f"Product data file not found at '{file_path}'. Creating with default data.")
        save_products(file_path, DEFAULT_PRODUCTS)
        products = DEFAULT_PRODUCTS
    except json.JSONDecodeError:
        logger.error(f"Error decoding product data JSON from '{file_path}'. Returning empty list.")
        products = []
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading products from '{file_path}': {e}")
        products = []
    return products

def save_products(file_path: str, products: list[dict]) -> None:
    """
    Saves a list of product dictionaries to the specified JSON file.
    Creates the directory if it doesn't exist.

    Args:
        file_path (str): The path to the JSON file.
        products (list[dict]): A list of product dictionaries to save.
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving product data to '{file_path}': {e}")

# filename: product_search.py
import logging

logger = logging.getLogger(__name__)

def parse_query(query_string: str) -> dict:
    """
    Parses a user-provided search query string into a dictionary of search criteria.
    Supports 'field:value' syntax and defaults to 'name' if no field is specified.
    Handles multiple criteria and combines multi-word name searches, prioritizing
    explicit 'name:' field values but appending other non-field tokens.

    Args:
        query_string (str): The raw search string entered by the user.

    Returns:
        dict: A dictionary where keys are search fields (e.g., 'name', 'id', 'category')
              and values are the corresponding search terms.
    """
    criteria = {}
    general_name_terms = []

    tokens = query_string.split()

    for token in tokens:
        if ':' in token:
            field, value = token.split(':', 1)
            criteria[field.lower()] = value # Explicit field overwrites if duplicated
        else:
            general_name_terms.append(token)

    # Combine explicit 'name' criteria with general terms
    if general_name_terms:
        current_name = criteria.get('name', '')
        if current_name:
            criteria['name'] = current_name + ' ' + ' '.join(general_name_terms)
        else:
            criteria['name'] = ' '.join(general_name_terms)

    return criteria

def search_products(products: list[dict], search_criteria: dict) -> list[dict]:
    """
    Filters a list of products based on the provided search criteria.
    Supports searching by 'name', 'id', and 'category'. Name and category
    searches are case-insensitive and partial matches. ID search is exact.

    Args:
        products (list[dict]): A list of product dictionaries to search through.
        search_criteria (dict): A dictionary of criteria
                                (e.g., {'name': 'laptop', 'category': 'electronics'}).

    Returns:
        list[dict]: A list of product dictionaries matching the search criteria.
                    Returns an empty list if search_criteria is empty.
    """
    if not search_criteria:
        return [] # As per spec, empty criteria yields no results.

    filtered_products = []

    for product in products:
        match = True
        for field, value in search_criteria.items():
            product_field_value = product.get(field)

            if product_field_value is None:
                match = False # Field missing in product
                break

            if field == 'id':
                if product_field_value != value:
                    match = False
                    break
            elif field in ['name', 'category']:
                if value.lower() not in str(product_field_value).lower():
                    match = False
                    break
            else:
                # If a criterion is provided for a field that is not 'id', 'name', or 'category',
                # it's considered an unsupported field for searching based on the spec.
                # This makes the product not match if such a criterion is present.
                match = False
                break
        
        if match:
            filtered_products.append(product)

    return filtered_products

# filename: main.py
import logging
from product_storage import load_products
from product_search import parse_query, search_products

# Configure logging at the application's entry point
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PRODUCT_DATA_FILE = 'data/products.json'

def display_product(product: dict) -> None:
    """
    Prints the formatted details of a single product to the console.

    Args:
        product (dict): A dictionary representing a single product.
    """
    print('--- Product Details ---')
    print(f"ID: {product.get('id', 'N/A')}")
    print(f"Name: {product.get('name', 'N/A')}")
    print(f"Category: {product.get('category', 'N/A')}")
    print(f"Price: ${product.get('price', 0.0):.2f}")
    print(f"Description: {product.get('description', 'N/A')}")
    print('-----------------------')


def display_results(results: list[dict]) -> None:
    """
    Displays the search results. If no products are found, an appropriate message is shown.
    Otherwise, each product is displayed using `display_product`.

    Args:
        results (list[dict]): A list of product dictionaries matching the search criteria.
    """
    if not results:
        print('No products found matching your search criteria.')
    else:
        print(f'\nFound {len(results)} product(s):')
        for product in results:
            display_product(product)
            print() # Add a newline for better separation between products


def main_menu() -> None:
    """
    The main loop of the CLI application. Loads product data, prompts the user for
    search queries, processes them, displays results, and handles program exit.
    Includes options to keep searching or exit.
    """
    products: list[dict] = []

    print("Loading product data...")
    products = load_products(PRODUCT_DATA_FILE)

    if not products:
        logger.warning("Could not load any product data. Search will yield no results.")

    while True:
        query_input = input("Enter search query (e.g., name:laptop, id:P001, category:electronics, or just 'laptop', or 'exit' to quit): ").strip()

        if query_input.lower() == 'exit':
            print("Exiting product search. Goodbye!")
            break

        if not query_input:
            print("Error: Search query cannot be empty. Please enter a query or 'exit'.")
            continue

        search_criteria = parse_query(query_input)
        results = search_products(products, search_criteria)
        display_results(results)

        print("-" * 30) # Separator for next search

if __name__ == "__main__":
    main_menu()

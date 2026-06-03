import sys

def display_menu():
    """
    Prints the main menu options to the console.

    Parameters:
        None

    Returns:
        None
    """
    print("\nProduct Management CLI")
    print("----------------------")
    print("1. Add New Product")
    print("2. List All Products")
    print("3. Search Products")
    print("4. Update Product")
    print("5. Delete Product")
    print("6. Exit")
    print("----------------------")


def get_user_choice() -> int:
    """
    Prompts the user for their menu choice and validates the input.

    The function loops until a valid integer choice between 1 and 6 (inclusive)
    is received. It handles non-integer input and out-of-range numbers.

    Parameters:
        None

    Returns:
        int: The validated menu choice.
    """
    while True:
        try:
            choice_str = input("Enter your choice: ")
            choice = int(choice_str)
            if 1 <= choice <= 6:
                return choice
            else:
                print("Invalid choice. Please enter a number between 1 and 6.")
        except ValueError:
            print("Invalid input. Please enter a number.")


def handle_add_product():
    """
    Placeholder function for adding a new product.

    Parameters:
        None

    Returns:
        None
    """
    print("\n--- Add New Product ---")
    print("Functionality to add a product will be implemented here.")


def handle_list_products():
    """
    Placeholder function for listing all products.

    Parameters:
        None

    Returns:
        None
    """
    print("\n--- List All Products ---")
    print("Functionality to list products will be implemented here.")


def handle_search_products():
    """
    Placeholder function for searching products.

    Parameters:
        None

    Returns:
        None
    """
    print("\n--- Search Products ---")
    print("Functionality to search products will be implemented here.")


def handle_update_product():
    """
    Placeholder function for updating a product.

    Parameters:
        None

    Returns:
        None
    """
    print("\n--- Update Product ---")
    print("Functionality to update products will be implemented here.")


def handle_delete_product():
    """
    Placeholder function for deleting a product.

    Parameters:
        None

    Returns:
        None
    """
    print("\n--- Delete Product ---")
    print("Functionality to delete products will be implemented here.")


def run_cli():
    """
    Main application loop, displays menu, gets choice, and dispatches to handlers.

    This function continuously displays the main menu, prompts the user for a choice,
    validates the input, and calls the appropriate handler function based on the choice.
    The loop terminates when the user chooses to exit.

    Parameters:
        None

    Returns:
        None
    """
    while True:
        display_menu()
        choice = get_user_choice()

        match choice:
            case 1:
                handle_add_product()
            case 2:
                handle_list_products()
            case 3:
                handle_search_products()
            case 4:
                handle_update_product()
            case 5:
                handle_delete_product()
            case 6:
                print("Exiting Product Management CLI. Goodbye!")
                break

        if choice != 6:
            input("Press Enter to continue...")


def main():
    """
    Entry point for the script.

    Checks if the script is run directly and calls the main CLI application loop.

    Parameters:
        None

    Returns:
        None
    """
    if sys.version_info < (3, 10):
        sys.exit("Python 3.10 or newer is required to run this application.")
    run_cli()


if __name__ == '__main__':
    main()

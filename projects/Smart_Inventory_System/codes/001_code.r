import sys

# Assume calculator.py and storage.py exist and are importable
# For the purpose of this task, we'll define placeholder functions
# that mimic their expected behavior.

# --- Placeholder for calculator.py ---
class Calculator:
    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b

    def multiply(self, a, b):
        return a * b

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Division by zero is not allowed.")
        return a / b

calculator = Calculator()

# --- Placeholder for storage.py ---

def load_history():
    # In a real implementation, this would load from a file like data/history.json
    print("\n--- Calculation History ---")
    print("History is currently empty (placeholder).")
    print("-------------------------")
    return []

def save_calculation(operation, result):
    # In a real implementation, this would save to a file like data/history.json
    print(f"(Placeholder: Saved {operation} = {result})")
    pass

# --- Main CLI Implementation ---

def display_menu():
    """
    Displays the available options to the user.

    Parameters:
        None.

    Returns:
        None.
    """
    print("\n--- Calculator Menu ---")
    print("1. Add")
    print("2. Subtract")
    print("3. Multiply")
    print("4. Divide")
    print("5. View History")
    print("6. Exit")
    print("---------------------")

def get_user_choice():
    """
    Prompts the user to enter their choice from the menu.

    Parameters:
        None.

    Returns:
        A string representing the user's choice.
    """
    choice = input("Enter your choice (1-6): ").strip()
    if not choice:
        print("Error: No choice entered. Please try again.")
        return get_user_choice() # Re-prompt if empty
    return choice

def handle_calculation_input():
    """
    Prompts the user for two numbers and the operation to perform.
    Validates that inputs are numbers and the operation is valid.

    Parameters:
        None.

    Returns:
        A tuple (num1, num2, operation) where num1 and num2 are floats,
        and operation is a string, or None if input is invalid.
    """
    while True:
        try:
            num1_str = input("Enter the first number: ").strip()
            num1 = float(num1_str)
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    while True:
        try:
            num2_str = input("Enter the second number: ").strip()
            num2 = float(num2_str)
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    valid_operations = {
        '+': calculator.add,
        '-': calculator.subtract,
        '*': calculator.multiply,
        '/': calculator.divide
    }

    while True:
        operation = input("Enter the operation (+, -, *, /): ").strip()
        if operation in valid_operations:
            return num1, num2, operation
        else:
            print("Invalid operation. Please use +, -, *, or /.")

def main_menu_loop():
    """
    The main loop for the CLI application.
    Continuously displays the menu, gets user input, and performs actions.

    Parameters:
        None.

    Returns:
        None.
    """
    while True:
        display_menu()
        choice = get_user_choice()

        try:
            if choice == '1':
                num1, num2, op = handle_calculation_input()
                result = calculator.add(num1, num2)
                print(f"\nResult: {num1} + {num2} = {result}")
                save_calculation(f"{num1} + {num2}", result)
            elif choice == '2':
                num1, num2, op = handle_calculation_input()
                result = calculator.subtract(num1, num2)
                print(f"\nResult: {num1} - {num2} = {result}")
                save_calculation(f"{num1} - {num2}", result)
            elif choice == '3':
                num1, num2, op = handle_calculation_input()
                result = calculator.multiply(num1, num2)
                print(f"\nResult: {num1} * {num2} = {result}")
                save_calculation(f"{num1} * {num2}", result)
            elif choice == '4':
                num1, num2, op = handle_calculation_input()
                try:
                    result = calculator.divide(num1, num2)
                    print(f"\nResult: {num1} / {num2} = {result}")
                    save_calculation(f"{num1} / {num2}", result)
                except ValueError as e:
                    print(f"\nError: {e}")
            elif choice == '5':
                load_history() # Placeholder call
            elif choice == '6':
                print("Exiting calculator. Goodbye!")
                sys.exit(0)
            else:
                print("Invalid choice. Please enter a number between 1 and 6.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            print("Please try again.")

if __name__ == '__main__':
    main_menu_loop()

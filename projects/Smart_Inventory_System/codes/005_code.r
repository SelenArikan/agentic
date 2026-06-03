import json
import os

# Assume calculator.py and storage.py exist and are functional
# from calculator import add, subtract, multiply, divide

# Placeholder for storage.py functions if not provided
def read_history():
    """Reads calculation history from history.json.

    Returns:
        list: A list of calculation records.
    """
    history_file = 'history.json'
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
            return history
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def write_history(history):
    """Writes calculation history to history.json.

    Args:
        history (list): A list of calculation records.
    """
    with open('history.json', 'w') as f:
        json.dump(history, f, indent=4)


def view_history():
    """Displays past calculations stored in history.json.

    Reads from history.json and prints each calculation record
    in a human-readable format to the console.
    Handles cases where history is empty.
    """
    history = read_history()
    if not history:
        print("\nNo calculation history available.")
    else:
        print("\n--- Calculation History ---")
        for entry in history:
            timestamp = entry.get('timestamp', 'N/A')
            operation = entry.get('operation', 'N/A')
            result = entry.get('result', 'N/A')
            print(f"[{timestamp}] Operation: {operation}, Result: {result}")
        print("-------------------------")

def display_menu():
    """Displays the main menu options to the user."""
    print("\nWelcome to the Calculator!")
    print("1. Perform Calculation")
    print("2. View History")
    print("3. Exit")
    choice = input("Enter your choice (1-3): ")
    return choice

def main():
    """Main function to run the calculator application."""
    while True:
        choice = display_menu()

        if choice == '1':
            # Placeholder for calculation logic
            print("\nPerforming calculation (Not yet implemented in this snippet)...")
            # Example of how history might be updated (requires calculator logic)
            # try:
            #     num1 = float(input("Enter first number: "))
            #     op = input("Enter operation (+, -, *, /): ")
            #     num2 = float(input("Enter second number: "))
            #     result = perform_operation(num1, op, num2) # Assumes perform_operation exists
            #     if result is not None:
            #         current_time = datetime.now().isoformat()
            #         history_entry = {"operation": f"{num1} {op} {num2}", "result": result, "timestamp": current_time}
            #         all_history = read_history()
            #         all_history.append(history_entry)
            #         write_history(all_history)
            #         print(f"Result: {result}")
            # except ValueError:
            #     print("Invalid input. Please enter numbers.")
            # except ZeroDivisionError:
            #     print("Error: Division by zero.")
            pass
        elif choice == '2':
            view_history()
        elif choice == '3':
            print("Exiting Calculator. Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 3.")

if __name__ == "__main__":
    # Create a dummy history.json for testing if it doesn't exist
    if not os.path.exists('history.json'):
        with open('history.json', 'w') as f:
            json.dump([
                {"operation": "2 + 2", "result": 4, "timestamp": "2023-10-27T10:00:00"},
                {"operation": "10 / 2", "result": 5, "timestamp": "2023-10-27T10:05:00"}
            ], f, indent=4)
    main()

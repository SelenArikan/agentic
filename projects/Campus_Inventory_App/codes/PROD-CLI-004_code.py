from typing import Union

def _validate_numerical_value(
    input_str: str,
    target_type: type,
    min_value: float = 0,
    inclusive_min: bool = False
) -> Union[int, float]:
    """
    Internal helper to validate a single numerical string against type and min_value constraints.
    Raises ValueError with a specific message if validation fails.

    Args:
        input_str (str): The raw string input to validate.
        target_type (type): The desired numerical type (e.g., int, float).
        min_value (float): The minimum acceptable value (default is 0).
        inclusive_min (bool): If True, value can be equal to min_value.
                              If False, value must be strictly greater than min_value.

    Returns:
        Union[int, float]: The validated numerical input.

    Raises:
        ValueError: If the input_str cannot be converted to target_type or
                    if the value does not meet the min_value constraint.
    """
    try:
        value = target_type(input_str)

        if inclusive_min:
            if value < min_value:
                raise ValueError(f"Value must be at least {min_value}.")
        else:  # strictly greater than min_value
            if value <= min_value:
                raise ValueError(f"Value must be greater than {min_value}.")
        return value
    except ValueError as e:
        # Re-raise with a more specific message if it was a type conversion error
        if "invalid literal for int()" in str(e) or \
           "invalid literal for float()" in str(e) or \
           f"could not convert string to {target_type.__name__}" in str(e):
            raise ValueError(f"Invalid input. Please enter a valid {target_type.__name__}.")
        raise  # Re-raise other ValueErrors from min_value checks


def get_validated_numerical_input(
    prompt: str,
    target_type: type,
    min_value: float = 0,
    inclusive_min: bool = False
) -> Union[int, float]:
    """
    Prompts the user for mandatory numerical input, validates it using _validate_numerical_value,
    and repeatedly prompts until valid input is provided.

    Args:
        prompt (str): The message displayed to the user.
        target_type (type): The desired numerical type (e.g., int, float).
        min_value (float): The minimum acceptable value (default is 0).
        inclusive_min (bool): If True, value can be equal to min_value.
                              If False, value must be strictly greater than min_value.

    Returns:
        Union[int, float]: The validated numerical input.
    """
    while True:
        user_input = input(prompt).strip()
        try:
            return _validate_numerical_value(user_input, target_type, min_value, inclusive_min)
        except ValueError as e:
            print(f"Error: {e} Please try again.")


def get_optional_numerical_input_for_update(
    prompt: str,
    current_value: Union[int, float],
    target_type: type,
    min_value: float = 0,
    inclusive_min: bool = False
) -> Union[int, float]:
    """
    Prompts the user for optional numerical input for updates.
    Allows leaving the input blank to retain the current_value.
    Validates non-blank input using _validate_numerical_value.
    If invalid, repeatedly prompts until valid input is provided or user keeps current value.

    Args:
        prompt (str): The message displayed to the user for the field.
        current_value (Union[int, float]): The current value of the field,
                                            returned if the user leaves the input blank.
        target_type (type): The desired numerical type (e.g., int, float).
        min_value (float): The minimum acceptable value (default is 0).
        inclusive_min (bool): If True, value can be equal to min_value.
                              If False, value must be strictly greater than min_value.

    Returns:
        Union[int, float]: The validated new numerical input, or the current_value
                           if the input was left blank.
    """
    while True:
        user_input = input(f"{prompt} (current: {current_value}, leave blank to keep): ").strip()
        if not user_input:
            return current_value  # User chose to keep current value
        try:
            return _validate_numerical_value(user_input, target_type, min_value, inclusive_min)
        except ValueError as e:
            print(f"Error: {e} Please try again.")


if __name__ == "__main__":
    print("--- Testing get_validated_numerical_input (Mandatory Input) ---")
    # Test Case: Valid Quantity
    print("\nScenario: Valid Quantity (10)")
    # Simulate user input: 10
    # quantity = get_validated_numerical_input("Enter quantity (int > 0): ", int, min_value=0, inclusive_min=False)
    # print(f"Result: {quantity}, Type: {type(quantity)}")

    # Test Case: Invalid Quantity (non-numeric) then Valid
    print("\nScenario: Invalid Quantity (abc) then Valid (5)")
    # Simulate user input: abc, then 5
    # quantity = get_validated_numerical_input("Enter quantity (int > 0): ", int, min_value=0, inclusive_min=False)
    # print(f"Result: {quantity}, Type: {type(quantity)}")

    # Test Case: Invalid Quantity (zero) then Valid
    print("\nScenario: Invalid Quantity (0) then Valid (1)")
    # Simulate user input: 0, then 1
    # quantity = get_validated_numerical_input("Enter quantity (int > 0): ", int, min_value=0, inclusive_min=False)
    # print(f"Result: {quantity}, Type: {type(quantity)}")

    # Test Case: Invalid Quantity (negative) then Valid
    print("\nScenario: Invalid Quantity (-5) then Valid (2)")
    # Simulate user input: -5, then 2
    # quantity = get_validated_numerical_input("Enter quantity (int > 0): ", int, min_value=0, inclusive_min=False)
    # print(f"Result: {quantity}, Type: {type(quantity)}")

    # Test Case: Valid Unit Price (19.99)
    print("\nScenario: Valid Unit Price (19.99)")
    # Simulate user input: 19.99
    # unit_price = get_validated_numerical_input("Enter unit price (float > 0): ", float, min_value=0, inclusive_min=False)
    # print(f"Result: {unit_price}, Type: {type(unit_price)}")

    # Test Case: Invalid Unit Price (float instead of int for target_type=int)
    print("\nScenario: Invalid Quantity (10.5 for int) then Valid (10)")
    # Simulate user input: 10.5, then 10
    # quantity_int_test = get_validated_numerical_input("Enter integer quantity (>0): ", int, min_value=0, inclusive_min=False)
    # print(f"Result: {quantity_int_test}, Type: {type(quantity_int_test)}")


    print("\n--- Testing get_optional_numerical_input_for_update (Optional Input) ---")
    current_qty = 100
    current_price = 49.99

    # Test Case: Update Quantity - Blank Input (Keep current)
    print(f"\nScenario: Update Quantity - Blank Input (current: {current_qty})")
    # Simulate user input: '' (empty string)
    # new_quantity = get_optional_numerical_input_for_update(
    #     prompt="Enter new quantity",
    #     current_value=current_qty,
    #     target_type=int,
    #     min_value=0,
    #     inclusive_min=False
    # )
    # print(f"Result: {new_quantity}, Type: {type(new_quantity)}")

    # Test Case: Update Unit Price - Invalid then Valid
    print(f"\nScenario: Update Unit Price - Invalid (xyz) then Valid (55.50) (current: {current_price})")
    # Simulate user input: xyz, then 55.50
    # new_unit_price = get_optional_numerical_input_for_update(
    #     prompt="Enter new unit price",
    #     current_value=current_price,
    #     target_type=float,
    #     min_value=0,
    #     inclusive_min=False
    # )
    # print(f"Result: {new_unit_price}, Type: {type(new_unit_price)}")

    # Test Case: Update Quantity - Invalid (negative) then Valid
    print(f"\nScenario: Update Quantity - Invalid (-10) then Valid (120) (current: {current_qty})")
    # Simulate user input: -10, then 120
    # new_quantity = get_optional_numerical_input_for_update(
    #     prompt="Enter new quantity",
    #     current_value=current_qty,
    #     target_type=int,
    #     min_value=0,
    #     inclusive_min=False
    # )
    # print(f"Result: {new_quantity}, Type: {type(new_quantity)}")

    # To run the tests, uncomment the desired lines above and run this script.
    print("\nTo test, uncomment the example calls and provide input as prompted.")

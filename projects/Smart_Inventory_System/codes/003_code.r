def perform_operation(num1: float, num2: float, operation: str) -> float | str:
    """Performs the requested arithmetic operation, including validation for division by zero.

    Args:
        num1: The first operand.
        num2: The second operand.
        operation: The arithmetic operation to perform ('+', '-', '*', '/').

    Returns:
        The result of the operation, or an error message string if validation fails.
    """
    if operation == '/' and num2 == 0:
        return 'Error: Division by zero is not allowed.'

    if operation == '+':
        return num1 + num2
    elif operation == '-':
        return num1 - num2
    elif operation == '*':
        return num1 * num2
    elif operation == '/':
        return num1 / num2
    else:
        return 'Error: Invalid operation.'

def add(num1: float, num2: float) -> float:
    """Performs addition of two numbers.

    Args:
        num1 (float): The first number.
        num2 (float): The second number.

    Returns:
        float: The sum of num1 and num2.
    """
    return num1 + num2

def subtract(num1: float, num2: float) -> float:
    """Performs subtraction of two numbers.

    Args:
        num1 (float): The number to subtract from.
        num2 (float): The number to subtract.

    Returns:
        float: The difference between num1 and num2.
    """
    return num1 - num2

def multiply(num1: float, num2: float) -> float:
    """Performs multiplication of two numbers.

    Args:
        num1 (float): The first number.
        num2 (float): The second number.

    Returns:
        float: The product of num1 and num2.
    """
    return num1 * num2

def divide(num1: float, num2: float) -> float:
    """Performs division of two numbers. Handles division by zero.

    Args:
        num1 (float): The dividend.
        num2 (float): The divisor.

    Returns:
        float: The result of num1 divided by num2.

    Raises:
        ValueError: If num2 is zero.
    """
    if num2 == 0:
        raise ValueError("Division by zero is not allowed.")
    return num1 / num2

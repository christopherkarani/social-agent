# Utility functions for the LangChain agent

def format_input(input_text):
    """Format the input text for processing."""
    return input_text.strip()

def log_message(message):
    """Log a message to the console."""
    print(f"[LOG]: {message}")

def validate_input(input_text):
    """Validate the input text."""
    if not input_text:
        raise ValueError("Input text cannot be empty.")
    return True
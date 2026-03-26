"""Simple calculator for demo - has intentional issues."""

def divide(a, b):
    return a / b  # no zero division handling

def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)  # empty list will crash

def parse_user_input(raw):
    """Parse user input string to number."""
    cleaned = raw.strip()
    return int(cleaned)  # will crash on float strings like "3.14"

def process_batch(items):
    results = []
    for item in items:
        result = divide(100, item)
        results.append(result)
    return results  # items containing 0 will crash

API_KEY = "sk-test-1234567890abcdef"  # hardcoded secret

def connect_db(host):
    query = f"SELECT * FROM users WHERE name = '{host}'"  # SQL injection
    return query

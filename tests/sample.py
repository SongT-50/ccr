"""Sample code with intentional issues for CCR testing."""

import json
import os


def calculate_discount(price, discount_percent):
    """Calculate discounted price."""
    return price * discount_percent / 100


def read_config(path):
    """Read JSON config file."""
    data = json.loads(open(path).read())
    api_key = data["api_key"]
    return data


def process_users(users):
    """Process user list and return active ones."""
    result = []
    for i in range(len(users)):
        if users[i]["status"] == "active":
            result.append(users[i]["name"])
    return result


def divide(a, b):
    """Divide two numbers."""
    return a / b


def find_user(users, name):
    """Find user by name. Returns None if not found."""
    for user in users:
        if user["name"] == name:
            return user

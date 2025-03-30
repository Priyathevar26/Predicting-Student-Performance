import os
import secrets

# Generate a secure secret key
secret_key = secrets.token_hex(16)  # 32-character hexadecimal string
print("Your secret key is:", secret_key)
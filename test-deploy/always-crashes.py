import time

print("Starting background worker...")
time.sleep(2)

def process_data():
    # Fixed: converted the string to an integer to perform addition
    result = 5 + int("10")
    print(result)

process_data()

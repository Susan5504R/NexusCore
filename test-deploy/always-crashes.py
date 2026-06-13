import time

print("Starting background worker...")
time.sleep(2)

def process_data():
    # Intentionally broken: you cannot add an int and a string!
    result = 5 + "10"
    print(result)

process_data()

import os, json, random

NUM_TEST_CASES = 10

def rotr(x, n):
    return (x >> n) | (x << (32 - n))

def shr(x, n):
    return (x >> n)

def sigma0(w_15):
    return rotr(w_15, 7) ^ rotr(w_15, 18) ^ shr(w_15, 3)

def sigma1(w_2):
    return rotr(w_2, 17) ^ rotr(w_2, 19) ^ shr(w_2, 10)
    
def store_in_file(file, input, expected):
    json.dump({"input": input, "expected": expected}, file, indent=2)

def to_hex(list):
    return [f"{num:x}" for num in list]

def compute_message_schedule(block):
    schedule = [None for i in range(64)]

    for i in range(16):
        schedule[i] = block[i]
    
    for i in range(16, 64):
        schedule[i] = (sigma0(schedule[i - 15]) + schedule[i - 7] + sigma1(schedule[i - 2]) + schedule[i - 16])\
            & 0xffffffff # Truncate when exceeding one byte in size

    return schedule

def generate_test_cases():
    os.makedirs("test_cases", exist_ok = True)

    for i in range(NUM_TEST_CASES):
        block = [random.getrandbits(32) for i in range(16)] # 512-bit input message

        with open(f"test_cases/test_case_{i+1}.json","w") as file:
            # Convert to hexadecimal strings for easy debugging
            # when comparing waveform values to test_case JSON files
            store_in_file(file, to_hex(block), to_hex(compute_message_schedule(block)))

if __name__ == "__main__":
    generate_test_cases()
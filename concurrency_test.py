import requests
import threading
import uuid
import time

# Configuration
API_BASE = "http://localhost:8000/api/v1"
API_URL = f"{API_BASE}/payouts"

def get_merchant_id(name):
    try:
        response = requests.get(f"{API_BASE}/merchants")
        merchants = response.json()
        for merchant in merchants:
            if merchant['name'] == name:
                return merchant['id']
    except Exception as error:
        print(f"Failed to fetch merchant ID: {error}")
    return None

# Find ID dynamically
MERCHANT_ID = get_merchant_id("Aman Agencies")
if not MERCHANT_ID:
    print("ERROR: Could not find merchant 'Aman Agencies'. Did you run seed_data?")
    exit(1)
else:
    print(f"Found 'Aman Agencies' ID: {MERCHANT_ID}")

def test_race_condition():
    print(f"\n--- Testing Race Condition (Concurrency) ---")
    print(f"Goal: Request 6,000 INR twice when balance is 10,000 INR. Only ONE should succeed.")
    
    # We use a large amount to trigger 'Insufficient funds' for the second thread
    # Merchant starts with 1,000,000 paise (10,000 INR)
    AMOUNT = 600000 # 6,000 INR
    
    results = []
    
    def send_request(thread_id):
        idem_key = str(uuid.uuid4())
        payload = {
            "merchant_id": MERCHANT_ID,
            "amount_paise": AMOUNT,
            "bank_account_id": f"TEST_BANK_{thread_id}"
        }
        headers = {"Idempotency-Key": idem_key, "Content-Type": "application/json"}
        
        try:
            response = requests.post(API_URL, json=payload, headers=headers)
            results.append(response.status_code)
            print(f"Thread {thread_id}: Status {response.status_code}, Body: {response.json().get('status', response.text)}")
        except Exception as error:
            print(f"Thread {thread_id}: Failed - {error}")

    threads = [threading.Thread(target=send_request, args=(thread_id,)) for thread_id in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    
    succeeded = results.count(201)
    failed = results.count(422)
    print(f"\nResult: {succeeded} succeeded, {failed} failed")
    
    # ASSERTIONS
    assert succeeded == 1, f"Expected exactly 1 success, got {succeeded}"
    assert failed == 1, f"Expected exactly 1 failure (422), got {failed}"
    print("Race condition test PASSED")

def test_idempotency():
    print(f"\n--- Testing Idempotency ---")
    print(f"Goal: Send the SAME request twice. Second should return same response as first.")
    
    idem_key = str(uuid.uuid4())
    payload = {
        "merchant_id": MERCHANT_ID,
        "amount_paise": 1000,
        "bank_account_id": "IDEM_TEST_BANK"
    }
    headers = {"Idempotency-Key": idem_key, "Content-Type": "application/json"}
    
    # Request 1
    response1 = requests.post(API_URL, json=payload, headers=headers)
    id1 = response1.json().get('id')
    print(f"Request 1: Status {response1.status_code}, Payout ID: {id1}")
    
    # Request 2 (Immediate)
    response2 = requests.post(API_URL, json=payload, headers=headers)
    id2 = response2.json().get('id')
    print(f"Request 2: Status {response2.status_code}, Payout ID: {id2}")
    
    # ASSERTIONS
    assert response1.status_code == 201, f"Expected 201 for first request, got {response1.status_code}"
    assert response2.status_code == 201, f"Expected 201 for second request, got {response2.status_code}"
    assert id1 == id2, f"Expected identical Payout IDs, got {id1} vs {id2}"
    print("Idempotency test PASSED")

if __name__ == "__main__":
    test_race_condition()
    test_idempotency()

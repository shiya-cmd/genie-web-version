import random, string, requests, segno, time

FIREBASE_DB_URL = "https://genie-6bb04-default-rtdb.asia-southeast1.firebasedatabase.app"
SMSBOWER_API_KEY = "q3xSZbaPVpaZW5zsI4tzea7s0RlLfun3"
PAYTM_WORKER_URL = "https://paytm.udayscriptsx.workers.dev/"
PAYTM_MID = "OtWRkM00455638249469"

UPI_VPA = "paytmqr2810050501013202t473pymf@paytm"
MERCHANT_NAME = "OORPAY"

SERVICE_CONFIG = {
    "wa": {"label": "WhatsApp", "price": 1.5, "service": "wa", "country": 288882, "max_price": 0.4},
    "tg": {"label": "Telegram", "price": 1.2, "service": "tg", "country": 22, "max_price": 0.5},
}

# ---------- ORDER ----------
def generate_order_id():
    return "OOR" + "".join(random.choices(string.ascii_uppercase + string.digits, k=13))

def order_exists(order_id):
    r = requests.get(f"{FIREBASE_DB_URL}/orders/{order_id}.json")
    return r.json() is not None

def generate_unique_order_id():
    while True:
        oid = generate_order_id()
        if not order_exists(oid):
            return oid

# ---------- FIREBASE ----------
import time
def save_order(order_id, service):
    data = {
        "order_id": order_id,
        "service": service,
        "amount": SERVICE_CONFIG[service]["price"],
        "status": "PENDING",
        "created_at": int(time.time()),  # ✅ UNIX timestamp
        "phone": "",
        "otp": "",
    }

    requests.put(
        f"{FIREBASE_DB_URL}/orders/{order_id}.json",
        json=data
    )

def update_order(order_id, data):
    requests.patch(f"{FIREBASE_DB_URL}/orders/{order_id}.json", json=data)

def get_order(order_id):
    r = requests.get(f"{FIREBASE_DB_URL}/orders/{order_id}.json")
    return r.json()

# ---------- QR ----------
import os
def generate_qr(order_id, amount):
    os.makedirs("static/qr", exist_ok=True)  # ✅ ensures folder exists

    uri = (
        f"upi://pay?"
        f"pa={UPI_VPA}&pn={MERCHANT_NAME}"
        f"&am={amount}&cu=INR"
        f"&tn={order_id}&tr={order_id}&tid={order_id}"
    )

    path = f"static/qr/{order_id}.png"
    segno.make(uri, error="m").save(path, scale=8, border=4)

    return f"qr/{order_id}.png"  # 👈 relative for Flask static


# ---------- PAYMENT ----------
def check_payment(order_id):
    try:
        r = requests.get(PAYTM_WORKER_URL, params={"mid": PAYTM_MID, "id": order_id}, timeout=10)
        return r.json().get("STATUS") == "TXN_SUCCESS"
    except:
        return False

# ---------- SMSBOWER ----------
def get_number(service):
    cfg = SERVICE_CONFIG[service]
    r = requests.get(
        "https://smsbower.online/stubs/handler_api.php",
        params={
            "api_key": SMSBOWER_API_KEY,
            "action": "getNumberV2",
            "service": cfg["service"],
            "country": cfg["country"],
            "maxPrice": cfg["max_price"],
        },
    )
    print(r.text)
    d = r.json()

    return d["activationId"], d["phoneNumber"]

def get_otp(activation_id):
    r = requests.get(
        "https://smsbower.online/stubs/handler_api.php",
        params={"api_key": SMSBOWER_API_KEY, "action": "getStatus", "id": activation_id},
    )
    t = r.text.strip()
    if t.startswith("STATUS_OK"):
        return t.split(":")[1]
    return None

def cancel_activation(activation_id):
    requests.get(
        "https://smsbower.online/stubs/handler_api.php",
        params={"api_key": SMSBOWER_API_KEY, "action": "setStatus", "id": activation_id, "status": 8},
    )

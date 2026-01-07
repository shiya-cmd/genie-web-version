from flask import Flask, render_template, redirect, url_for, jsonify
import time
from logic import *

app = Flask(__name__)

# ---------- HOME ----------
@app.route("/")
def index():
    return render_template("index.html", services=SERVICE_CONFIG)

# ---------- BUY ----------
@app.route("/buy/<service>")
def buy(service):
    order_id = generate_unique_order_id()
    save_order(order_id, service)
    qr = generate_qr(order_id, SERVICE_CONFIG[service]["price"])
    return redirect(url_for("status", order_id=order_id))


import time
from flask import jsonify

ORDER_TIMEOUT = 300  # 5 minutes

def format_time(seconds: int) -> str:
    mins, secs = divmod(max(seconds, 0), 60)
    return f"{mins}:{secs:02d}"


@app.route("/api/time/<order_id>")
def api_time(order_id):
    order = get_order(order_id)

    if not order:
        return jsonify({"expired": True})

    created_at = order.get("created_at", 0)
    now = int(time.time())
    elapsed = now - created_at
    remaining = ORDER_TIMEOUT - elapsed

    if remaining <= 0:
        # ⛔ expire order server-side
        if order.get("status") != "FAILED":
            update_order(order_id, {"status": "FAILED"})
        return jsonify({
            "expired": True,
            "time_left": "0:00",
            "seconds_left": 0
        })

    return jsonify({
        "expired": False,
        "time_left": format_time(remaining),
        "seconds_left": remaining
    })



# ---------- STATUS ----------
ORDER_TIMEOUT = 300  # 5 minutes
@app.route("/status/<order_id>")
def status(order_id):
    order = get_order(order_id)

    if not order:
        return render_template("failed.html", reason="Invalid order")

    if order["status"] == "SUCCESS":
        return redirect(url_for("otp", order_id=order_id))

    if order["status"] == "FAILED":
        return render_template("failed.html", reason="Payment failed")

    created_at = order.get("created_at", 0)
    now = int(time.time())
    elapsed = now - created_at
    remaining = ORDER_TIMEOUT - elapsed

    # ⛔ TIME EXPIRED
    if remaining <= 0:
        update_order(order_id, {"status": "FAILED"})
        return render_template(
            "failed.html",
            reason="Payment time expired (5 minutes)"
        )

    # ✅ CHECK PAYMENT
    if True:
        update_order(order_id, {"status": "SUCCESS"})
        return redirect(url_for("otp", order_id=order_id))

    # ⏳ STILL WAITING
    return render_template(
        "status.html",
        order_id=order_id,
        time_left=format_time(remaining),  # ✅ formatted MM:SS
        seconds_left=remaining              # optional (for JS)
    )


# ---------- OTP PAGE ----------
@app.route("/otp/<order_id>")
def otp(order_id):
    order = get_order(order_id)

    if not order:
        return render_template(
            "failed.html",
            reason="Invalid order. Please contact support."
        )

    # If number assigned in firebase db as NONE
    if order.get("phone") == "NONE":
        return render_template(
            "failed.html",
            reason="Something went wrong while assigning the number.",
            order_id=order_id
        )

    # If number already assigned, just show page
    if order.get("phone"):
        return render_template(
            "otp.html",
            order_id=order_id,
            phone=order["phone"]
        )

    # 🔐 TRY TO GET NUMBER SAFELY
    try:
        act_id, phone = get_number(order["service"])

        # Validate response
        if not act_id or not phone:
            raise ValueError("SMS provider returned empty data")

        update_order(
            order_id,
            {
                "phone": phone,
                "activation_id": act_id
            }
        )

        return render_template(
            "otp.html",
            order_id=order_id,
            phone=phone
        )

    except Exception as e:
        # Log error (optional)
        print(f"[OTP ERROR] Order {order_id}: {e}")

        # Mark order failed
        update_order(
            order_id,
            {
                "phone": "NONE"
            }
        )

        return render_template(
            "failed.html",
            reason="Something went wrong while assigning the number.",
            order_id=order_id
        )


# ---------- OTP API ----------
@app.route("/api/otp/<order_id>")
def api_otp(order_id):
    order = get_order(order_id)
    code = get_otp(order["activation_id"])
    if code:
        update_order(order_id, {"otp": code})
        return jsonify({"otp": code})
    return jsonify({"otp": None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)


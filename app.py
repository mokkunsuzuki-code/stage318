from flask import Flask, request, jsonify
from dotenv import load_dotenv
from auth import is_valid_key, get_plan
from plans import PLANS
from rate_limit import check_rate_limit
from billing import create_checkout_session
from db import (
    init_db,
    seed_demo_keys,
    create_or_update_user,
    generate_api_key,
    save_payment,
    list_keys_for_email
)
import subprocess
import json
import os
import stripe

load_dotenv()

app = Flask(__name__)

init_db()
seed_demo_keys()


@app.route("/")
def home():
    return """
    <h1>REMEDA Stage317</h1>
    <h2>Real SaaS Trust Verification API</h2>
    <p>Stage317 adds Stripe Webhook, user DB, and automatic API key issuance.</p>

    <h3>Core SaaS Flow</h3>
    <ol>
      <li>User subscribes with Stripe Checkout</li>
      <li>Stripe Webhook confirms payment</li>
      <li>User is upgraded to Pro</li>
      <li>Pro API key is automatically issued</li>
    </ol>

    <p><a href="/pricing">View Pricing</a></p>
    """


@app.route("/pricing")
def pricing():
    return """
    <h1>Pricing</h1>

    <h2>Free</h2>
    <p>100 requests/day. Limited verification.</p>

    <h2>Pro</h2>
    <p>10,000 requests/day. Sigstore verification included.</p>

    <form action="/api/subscribe" method="post">
      <input name="email" placeholder="your@email.com" required>
      <button type="submit">Subscribe to Pro</button>
    </form>

    <h2>Enterprise</h2>
    <p>Custom policies, dedicated environment, and QSP integration.</p>
    """


@app.route("/success")
def success():
    return """
    <h1>Subscription Success</h1>
    <p>Payment completed. Your Pro API key will be issued by Stripe Webhook.</p>
    """


@app.route("/cancel")
def cancel():
    return """
    <h1>Subscription Canceled</h1>
    <p>Your checkout session was canceled.</p>
    """


@app.route("/api/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email") or request.json.get("email") if request.is_json else None

    if not email:
        return jsonify({
            "error": "email_required"
        }), 400

    session = create_checkout_session(email)

    if session is None:
        return jsonify({
            "error": "stripe_not_configured",
            "message": "Set STRIPE_SECRET_KEY and STRIPE_PRICE_PRO in .env"
        }), 500

    return jsonify({
        "checkout_url": session.url,
        "session_id": session.id
    })


@app.route("/api/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        if webhook_secret and sig_header:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                webhook_secret
            )
        else:
            event = request.get_json()
    except Exception as e:
        return jsonify({
            "error": "webhook_verification_failed",
            "message": str(e)
        }), 400

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]

        email = (
            session.get("customer_details", {}).get("email")
            or session.get("customer_email")
            or session.get("metadata", {}).get("email")
        )

        session_id = session.get("id")
        customer_id = session.get("customer")

        if not email:
            return jsonify({
                "error": "email_missing"
            }), 400

        create_or_update_user(email, plan="pro", stripe_customer_id=customer_id)
        api_key = generate_api_key(email, plan="pro")
        save_payment(session_id, email, "pro", "completed")

        return jsonify({
            "ok": True,
            "message": "Pro API key issued",
            "email": email,
            "plan": "pro",
            "api_key": api_key
        })

    return jsonify({
        "ok": True,
        "ignored_event": event.get("type")
    })


@app.route("/api/customer/<path:email>/keys")
def customer_keys(email):
    # Development helper. In production this should require login.
    return jsonify({
        "email": email,
        "keys": list_keys_for_email(email)
    })


@app.route("/api/verify", methods=["POST"])
def verify():
    api_key = request.headers.get("x-api-key")

    if not is_valid_key(api_key):
        return jsonify({
            "error": "unauthorized",
            "message": "Invalid API Key"
        }), 403

    plan_name = get_plan(api_key)
    plan = PLANS.get(plan_name, PLANS["free"])

    if not check_rate_limit(api_key, plan["limit"]):
        return jsonify({
            "error": "rate_limit_exceeded",
            "plan": plan_name,
            "limit_per_day": plan["limit"]
        }), 429

    result = subprocess.run(
        ["python3", "evaluate.py"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return jsonify({
            "error": "execution_failed",
            "stderr": result.stderr
        }), 500

    if not result.stdout:
        return jsonify({
            "error": "empty_output",
            "stderr": result.stderr
        }), 500

    try:
        data = json.loads(result.stdout)
    except Exception:
        return jsonify({
            "error": "invalid_json",
            "raw_output": result.stdout
        }), 500

    if not plan["sigstore"]:
        data["sigstore_verified"] = False

        if "breakdown" in data:
            data["breakdown"]["sigstore"] = 0.0

        scores = data.get("breakdown", {})
        if scores:
            data["score"] = sum(scores.values()) / len(scores)

    response = jsonify(data)

    response.headers["X-REMEDA-Stage"] = "317"
    response.headers["X-REMEDA-Plan"] = plan_name
    response.headers["X-REMEDA-Plan-Name"] = plan["name"]
    response.headers["X-REMEDA-Daily-Limit"] = str(plan["limit"])
    response.headers["X-REMEDA-Sigstore-Enabled"] = str(plan["sigstore"]).lower()

    return response


@app.route("/api/health")
def health():
    return jsonify({
        "ok": True,
        "service": "remeda-saas-api",
        "stage": 317,
        "monetization": True,
        "billing": "stripe",
        "webhook": True,
        "user_db": "sqlite",
        "api_key_auto_issue": True,
        "plans": list(PLANS.keys())
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=3120, debug=True)

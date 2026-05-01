import os
import stripe

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_checkout_session(email):
    price_id = os.getenv("STRIPE_PRICE_PRO")

    if not stripe.api_key or not price_id:
        return None

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer_email=email,
        line_items=[
            {
                "price": price_id,
                "quantity": 1,
            }
        ],
        metadata={
            "email": email,
            "plan": "pro"
        },
        success_url="http://127.0.0.1:3120/success",
        cancel_url="http://127.0.0.1:3120/cancel",
    )

    return session

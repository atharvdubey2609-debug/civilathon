# CIVILATHON Stage 3 — Active Registration + Razorpay

This version activates the registration portal, PPT upload, payment page and Razorpay Checkout flow.

## 1. Install

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 2. Configure Razorpay

Create/get your Razorpay API keys from the Razorpay Dashboard. Start with **Test Mode** while testing.

Set these environment variables before starting Flask:

```bash
export RAZORPAY_KEY_ID="rzp_test_xxxxxxxxx"
export RAZORPAY_KEY_SECRET="xxxxxxxxxxxxxxxx"
export FLASK_SECRET_KEY="use-a-long-random-secret"
```

Do **not** put the secret key in HTML, JavaScript, GitHub, or the public repository.

## 3. Run

```bash
python app.py
```

Open `http://127.0.0.1:5000/register`.

## 4. Flow

1. Participant completes registration.
2. Final PPT/PPTX is stored locally under `uploads/ppt/`.
3. A unique registration ID is generated.
4. Participant is sent to the Razorpay payment page.
5. Flask creates a Razorpay order server-side.
6. Razorpay Checkout opens.
7. Payment signature is verified server-side using the secret key.
8. Registration is marked **Paid** and the confirmation page is shown.

## Important production notes

- Keep Razorpay keys in environment variables / deployment secrets.
- Use Razorpay Test Mode first.
- For production, switch to live keys only after completing end-to-end testing.
- The local SQLite database and local PPT folder are suitable for development, but a production deployment should move the database to PostgreSQL/Supabase and PPT storage to object storage such as Supabase Storage/S3.
- Add Razorpay webhooks before production so asynchronous payment/refund events are captured reliably.

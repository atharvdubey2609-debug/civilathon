# CIVILATHON Website — Stage 2

A Flask-based frontend for the Civilathon civil engineering innovation challenge.

## What's included
- Expanded content across Home, About, Research Areas, Rules, Guidelines, Submission and Registration.
- LNCT Bhopal and Civil Impact Club branding in the header.
- Civilathon poster artwork used as the landing-page visual.
- Event fees: ₹149 per team and ₹49 per individual.
- Prizes: ₹1,999 first prize and ₹999 second prize.
- Certificate of Participation for all participants.
- Coming Soon event schedule.
- Responsive desktop/mobile navigation.

## Run in PyCharm
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

Windows PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Next stages
1. Build real registration form and database.
2. Add PPT upload/storage.
3. Add Razorpay payment verification.
4. Generate registration IDs and confirmation.
5. Build protected admin dashboard.
6. Deploy the production website.

## Stage 3 — Registration + Local Database + PPT Upload
Stage 3 adds a working registration portal for local development. It includes:
- Team/individual participation selection
- Participant and college details
- Research-domain selection
- Problem, solution, innovation and impact fields
- PPT/PPTX upload (maximum 25 MB)
- Automatic registration ID generation
- SQLite database (`civilathon.db`)
- Registration success page
- Payment status stored as `Pending` for the next Razorpay stage

### Run Stage 3
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Then open `http://127.0.0.1:5000/register`.

**Next stage:** Razorpay payment integration + payment verification, followed by the protected admin dashboard.

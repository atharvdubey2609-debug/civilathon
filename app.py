from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime
import sqlite3
import uuid
import os
import hmac
import hashlib

try:
    import razorpay
except ImportError:
    razorpay = None

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'civilathon.db'
UPLOAD_DIR = BASE_DIR / 'uploads' / 'ppt'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'.ppt', '.pptx'}
MAX_FILE_SIZE = 25 * 1024 * 1024
TEAM_FEE = 14900       # ₹149 in paise
INDIVIDUAL_FEE = 4900  # ₹49 in paise

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'civilathon-stage3-dev-key-change-before-production')
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

DOMAINS = [
    'Smart Construction & Construction Management',
    'Sustainable & Green Construction',
    'Innovative Construction Materials',
    'AI/ML & Automation',
    'IoT & Smart Infrastructure',
    'GIS, Surveying & Geospatial Technology',
    'Transportation & Smart Mobility',
    'Water Resources & Management',
    'Smart Cities & Urban Infrastructure',
    'Structural Engineering & Safety',
    'Waste Management & Circular Construction',
    'Any Other Real-World Civil Engineering Problem',
]

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '').strip()
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '').strip()


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            registration_id TEXT UNIQUE NOT NULL,
            participation_type TEXT NOT NULL,
            team_name TEXT,
            college TEXT NOT NULL,
            leader_name TEXT NOT NULL,
            leader_mobile TEXT NOT NULL,
            leader_email TEXT NOT NULL,
            member_2 TEXT,
            member_3 TEXT,
            member_4 TEXT,
            research_domain TEXT NOT NULL,
            problem_statement TEXT NOT NULL,
            proposed_solution TEXT NOT NULL,
            innovation TEXT NOT NULL,
            expected_impact TEXT NOT NULL,
            ppt_filename TEXT NOT NULL,
            ppt_path TEXT NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'Pending',
            payment_id TEXT,
            payment_order_id TEXT,
            payment_signature TEXT,
            amount_paise INTEGER,
            created_at TEXT NOT NULL,
            paid_at TEXT
        )
    ''')
    # Safe migration for databases created by earlier Stage 3 builds.
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(registrations)').fetchall()}
    migrations = {
        'payment_order_id': 'ALTER TABLE registrations ADD COLUMN payment_order_id TEXT',
        'payment_signature': 'ALTER TABLE registrations ADD COLUMN payment_signature TEXT',
        'amount_paise': 'ALTER TABLE registrations ADD COLUMN amount_paise INTEGER',
        'paid_at': 'ALTER TABLE registrations ADD COLUMN paid_at TEXT',
    }
    for name, sql in migrations.items():
        if name not in columns:
            conn.execute(sql)
    conn.commit()
    conn.close()


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


def make_registration_id():
    return f"CIV-26-{uuid.uuid4().hex[:6].upper()}"


def razorpay_client():
    if not razorpay or not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        return None
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


@app.context_processor
def inject_common():
    return {
        'event_domains': DOMAINS,
        'razorpay_enabled': bool(razorpay_client()),
        'razorpay_key_id': RAZORPAY_KEY_ID,
    }


@app.route('/')
def home():
    return render_template('index.html')


@app.get('/about')
def about():
    return render_template('about.html')

@app.get('/domains')
def domains():
    return render_template('domains.html')

@app.get('/rules')
def rules():
    return render_template('rules.html')

@app.get('/guidelines')
def guidelines():
    return render_template('guidelines.html')

@app.get('/submission')
def submission():
    return render_template('submission.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', domains=DOMAINS)

    participation_type = request.form.get('participation_type', '').strip().lower()
    team_name = request.form.get('team_name', '').strip()
    college = request.form.get('college', '').strip()
    leader_name = request.form.get('leader_name', '').strip()
    leader_mobile = request.form.get('leader_mobile', '').strip()
    leader_email = request.form.get('leader_email', '').strip()
    member_2 = request.form.get('member_2', '').strip()
    member_3 = request.form.get('member_3', '').strip()
    member_4 = request.form.get('member_4', '').strip()
    research_domain = request.form.get('research_domain', '').strip()
    problem_statement = request.form.get('problem_statement', '').strip()
    proposed_solution = request.form.get('proposed_solution', '').strip()
    innovation = request.form.get('innovation', '').strip()
    expected_impact = request.form.get('expected_impact', '').strip()
    ppt = request.files.get('ppt')

    errors = []
    if participation_type not in {'team', 'individual'}:
        errors.append('Please select team or individual participation.')
    if not college:
        errors.append('College name is required.')
    if not leader_name:
        errors.append('Participant/team leader name is required.')
    if not leader_mobile or not leader_mobile.replace('+', '').replace(' ', '').isdigit():
        errors.append('Enter a valid mobile number.')
    if not leader_email or '@' not in leader_email:
        errors.append('Enter a valid email address.')
    if not research_domain or research_domain not in DOMAINS:
        errors.append('Please select a valid research domain.')
    for label, value in [
        ('problem statement', problem_statement),
        ('proposed solution', proposed_solution),
        ('innovation', innovation),
        ('expected impact', expected_impact),
    ]:
        if not value:
            errors.append(f'{label.capitalize()} is required.')

    if participation_type == 'team':
        if not team_name:
            errors.append('Team name is required for team participation.')
        members = [member_2, member_3, member_4]
        if not any(members):
            errors.append('Add at least one additional team member for team participation.')
    else:
        team_name = ''
        member_2 = member_3 = member_4 = ''

    if not ppt or not ppt.filename:
        errors.append('Please upload your final PPT/PPTX.')
    elif not allowed_file(ppt.filename):
        errors.append('Only .ppt and .pptx files are accepted.')

    if errors:
        for error in errors:
            flash(error, 'error')
        return render_template('register.html', domains=DOMAINS), 400

    registration_id = make_registration_id()
    original_name = secure_filename(ppt.filename)
    stored_name = f'{registration_id}_{original_name}'
    stored_path = UPLOAD_DIR / stored_name
    ppt.save(stored_path)

    amount_paise = TEAM_FEE if participation_type == 'team' else INDIVIDUAL_FEE
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    conn.execute('''
        INSERT INTO registrations (
            registration_id, participation_type, team_name, college,
            leader_name, leader_mobile, leader_email, member_2, member_3,
            member_4, research_domain, problem_statement, proposed_solution,
            innovation, expected_impact, ppt_filename, ppt_path,
            payment_status, amount_paise, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        registration_id, participation_type, team_name, college,
        leader_name, leader_mobile, leader_email, member_2, member_3,
        member_4, research_domain, problem_statement, proposed_solution,
        innovation, expected_impact, original_name, str(stored_path),
        'Pending', amount_paise, created_at
    ))
    conn.commit()
    conn.close()

    return redirect(url_for('payment', registration_id=registration_id))


@app.route('/payment/<registration_id>')
def payment(registration_id):
    conn = get_db()
    registration = conn.execute(
        'SELECT * FROM registrations WHERE registration_id = ?',
        (registration_id,)
    ).fetchone()
    conn.close()
    if not registration:
        return render_template('page.html', title='Registration Not Found', content='<p class="lead-dark">The registration ID could not be found.</p>'), 404
    if registration['payment_status'] == 'Paid':
        return redirect(url_for('success', registration_id=registration_id))
    return render_template('payment.html', registration=registration, amount=registration['amount_paise'] / 100)


@app.post('/api/create-order/<registration_id>')
def create_order(registration_id):
    client = razorpay_client()
    if not client:
        return jsonify({'ok': False, 'message': 'Razorpay is not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET to the environment, then restart the server.'}), 503

    conn = get_db()
    registration = conn.execute('SELECT * FROM registrations WHERE registration_id = ?', (registration_id,)).fetchone()
    if not registration:
        conn.close()
        return jsonify({'ok': False, 'message': 'Registration not found.'}), 404
    if registration['payment_status'] == 'Paid':
        conn.close()
        return jsonify({'ok': False, 'message': 'This registration is already paid.'}), 409

    if registration['payment_order_id']:
        order_id = registration['payment_order_id']
    else:
        try:
            order = client.order.create({
                'amount': int(registration['amount_paise']),
                'currency': 'INR',
                'receipt': registration_id,
                'notes': {
                    'registration_id': registration_id,
                    'event': 'CIVILATHON 2026',
                },
            })
            order_id = order['id']
            conn.execute('UPDATE registrations SET payment_order_id = ? WHERE registration_id = ?', (order_id, registration_id))
            conn.commit()
        except Exception as exc:
            conn.close()
            return jsonify({'ok': False, 'message': f'Unable to create payment order: {exc}'}), 502
    conn.close()
    return jsonify({
        'ok': True,
        'key_id': RAZORPAY_KEY_ID,
        'order_id': order_id,
        'amount': int(registration['amount_paise']),
        'currency': 'INR',
        'name': registration['leader_name'],
        'email': registration['leader_email'],
        'contact': registration['leader_mobile'],
        'registration_id': registration_id,
    })


@app.post('/api/verify-payment/<registration_id>')
def verify_payment(registration_id):
    payload = request.get_json(silent=True) or {}
    payment_id = payload.get('razorpay_payment_id', '')
    order_id = payload.get('razorpay_order_id', '')
    signature = payload.get('razorpay_signature', '')

    conn = get_db()
    registration = conn.execute('SELECT * FROM registrations WHERE registration_id = ?', (registration_id,)).fetchone()
    if not registration:
        conn.close()
        return jsonify({'ok': False, 'message': 'Registration not found.'}), 404

    if not payment_id or not order_id or not signature:
        conn.close()
        return jsonify({'ok': False, 'message': 'Incomplete Razorpay payment response.'}), 400

    expected = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        f'{order_id}|{payment_id}'.encode(),
        hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        conn.close()
        return jsonify({'ok': False, 'message': 'Payment signature verification failed.'}), 400

    if registration['payment_order_id'] and order_id != registration['payment_order_id']:
        conn.close()
        return jsonify({'ok': False, 'message': 'Payment order does not match this registration.'}), 400

    paid_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute('''
        UPDATE registrations
        SET payment_status = 'Paid', payment_id = ?, payment_order_id = ?, payment_signature = ?, paid_at = ?
        WHERE registration_id = ?
    ''', (payment_id, order_id, signature, paid_at, registration_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'redirect': url_for('success', registration_id=registration_id)})


@app.route('/success/<registration_id>')
def success(registration_id):
    conn = get_db()
    registration = conn.execute(
        'SELECT * FROM registrations WHERE registration_id = ?',
        (registration_id,)
    ).fetchone()
    conn.close()
    if not registration:
        return render_template('page.html', title='Registration Not Found', content='<p class="lead-dark">The registration ID could not be found.</p>'), 404
    return render_template('success.html', registration=registration)


@app.route('/uploads/ppt/<path:filename>')
def uploaded_ppt(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)


@app.errorhandler(413)
def too_large(_error):
    flash('PPT file is too large. Maximum allowed size is 25 MB.', 'error')
    return redirect(url_for('register'))


init_db()

if __name__ == '__main__':
    app.run(debug=True)

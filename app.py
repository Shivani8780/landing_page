from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, validators
import json
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
import stripe

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tickets.db'
app.config['STRIPE_PUBLIC_KEY'] = 'your-stripe-public-key'
app.config['STRIPE_SECRET_KEY'] = 'your-stripe-secret-key'

# Local Development Configuration
app.config['MAIL_SERVER'] = 'localhost'
app.config['MAIL_PORT'] = 1025
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_DEBUG'] = True  # Enable debug output for email
# Remove auth requirements for local debug
app.config['MAIL_USERNAME'] = None
app.config['MAIL_PASSWORD'] = None
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)  # Now properly initialized with the import
stripe.api_key = app.config['STRIPE_SECRET_KEY']

class TicketOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TicketForm(FlaskForm):
    name = StringField('Full Name', [validators.InputRequired()])
    email = StringField('Email', [validators.InputRequired(), validators.Email()])
    quantity = IntegerField('Quantity', [validators.InputRequired(), validators.NumberRange(min=1, max=10)])
    event = SelectField('Event', choices=[
        ('winter-festival', 'Winter Music Festival 2025'), 
        ('spring-jazz', 'Spring Jazz Night 2025'),
        ('summer-rock', 'Summer Rock Fest 2025')
    ])

# Load event data
def load_events():
    with open('data/events.json') as f:
        return json.load(f)

@app.route('/')
def home():
    event_date = datetime(2025, 12, 25, 19, 30)  # Updated to 2025
    return render_template('index.html', event_date=event_date.isoformat())

@app.route('/history')
def history():
    events = load_events()
    return render_template('history.html', events=events)

@app.route('/tickets', methods=['GET', 'POST'])
def tickets():
    if request.method == 'POST':
        # Process form data
        name = request.form.get('name')
        email = request.form.get('email')
        quantity = int(request.form.get('quantity'))
        event = request.form.get('event')
        return redirect(url_for('confirmation', event=event, quantity=quantity))
    return render_template('tickets.html')

@app.route('/confirmation')
def confirmation():
    order_id = request.args.get('order_id')
    if order_id:
        order = TicketOrder.query.get(order_id)
        if order and order.payment_status == 'succeeded':
            return render_template('confirmation.html',
                                event=order.event,
                                event_name=get_event_name(order.event),
                                quantity=order.quantity,
                                price=order.amount/order.quantity/100,
                                total=order.amount/100)
    
    flash('Invalid order or payment not completed', 'error')
    return redirect(url_for('tickets'))

def get_event_name(event_id):
    names = {
        'winter-festival': 'Winter Music Festival 2025',
        'spring-jazz': 'Spring Jazz Night 2025',
        'summer-rock': 'Summer Rock Fest 2025'
    }
    return names.get(event_id, 'Winter Music Festival 2025')

@app.route('/api/history')
def api_history():
    return jsonify(load_events())

@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    data = request.get_json()
    # Validate data here
    return jsonify({'status': 'success', 'message': 'Purchase completed'})

@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, 'your_webhook_signing_secret'
        )
    except ValueError as e:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400

    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        order_id = payment_intent.metadata.get('order_id')
        if order_id:
            order = TicketOrder.query.get(order_id)
            if order:
                order.payment_status = 'succeeded'
                db.session.commit()
                # Send confirmation email
                msg = Message(
                    'Your Ticket Purchase Confirmation',
                    recipients=[order.email]
                )
                msg.html = render_template(
                    'email/confirmation.html',
                    name=order.name,
                    event=order.event,
                    event_name=get_event_name(order.event),
                    quantity=order.quantity,
                    total=order.amount/100
                )
                mail.send(msg)

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)

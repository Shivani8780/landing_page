from flask import Flask, render_template, request, redirect, url_for, jsonify
import json
from datetime import datetime
import os

app = Flask(__name__)

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
        return redirect(url_for('confirmation'))
    return render_template('tickets.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/api/history')
def api_history():
    return jsonify(load_events())

@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    data = request.get_json()
    # Validate data here
    return jsonify({'status': 'success', 'message': 'Purchase completed'})

if __name__ == '__main__':
    app.run(debug=True)
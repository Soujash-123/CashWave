from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo import MongoClient
import bcrypt
import re
import os
from datetime import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB connection
client = MongoClient("mongodb+srv://oppurtunest:hAPV3Tf0QoB0GgiQ@cluster0.mbbgm.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["wallet_system"]
users_collection = db["users"]
transactions_collection = db["transactions"]
money_requests_collection = db["money_requests"]  # New collection

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        # Get form data
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate form data
        if not name or not email or not password or not confirm_password:
            flash('All fields are required', 'error')
            return redirect(url_for('signup'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('signup'))
        
        # Check if email is valid
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            flash('Invalid email address', 'error')
            return redirect(url_for('signup'))
        
        # Check if user already exists
        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('signup'))
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Create user
        user_id = str(uuid.uuid4())
        new_user = {
            'user_id': user_id,
            'name': name,
            'email': email,
            'password': hashed_password,
            'balance': 0.0,
            'created_at': datetime.now()
        }
        
        users_collection.insert_one(new_user)
        
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Find user
        user = users_collection.find_one({'email': email})
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            # Set session
            session['user_id'] = user['user_id']
            session['name'] = user['name']
            session['email'] = user['email']
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = users_collection.find_one({'user_id': session['user_id']})
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    # Get transactions (only completed ones)
    transactions = list(transactions_collection.find({
        '$and': [
            {'type': {'$ne': 'request'}},
            {'$or': [
                {'sender_id': session['user_id']},
                {'receiver_id': session['user_id']}
            ]}
        ]
    }).sort('timestamp', -1).limit(10))
    
    # Add sender/receiver names to transactions
    for transaction in transactions:
        if transaction.get('sender_id'):
            sender = users_collection.find_one({'user_id': transaction['sender_id']})
            transaction['sender_name'] = sender['name'] if sender else 'Unknown'
        if transaction.get('receiver_id'):
            receiver = users_collection.find_one({'user_id': transaction['receiver_id']})
            transaction['receiver_name'] = receiver['name'] if receiver else 'Unknown'
    
    # Get money requests
    money_requests = list(money_requests_collection.find({
        '$or': [
            {'from_user_id': session['user_id']},
            {'to_user_id': session['user_id']}
        ]
    }).sort('timestamp', -1))
    
    # Add requester/requestee names
    for request in money_requests:
        requester = users_collection.find_one({'user_id': request['from_user_id']})
        request['requester_name'] = requester['name'] if requester else 'Unknown'
    
    return render_template('dashboard.html', 
                         user=user, 
                         transactions=transactions,
                         money_requests=money_requests)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/search_users')
def search_users():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    query = request.args.get('query', '')
    if len(query) < 2:
        return jsonify([])
    
    users = users_collection.find({
        '$and': [
            {'user_id': {'$ne': session['user_id']}},
            {'$or': [
                {'name': {'$regex': query, '$options': 'i'}},
                {'email': {'$regex': query, '$options': 'i'}}
            ]}
        ]
    }, {'_id': 0, 'user_id': 1, 'name': 1, 'email': 1})
    
    return jsonify(list(users))

@app.route('/add_money', methods=['POST'])
def add_money():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    amount = float(request.form.get('amount', 0))
    if amount <= 0:
        flash('Invalid amount', 'error')
        return redirect(url_for('dashboard'))
    
    # Add money to user's balance
    users_collection.update_one(
        {'user_id': session['user_id']},
        {'$inc': {'balance': amount}}
    )
    
    # Record transaction with sender_id and receiver_id
    transaction = {
        'transaction_id': str(uuid.uuid4()),
        'type': 'deposit',
        'sender_id': session['user_id'],  # Set sender as self
        'receiver_id': session['user_id'],  # Set receiver as self
        'amount': amount,
        'status': 'Completed',
        'sender_name': session['name'],  # Add sender name
        'receiver_name': session['name'],  # Add receiver name
        'timestamp': datetime.now()
    }
    transactions_collection.insert_one(transaction)
    
    flash(f'Added ₹{amount:.2f} to your balance', 'success')
    return redirect(url_for('dashboard'))

@app.route('/send_money', methods=['POST'])
def send_money():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    recipient_id = request.form.get('recipient_id')
    amount = float(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('Invalid amount', 'error')
        return redirect(url_for('dashboard'))
    
    # Verify sender has enough balance
    sender = users_collection.find_one({'user_id': session['user_id']})
    if sender['balance'] < amount:
        flash('Insufficient balance', 'error')
        return redirect(url_for('dashboard'))
    
    # Verify recipient exists
    recipient = users_collection.find_one({'user_id': recipient_id})
    if not recipient:
        flash('Recipient not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Process transaction
    users_collection.update_one(
        {'user_id': session['user_id']},
        {'$inc': {'balance': -amount}}
    )
    users_collection.update_one(
        {'user_id': recipient_id},
        {'$inc': {'balance': amount}}
    )
    
    # Record transaction
    transaction = {
        'transaction_id': str(uuid.uuid4()),
        'type': 'transfer',
        'sender_id': session['user_id'],
        'receiver_id': recipient_id,
        'amount': amount,
        'status': 'completed',
        'timestamp': datetime.now()
    }
    transactions_collection.insert_one(transaction)
    
    flash(f'Sent ₹{amount:.2f} to {recipient["name"]}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/request_money', methods=['POST'])
def request_money():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    to_user_id = request.form.get('sender_id')  # The person who will send money
    amount = float(request.form.get('amount', 0))
    
    if amount <= 0:
        flash('Invalid amount', 'error')
        return redirect(url_for('dashboard'))
    
    # Verify user exists
    to_user = users_collection.find_one({'user_id': to_user_id})
    if not to_user:
        flash('User not found', 'error')
        return redirect(url_for('dashboard'))
    
    # Create money request
    request_data = {
        'request_id': str(uuid.uuid4()),
        'from_user_id': session['user_id'],  # Person requesting money
        'to_user_id': to_user_id,  # Person who will send money
        'amount': amount,
        'status': 'Pending',
        'timestamp': datetime.now()
    }
    money_requests_collection.insert_one(request_data)
    
    flash(f'Money request sent to {to_user["name"]}', 'success')
    return redirect(url_for('dashboard'))

@app.route('/money-request/<request_id>/<action>', methods=['POST'])
def handle_money_request(request_id, action):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # Find the money request
    money_request = money_requests_collection.find_one({'request_id': request_id})
    if not money_request:
        return jsonify({'success': False, 'message': 'Request not found'})
    
    if action == 'approve':
        # Check if user has enough balance
        sender = users_collection.find_one({'user_id': money_request['to_user_id']})
        if sender['balance'] < money_request['amount']:
            return jsonify({'success': False, 'message': 'Insufficient balance'})
        
        # Process the transfer
        users_collection.update_one(
            {'user_id': money_request['to_user_id']},
            {'$inc': {'balance': -money_request['amount']}}
        )
        users_collection.update_one(
            {'user_id': money_request['from_user_id']},
            {'$inc': {'balance': money_request['amount']}}
        )
        
        # Create transaction record
        transaction = {
            'transaction_id': str(uuid.uuid4()),
            'type': 'transfer',
            'sender_id': money_request['to_user_id'],
            'receiver_id': money_request['from_user_id'],
            'amount': money_request['amount'],
            'status': 'Completed',
            'timestamp': datetime.now()
        }
        transactions_collection.insert_one(transaction)
        
        # Update request status
        money_requests_collection.update_one(
            {'request_id': request_id},
            {'$set': {'status': 'Approved'}}
        )
    
    elif action == 'reject':
        money_requests_collection.update_one(
            {'request_id': request_id},
            {'$set': {'status': 'Rejected'}}
        )
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port="8000")

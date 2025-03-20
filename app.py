from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId  # Add this import
import bcrypt
import os
from datetime import datetime
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
import qrcode
from PIL import Image
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB Connection
uri = "mongodb+srv://soujashdb:03QCpRZhezwWV6Aq@cluster0.8ksc8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

# Database and Collections
db = client.antique_treasures
users = db.users
products = db.products

# Admin credentials (hidden, only one set)
admin_username = "admin"
admin_password = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())

# Cloudinary Configuration
cloudinary.config( 
    cloud_name = "drabj4clh", 
    api_key = "275188839364347", 
    api_secret = "gBPxAI6YaQA_F6I8ub12K6zAwBI",
    secure = True
)

def generate_upi_qr(upi_id, name, amount="undefined", note="undefined"):
    upi_uri = f"upi://pay?pn={name}&pa={upi_id}&am={amount}&tn={note}&cu=INR"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(upi_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}", upi_uri

# Routes
@app.route('/')
def home():
    return render_template('login.html')

# User (Buyer) Login and Signup
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if it's admin
        if username == admin_username and bcrypt.checkpw(password.encode('utf-8'), admin_password):
            session['username'] = username
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))
        
        # Check if it's a buyer
        user = users.find_one({"username": username, "role": "buyer"})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['username'] = username
            session['role'] = 'buyer'
            return redirect(url_for('buyer_dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        
        # Check if username already exists
        existing_user = users.find_one({"username": username})
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('signup'))
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insert new user
        users.insert_one({
            "username": username,
            "password": hashed_password,
            "email": email,
            "role": "buyer"
        })
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

# Seller Login and Signup
@app.route('/login_seller', methods=['GET', 'POST'])
def login_seller():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Check if it's a seller
        user = users.find_one({"username": username, "role": "seller"})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            session['username'] = username
            session['role'] = 'seller'
            return redirect(url_for('seller_dashboard'))
        
        flash('Invalid username or password')
    
    return render_template('login_seller.html')

@app.route('/signup_seller', methods=['GET', 'POST'])
def signup_seller():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        business_name = request.form['business_name']
        upi_id = request.form['upi_id']  # New field
        
        # Check if username already exists
        existing_user = users.find_one({"username": username})
        if existing_user:
            flash('Username already exists')
            return redirect(url_for('signup_seller'))
        
        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # Insert new seller
        users.insert_one({
            "username": username,
            "password": hashed_password,
            "email": email,
            "business_name": business_name,
            "upi_id": upi_id,  # Add UPI ID
            "role": "seller"
        })
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login_seller'))
    
    return render_template('signup_seller.html')

# Dashboard placeholders
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        return "Admin Dashboard - Coming Soon"
    return redirect(url_for('login'))

@app.route('/buyer_dashboard')
def buyer_dashboard():
    if 'username' in session and session['role'] == 'buyer':
        search_query = request.args.get('search', '')
        if search_query:
            product_list = products.find({
                'name': {'$regex': search_query, '$options': 'i'}
            })
        else:
            product_list = products.find()
        return render_template('dashboard.html', products=product_list)
    return redirect(url_for('login'))

@app.route('/seller_dashboard')
def seller_dashboard():
    if 'username' in session and session['role'] == 'seller':
        seller_products = products.find({'seller': session['username']})
        orders = db.orders.find({'seller': session['username']})
        return render_template('seller_dashboard.html', products=seller_products, orders=orders)
    return redirect(url_for('login_seller'))

@app.route('/add_product', methods=['POST'])
def add_product():
    if 'username' in session and session['role'] == 'seller':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        quantity = int(request.form['quantity'])
        
        # Handle image uploads
        images = request.files.getlist('images')
        if len(images) < 2 or len(images) > 5:
            flash('Please upload between 2 and 5 images')
            return redirect(url_for('seller_dashboard'))
        
        image_urls = []
        for image in images:
            if image:
                upload_result = cloudinary.uploader.upload(image,
                    folder=f"antique_treasures/{session['username']}")
                image_urls.append({
                    'url': upload_result['secure_url'],
                    'public_id': upload_result['public_id']
                })
        
        products.insert_one({
            'name': name,
            'description': description,
            'price': price,
            'quantity': quantity,
            'seller': session['username'],
            'images': image_urls,
            'created_at': datetime.now()
        })
        
        flash('Product added successfully!')
        return redirect(url_for('seller_dashboard'))
    return redirect(url_for('login_seller'))

@app.route('/generate_payment_qr/<product_id>/<quantity>')
def generate_payment_qr(product_id, quantity):
    if 'username' in session and session['role'] == 'buyer':
        product = products.find_one({'_id': ObjectId(product_id)})
        if product:
            seller = users.find_one({'username': product['seller']})
            amount = float(product['price']) * int(quantity)
            qr_code, upi_url = generate_upi_qr(
                seller['upi_id'],
                seller['business_name'],
                f"{amount:.2f}",
                f"Payment for {product['name']}"
            )
            return jsonify({
                'qr_code': qr_code,
                'upi_url': upi_url,
                'amount': amount
            })
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/submit_payment/<product_id>', methods=['POST'])
def submit_payment(product_id):
    if 'username' in session and session['role'] == 'buyer':
        try:
            receipt = request.files.get('receipt')
            quantity = request.form.get('quantity')
            
            if not receipt or not quantity:
                return jsonify({'error': 'Missing receipt or quantity'}), 400
            
            # Validate file type
            allowed_extensions = {'png', 'jpg', 'jpeg'}
            if not '.' in receipt.filename or \
               receipt.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                return jsonify({'error': 'Invalid file type. Please upload a PNG or JPEG image'}), 400
            
            quantity = int(quantity)
            product = products.find_one({'_id': ObjectId(product_id)})
            
            if not product:
                return jsonify({'error': 'Product not found'}), 404
                
            if quantity > product['quantity']:
                return jsonify({'error': 'Requested quantity not available'}), 400
            
            # Upload to Cloudinary with specific folder and format
            upload_result = cloudinary.uploader.upload(
                receipt,
                folder=f"antique_treasures/receipts/{session['username']}",
                allowed_formats=['png', 'jpg', 'jpeg'],
                transformation=[
                    {'quality': 'auto:good'},
                    {'width': 800, 'crop': 'limit'}
                ]
            )
            
            # Create order with receipt details
            order = {
                'product_id': ObjectId(product_id),
                'buyer': session['username'],
                'quantity': quantity,
                'receipt_url': upload_result['secure_url'],
                'receipt_id': upload_result['public_id'],
                'receipt_created': upload_result['created_at'],
                'status': 'pending',
                'created_at': datetime.now(),
                'product_name': product['name'],
                'seller': product['seller'],
                'total_amount': float(product['price']) * quantity
            }
            
            result = db.orders.insert_one(order)
            
            if not result.inserted_id:
                # If order creation fails, delete the uploaded image
                cloudinary.uploader.destroy(upload_result['public_id'])
                return jsonify({'error': 'Failed to create order'}), 500
                
            return jsonify({'success': True})
            
        except Exception as e:
            print(f"Error in submit_payment: {str(e)}")
            return jsonify({'error': 'Server error occurred'}), 500
            
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/verify_payment/<order_id>/<action>')
def verify_payment(order_id, action):
    if 'username' in session and session['role'] == 'seller':
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        
        if order and order['seller'] == session['username']:
            if action == 'approve':
                # Update order status and reduce product quantity
                db.orders.update_one(
                    {'_id': ObjectId(order_id)},
                    {'$set': {'status': 'approved'}}
                )
                products.update_one(
                    {'_id': order['product_id']},
                    {'$inc': {'quantity': -order['quantity']}}
                )
            elif action == 'reject':
                db.orders.update_one(
                    {'_id': ObjectId(order_id)},
                    {'$set': {'status': 'rejected'}}
                )
            
            return jsonify({'success': True})
    
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/my_orders')
def my_orders():
    if 'username' in session and session['role'] == 'buyer':
        orders = db.orders.find({'buyer': session['username']}).sort('created_at', -1)
        return render_template('my_orders.html', orders=orders)
    return redirect(url_for('login'))

@app.route('/update_order_status/<order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'username' in session and session['role'] == 'seller':
        status = request.form.get('status')
        update_notes = request.form.get('update_notes')
        current_time = datetime.now()
        
        order = db.orders.find_one({'_id': ObjectId(order_id)})
        if order and order['seller'] == session['username']:
            updates = order.get('status_updates', [])
            updates.append({
                'status': status,
                'notes': update_notes,
                'timestamp': current_time
            })
            
            db.orders.update_one(
                {'_id': ObjectId(order_id)},
                {
                    '$set': {
                        'status': status,
                        'status_updates': updates,
                        'last_updated': current_time
                    }
                }
            )
            return jsonify({'success': True})
    return jsonify({'error': 'Unauthorized'}), 401

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
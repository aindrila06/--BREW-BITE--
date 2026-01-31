from dotenv import load_dotenv
load_dotenv()

import os
import random
from datetime import datetime, timedelta

import requests
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   session, url_for)
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# --- App Initialization ---
app = Flask(__name__)
# For production, this key should be a long, random string stored securely as an environment variable
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_super_secret_key_for_your_cafe_app')


# --- Database Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/cafe.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
with app.app_context():
    db.create_all()



# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('EMAIL_USER')
mail = Mail(app)


# --- DATABASE MODELS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    sentiment = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.String(20), unique=True, nullable=False)
    table_id = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    party_size = db.Column(db.Integer, nullable=False)

class DineInOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), unique=True, nullable=False)
    table_number = db.Column(db.Integer, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    items = db.Column(db.JSON, nullable=False)
    total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='preparing') # preparing -> ready -> notified
    estimated_ready_time = db.Column(db.DateTime, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class OnlineOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(30), unique=True, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    items = db.Column(db.JSON, nullable=False)
    total = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- STATIC DATA ---
MENU_DATA = {
    'breakfast': [
        {'id': 1, 'name': 'Masala Oats', 'description': 'Healthy oats cooked with Indian spices.', 'price': 150, 'base_popularity': 7, 'category': 'warm', 'type': 'healthy'},
        {'id': 2, 'name': 'Pancakes & Syrup', 'description': 'Fluffy pancakes with maple syrup and berries.', 'price': 220, 'base_popularity': 8, 'category': 'sweet', 'type': 'classic'},
        {'id': 9, 'name': 'Aloo Paratha', 'description': 'Whole wheat flatbread stuffed with spiced potato, served with pickle.', 'price': 180, 'base_popularity': 9, 'category': 'hearty', 'type': 'classic'},
        {'id': 10, 'name': 'Fruit Smoothie Bowl', 'description': 'Blended fresh fruits topped with granola and seeds.', 'price': 200, 'base_popularity': 6, 'category': 'cold', 'type': 'healthy'},
        {'id': 11, 'name': 'Scrambled Eggs on Toast', 'description': 'Creamy scrambled eggs with buttered toast and grilled tomatoes.', 'price': 210, 'base_popularity': 7, 'category': 'warm', 'type': 'classic'},
        {'id': 12, 'name': 'Dosa', 'description': 'Crispy South Indian crepe served with sambar and chutneys.', 'price': 190, 'base_popularity': 8, 'category': 'classic', 'type': 'healthy'},
        {'id': 13, 'name': 'French Toast', 'description': 'Golden brown French toast with a dusting of powdered sugar.', 'price': 230, 'base_popularity': 7, 'category': 'sweet', 'type': 'classic'},
        {'id': 29, 'name': 'Muesli with Yogurt', 'description': 'Toasted muesli served with fresh yogurt and honey.', 'price': 170, 'base_popularity': 6, 'category': 'cold', 'type': 'healthy'},
        {'id': 30, 'name': 'Uttapam', 'description': 'Thick South Indian pancake topped with onions and tomatoes.', 'price': 195, 'base_popularity': 7, 'category': 'classic', 'type': 'healthy'},
        {'id': 31, 'name': 'Belgian Waffles', 'description': 'Crispy waffles served with whipped cream and chocolate sauce.', 'price': 240, 'base_popularity': 8, 'category': 'sweet', 'type': 'classic'},
        {'id': 32, 'name': 'Cheela (Savory Pancake)', 'description': 'Lentil flour pancake with mixed vegetables and spices.', 'price': 160, 'base_popularity': 7, 'category': 'warm', 'type': 'healthy'},
        {'id': 33, 'name': 'Omelette Pav', 'description': 'Spicy Indian omelette served inside a soft bread roll.', 'price': 185, 'base_popularity': 9, 'category': 'hearty', 'type': 'classic'},
    ],
    'lunch': [
        {'id': 3, 'name': 'Chicken Biryani', 'description': 'Aromatic rice dish with tender chicken.', 'price': 350, 'base_popularity': 9, 'category': 'hearty', 'type': 'classic'},
        {'id': 4, 'name': 'Veg Thali', 'description': 'Complete meal with rice, roti, dal, and sabzi.', 'price': 250, 'base_popularity': 8, 'category': 'classic', 'type': 'hearty'},
        {'id': 14, 'name': 'Paneer Butter Masala & Naan', 'description': 'Creamy paneer curry served with soft naan bread.', 'price': 300, 'base_popularity': 9, 'category': 'hearty', 'type': 'classic'},
        {'id': 15, 'name': 'Chicken Wrap', 'description': 'Grilled chicken and fresh veggies wrapped in a soft tortilla.', 'price': 280, 'base_popularity': 7, 'category': 'light', 'type': 'fast food'},
        {'id': 16, 'name': 'Pasta Arrabiata', 'description': 'Penne pasta in a spicy tomato sauce with olives.', 'price': 320, 'base_popularity': 7, 'category': 'continental', 'type': 'classic'},
        {'id': 17, 'name': 'Dal Makhani & Rice', 'description': 'Slow-cooked black lentils in a rich, creamy sauce with basmati rice.', 'price': 270, 'base_popularity': 8, 'category': 'hearty', 'type': 'classic'},
        {'id': 18, 'name': 'Caesar Salad with Grilled Chicken', 'description': 'Fresh romaine lettuce, croutons, parmesan, and grilled chicken with Caesar dressing.', 'price': 380, 'base_popularity': 6, 'category': 'light', 'type': 'healthy'},
        {'id': 34, 'name': 'Rajma Chawal (Kidney Beans & Rice)', 'description': 'Classic North Indian comfort food: red kidney bean curry served with steamed rice.', 'price': 240, 'base_popularity': 8, 'category': 'hearty', 'type': 'classic'},
        {'id': 35, 'name': 'Quinoa and Vegetable Bowl', 'description': 'High-protein quinoa mixed with roasted seasonal vegetables and a lemon vinaigrette.', 'price': 360, 'base_popularity': 6, 'category': 'light', 'type': 'healthy'},
        {'id': 36, 'name': 'Club Sandwich', 'description': 'Triple-decker sandwich with chicken/veg, cheese, lettuce, tomato, and fries.', 'price': 290, 'base_popularity': 9, 'category': 'light', 'type': 'fast food'},
        {'id': 37, 'name': 'Mutter Paneer & Roti', 'description': 'Peas and cottage cheese in a rich tomato gravy, served with Indian flatbread.', 'price': 295, 'base_popularity': 7, 'category': 'hearty', 'type': 'classic'},
        {'id': 38, 'name': 'Spicy Tuna Melt', 'description': 'Grilled sandwich with spicy tuna, melted cheese, and fresh slaw.', 'price': 310, 'base_popularity': 6, 'category': 'light', 'type': 'fast food'},
    ],
    'dinner': [
        {'id': 5, 'name': 'Paneer Tikka Masala', 'description': 'Grilled paneer in a spiced creamy tomato sauce.', 'price': 320, 'base_popularity': 9, 'category': 'hearty', 'type': 'classic'},
        {'id': 6, 'name': 'Grilled Fish', 'description': 'Fish fillet grilled with lemon-butter sauce.', 'price': 450, 'base_popularity': 7, 'category': 'light', 'type': 'healthy'},
        {'id': 19, 'name': 'Mushroom Do Pyaza', 'description': 'Mushrooms cooked with two types of onions in a rich gravy.', 'price': 290, 'base_popularity': 7, 'category': 'hearty', 'type': 'classic'},
        {'id': 20, 'name': 'Chicken Korma', 'description': 'Mildly spiced chicken curry in a rich cashew-based gravy.', 'price': 380, 'base_popularity': 8, 'category': 'hearty', 'type': 'classic'},
        {'id': 21, 'name': 'Veg Pulao with Raita', 'description': 'Fragrant basmati rice cooked with mixed vegetables, served with spiced yogurt.', 'price': 260, 'base_popularity': 6, 'category': 'light', 'type': 'healthy'},
        {'id': 22, 'name': 'Shepherd\'s Pie', 'description': 'Hearty minced meat and vegetable filling topped with mashed potatoes.', 'price': 400, 'base_popularity': 7, 'category': 'hearty', 'type': 'classic'},
        {'id': 23, 'name': 'Lemon Herb Roasted Chicken', 'description': 'Half chicken roasted with lemon and herbs, served with roasted vegetables.', 'price': 500, 'base_popularity': 8, 'category': 'light', 'type': 'healthy'},
        {'id': 39, 'name': 'Baingan Bharta', 'description': 'Smoked and mashed eggplant cooked with Indian spices, served with tandoori roti.', 'price': 310, 'base_popularity': 6, 'category': 'hearty', 'type': 'classic'},
        {'id': 40, 'name': 'Chicken Stroganoff', 'description': 'Slices of chicken breast in a creamy mushroom sauce, served over buttered rice.', 'price': 430, 'base_popularity': 7, 'category': 'hearty', 'type': 'classic'},
        {'id': 41, 'name': 'Minestrone Soup', 'description': 'Classic Italian vegetable soup with pasta and a drizzle of olive oil.', 'price': 280, 'base_popularity': 6, 'category': 'light', 'type': 'healthy'},
        {'id': 42, 'name': 'Tandoori Prawns', 'description': 'Prawns marinated in yogurt and spices, cooked in a tandoor (clay oven).', 'price': 550, 'base_popularity': 8, 'category': 'light', 'type': 'classic'},
        {'id': 43, 'name': 'Veggie Burger with Sweet Potato Fries', 'description': 'Homemade veggie patty in a sesame bun with all the fixings.', 'price': 340, 'base_popularity': 7, 'category': 'hearty', 'type': 'fast food'},
    ],
    'drinks': [
        {'id': 7, 'name': 'Cold Coffee', 'description': 'Rich and creamy cold coffee.', 'price': 180, 'base_popularity': 8, 'category': 'cold', 'type': 'sweet'},
        {'id': 8, 'name': 'Masala Chai', 'description': 'Traditional Indian spiced tea.', 'price': 90, 'base_popularity': 10, 'category': 'hot', 'type': 'classic'},
        {'id': 24, 'name': 'Fresh Lime Soda', 'description': 'Refreshing lime soda, available sweet, salty, or mixed.', 'price': 120, 'base_popularity': 9, 'category': 'cold', 'type': 'refreshing'},
        {'id': 25, 'name': 'Espresso', 'description': 'Strong, concentrated coffee shot.', 'price': 100, 'base_popularity': 6, 'category': 'hot', 'type': 'coffee'},
        {'id': 26, 'name': 'Green Tea', 'description': 'Light and healthy green tea, perfect for digestion.', 'price': 80, 'base_popularity': 7, 'category': 'hot', 'type': 'healthy'},
        {'id': 27, 'name': 'Mango Lassi', 'description': 'Sweet and creamy yogurt drink blended with fresh mango pulp.', 'price': 160, 'base_popularity': 8, 'category': 'cold', 'type': 'sweet'},
        {'id': 28, 'name': 'Iced Tea (Peach)', 'description': 'Chilled black tea infused with sweet peach flavor.', 'price': 140, 'base_popularity': 7, 'category': 'cold', 'type': 'sweet'},
        {'id': 44, 'name': 'Caramel Frappe', 'description': 'Blended coffee with caramel syrup and whipped cream.', 'price': 220, 'base_popularity': 9, 'category': 'cold', 'type': 'sweet'},
        {'id': 45, 'name': 'Hot Chocolate', 'description': 'Rich, dark melted chocolate with steamed milk.', 'price': 190, 'base_popularity': 8, 'category': 'hot', 'type': 'sweet'},
        {'id': 46, 'name': 'Ginger Lemon Honey Tea', 'description': 'A soothing, warm beverage for relaxation and immunity.', 'price': 110, 'base_popularity': 7, 'category': 'hot', 'type': 'healthy'},
        {'id': 47, 'name': 'Watermelon Juice', 'description': 'Freshly squeezed watermelon juice, a natural coolant.', 'price': 150, 'base_popularity': 8, 'category': 'cold', 'type': 'refreshing'},
        {'id': 48, 'name': 'Cappuccino', 'description': 'Espresso with steamed milk and a thick layer of foam.', 'price': 130, 'base_popularity': 9, 'category': 'hot', 'type': 'coffee'},
    ]
}
ALL_MENU_ITEMS = [item for category_items in MENU_DATA.values() for item in category_items]
TABLE_DATA = [
    {'id': 1, 'name': 'Table 1', 'capacity': 2, 'properties': ['window', 'quiet']},
    {'id': 2, 'name': 'Table 2', 'capacity': 2, 'properties': ['window']},
    {'id': 3, 'name': 'Table 3', 'capacity': 4, 'properties': ['quiet', 'corner']},
    {'id': 4, 'name': 'Table 4', 'capacity': 4, 'properties': ['social']},
    {'id': 5, 'name': 'Table 5', 'capacity': 6, 'properties': ['social', 'group']},
    {'id': 6, 'name': 'Table 6', 'capacity': 8, 'properties': ['group', 'private']},
]

# --- AI HELPER FUNCTIONS ---
def get_weather_data():
    try:
        api_url = f'https://api.open-meteo.com/v1/forecast?latitude=22.57&longitude=88.36&current_weather=true'
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return {'temperature': data['current_weather']['temperature']}
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch weather data: {e}")
        return {'temperature': 28}

def get_local_event():
    if datetime.now().weekday() >= 4:
        if random.random() < 0.4: return 'Festival Weekend'
    if random.random() < 0.1: return 'Gameday'
    return None

def calculate_dynamic_scores(weather, event):
    temperature = weather.get('temperature', 28)
    scored_items = []
    for item in ALL_MENU_ITEMS:
        item_copy = item.copy()
        score = item_copy['base_popularity']
        item_category = item_copy.get('category', '')
        item_type = item_copy.get('type', '')
        if temperature < 24:
            if item_category in ['hot', 'hearty', 'warm']: score += 3
            if item_type == 'cold': score -= 2
        elif temperature > 30:
            if item_category in ['cold', 'light']: score += 3
            if item_category in ['hot', 'hearty']: score -= 2
        if event == 'Festival Weekend':
            if item_type in ['sweet', 'classic', 'hearty']: score += 4
        elif event == 'Gameday':
            if item_copy['name'] in ['Chicken Biryani', 'Cold Coffee']: score += 3
        item_copy['dynamic_score'] = score + random.uniform(-0.5, 0.5)
        scored_items.append(item_copy)
    return scored_items

def apply_dynamic_pricing(menu_items):
    now = datetime.now()
    current_hour = now.hour
    updated_items = []
    for item in menu_items:
        new_item = item.copy()
        new_item['original_price'] = new_item['price']
        new_item['price_reason'] = None
        if 16 <= current_hour < 18 and new_item.get('category') == 'drinks' and new_item.get('type') == 'cold':
            new_item['price'] = round(new_item['price'] * 0.8)
            new_item['price_reason'] = 'Happy Hour!'
        if current_hour >= 21 and new_item.get('category') != 'drinks':
            new_item['price'] = round(new_item['price'] * 0.7)
            new_item['price_reason'] = 'Closing Time Deal!'
        if 13 <= current_hour < 14 and new_item.get('base_popularity', 0) >= 9:
            new_item['price'] = round(new_item['price'] * 1.1)
            new_item['price_reason'] = 'Peak Hour Pricing'
        updated_items.append(new_item)
    return updated_items

def get_image_map():
    return {
        1: 'images/masalaoats.jpg', 2: 'images/pancakes.jpg', 3: 'images/Chicken-Biryani.jpg',
        4: 'images/vegthali.jpg', 5: 'images/paneer.png', 6: 'images/grilledfish.jpg',
        7: 'images/coldcoffee.jpg', 8: 'images/masalachai.jpg', 9: 'images/alooparatha.jpg',
        10: 'images/fruit_smoothie_bowl.jpg', 11: 'images/scrambled_eggs.jpg', 12: 'images/dosa.jpg',
        13: 'images/french_toast.jpg', 14: 'images/paneer_butter_masala.jpg', 15: 'images/chicken_wrap.jpg',
        16: 'images/pasta_arrabiata.jpg', 17: 'images/dal_makhani.jpg', 18: 'images/caesar_salad.jpg',
        19: 'images/mushroom_do_pyaza.jpg', 20: 'images/chicken_korma.jpg', 21: 'images/veg_pulao.jpg',
        22: 'images/shepherds_pie.jpg', 23: 'images/roasted_chicken.jpg', 24: 'images/fresh_lime_soda.jpg',
        25: 'images/espresso.jpg', 26: 'images/green_tea.jpg', 27: 'images/mango_lassi.jpg',
        28: 'images/iced_peach_tea.jpg', 29: 'images/muesli.jpg', 30: 'images/uttapam.jpg',
        31: 'images/waffles.jpg', 32: 'images/cheela.jpg', 33: 'images/omelette_pav.jpg',
        34: 'images/rajmachawal.jpg', 35: 'images/quinoa_bowl.jpg', 36: 'images/club_sandwich.jpg',
        37: 'images/mutter_paneer.jpg', 38: 'images/tuna_melt.jpg', 39: 'images/baingan_bharta.jpg',
        40: 'images/chicken_stroganoff.jpg', 41: 'images/minestrone_soup.jpg', 42: 'images/tandoori_prawns.jpg',
        43: 'images/veggie_burger.jpg', 44: 'images/caramel_frappe.jpg', 45: 'images/hot_chocolate.jpg',
        46: 'images/ginger_tea.jpg', 47: 'images/watermelon_juice.jpg', 48: 'images/cappuccino.jpg',
    }

def check_prepared_orders():
    now = datetime.utcnow()
    orders_to_check = DineInOrder.query.filter(
        DineInOrder.status == 'preparing',
        DineInOrder.estimated_ready_time <= now
    ).all()
    if orders_to_check:
        for order in orders_to_check:
            order.status = 'ready'
        db.session.commit()

# --- STANDARD PAGE & AUTH ROUTES ---
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')

        if not name:
            flash('Name is required.', 'error')
            return redirect(url_for('signup'))
            
        if User.query.filter_by(email=email).first():
            flash('An account with this email already exists.', 'error')
            return redirect(url_for('signup'))
            
        otp = random.randint(100000, 999999)
        session['signup_data'] = {'name': name, 'email': email, 'password': password, 'otp': otp}

        try:
            msg = Message(subject="Your Brew & Bite Verification Code", recipients=[email])
            msg.body = f"Hello {name},\n\nYour verification code is: {otp}\n\n- The Brew & Bite Team"
            mail.send(msg)
            flash('A verification code has been sent to your email.', 'success')
            return redirect(url_for('verify_otp'))
        except Exception as e:
            print(f"Failed to send OTP email: {e}")
            flash('Could not send verification email. Please try again.', 'error')
            return redirect(url_for('signup'))
            
    return render_template('signup.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'signup_data' not in session:
        return redirect(url_for('signup'))

    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        signup_data = session.get('signup_data', {})
        
        if submitted_otp and int(submitted_otp) == signup_data.get('otp'):
            is_admin_user = signup_data.get('email') == 'aindrilas882@gmail.com'
            new_user = User(
                name=signup_data.get('name'),
                email=signup_data.get('email'),
                password=signup_data.get('password'),
                is_admin=is_admin_user
            )
            db.session.add(new_user)
            db.session.commit()
            
            session.pop('signup_data', None)
            flash('Email verified successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
            return redirect(url_for('verify_otp'))
            
    return render_template('verify_otp.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session['user'] = user.email
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin
            
            flash(f'Welcome back, {user.name}!', 'success')

            try:
                login_time = datetime.now().strftime('%d %b %Y at %I:%M %p')
                msg = Message(subject="New Login to Your Brew & Bite Account", recipients=[user.email])
                msg.body = (f"Hello {user.name},\n\nYour account was just accessed on {login_time}.\n\n- The Brew & Bite Team")
                mail.send(msg)
            except Exception as e:
                print(f"Failed to send login notification email: {e}")

            # ADDED THIS BLOCK
            # Checks if the user was trying to access a protected page before logging in.
            next_url = session.pop('next', None)
            if next_url:
                return redirect(next_url)

            # Default redirects if no specific page was requested
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password. Please try again.', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('landing'))

@app.route('/home')
def home():
    user_name = session.get('user_name')
    latest_feedback_db = Feedback.query.order_by(Feedback.timestamp.desc()).limit(3).all()
    feedback_items = [{'text': item.text, 'sentiment': item.sentiment, 'timestamp': item.timestamp.strftime('%d %b %Y, %I:%M %p')} for item in latest_feedback_db]
    return render_template('home.html', feedback_items=feedback_items, user_name=user_name)

# --- Dynamic Page Routes ---
@app.route('/main_menu')
def main_menu():
    user_name = session.get('user_name')
    return render_template('main_menu.html', user_name=user_name)

@app.route('/breakfast')
def breakfast(): return render_template('breakfast.html')

@app.route('/lunch')
def lunch(): return render_template('lunch.html')

@app.route('/dinner')
def dinner(): return render_template('dinner.html')

@app.route('/drinks')
def drinks(): return render_template('drinks.html')

@app.route('/add_to_cart')
def add_to_cart(): return render_template('add_to_cart.html')

@app.route('/card')
def card(): return render_template('card.html')

@app.route('/upi')
def upi(): return render_template('upi.html')

@app.route('/order_confirm/<order_id>')
def order_confirm(order_id):
    return render_template('order_confirm.html', order_id=order_id)

@app.route('/order_confirm')
def order_confirm_fallback():
    flash('To see a specific order, please complete the checkout process first.', 'info')
    return redirect(url_for('main_menu'))

# In app.py, find and UPDATE this route

@app.route('/offline_table_booking')
def offline_table_booking():
    # If the 'user' key is not in the session, they are not logged in
    if 'user' not in session:
        flash('You must be logged in to book a table.', 'error')
        # Store the page they wanted to visit
        session['next'] = url_for('offline_table_booking')
        # Redirect them to the login page
        return redirect(url_for('login'))
        
    # If they are logged in, show them the booking page as normal
    return render_template('offline_table_booking.html')

@app.route('/dine_in_menu')
def dine_in_menu():
    # Get user details from the session if they exist
    user_name = session.get('user_name')
    user_email = session.get('user')
    return render_template('dine_in_menu.html', user_name=user_name, user_email=user_email)

@app.route('/table_order')
def table_order():
    # Get the user's name from the session to pass to the template
    user_name = session.get('user_name')
    return render_template('table_order.html', user_name=user_name)

@app.route('/dine_in_receipt')
def dine_in_receipt(): return render_template('dine_in_receipt.html')

@app.route('/kitchen')
def kitchen_display(): return render_template('kitchen_display.html')

@app.route('/online-order')
def online_order_page():
    user_name = session.get('user_name')
    return render_template('online_order.html', user_name=user_name)

# --- ADMIN ROUTES ---
@app.route('/admin_login')
def admin_login():
    return redirect(url_for('login'))

@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get('is_admin'):
        flash('You must be an admin to view this page.', 'error')
        return redirect(url_for('login'))
    all_feedback = Feedback.query.order_by(Feedback.timestamp.desc()).all()
    all_bookings = Booking.query.order_by(Booking.date.desc(), Booking.time.desc()).all()
    positive_count = sum(1 for item in all_feedback if item.sentiment == 'Positive')
    negative_count = sum(1 for item in all_feedback if item.sentiment == 'Negative')
    neutral_count = len(all_feedback) - positive_count - negative_count
    bookings_with_names = []
    for booking in all_bookings:
        table_name = next((table['name'] for table in TABLE_DATA if table['id'] == booking.table_id), 'Unknown')
        bookings_with_names.append({
            'booking_id': booking.booking_id, 'table_name': table_name,
            'date': booking.date, 'time': booking.time, 'party_size': booking.party_size
        })
    return render_template('admin_dashboard.html',
                           positive_count=positive_count, negative_count=negative_count,
                           neutral_count=neutral_count, total_count=len(all_feedback),
                           feedback_items=all_feedback, booking_items=bookings_with_names)

# --- API & AI FEATURE ROUTES ---
@app.route("/todays-specials")
def get_todays_specials():
    weather = get_weather_data()
    event = get_local_event()
    scored_menu = calculate_dynamic_scores(weather, event)
    scored_menu.sort(key=lambda x: x['dynamic_score'], reverse=True)
    specials = scored_menu[:4]
    image_map = get_image_map()
    for special in specials:
        special['image_url'] = url_for('static', filename=image_map.get(special['id'], 'images/logo.png'))
    context_string = f"Based on the current weather ({weather.get('temperature')}°C) "
    context_string += f"and a {event}, " if event else "in Kolkata, "
    context_string += "here are our top picks for you!"
    return jsonify({'specials': specials, 'context': context_string})

@app.route("/api/menu/<category_name>")
def get_dynamic_menu(category_name):
    if category_name not in MENU_DATA:
        return jsonify({'error': 'Category not found'}), 404
    menu_items = MENU_DATA[category_name]
    dynamically_priced_items = apply_dynamic_pricing(menu_items)
    image_map = get_image_map()
    for item in dynamically_priced_items:
        item['image_url'] = url_for('static', filename=image_map.get(item['id'], 'images/logo.png'))
    return jsonify({'items': dynamically_priced_items})

@app.route("/api/cart-suggestions", methods=['POST'])
def get_cart_suggestions():
    cart_data = request.get_json()
    if not cart_data or 'items' not in cart_data:
        return jsonify({'error': 'Invalid request format'}), 400
    cart_item_names = {item for item in cart_data.get('items', [])}
    weather = get_weather_data()
    event = get_local_event()
    scored_menu = calculate_dynamic_scores(weather, event)
    suggestions = [item for item in scored_menu if item['name'] not in cart_item_names]
    suggestions.sort(key=lambda x: x['dynamic_score'], reverse=True)
    top_suggestions = suggestions[:3]
    return jsonify({'suggestions': top_suggestions})

@app.route("/feedback", methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        feedback_text = request.form.get('feedback_text')
        if not feedback_text or not feedback_text.strip():
            flash('Please enter your feedback before submitting.', 'error')
            return redirect(url_for('feedback'))
        analyzer = SentimentIntensityAnalyzer()
        score = analyzer.polarity_scores(feedback_text)
        sentiment = 'Positive' if score['compound'] >= 0.05 else 'Negative' if score['compound'] <= -0.05 else 'Neutral'
        new_feedback = Feedback(text=feedback_text, sentiment=sentiment)
        db.session.add(new_feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('home'))
    return render_template('feedback.html')

@app.route('/api/table-recommendations', methods=['POST'])
def get_table_recommendations():
    data = request.get_json()
    date, time, party_size_str, preference = data.get('date'), data.get('time'), data.get('party_size'), data.get('preference', 'any')
    if not date or not time or not party_size_str:
        return jsonify({'error': 'Date, time, and party size are required'}), 400
    party_size = int(party_size_str)
    booking_datetime = datetime.strptime(f"{date} {time}", '%Y-%m-%d %H:%M')
    bookings_on_date = Booking.query.filter_by(date=date).all()
    booked_table_ids = set()
    for b in bookings_on_date:
        existing_booking_time = datetime.strptime(f"{b.date} {b.time}", '%Y-%m-%d %H:%M')
        if abs((existing_booking_time - booking_datetime).total_seconds()) < 7200:
            booked_table_ids.add(b.table_id)
    available_tables = [table for table in TABLE_DATA if table['capacity'] >= party_size and table['id'] not in booked_table_ids]
    scored_tables = []
    for table in available_tables:
        score = 0
        if preference != 'any' and preference in table['properties']: score += 10
        if 'window' in table['properties']: score += 2
        scored_tables.append({'table': table, 'score': score})
    scored_tables.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({'available_tables': [item['table'] for item in scored_tables]})

@app.route('/api/book-table', methods=['POST'])
def book_table():
    data = request.get_json()
    table_id, date, time, party_size = data.get('table_id'), data.get('date'), data.get('time'), data.get('party_size')
    user_email = session.get('user')
    if not all([table_id, date, time, party_size, user_email]):
        return jsonify({'error': 'Missing booking information or not logged in'}), 400
    booking_id = f"BNB-{random.randint(1000, 9999)}"
    new_booking = Booking(booking_id=booking_id, table_id=table_id, date=date, time=time, party_size=party_size)
    db.session.add(new_booking)
    db.session.commit()
    table_name = next((table['name'] for table in TABLE_DATA if table['id'] == table_id), 'your booked table')
    try:
        msg = Message("Your Table Booking at Brew & Bite is Confirmed!", recipients=[user_email])
        msg.body = f"Hello,\n\nYour booking for {table_name} on {date} at {time} for {party_size} guests is confirmed.\nYour Booking ID is: {booking_id}\n\nWe look forward to seeing you!\n- The Brew & Bite Team"
        mail.send(msg)
    except Exception as e:
        print(f"Error sending booking confirmation email: {e}")
    return jsonify({'success': True, 'booking_id': booking_id, 'table_name': table_name})

@app.route('/api/admin/delete-booking/<string:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    booking_to_delete = Booking.query.filter_by(booking_id=booking_id).first()
    if booking_to_delete:
        db.session.delete(booking_to_delete)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Booking removed successfully'})
    else:
        return jsonify({'success': False, 'error': 'Booking not found'}), 404

@app.route('/api/confirm-dine-in-order', methods=['POST'])
def confirm_dine_in_order():
    data = request.get_json()
    cart = data.get('cart')
    customer_name = session.get('user_name', data.get('customer_name', 'Guest'))
    user_email = session.get('user')
    table_number = data.get('table_number', random.randint(1, 6))
    if not cart or not user_email:
        return jsonify({'error': 'Missing cart information or not logged in'}), 400
    order_id = f"T{table_number}-ORD-{random.randint(100, 999)}"
    total_items = sum(item['quantity'] for item in cart)
    preparation_minutes = total_items * 2
    order_time = datetime.utcnow()
    estimated_ready_time = order_time + timedelta(minutes=preparation_minutes)
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    gst = round(subtotal * 0.05)
    total = subtotal + gst
    new_order = DineInOrder(
        order_id=order_id, table_number=table_number, customer_name=customer_name,
        user_email=user_email, items=cart, total=total,
        estimated_ready_time=estimated_ready_time, timestamp=order_time
    )
    db.session.add(new_order)
    db.session.commit()
    try:
        receipt_url = url_for('receipt', order_id=new_order.order_id, _external=True)
        msg = Message(f"Your Brew & Bite Order ({order_id}) is Confirmed!", recipients=[user_email])
        msg.html = render_template('order_confirmation_email.html', order=new_order, receipt_url=receipt_url)
        mail.send(msg)
    except Exception as e:
        print(f"An exception occurred while sending dine-in email: {e}")
    confirmation_url = url_for('order_confirm', order_id=new_order.order_id)
    return jsonify({'success': True, 'confirmation_url': confirmation_url})

@app.route('/api/confirm-online-order', methods=['POST'])
def confirm_online_order():
    data = request.get_json()
    cart, address = data.get('cart'), data.get('address')
    customer_name = session.get('user_name', data.get('customer_name'))
    user_email = session.get('user')
    if not all([cart, customer_name, user_email, address]):
        return jsonify({'error': 'Missing order information or not logged in'}), 400
    order_id = f"BNB-ONLINE-{random.randint(1000, 9999)}"
    subtotal = sum(item['price'] * item['quantity'] for item in cart)
    gst = round(subtotal * 0.05)
    total = subtotal + gst
    new_order = OnlineOrder(
        order_id=order_id, customer_name=customer_name, user_email=user_email,
        address=address, items=cart, total=total, timestamp=datetime.utcnow()
    )
    db.session.add(new_order)
    db.session.commit()
    try:
        receipt_url = url_for('receipt', order_id=new_order.order_id, _external=True)
        msg = Message(f"Your Brew & Bite Online Order ({order_id}) is Confirmed!", recipients=[user_email])
        msg.html = render_template('order_confirmation_email.html', order=new_order, receipt_url=receipt_url)
        mail.send(msg)
    except Exception as e:
        print(f"An exception occurred while sending online email: {e}")
    confirmation_url = url_for('order_confirm', order_id=new_order.order_id)
    return jsonify({'success': True, 'confirmation_url': confirmation_url})

@app.route('/receipt/<order_id>')
def receipt(order_id):
    order = OnlineOrder.query.filter_by(order_id=order_id).first()
    order_type = "Online Delivery"
    if not order:
        order = DineInOrder.query.filter_by(order_id=order_id).first()
        order_type = "Dine-In"
    if not order:
        flash('Receipt not found.', 'error')
        return redirect(url_for('home'))
    subtotal = sum(item['price'] * item['quantity'] for item in order.items)
    gst = round(subtotal * 0.05)
    return render_template("receipt.html", order=order, subtotal=subtotal, gst=gst, order_type=order_type)

@app.route('/api/kitchen-notifications')
def get_kitchen_notifications():
    check_prepared_orders()
    ready_orders = DineInOrder.query.filter_by(status='ready').all()
    notifications_to_send = []
    for order in ready_orders:
        notifications_to_send.append({
            'order_id': order.order_id,
            'message': f"Order {order.order_id} for {order.customer_name} is ready!"
        })
        order.status = 'notified'
    if ready_orders:
        db.session.commit()
    return jsonify({'notifications': notifications_to_send})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)


from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy import func, extract, desc, text
import calendar
import math
import os
import random
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-prod')

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance', 'shop.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

from models import db, User, Product, StockIn, Sale, Customer, KhataEntry, Transaction
db.init_app(app)

# Register Blueprints
from blueprints.prediction import prediction_bp
from blueprints.reports import reports_bp
from blueprints.payment import payment_bp
from blueprints.billing import billing_bp
from blueprints.customers import customers_bp
from blueprints.khatabook import khatabook_bp
from blueprints.transactions import transactions_bp
app.register_blueprint(prediction_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(payment_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(khatabook_bp)
app.register_blueprint(transactions_bp)

# Create tables
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        shop_name = request.form['shop_name']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return "Username already exists! Try another."
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, shop_name=shop_name)
        db.session.add(new_user)
        db.session.commit()
        
        return redirect('/login')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect('/dashboard')
        else:
            return "Invalid credentials! Try again."
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ============= DASHBOARD =============
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Today's sales (Optimized)
    today = datetime.now().date()
    today_sales_total = db.session.query(func.sum(Sale.total_amount)).filter(
        func.date(Sale.date) == today,
        Sale.user_id == user_id
    ).scalar() or 0
    
    # This month's sales (Optimized)
    current_month = datetime.now().month
    current_year = datetime.now().year
    month_sales_total = db.session.query(func.sum(Sale.total_amount)).filter(
        extract('month', Sale.date) == current_month,
        extract('year', Sale.date) == current_year,
        Sale.user_id == user_id
    ).scalar() or 0
    
    # Total products and Low stock (Efficient count)
    total_products = Product.query.filter_by(user_id=user_id).count()
    
    low_stock = Product.query.filter(
        Product.user_id == user_id,
        Product.current_stock < 10
    ).count()
    
    # Recent sales (Joined query to avoid N+1)
    recent_sales = db.session.query(Sale, Product.name).join(Product).filter(
        Sale.user_id == user_id
    ).order_by(Sale.date.desc()).limit(5).all()
    
    recent_sales_data = []
    for sale, product_name in recent_sales:
        recent_sales_data.append({
            'product_name': product_name,
            'quantity': sale.quantity,
            'total': sale.total_amount,
            'time': sale.date.strftime('%H:%M')
        })
    
    
    # Chart Data (Last 30 Days)
    daily_labels = []
    daily_data = []
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Query daily totals efficiently
    daily_sales_query = db.session.query(
        func.date(Sale.date).label('date'),
        func.sum(Sale.total_amount).label('total')
    ).filter(
        Sale.user_id == user_id,
        Sale.date >= thirty_days_ago
    ).group_by(func.date(Sale.date)).all()
    
    # Map query results to dictionary for O(1) lookup
    sales_map = {r.date: r.total for r in daily_sales_query}
    
    # Generate last 30 days list
    for i in range(29, -1, -1):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        label = date.strftime('%d %b')
        total = sales_map.get(date_str, 0)
        
        daily_labels.append(label)
        daily_data.append(total)
        
    # Top Products
    top_products_query = db.session.query(
        Product.name,
        func.sum(Sale.quantity).label('qty'),
        func.sum(Sale.total_amount).label('rev')
    ).join(Sale).filter(
        Sale.user_id == user_id
    ).group_by(Product.id).order_by(desc('rev')).limit(5).all()
    
    top_products_data = [
        {'name': p.name, 'quantity': p.qty, 'revenue': p.rev} 
        for p in top_products_query
    ]

    return render_template('dashboard.html', 
                         username=session['username'],
                         total_today=today_sales_total,
                         total_month=month_sales_total,
                         total_products=total_products,
                         low_stock=low_stock,
                         recent_sales=recent_sales_data,
                         daily_labels=daily_labels,
                         daily_data=daily_data,
                         top_products=top_products_data,
                         datetime=datetime)

# ============= INVENTORY (SALES ENTRY) =============
@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        quantity = float(request.form['quantity'])
        
        product = Product.query.get(product_id)
        
        if product.current_stock >= quantity:
            total = quantity * product.selling_price
            
            sale = Sale(
                product_id=product_id,
                quantity=quantity,
                selling_price=product.selling_price,
                cost_at_sale=product.cost_price,
                total_amount=total,
                user_id=user_id
            )
            
            product.current_stock -= quantity
            
            db.session.add(sale)
            db.session.commit()
            
            return redirect('/inventory')
        else:
            return f"Not enough stock! Available: {product.current_stock}"
    
    # Get all products for dropdown
    products = Product.query.filter_by(user_id=user_id).all()
    
    # Get today's sales
    today = datetime.now().date()
    today_sales = Sale.query.filter(
        func.date(Sale.date) == today,
        Sale.user_id == user_id
    ).order_by(Sale.date.desc()).all()
    
    sales_with_names = []
    for sale in today_sales:
        product = Product.query.get(sale.product_id)
        sales_with_names.append({
            'product_name': product.name if product else 'Unknown',
            'quantity': sale.quantity,
            'total': sale.total_amount,
            'time': sale.date.strftime('%H:%M')
        })
    
    return render_template('inventory.html', 
                         products=products,
                         sales=sales_with_names,
                         datetime=datetime)

# ============= STOCK MANAGEMENT =============
@app.route('/stock', methods=['GET', 'POST'])
def stock():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    if request.method == 'POST':
        action = request.form['action']
        
        if action == 'add_product':
            name = request.form['name']
            category = request.form['category']
            unit = request.form['unit']
            selling_price = float(request.form['selling_price'])
            cost_price = float(request.form['cost_price'])
            
            new_product = Product(
                name=name,
                category=category,
                unit=unit,
                selling_price=selling_price,
                cost_price=cost_price,
                current_stock=0,
                user_id=user_id
            )
            db.session.add(new_product)
            db.session.commit()
            
        elif action == 'stock_in':
            product_id = request.form['product_id']
            quantity = float(request.form['quantity'])
            cost_price = float(request.form['cost_price'])
            
            product = Product.query.get(product_id)
            product.current_stock += quantity
            
            stock_entry = StockIn(
                product_id=product_id,
                quantity=quantity,
                cost_price=cost_price,
                user_id=user_id
            )
            db.session.add(stock_entry)
            db.session.commit()
    
    # Get all products
    products = Product.query.filter_by(user_id=user_id).all()
    
    # Get recent stock in entries
    recent_stock = StockIn.query.filter_by(user_id=user_id).order_by(StockIn.date.desc()).limit(10).all()
    
    stock_with_names = []
    for entry in recent_stock:
        product = Product.query.get(entry.product_id)
        stock_with_names.append({
            'product_name': product.name if product else 'Unknown',
            'quantity': entry.quantity,
            'date': entry.date.strftime('%Y-%m-%d %H:%M')
        })
    
    return render_template('stock.html', 
                         products=products,
                         recent_stock=stock_with_names)

@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    
    # Get current date info
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    current_month_name = calendar.month_name[current_month]
    today_date_formatted = now.strftime('%d %B %Y')
    
    # ===== TODAY'S SALES =====
    today = now.date()
    today_sales_data = Sale.query.filter(
        func.date(Sale.date) == today,
        Sale.user_id == user_id
    ).all()
    today_sales = float(sum(sale.total_amount for sale in today_sales_data) or 0)
    
    # ===== THIS MONTH'S SALES =====
    monthly_sales_data = Sale.query.filter(
        extract('month', Sale.date) == current_month,
        extract('year', Sale.date) == current_year,
        Sale.user_id == user_id
    ).all()
    monthly_sales = float(sum(sale.total_amount for sale in monthly_sales_data) or 0)
    
    # ===== AVERAGE DAILY SALES (LAST 30 DAYS) =====
    thirty_days_ago = now - timedelta(days=30)
    last_30_days_sales = Sale.query.filter(
        Sale.date >= thirty_days_ago,
        Sale.user_id == user_id
    ).all()
    
    if last_30_days_sales:
        avg_daily = float(sum(s.total_amount for s in last_30_days_sales)) / 30
    else:
        avg_daily = 0
    
    # ===== BEST DAY EVER =====
    best_day_data = db.session.query(
        func.date(Sale.date).label('sale_date'),
        func.sum(Sale.total_amount).label('daily_total')
    ).filter(
        Sale.user_id == user_id
    ).group_by(
        func.date(Sale.date)
    ).order_by(
        func.sum(Sale.total_amount).desc()
    ).first()
    
    if best_day_data:
        best_day = float(best_day_data.daily_total)
        # The date is already a string from func.date()
        best_day_date = best_day_data.sale_date  # Format: YYYY-MM-DD
    else:
        best_day = 0
        best_day_date = 'N/A'
    
    # ===== DAILY SALES FOR CHART (LAST 30 DAYS) =====
    daily_labels = []
    daily_data = []
    
    for i in range(29, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        day_sales = Sale.query.filter(
            func.date(Sale.date) == date_str,
            Sale.user_id == user_id
        ).all()
        daily_total = float(sum(s.total_amount for s in day_sales) or 0)
        
        daily_labels.append(date.strftime('%d %b'))
        daily_data.append(daily_total)
    
    # ===== MONTHLY SALES FOR CHART =====
    monthly_labels = []
    monthly_data = []
    
    for i in range(5, -1, -1):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        
        month_sales = Sale.query.filter(
            extract('month', Sale.date) == month,
            extract('year', Sale.date) == year,
            Sale.user_id == user_id
        ).all()
        month_total = float(sum(s.total_amount for s in month_sales) or 0)
        
        monthly_labels.append(calendar.month_abbr[month])
        monthly_data.append(month_total)
    
    # ===== WEEKDAY ANALYSIS =====
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekday_analysis = []
    
    weekday_totals = {0: [], 1: [], 2: [], 3: [], 4: [], 5: [], 6: []}
    
    all_sales = Sale.query.filter_by(user_id=user_id).all()
    
    for sale in all_sales:
        weekday_num = sale.date.weekday()
        weekday_totals[weekday_num].append(sale.total_amount)
    
    max_avg_sales = 1  # Prevent division by zero in template
    for day_num in range(7):
        if weekday_totals[day_num]:
            avg_sales = sum(weekday_totals[day_num]) / len(weekday_totals[day_num])
            transactions = len(weekday_totals[day_num])
            max_avg_sales = max(max_avg_sales, avg_sales)
        else:
            avg_sales = 0
            transactions = 0
        
        weekday_analysis.append({
            'day': weekday_names[day_num],
            'avg_sales': avg_sales,
            'transactions': transactions
        })
    
    # ===== TOP PRODUCTS =====
    products = Product.query.filter_by(user_id=user_id).all()
    product_sales = []
    
    for product in products:
        sales = Sale.query.filter(
            Sale.product_id == product.id,
            Sale.user_id == user_id
        ).all()
        
        if sales:
            total_qty = float(sum(s.quantity for s in sales))
            total_revenue = float(sum(s.total_amount for s in sales))
            
            product_sales.append({
                'name': product.name,
                'quantity': total_qty,
                'revenue': total_revenue
            })
    
    top_products = sorted(product_sales, key=lambda x: x['revenue'], reverse=True)[:5]
    
    # ===== LAST 7 DAYS DETAILS =====
    last_7_days = []
    
    for i in range(6, -1, -1):
        date = now - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        day_sales = Sale.query.filter(
            func.date(Sale.date) == date_str,
            Sale.user_id == user_id
        ).all()
        
        if day_sales:
            transactions = len(day_sales)
            items = sum(s.quantity for s in day_sales)
            revenue = float(sum(s.total_amount for s in day_sales))
            
            profit = 0
            for sale in day_sales:
                product = Product.query.get(sale.product_id)
                if product:
                    cost_price = sale.cost_at_sale if sale.cost_at_sale is not None else product.cost_price
                    profit += float(sale.quantity) * (float(sale.selling_price) - float(cost_price))
            
            margin = round((profit / revenue * 100) if revenue > 0 else 0, 1)
        else:
            transactions = 0
            items = 0
            revenue = 0
            profit = 0
            margin = 0
        
        last_7_days.append({
            'date': date.strftime('%d %b'),
            'day_name': date.strftime('%A'),
            'transactions': transactions,
            'items_sold': items,
            'revenue': revenue,
            'profit': profit,
            'margin': margin
        })
    
    # ===== CURRENT MONTH PROFIT =====
    current_month_profit = 0
    for sale in monthly_sales_data:
        product = Product.query.get(sale.product_id)
        if product:
            cost_price = sale.cost_at_sale if sale.cost_at_sale is not None else product.cost_price
            current_month_profit += float(sale.quantity) * (float(sale.selling_price) - float(cost_price))
    
    profit_margin = round((current_month_profit / monthly_sales * 100) if monthly_sales > 0 else 0, 1)
    
    # ===== CATEGORY BREAKDOWN =====
    categories = {}
    for sale in monthly_sales_data:
        product = Product.query.get(sale.product_id)
        if product and product.category:
            if product.category not in categories:
                categories[product.category] = {
                    'sales': 0,
                    'revenue': 0
                }
            categories[product.category]['sales'] += float(sale.quantity)
            categories[product.category]['revenue'] += float(sale.total_amount)
    
    category_data = []
    max_category_revenue = 1  # Prevent division by zero
    for cat, data in categories.items():
        category_data.append({
            'category': cat,
            'sales': data['sales'],
            'revenue': data['revenue']
        })
        max_category_revenue = max(max_category_revenue, data['revenue'])
    
    # ===== MONTHS DATA FOR TABLE =====
    months_data = []
    for i in range(5, -1, -1):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        
        month_sales = Sale.query.filter(
            extract('month', Sale.date) == month,
            extract('year', Sale.date) == year,
            Sale.user_id == user_id
        ).all()
        
        month_total = float(sum(s.total_amount for s in month_sales) or 0)
        
        month_profit = 0
        for sale in month_sales:
            product = Product.query.get(sale.product_id)
            if product:
                cost_price = sale.cost_at_sale if sale.cost_at_sale is not None else product.cost_price
                month_profit += float(sale.quantity) * (float(sale.selling_price) - float(cost_price))
        
        months_data.append({
            'month': calendar.month_abbr[month],
            'sales': month_total,
            'profit': month_profit
        })
    
    # ===== ADDITIONAL METRICS =====
    unique_days = db.session.query(func.date(Sale.date)).distinct().filter(Sale.user_id == user_id).count()
    
    total_transactions = Sale.query.filter_by(user_id=user_id).count()
    avg_transaction = (monthly_sales / total_transactions) if total_transactions > 0 else 0
    
    ytd_sales = Sale.query.filter(
        extract('year', Sale.date) == current_year,
        Sale.user_id == user_id
    ).all()
    ytd_total = float(sum(s.total_amount for s in ytd_sales) or 0)
    
    return render_template('analytics.html',
                         # Date info
                         now=now,
                         today_date_formatted=today_date_formatted,
                         
                         # Summary cards
                         today_sales=today_sales,
                         monthly_sales=monthly_sales,
                         avg_daily=avg_daily,
                         best_day=best_day,
                         best_day_date=best_day_date,
                         
                         # Additional metrics
                         ytd_sales=ytd_total,
                         avg_transaction=avg_transaction,
                         unique_days=unique_days,
                         
                         # Charts data
                         daily_labels=daily_labels,
                         daily_data=daily_data,
                         monthly_labels=monthly_labels,
                         monthly_data=monthly_data,
                         
                         # Analysis tables
                         weekday_analysis=weekday_analysis,
                         top_products=top_products,
                         last_7_days=last_7_days,
                         category_data=category_data,
                         months_data=months_data,
                         
                         # For template calculations
                         max_avg_sales=max_avg_sales,
                         max_category_revenue=max_category_revenue,
                         
                         # Current month details
                         current_month=current_month_name,
                         monthly_profit=current_month_profit,
                         profit_margin=profit_margin)
# ============= FIXED PREDICTION PAGE =============



def auto_correct_timestamps():
    """Automatically fixes sales/transactions that are in the future relative to now."""
    with app.app_context():
        try:
            now = datetime.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 1. Fix Future Sales
            future_sales = Sale.query.filter(Sale.date > now).all()
            if future_sales:
                print(f"Auto-correcting {len(future_sales)} future sales...")
                for sale in future_sales:
                    # Shift to random time earlier today
                    random_hour = random.randint(9, now.hour if now.hour > 9 else 9)
                    random_minute = random.randint(0, 59)
                    if random_hour == now.hour and random_minute > now.minute:
                        random_minute = random.randint(0, now.minute)
                    
                    new_time = now.replace(hour=random_hour, minute=random_minute)
                    # Create a new offset if new_time is still in future (edge case)
                    if new_time > now:
                        new_time = now - timedelta(minutes=random.randint(1, 60))
                        
                    sale.date = new_time
            
            # 2. Fix Future Transactions
            future_txns = Transaction.query.filter(Transaction.date > now).all()
            if future_txns:
                print(f"Auto-correcting {len(future_txns)} future transactions...")
                for txn in future_txns:
                    # Shift logic
                    new_time = txn.date
                    if txn.date > now:
                        minutes_back = random.randint(1, 120)
                        new_time = now - timedelta(minutes=minutes_back)
                        txn.date = new_time
                    
                    # Update JSON data payload
                    if txn.data:
                        try:
                            data = json.loads(txn.data)
                            data['date'] = new_time.strftime('%b %d, %Y')
                            data['time'] = new_time.strftime('%I:%M %p')
                            # Also update invoice no if necessary? Keep it simple
                            txn.data = json.dumps(data)
                        except:
                            pass
                            
            db.session.commit()
        except Exception as e:
            print(f"Auto-correction warning: {e}")

def optimize_db():
    """Adds database indexes for performance."""
    with app.app_context():
        try:
            # Add indexes to speed up dashboard queries and date filtering
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_sale_date ON sale (date)'))
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_sale_user_date ON sale (user_id, date)'))
            # "transaction" is a reserved word so quoting it is safer
            db.session.execute(text('CREATE INDEX IF NOT EXISTS idx_txn_date ON "transaction" (date)'))
            db.session.commit()
            print("Database optimized with indexes.")
        except Exception as e:
            print(f"Optimization warning: {e}")

if __name__ == "__main__":
    optimize_db()
    auto_correct_timestamps()
    app.run(host="0.0.0.0", port=5000)

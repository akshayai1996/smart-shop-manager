from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100), nullable=False)
    shop_name = db.Column(db.String(200))

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100))
    current_stock = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))
    selling_price = db.Column(db.Numeric(10, 2))
    cost_price = db.Column(db.Numeric(10, 2))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class StockIn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Float)
    cost_price = db.Column(db.Numeric(10, 2))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Float)
    selling_price = db.Column(db.Numeric(10, 2))
    cost_at_sale = db.Column(db.Numeric(10, 2)) # Store cost price snapshot
    total_amount = db.Column(db.Numeric(10, 2))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.String(500))
    balance = db.Column(db.Numeric(10, 2), default=0)  # Outstanding credit amount
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    entries = db.relationship('KhataEntry', backref='customer', lazy=True)

class KhataEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    entry_type = db.Column(db.String(10), nullable=False)  # 'credit' or 'payment'
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.String(500))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    txn_type = db.Column(db.String(20), nullable=False)       # 'invoice' or 'khata_receipt'
    txn_ref = db.Column(db.String(50), nullable=False)         # Invoice # or Receipt #
    customer_name = db.Column(db.String(200))
    customer_phone = db.Column(db.String(20))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50))                  # Card, UPI, Cash, Khata
    data = db.Column(db.Text)                                  # JSON blob with full details
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


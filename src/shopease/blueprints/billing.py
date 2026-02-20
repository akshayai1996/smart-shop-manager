from flask import Blueprint, render_template, request, redirect, url_for, session
from models import db, Product, Sale
from datetime import datetime

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/billing', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['customer_name'] = request.form.get('customer_name')
        session['customer_phone'] = request.form.get('customer_phone')
        return redirect(url_for('billing.items'))
    return render_template('billing_customer.html')

@billing_bp.route('/billing/items', methods=['GET'])
def items():
    if 'customer_name' not in session:
        return redirect(url_for('billing.index'))
    
    # Fetch top 30 products for the billing list
    products = Product.query.limit(30).all()
    return render_template('billing_items.html', products=products, customer_name=session['customer_name'])

@billing_bp.route('/billing/checkout', methods=['POST'])
def checkout():
    total_amount = 0
    items = []
    
    # Process form data
    # Form data expected: product_ids (list), quantity_<id>
    
    selected_product_ids = request.form.getlist('product_ids')
    
    for pid in selected_product_ids:
        qty = int(request.form.get(f'quantity_{pid}', 0))
        if qty > 0:
            product = Product.query.get(pid)
            if product:
                price = float(product.selling_price) if product.selling_price is not None else 0.0
                item_total = round(price * qty, 2)
                total_amount += item_total
                items.append({
                    'id': product.id,
                    'name': product.name,
                    'qty': qty,
                    'price': price,
                    'total': item_total
                })
    
    if not items:
        # No items selected
        return redirect(url_for('billing.items'))
        
    # Store order in session to pass to payment page
    session['current_order'] = {
        'items': items,
        'total_amount': total_amount,
        'customer_name': session.get('customer_name'),
        'customer_phone': session.get('customer_phone')
    }
    
    return redirect(url_for('payment.checkout'))

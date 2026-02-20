from flask import Blueprint, render_template, request, flash, redirect, url_for, send_file, session
from models import db, Product, StockIn, Sale, Customer, KhataEntry, Transaction
from blueprints.customers import upsert_customer
import qrcode
import io
import json
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/payment/<int:product_id>')
def index(product_id):
    product = Product.query.get_or_404(product_id)
    reorder_qty = 50
    amount = float(reorder_qty * product.cost_price)
    return render_template('payment.html', product=product, quantity=reorder_qty, amount=amount, order=None)

@payment_bp.route('/payment/checkout')
def checkout():
    if 'current_order' not in session:
        return redirect(url_for('billing.index'))
    order = session['current_order']
    amount = float(order['total_amount'])
    return render_template('payment.html', order=order, amount=amount, product=None, quantity=0)

@payment_bp.route('/payment/process', methods=['POST'])
def process_payment():
    payment_method = request.form.get('payment_method')

    if 'current_order' in session and request.form.get('is_cart') == 'true':
        # --- Cart Checkout ---
        order = session['current_order']
        
        # Ensure all numeric values are floats (session may serialize Decimals as strings)
        order_total = float(order['total_amount'])
        
        for item in order['items']:
            item['price'] = float(item['price'])
            item['total'] = float(item['total'])
            product = Product.query.get(item['id'])
            if product:
                product.current_stock -= item['qty']
                sale = Sale(
                    product_id=product.id,
                    quantity=item['qty'],
                    selling_price=product.selling_price,
                    cost_at_sale=product.cost_price,
                    total_amount=item['total'],
                    user_id=product.user_id,
                    date=datetime.now()
                )
                db.session.add(sale)
        db.session.commit()

        # Generate invoice number: ddmmyyhhmm (Philosophy: DayMonthYearHourMinute)
        invoice_no = datetime.now().strftime('%d%m%y%H%M')

        # Update Customer Database (Excel)
        upsert_customer(
            name=order['customer_name'],
            phone=order['customer_phone'],
            amount=order_total,
            invoice_no=invoice_no
        )

        # ---- KHATA HANDLING ----
        if payment_method == 'Khata':
            user_id = session.get('user_id')
            customer_name = order['customer_name']
            customer_phone = order['customer_phone']
            description = request.form.get('khata_description', '').strip()

            # Find or create Customer in Khatabook DB
            customer = Customer.query.filter_by(
                user_id=user_id,
                phone=customer_phone
            ).first()

            if not customer:
                customer = Customer(
                    name=customer_name,
                    phone=customer_phone,
                    balance=0,
                    user_id=user_id
                )
                db.session.add(customer)
                db.session.commit()

            # Create credit entry
            entry = KhataEntry(
                customer_id=customer.id,
                entry_type='credit',
                amount=order_total,
                description=description or f'Invoice #{invoice_no}',
                user_id=user_id
            )
            db.session.add(entry)
            customer.balance = float(customer.balance or 0) + order_total
            db.session.commit()

        # Store invoice data in session for display
        invoice_data = {
            'invoice_no': invoice_no,
            'customer_name': order['customer_name'],
            'customer_phone': order['customer_phone'],
            'items': order['items'],
            'total_amount': order_total,
            'payment_method': payment_method,
            'date': datetime.now().strftime('%b %d, %Y')
        }
        session['last_invoice'] = invoice_data

        # Save to Transaction History
        txn = Transaction(
            txn_type='invoice',
            txn_ref=invoice_no,
            customer_name=order['customer_name'],
            customer_phone=order['customer_phone'],
            amount=order_total,
            payment_method=payment_method,
            data=json.dumps(invoice_data),
            date=datetime.now(),
            user_id=session.get('user_id')
        )
        db.session.add(txn)
        db.session.commit()

        session.pop('current_order', None)
        return redirect(url_for('payment.invoice'))

    else:
        # --- Stock Reorder ---
        product_id = request.form.get('product_id')
        quantity = float(request.form.get('quantity'))
        amount = float(request.form.get('amount'))
        product = Product.query.get(product_id)
        if product:
            product.current_stock += quantity
            stock_in = StockIn(
                product_id=product.id,
                quantity=quantity,
                cost_price=product.cost_price,
                user_id=product.user_id,
                date=datetime.now()
            )
            db.session.add(stock_in)
            db.session.commit()
            flash(f'Payment of ₹{amount:,.2f} successful via {payment_method}! Stock updated.', 'success')
        else:
            flash('Product not found.', 'danger')
        return redirect(url_for('prediction.index'))

@payment_bp.route('/payment/invoice')
def invoice():
    inv = session.get('last_invoice')
    if not inv:
        return redirect(url_for('billing.index'))
    return render_template('invoice.html',
                           invoice_no=inv['invoice_no'],
                           customer_name=inv['customer_name'],
                           customer_phone=inv['customer_phone'],
                           items=inv['items'],
                           total_amount=inv['total_amount'],
                           payment_method=inv['payment_method'],
                           date=inv['date'])


# ---- KHATABOOK PAYMENT ROUTE ----
# When receiving payment from Khatabook via UPI/Card
@payment_bp.route('/payment/khata/<int:customer_id>')
def khata_payment(customer_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    customer = Customer.query.get_or_404(customer_id)
    if customer.user_id != user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('khatabook.index'))
    
    payment_mode = request.args.get('mode', 'card')  # 'card' or 'upi'
    amount = float(request.args.get('amount', float(customer.balance or 0)))
    
    return render_template('khata_payment.html',
                           customer=customer,
                           amount=amount,
                           payment_mode=payment_mode)


@payment_bp.route('/payment/khata_process', methods=['POST'])
def khata_process_payment():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    customer_id = int(request.form.get('customer_id'))
    amount = float(request.form.get('amount'))
    payment_method = request.form.get('payment_method')
    
    customer = Customer.query.get_or_404(customer_id)
    if customer.user_id != user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('khatabook.index'))
    
    # Record payment in Khatabook
    entry = KhataEntry(
        customer_id=customer.id,
        entry_type='payment',
        amount=amount,
        description=f'Payment via {payment_method}',
        user_id=user_id
    )
    db.session.add(entry)
    customer.balance = float(customer.balance or 0) - amount
    db.session.commit()
    
    # Store receipt in session
    receipt_data = {
        'customer_name': customer.name,
        'customer_phone': customer.phone,
        'amount': amount,
        'payment_method': payment_method,
        'remaining_balance': float(customer.balance),
        'date': datetime.now().strftime('%b %d, %Y'),
        'time': datetime.now().strftime('%I:%M %p'),
        'receipt_no': datetime.now().strftime('KP%d%m%y%H%M')
    }
    session['last_khata_receipt'] = receipt_data

    # Save to Transaction History
    txn = Transaction(
        txn_type='khata_receipt',
        txn_ref=receipt_data['receipt_no'],
        customer_name=customer.name,
        customer_phone=customer.phone,
        amount=amount,
        payment_method=payment_method,
        data=json.dumps(receipt_data),
        date=datetime.now(),
        user_id=user_id
    )
    db.session.add(txn)
    db.session.commit()
    
    return redirect(url_for('payment.khata_receipt'))


@payment_bp.route('/payment/khata_receipt')
def khata_receipt():
    receipt = session.get('last_khata_receipt')
    if not receipt:
        return redirect(url_for('khatabook.index'))
    return render_template('khata_receipt.html', receipt=receipt)


@payment_bp.route('/payment/qr_code')
def qr_code():
    upi_url = "upi://pay?pa=shopease@dummybank&pn=ShopEase&mc=1234&tid=1234567890&tr=1234567890&tn=StockReorder&am=0&cu=INR"
    
    img = qrcode.make(upi_url)
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return send_file(buffer, mimetype='image/png')

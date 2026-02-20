from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models import db, Customer, KhataEntry
from datetime import datetime
from sqlalchemy import func, desc

khatabook_bp = Blueprint('khatabook', __name__)


@khatabook_bp.route('/khatabook')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Get all customers with balance info
    customers = Customer.query.filter_by(user_id=user_id).order_by(Customer.name).all()

    # Summary stats
    total_customers = len(customers)
    total_credit = sum(float(c.balance) for c in customers if c.balance and float(c.balance) > 0)
    total_debtors = sum(1 for c in customers if c.balance and float(c.balance) > 0)

    # Recent entries
    recent_entries = db.session.query(KhataEntry, Customer.name).join(Customer).filter(
        KhataEntry.user_id == user_id
    ).order_by(KhataEntry.date.desc()).limit(10).all()

    return render_template('khatabook.html',
                           customers=customers,
                           total_customers=total_customers,
                           total_credit=total_credit,
                           total_debtors=total_debtors,
                           recent_entries=recent_entries)


@khatabook_bp.route('/khatabook/add_customer', methods=['POST'])
def add_customer():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()

    if not name or not phone:
        flash('Name and Phone are required.', 'danger')
        return redirect(url_for('khatabook.index'))

    # Check duplicate
    existing = Customer.query.filter_by(user_id=user_id, phone=phone).first()
    if existing:
        flash(f'Customer with phone {phone} already exists.', 'danger')
        return redirect(url_for('khatabook.index'))

    customer = Customer(
        name=name,
        phone=phone,
        address=address,
        balance=0,
        user_id=user_id
    )
    db.session.add(customer)
    db.session.commit()
    flash(f'Customer "{name}" added successfully!', 'success')
    return redirect(url_for('khatabook.index'))


@khatabook_bp.route('/khatabook/entry', methods=['POST'])
def add_entry():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    customer_id = request.form.get('customer_id')
    entry_type = request.form.get('entry_type')  # 'credit' or 'payment'
    amount = float(request.form.get('amount', 0))
    description = request.form.get('description', '').strip()

    if amount <= 0:
        flash('Amount must be positive.', 'danger')
        return redirect(url_for('khatabook.index'))

    customer = Customer.query.get(customer_id)
    if not customer or customer.user_id != user_id:
        flash('Customer not found.', 'danger')
        return redirect(url_for('khatabook.index'))

    entry = KhataEntry(
        customer_id=customer_id,
        entry_type=entry_type,
        amount=amount,
        description=description,
        user_id=user_id
    )
    db.session.add(entry)

    # Update balance
    if entry_type == 'credit':
        customer.balance = float(customer.balance or 0) + amount
    elif entry_type == 'payment':
        customer.balance = float(customer.balance or 0) - amount

    db.session.commit()

    type_label = 'Udhaar (Credit)' if entry_type == 'credit' else 'Payment Received'
    flash(f'{type_label} of ₹{amount:,.2f} recorded for {customer.name}.', 'success')
    return redirect(url_for('khatabook.ledger', customer_id=customer_id))


@khatabook_bp.route('/khatabook/ledger/<int:customer_id>')
def ledger(customer_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    customer = Customer.query.get_or_404(customer_id)

    if customer.user_id != user_id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('khatabook.index'))

    entries = KhataEntry.query.filter_by(
        customer_id=customer_id,
        user_id=user_id
    ).order_by(KhataEntry.date.desc()).all()

    # Calculate running balance for display
    running = []
    bal = 0
    for entry in reversed(entries):
        if entry.entry_type == 'credit':
            bal += float(entry.amount)
        else:
            bal -= float(entry.amount)
        running.append(bal)
    running.reverse()

    return render_template('khatabook_ledger.html',
                           customer=customer,
                           entries=entries,
                           running_balances=running)


@khatabook_bp.route('/khatabook/delete_entry/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    entry = KhataEntry.query.get_or_404(entry_id)

    if entry.user_id != user_id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('khatabook.index'))

    customer = Customer.query.get(entry.customer_id)

    # Reverse the balance effect
    if entry.entry_type == 'credit':
        customer.balance = float(customer.balance or 0) - float(entry.amount)
    else:
        customer.balance = float(customer.balance or 0) + float(entry.amount)

    customer_id = entry.customer_id
    db.session.delete(entry)
    db.session.commit()

    flash('Entry deleted.', 'success')
    return redirect(url_for('khatabook.ledger', customer_id=customer_id))

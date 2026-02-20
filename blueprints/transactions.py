from flask import Blueprint, render_template, redirect, session, url_for
from models import db, Transaction
from datetime import datetime, timedelta
import json

transactions_bp = Blueprint('transactions', __name__)


@transactions_bp.route('/transactions')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']

    # Get transactions from last 7 days
    week_ago = datetime.now() - timedelta(days=7)
    transactions = Transaction.query.filter(
        Transaction.user_id == user_id,
        Transaction.date >= week_ago
    ).order_by(Transaction.date.desc()).all()

    # Summary stats
    total_invoices = sum(1 for t in transactions if t.txn_type == 'invoice')
    total_receipts = sum(1 for t in transactions if t.txn_type == 'khata_receipt')
    total_invoice_amount = sum(float(t.amount) for t in transactions if t.txn_type == 'invoice')
    total_receipt_amount = sum(float(t.amount) for t in transactions if t.txn_type == 'khata_receipt')

    return render_template('transaction_history.html',
                           transactions=transactions,
                           total_invoices=total_invoices,
                           total_receipts=total_receipts,
                           total_invoice_amount=total_invoice_amount,
                           total_receipt_amount=total_receipt_amount)


@transactions_bp.route('/transactions/<int:txn_id>')
def view_transaction(txn_id):
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    txn = Transaction.query.get_or_404(txn_id)

    if txn.user_id != user_id:
        return redirect(url_for('transactions.index'))

    data = json.loads(txn.data) if txn.data else {}

    if txn.txn_type == 'invoice':
        return render_template('invoice.html',
                               invoice_no=txn.txn_ref,
                               customer_name=txn.customer_name,
                               customer_phone=txn.customer_phone,
                               items=data.get('items', []),
                               total_amount=float(txn.amount),
                               payment_method=txn.payment_method,
                               date=data.get('date', txn.date.strftime('%b %d, %Y')),
                               from_history=True)
    elif txn.txn_type == 'khata_receipt':
        # Build a receipt-like dict for the template
        receipt = {
            'receipt_no': txn.txn_ref,
            'customer_name': txn.customer_name,
            'customer_phone': txn.customer_phone,
            'amount': float(txn.amount),
            'payment_method': txn.payment_method,
            'date': data.get('date', txn.date.strftime('%b %d, %Y')),
            'time': data.get('time', txn.date.strftime('%I:%M %p')),
            'remaining_balance': data.get('remaining_balance', 0)
        }
        # Convert dict to object-like access for template
        class ReceiptObj:
            def __init__(self, d):
                for k, v in d.items():
                    setattr(self, k, v)
        return render_template('khata_receipt.html',
                               receipt=ReceiptObj(receipt),
                               from_history=True)

    return redirect(url_for('transactions.index'))

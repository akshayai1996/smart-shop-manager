from flask import Blueprint, render_template, session, redirect
from models import db, Product, Sale
from sqlalchemy import extract
from datetime import datetime, timedelta
import numpy as np

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/prediction')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    
    user_id = session['user_id']
    products = Product.query.filter_by(user_id=user_id).all()
    
    predictions = []
    total_predicted_sales = 0
    total_recommended_stock = 0
    total_current_stock = 0
    
    # Get last 90 days sales for trend analysis
    ninety_days_ago = datetime.now() - timedelta(days=90)
    
    for product in products:
        # Get last 90 days sales
        sales_90d = Sale.query.filter(
            Sale.product_id == product.id,
            Sale.date >= ninety_days_ago
        ).order_by(Sale.date).all()
        
        # Group sales by day
        daily_sales = {}
        for sale in sales_90d:
            date_str = sale.date.strftime('%Y-%m-%d')
            if date_str not in daily_sales:
                daily_sales[date_str] = 0
            daily_sales[date_str] += sale.quantity
            
        sales_values = list(daily_sales.values())
        
        # Calculate Average Daily Sales (last 30 days weighted more)
        if sales_values:
            if len(sales_values) > 30:
                recent_sales = sales_values[-30:]
                avg_daily = sum(recent_sales) / 30
            else:
                avg_daily = sum(sales_values) / len(sales_values)
        else:
            avg_daily = 0
            
        # Determine Trend (Increasing/Decreasing)
        if len(sales_values) >= 14:
            last_7 = sum(sales_values[-7:]) / 7
            prev_7 = sum(sales_values[-14:-7]) / 7
            if prev_7 > 0:
                growth = (last_7 - prev_7) / prev_7
                if growth > 0.1: trend_factor = 1.15
                elif growth < -0.1: trend_factor = 0.85
                else: trend_factor = 1.0
            else:
                trend_factor = 1.0 if last_7 == 0 else 1.2
        else:
            trend_factor = 1.0

        # Calculate Forecasts
        predicted_7 = avg_daily * 7 * trend_factor
        predicted_30 = avg_daily * 30 * trend_factor
        
        # Determine Status
        # 7-Day Status
        if product.current_stock < predicted_7:
            status_7 = 'Reorder Needed'
        elif product.current_stock < predicted_7 * 1.5:
            status_7 = 'Low Stock'
        else:
            status_7 = 'Sufficient'
            
        # 30-Day Status
        if product.current_stock < predicted_30:
            status_30 = 'Critical Reorder' if status_7 == 'Reorder Needed' else 'Reorder Needed'
        elif product.current_stock < predicted_30 * 1.2:
            status_30 = 'Low Stock'
        else:
            status_30 = 'Sufficient'
            
        predictions.append({
            'id': product.id,
            'name': product.name,
            'current_stock': product.current_stock,
            'avg_daily_sales': round(avg_daily, 1),
            'predicted_7_days': round(predicted_7, 1),
            'predicted_30_days': round(predicted_30, 1),
            'status_7': status_7,
            'status_30': status_30
        })

    # Sort: Critical items first
    def sort_priority(p):
        score = 0
        if 'Reorder' in p['status_7']: score += 10
        if 'Low' in p['status_7']: score += 5
        if 'Reorder' in p['status_30']: score += 3
        if 'Low' in p['status_30']: score += 1
        return score

    predictions.sort(key=sort_priority, reverse=True)
    
    return render_template('prediction.html', predictions=predictions)

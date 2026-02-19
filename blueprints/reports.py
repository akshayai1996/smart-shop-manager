from flask import Blueprint, send_file, Response, render_template, url_for
from models import db, Product, Sale
from fpdf import FPDF
import pandas as pd
import io
from datetime import datetime, timedelta

reports_bp = Blueprint('reports', __name__)

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'ShopEase - Retail Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Generated on: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

@reports_bp.route('/reports')
def index():
    return render_template('reports.html')

@reports_bp.route('/reports/download/sales_pdf')
def download_sales_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 30 Day Window
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Sales Summary
    sales = db.session.query(Sale).filter(Sale.date >= start_date).all()
    total_sales = sum(s.total_amount for s in sales)
    total_items = sum(s.quantity for s in sales)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Sales Summary (Last 30 Days)", 0, 1)
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"From: {start_date.strftime('%Y-%m-%d')} To: {end_date.strftime('%Y-%m-%d')}", 0, 1)
    pdf.cell(0, 10, f"Total Revenue: Rs. {total_sales:,.2f}", 0, 1)
    pdf.cell(0, 10, f"Total Items Sold: {total_items:,.0f}", 0, 1)
    pdf.ln(10)
    
    # Transactions Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Transaction History", 0, 1)
    
    # Header
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(60, 10, "Product", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(40, 10, "Amount", 1)
    pdf.ln()
    
    # Rows
    pdf.set_font("Arial", size=10)
    recent_sales = db.session.query(Sale).filter(Sale.date >= start_date).order_by(Sale.date.desc()).all()
    
    for sale in recent_sales:
        product = Product.query.get(sale.product_id)
        product_name = product.name if product else "Unknown"
        
        pdf.cell(40, 8, sale.date.strftime('%Y-%m-%d'), 1)
        pdf.cell(60, 8, product_name[:25], 1)
        pdf.cell(30, 8, str(int(sale.quantity)), 1)
        pdf.cell(40, 8, f"{sale.total_amount:.2f}", 1)
        pdf.ln()

    # Buffer
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'sales_report_30days_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

@reports_bp.route('/reports/download/inventory_excel')
def download_inventory_excel():
    products = Product.query.all()
    data = []
    
    for p in products:
        data.append({
            'Product ID': p.id,
            'Name': p.name,
            'Category': p.category,
            'Current Stock': p.current_stock,
            'Unit': p.unit,
            'Cost Price': p.cost_price,
            'Selling Price': p.selling_price,
            'Stock Value': p.current_stock * p.cost_price
        })
    
    df = pd.DataFrame(data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory')
    
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name=f'inventory_report_{datetime.now().strftime("%Y%m%d")}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@reports_bp.route('/reports/download/pnl_pdf')
def download_pnl_pdf():
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Calculate Dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Fetch Sales (Revenue)
    sales = db.session.query(Sale).filter(Sale.date >= start_date).all()
    total_revenue = sum(s.total_amount for s in sales)
    
    # Calculate COGS (Cost of Goods Sold)
    total_cogs = 0
    for sale in sales:
        product = Product.query.get(sale.product_id)
        if product:
             # Use current cost price as approximation since we don't track historical cost per batch yet
            total_cogs += sale.quantity * product.cost_price
            
    gross_profit = total_revenue - total_cogs
    net_profit = gross_profit # Assuming no other expenses for now
    
    profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0
    
    # Title
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Profit & Loss Statement", 0, 1, 'C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}", 0, 1, 'C')
    pdf.ln(10)
    
    # Financial Table
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Description", 1)
    pdf.cell(50, 10, "Amount (Rs.)", 1)
    pdf.ln()
    
    pdf.set_font("Arial", size=12)
    # Revenue
    pdf.cell(100, 10, "Total Revenue", 1)
    pdf.cell(50, 10, f"{total_revenue:,.2f}", 1)
    pdf.ln()
    
    # COGS
    pdf.cell(100, 10, "Cost of Goods Sold (COGS)", 1)
    pdf.cell(50, 10, f"{total_cogs:,.2f}", 1)
    pdf.ln()
    
    # Gross Profit
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Gross Profit", 1)
    pdf.cell(50, 10, f"{gross_profit:,.2f}", 1)
    pdf.ln()
    
    # Net Profit
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(100, 10, "Net Profit", 1, 0, 'L', True)
    pdf.cell(50, 10, f"{net_profit:,.2f}", 1, 0, 'L', True)
    pdf.ln(15)
    
    # Summary Metrics
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Key Metrics", 0, 1)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Net Profit Margin: {profit_margin:.1f}%", 0, 1)
    
    # Buffer
    buffer = io.BytesIO()
    pdf_output = pdf.output(dest='S').encode('latin-1')
    buffer.write(pdf_output)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'pnl_statement_{datetime.now().strftime("%Y%m%d")}.pdf',
        mimetype='application/pdf'
    )

# 🛒 Smart Shop Manager

> A full-featured retail management web app built with **Python Flask**. Manage your entire shop from one dashboard — billing, inventory, AI-powered sales prediction, customer CRM, Khatabook, and real-time analytics.

---

## ✨ Features

| Module                  | Description                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| 📊 **Dashboard**        | Real-time overview — today's revenue, monthly sales, low-stock alerts, recent transactions        |
| 📦 **Stock Management** | Add products, restock inventory, view current stock levels with units                             |
| 🧾 **Billing / POS**    | Create customer orders, select multiple products with quantity validation, auto-generate invoices |
| 💳 **Payments**         | Accept Card, UPI/QR, and Khata (Credit) payments with invoice generation                          |
| 🤖 **AI Prediction**    | Predict weekly & monthly demand per product using sales history; automated reorder alerts         |
| 📈 **Analytics**        | Interactive charts — daily/monthly revenue trends, top products, category breakdown               |
| 📋 **Reports**          | Downloadable sales reports with date range filtering                                              |
| 👥 **Customer CRM**     | Maintain customer profiles with purchase history                                                  |
| 📒 **Khatabook**        | Track credit sales and collect payments with full ledger per customer                             |
| 🧾 **Transactions**     | Full transaction history with invoice reference numbers                                           |

---

## 🖥️ Tech Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy
- **Database:** SQLite (auto-created on first run)
- **Frontend:** HTML5, CSS3, Vanilla JavaScript
- **Charts:** Chart.js
- **Icons:** Font Awesome 6
- **PDF/Invoice:** FPDF
- **Payments QR:** qrcode[pil]
- **Excel Support:** openpyxl, pandas

---

## 🚀 Installation & Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

---

### Step 1 — Clone the Repository

```bash
git clone https://github.com/akshayai1996/smart-shop-manager.git
cd smart-shop-manager
```

---

### Step 2 — Create a Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 — Run the Application

```bash
python app.py
```

The app will start at **http://localhost:5000**

> ✅ The database (`instance/shop.db`) is created automatically on first run. No manual setup needed.

---

### Step 5 — Register & Login

1. Open **http://localhost:5000** in your browser
2. Click **Register** to create your shop account
3. Login with your credentials
4. You're in! 🎉

---

## 📁 Project Structure

```
smart-shop-manager/
│
├── app.py                  # Main Flask application & routes
├── models.py               # Database models (SQLAlchemy)
├── requirements.txt        # Python dependencies
│
├── blueprints/             # Modular Flask blueprints
│   ├── billing.py          # Order creation flow
│   ├── customers.py        # Customer CRM
│   ├── khatabook.py        # Credit book management
│   ├── payment.py          # Payment processing & invoices
│   ├── prediction.py       # AI demand forecasting
│   ├── reports.py          # Report generation
│   └── transactions.py     # Transaction history
│
├── templates/              # Jinja2 HTML templates
│   ├── base.html           # Base layout with sidebar
│   ├── dashboard.html      # Main dashboard
│   ├── stock.html          # Inventory management
│   ├── billing_*.html      # Billing flow pages
│   ├── payment.html        # Payment gateway page
│   ├── analytics.html      # Charts & analytics
│   ├── khatabook*.html     # Khatabook pages
│   └── ...                 # Other templates
│
└── static/
    └── style.css           # Global stylesheet
```

---

## 🔑 Default Credentials

> There are no default credentials. **Register a new account** on first use.

---

## ⚙️ Configuration

The app uses a secret key for sessions. You can change it by setting an environment variable:

```bash
# Windows (PowerShell)
$env:SECRET_KEY = "your-super-secret-key"

# macOS / Linux
export SECRET_KEY="your-super-secret-key"
```

If not set, a default development key is used _(not recommended for production)_.

---

## 🌐 Deploying to Production

For production deployment (e.g., on a VPS or cloud server):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Or use **Render**, **Railway**, or **PythonAnywhere** for free hosting. Make sure to:

- Set `SECRET_KEY` as an environment variable
- Use a persistent disk for the `instance/` folder (SQLite database)

---

## 🤝 Contributing

1. Fork the repository
2. Create a new branch: `git checkout -b feature/your-feature-name`
3. Make your changes and commit: `git commit -m "Add: feature description"`
4. Push to your fork: `git push origin feature/your-feature-name`
5. Open a Pull Request

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---

## 👨‍💻 Author

Made with ❤️ by **[akshayai1996](https://github.com/akshayai1996)**

---

> ⭐ If you found this useful, please give it a star on GitHub!

# ShopEase - Smart Shop Manager

ShopEase is a powerful, standalone retail management application designed for small to medium-sized businesses. It provides features for billing, inventory management, customer khtabook, and detailed profit & loss analytics.

## 🚀 Two Ways to Use ShopEase

### 1. Standalone Desktop App (Recommended)

The easiest way to use ShopEase on Windows. No Python installation required.

- **Download**: Go to the `dist/` folder and download `shopease-desktop Setup 1.0.0.exe`.
- **Install**: Run the installer. It will install the application and create a shortcut on your Desktop.
- **Run**: Launch "ShopEase" from your Desktop.
- **Data**: The app automatically generates 6 months of demo data (up to today's date) on first launch so you can explore the features immediately.

---

### 2. Python Source Code (Technical/Development)

If you want to run the application from the source or contribute to development.

#### Prerequisites

- Python 3.10 or higher
- Git LFS (needed to download the installer file)

#### Installation

1.  **Clone the repo**:
    ```bash
    git clone https://github.com/akshayai1996/smart-shop-manager.git
    cd smart-shop-manager
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

#### Running the App

1.  **Start the Flask Server**:
    ```bash
    python app.py
    ```
2.  **Access the App**: Open your browser and go to `http://127.0.0.1:5000`.

---

## 📊 Key Features

- **Dynamic Dashboard**: Real-time sales, revenue, and profit metrics.
- **Smart Billing**: Quick search for products and instant invoice generation.
- **Inventory Tracking**: Stock-in history and low-stock alerts.
- **Khatabook**: Track customer credit (Udhaar) and payment history.
- **Detailed Reports**: Download Sales, Inventory, and P&L reports in PDF/Excel format.

## 🛠 Tech Stack

- **Backend**: Flask (Python)
- **Database**: SQLite
- **Frontend**: HTML5, CSS3, Vanilla JS
- **Desktop Layer**: Electron
- **Report Engine**: FPDF (PDFs), Pandas/OpenPyXL (Excel)

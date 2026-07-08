 # kra_tax_system.py
import os
import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib
import requests
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ReceiptStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    PROCESSING = "processing"

class ExpenseCategory(Enum):
    OFFICE_SUPPLIES = "Office Supplies"
    TRAVEL_ACCOMMODATION = "Travel & Accommodation"
    PROFESSIONAL_SERVICES = "Professional Services"
    EQUIPMENT_MACHINERY = "Equipment & Machinery"
    MARKETING_ADVERTISING = "Marketing & Advertising"
    UTILITIES = "Utilities"
    VEHICLE_EXPENSES = "Vehicle Expenses"
    OTHER = "Other Business Expenses"

@dataclass
class ExpenseReceipt:
    id: str
    user_id: str
    amount: float
    category: ExpenseCategory
    description: str
    date: datetime
    vat_status: str
    file_path: str
    status: ReceiptStatus
    created_at: datetime
    verified_at: Optional[datetime] = None
    etims_reference: Optional[str] = None
    hash_value: Optional[str] = None

@dataclass
class TaxCalculationResult:
    total_expenses: float
    allowable_deduction: float
    tax_savings: float
    compliance_score: float
    tax_rate: float
    breakdown: Dict[str, float]

class KRATaxSystem:
    def __init__(self, db_path: str = "kra_tax.db"):
        self.db_path = db_path
        self.init_database()
        self.etims_api_url = "https://api.etims.gov.ke/verify"  # Mock URL
        self.tax_rates = {
            "individual": 0.30,  # 30% tax rate
            "corporation": 0.30
        }
        self.allowable_percentages = {
            ExpenseCategory.OFFICE_SUPPLIES: 0.85,
            ExpenseCategory.TRAVEL_ACCOMMODATION: 0.75,
            ExpenseCategory.PROFESSIONAL_SERVICES: 0.90,
            ExpenseCategory.EQUIPMENT_MACHINERY: 0.50,  # Capital allowance
            ExpenseCategory.MARKETING_ADVERTISING: 0.80,
            ExpenseCategory.UTILITIES: 0.95,
            ExpenseCategory.VEHICLE_EXPENSES: 0.65,
            ExpenseCategory.OTHER: 0.70
        }
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create expenses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                vat_status TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                verified_at TEXT,
                etims_reference TEXT,
                hash_value TEXT
            )
        ''')
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                tax_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                tax_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create tax_calculations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tax_calculations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                calculation_date TEXT NOT NULL,
                total_expenses REAL NOT NULL,
                allowable_deduction REAL NOT NULL,
                tax_savings REAL NOT NULL,
                compliance_score REAL NOT NULL,
                calculation_data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def create_user(self, tax_id: str, name: str, email: str, tax_type: str = "individual") -> str:
        """Create a new user in the system"""
        user_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (id, tax_id, name, email, tax_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, tax_id, name, email, tax_type, created_at))
            
            conn.commit()
            logger.info(f"User created successfully: {tax_id}")
            return user_id
        except sqlite3.IntegrityError:
            logger.warning(f"User with tax ID {tax_id} already exists")
            # Return existing user ID
            cursor.execute('SELECT id FROM users WHERE tax_id = ?', (tax_id,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()
    
    def upload_receipt(self, user_id: str, amount: float, category: str, 
                      description: str, date: str, vat_status: str, 
                      file_data: bytes, filename: str) -> Tuple[bool, str]:
        """Upload and process a new expense receipt"""
        try:
            # Validate inputs
            if amount <= 0:
                return False, "Amount must be greater than zero"
            
            # Create receipt directory if it doesn't exist
            receipt_dir = Path("receipts") / user_id
            receipt_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate unique filename
            file_extension = Path(filename).suffix
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = receipt_dir / unique_filename
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Calculate file hash for integrity
            file_hash = hashlib.sha256(file_data).hexdigest()
            
            # Create receipt object
            receipt = ExpenseReceipt(
                id=str(uuid.uuid4()),
                user_id=user_id,
                amount=amount,
                category=ExpenseCategory(category),
                description=description,
                date=datetime.fromisoformat(date),
                vat_status=vat_status,
                file_path=str(file_path),
                status=ReceiptStatus.PROCESSING,
                created_at=datetime.now(),
                hash_value=file_hash
            )
            
            # Save to database
            self._save_receipt(receipt)
            
            # Start verification process
            self._verify_receipt_async(receipt.id)
            
            logger.info(f"Receipt uploaded successfully: {receipt.id}")
            return True, receipt.id
            
        except Exception as e:
            logger.error(f"Error uploading receipt: {str(e)}")
            return False, str(e)
    
    def _save_receipt(self, receipt: ExpenseReceipt):
        """Save receipt to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO expenses (id, user_id, amount, category, description, date, 
                                vat_status, file_path, status, created_at, hash_value)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            receipt.id, receipt.user_id, receipt.amount, receipt.category.value,
            receipt.description, receipt.date.isoformat(), receipt.vat_status,
            receipt.file_path, receipt.status.value, receipt.created_at.isoformat(),
            receipt.hash_value
        ))
        
        conn.commit()
        conn.close()
    
    def _verify_receipt_async(self, receipt_id: str):
        """Asynchronously verify receipt with eTIMS system"""
        # In a real implementation, this would use Celery or similar for async processing
        import threading
        
        def verify_task():
            try:
                # Simulate eTIMS API verification
                receipt = self._get_receipt(receipt_id)
                if receipt:
                    # Mock verification logic
                    is_valid = self._mock_etims_verification(receipt)
                    
                    if is_valid:
                        self._update_receipt_status(receipt_id, ReceiptStatus.VERIFIED)
                        logger.info(f"Receipt {receipt_id} verified successfully")
                    else:
                        self._update_receipt_status(receipt_id, ReceiptStatus.REJECTED)
                        logger.warning(f"Receipt {receipt_id} rejected by eTIMS")
            except Exception as e:
                logger.error(f"Error verifying receipt {receipt_id}: {str(e)}")
                self._update_receipt_status(receipt_id, ReceiptStatus.REJECTED)
        
        thread = threading.Thread(target=verify_task)
        thread.daemon = True
        thread.start()
    
    def _mock_etims_verification(self, receipt: ExpenseReceipt) -> bool:
        """Mock eTIMS verification - in real implementation, this would call actual eTIMS API"""
        # Simulate API call delay
        import time
        time.sleep(2)
        
        # Mock verification logic - 90% success rate for demo
        import random
        return random.random() < 0.9
    
    def _get_receipt(self, receipt_id: str) -> Optional[ExpenseReceipt]:
        """Retrieve receipt from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM expenses WHERE id = ?', (receipt_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ExpenseReceipt(
                id=row[0], user_id=row[1], amount=row[2], 
                category=ExpenseCategory(row[3]), description=row[4],
                date=datetime.fromisoformat(row[5]), vat_status=row[6],
                file_path=row[7], status=ReceiptStatus(row[8]),
                created_at=datetime.fromisoformat(row[9]),
                verified_at=datetime.fromisoformat(row[10]) if row[10] else None,
                etims_reference=row[11], hash_value=row[12]
            )
        return None
    
    def _update_receipt_status(self, receipt_id: str, status: ReceiptStatus, 
                             etims_reference: str = None):
        """Update receipt status in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        verified_at = datetime.now().isoformat() if status == ReceiptStatus.VERIFIED else None
        
        cursor.execute('''
            UPDATE expenses 
            SET status = ?, verified_at = ?, etims_reference = ?
            WHERE id = ?
        ''', (status.value, verified_at, etims_reference, receipt_id))
        
        conn.commit()
        conn.close()
    
    def calculate_tax_deduction(self, user_id: str, new_expense_amount: float = 0) -> TaxCalculationResult:
        """Calculate tax deductions for a user"""
        # Get all verified receipts for user
        verified_receipts = self._get_user_receipts(user_id, ReceiptStatus.VERIFIED)
        
        # Calculate totals
        total_expenses = sum(receipt.amount for receipt in verified_receipts) + new_expense_amount
        
        # Calculate allowable deductions by category
        category_totals = {}
        allowable_deduction = 0
        
        for receipt in verified_receipts:
            category = receipt.category
            amount = receipt.amount
            allowable_percentage = self.allowable_percentages.get(category, 0.7)
            category_allowable = amount * allowable_percentage
            
            if category not in category_totals:
                category_totals[category.value] = {
                    'total': 0,
                    'allowable': 0
                }
            
            category_totals[category.value]['total'] += amount
            category_totals[category.value]['allowable'] += category_allowable
            allowable_deduction += category_allowable
        
        # Add new expense (assuming default category percentage)
        if new_expense_amount > 0:
            default_percentage = 0.7
            allowable_deduction += new_expense_amount * default_percentage
        
        # Get user tax rate
        user_tax_rate = self._get_user_tax_rate(user_id)
        
        # Calculate tax savings
        tax_savings = allowable_deduction * user_tax_rate
        
        # Calculate compliance score
        all_receipts = self._get_user_receipts(user_id)
        verified_count = len(verified_receipts)
        total_count = len(all_receipts)
        compliance_score = (verified_count / total_count * 100) if total_count > 0 else 100
        
        # Prepare breakdown
        breakdown = {
            'total_expenses': total_expenses,
            'verified_expenses': sum(receipt.amount for receipt in verified_receipts),
            'allowable_deduction': allowable_deduction,
            'tax_rate': user_tax_rate,
            'tax_savings': tax_savings,
            'compliance_score': compliance_score,
            'category_breakdown': category_totals
        }
        
        result = TaxCalculationResult(
            total_expenses=total_expenses,
            allowable_deduction=allowable_deduction,
            tax_savings=tax_savings,
            compliance_score=compliance_score,
            tax_rate=user_tax_rate,
            breakdown=breakdown
        )
        
        # Save calculation to database
        self._save_tax_calculation(user_id, result)
        
        return result
    
    def _get_user_receipts(self, user_id: str, status: ReceiptStatus = None) -> List[ExpenseReceipt]:
        """Get user's receipts with optional status filter"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status:
            cursor.execute('SELECT * FROM expenses WHERE user_id = ? AND status = ?', 
                         (user_id, status.value))
        else:
            cursor.execute('SELECT * FROM expenses WHERE user_id = ?', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        receipts = []
        for row in rows:
            receipt = ExpenseReceipt(
                id=row[0], user_id=row[1], amount=row[2], 
                category=ExpenseCategory(row[3]), description=row[4],
                date=datetime.fromisoformat(row[5]), vat_status=row[6],
                file_path=row[7], status=ReceiptStatus(row[8]),
                created_at=datetime.fromisoformat(row[9]),
                verified_at=datetime.fromisoformat(row[10]) if row[10] else None,
                etims_reference=row[11], hash_value=row[12]
            )
            receipts.append(receipt)
        
        return receipts
    
    def _get_user_tax_rate(self, user_id: str) -> float:
        """Get user's tax rate"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT tax_type FROM users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        tax_type = result[0] if result else "individual"
        return self.tax_rates.get(tax_type, 0.30)
    
    def _save_tax_calculation(self, user_id: str, result: TaxCalculationResult):
        """Save tax calculation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        calculation_id = str(uuid.uuid4())
        calculation_date = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO tax_calculations (id, user_id, calculation_date, total_expenses, 
                                        allowable_deduction, tax_savings, compliance_score, calculation_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            calculation_id, user_id, calculation_date, result.total_expenses,
            result.allowable_deduction, result.tax_savings, result.compliance_score,
            json.dumps(result.breakdown)
        ))
        
        conn.commit()
        conn.close()
    
    def generate_report(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict:
        """Generate comprehensive tax report"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).isoformat()
        if not end_date:
            end_date = datetime.now().isoformat()
        
        # Get receipts for period
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM expenses 
            WHERE user_id = ? AND date BETWEEN ? AND ?
        ''', (user_id, start_date, end_date))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Calculate report data
        total_expenses = sum(row[2] for row in rows)
        verified_expenses = sum(row[2] for row in rows if ReceiptStatus(row[8]) == ReceiptStatus.VERIFIED)
        
        report = {
            'period': {
                'start': start_date,
                'end': end_date
            },
            'summary': {
                'total_expenses': total_expenses,
                'verified_expenses': verified_expenses,
                'compliance_rate': (verified_expenses / total_expenses * 100) if total_expenses > 0 else 0
            },
            'receipts': [
                {
                    'id': row[0],
                    'amount': row[2],
                    'category': row[3],
                    'description': row[4],
                    'date': row[5],
                    'status': row[8],
                    'etims_reference': row[11]
                } for row in rows
            ]
        }
        
        return report
    
    def export_to_pdf(self, user_id: str, calculation_id: str = None) -> str:
        """Export tax calculation to PDF"""
        # This would integrate with a PDF generation library like ReportLab
        # For now, return a mock PDF path
        pdf_path = f"exports/tax_calculation_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # Ensure exports directory exists
        Path("exports").mkdir(exist_ok=True)
        
        # Mock PDF generation
        logger.info(f"PDF export generated: {pdf_path}")
        return pdf_path

# Flask API Integration
from flask import Flask, request, jsonify, send_file
import io

app = Flask(__name__)
tax_system = KRATaxSystem()

@app.route('/api/upload-receipt', methods=['POST'])
def api_upload_receipt():
    """API endpoint for uploading receipts"""
    try:
        user_id = request.form.get('user_id')
        amount = float(request.form.get('amount', 0))
        category = request.form.get('category')
        description = request.form.get('description', '')
        date = request.form.get('date')
        vat_status = request.form.get('vat_status', 'included')
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        success, result = tax_system.upload_receipt(
            user_id, amount, category, description, date, vat_status,
            file.read(), file.filename
        )
        
        if success:
            return jsonify({'success': True, 'receipt_id': result})
        else:
            return jsonify({'success': False, 'error': result}), 400
            
    except Exception as e:
        logger.error(f"API error in upload-receipt: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate-tax', methods=['POST'])
def api_calculate_tax():
    """API endpoint for tax calculation"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        new_expense_amount = data.get('new_expense_amount', 0)
        
        result = tax_system.calculate_tax_deduction(user_id, new_expense_amount)
        
        return jsonify({
            'success': True,
            'result': {
                'total_expenses': result.total_expenses,
                'allowable_deduction': result.allowable_deduction,
                'tax_savings': result.tax_savings,
                'compliance_score': result.compliance_score,
                'tax_rate': result.tax_rate,
                'breakdown': result.breakdown
            }
        })
        
    except Exception as e:
        logger.error(f"API error in calculate-tax: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate-report', methods=['POST'])
def api_generate_report():
    """API endpoint for report generation"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        report = tax_system.generate_report(user_id, start_date, end_date)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        logger.error(f"API error in generate-report: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-pdf', methods=['POST'])
def api_export_pdf():
    """API endpoint for PDF export"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        calculation_id = data.get('calculation_id')
        
        pdf_path = tax_system.export_to_pdf(user_id, calculation_id)
        
        return jsonify({
            'success': True,
            'pdf_path': pdf_path
        })
        
    except Exception as e:
        logger.error(f"API error in export-pdf: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == "__main__":
    # Initialize with sample data
    tax_system = KRATaxSystem()
    user_id = tax_system.create_user("A123456789X", "John Doe", "john.doe@example.com")
    
    print("KRA Tax System initialized successfully!")
    print(f"Sample User ID: {user_id}")
    
    # Start Flask API
    app.run(debug=True, port=5000)
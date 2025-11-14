# Database setup for barcode scanning and approval system
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

class ApprovalDatabase:
    """Database class to manage scanned items and approvals"""
    
    def __init__(self, db_path: str = '../approval_system.db'):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create scanned_items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scanned_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE NOT NULL,
                item_number TEXT NOT NULL,
                sender_name TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                recipient_address TEXT NOT NULL,
                item_type TEXT,
                weight REAL,
                dimensions TEXT,
                special_handling TEXT,
                scan_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'system',
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Create approval_requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approval_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER,
                action_type TEXT NOT NULL,
                equipment_id TEXT,
                equipment_type TEXT,
                status TEXT DEFAULT 'PENDING',
                request_reason TEXT,
                requested_by TEXT DEFAULT 'system',
                requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                approved_by TEXT,
                approved_at DATETIME,
                rejection_reason TEXT,
                FOREIGN KEY (item_id) REFERENCES scanned_items (id)
            )
        ''')
        
        # Create equipment_maintenance table for tracking equipment status
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS equipment_maintenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_id TEXT NOT NULL,
                equipment_type TEXT NOT NULL,
                current_status TEXT DEFAULT 'operational',
                last_maintenance DATETIME,
                next_maintenance DATETIME,
                maintenance_notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database initialized successfully")
    
    def add_scanned_item(self, barcode: str, item_number: str, sender_name: str, 
                        recipient_name: str, recipient_address: str, 
                        item_type: str = None, weight: float = None, 
                        dimensions: str = None, special_handling: str = None) -> int:
        """Add a new scanned item to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO scanned_items 
                (barcode, item_number, sender_name, recipient_name, recipient_address,
                 item_type, weight, dimensions, special_handling)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (barcode, item_number, sender_name, recipient_name, recipient_address,
                  item_type, weight, dimensions, special_handling))
            
            item_id = cursor.lastrowid
            conn.commit()
            print(f"Item added successfully with ID: {item_id}")
            return item_id
            
        except sqlite3.IntegrityError as e:
            print(f"Error: Barcode {barcode} already exists")
            raise e
        finally:
            conn.close()
    
    def get_all_items(self, active_only: bool = True) -> List[Dict]:
        """Get all scanned items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, barcode, item_number, sender_name, recipient_name, 
                   recipient_address, item_type, weight, dimensions, 
                   special_handling, scan_timestamp
            FROM scanned_items
        '''
        
        if active_only:
            query += " WHERE is_active = 1"
        
        cursor.execute(query)
        items = cursor.fetchall()
        
        # Convert to list of dictionaries
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in items]
        
        conn.close()
        return result
    
    def request_approval(self, item_id: int, action_type: str, 
                        equipment_id: str = None, equipment_type: str = None,
                        request_reason: str = None) -> int:
        """Request approval for an action"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO approval_requests 
            (item_id, action_type, equipment_id, equipment_type, request_reason)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_id, action_type, equipment_id, equipment_type, request_reason))
        
        approval_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"Approval request created with ID: {approval_id}")
        return approval_id
    
    def get_pending_approvals(self) -> List[Dict]:
        """Get all pending approval requests"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ar.id, ar.action_type, ar.equipment_id, ar.equipment_type,
                   ar.request_reason, ar.requested_at,
                   si.barcode, si.item_number, si.sender_name, si.recipient_name
            FROM approval_requests ar
            JOIN scanned_items si ON ar.item_id = si.id
            WHERE ar.status = 'PENDING'
            ORDER BY ar.requested_at
        ''')
        
        approvals = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in approvals]
        
        conn.close()
        return result
    
    def update_approval_status(self, approval_id: int, status: str, 
                              approved_by: str = None, rejection_reason: str = None) -> bool:
        """Update approval status (APPROVED, REJECTED, etc.)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if status.upper() == 'APPROVED':
            cursor.execute('''
                UPDATE approval_requests 
                SET status = ?, approved_by = ?, approved_at = ?
                WHERE id = ?
            ''', (status.upper(), approved_by, datetime.now().isoformat(), approval_id))
        else:
            cursor.execute('''
                UPDATE approval_requests 
                SET status = ?, rejection_reason = ?
                WHERE id = ?
            ''', (status.upper(), rejection_reason, approval_id))
        
        rows_affected = cursor.rowcount
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def get_approved_items(self) -> List[Dict]:
        """Get all approved items"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ar.id, ar.action_type, ar.equipment_id, ar.equipment_type,
                   ar.approved_by, ar.approved_at,
                   si.barcode, si.item_number, si.sender_name, si.recipient_name
            FROM approval_requests ar
            JOIN scanned_items si ON ar.item_id = si.id
            WHERE ar.status = 'APPROVED'
            ORDER BY ar.approved_at DESC
        ''')
        
        approvals = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        result = [dict(zip(columns, row)) for row in approvals]
        
        conn.close()
        return result
    
    def add_sample_data(self):
        """Add sample data for testing"""
        sample_items = [
            {
                'barcode': '123456789012',
                'item_number': 'PKG001',
                'sender_name': 'John Smith',
                'recipient_name': 'Alice Johnson',
                'recipient_address': '123 Main St, City, State 12345',
                'item_type': 'electronics',
                'weight': 2.5,
                'dimensions': '20x15x10cm',
                'special_handling': 'fragile'
            },
            {
                'barcode': '123456789013',
                'item_number': 'PKG002',
                'sender_name': 'Bob Wilson',
                'recipient_name': 'Carol Davis',
                'recipient_address': '456 Oak Ave, City, State 67890',
                'item_type': 'documents',
                'weight': 0.3,
                'dimensions': '30x22x2cm',
                'special_handling': 'confidential'
            },
            {
                'barcode': '123456789014',
                'item_number': 'PKG003',
                'sender_name': 'Emma Brown',
                'recipient_name': 'David Lee',
                'recipient_address': '789 Pine Rd, City, State 54321',
                'item_type': 'medical',
                'weight': 1.8,
                'dimensions': '15x15x8cm',
                'special_handling': 'temperature_controlled'
            }
        ]
        
        for item in sample_items:
            try:
                item_id = self.add_scanned_item(**item)
                # Add some approval requests
                self.request_approval(
                    item_id=item_id,
                    action_type='Process Shipment',
                    equipment_id=f"scanner_{item_id}",
                    equipment_type='barcode_scanner',
                    request_reason='Special handling required'
                )
            except sqlite3.IntegrityError:
                print(f"Sample item with barcode {item['barcode']} already exists")

# Utility function for easy import
def get_database() -> ApprovalDatabase:
    """Get database instance"""
    return ApprovalDatabase()

if __name__ == "__main__":
    # Example usage
    db = ApprovalDatabase()
    db.add_sample_data()
    
    print("=== All Items ===")
    items = db.get_all_items()
    for item in items:
        print(f"Barcode: {item['barcode']}, Item: {item['item_number']}, "
              f"From: {item['sender_name']}, To: {item['recipient_name']}")
    
    print("\n=== Pending Approvals ===")
    pending = db.get_pending_approvals()
    for approval in pending:
        print(f"ID: {approval['id']}, Action: {approval['action_type']}, "
              f"Item: {approval['item_number']}, Barcode: {approval['barcode']}")
#!/usr/bin/env python3
"""
Database migration script to add new user fields.
Run this once to update your existing database schema.
"""

import sqlite3
import os

def migrate_database():
    db_path = "sukoon.db"
    
    if not os.path.exists(db_path):
        print("Database doesn't exist yet. No migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if new columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns
        if 'email' not in columns:
            print("Adding email column...")
            cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            
        if 'full_name' not in columns:
            print("Adding full_name column...")
            cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            
        if 'age' not in columns:
            print("Adding age column...")
            cursor.execute("ALTER TABLE users ADD COLUMN age INTEGER")
            
        if 'gender' not in columns:
            print("Adding gender column...")
            cursor.execute("ALTER TABLE users ADD COLUMN gender TEXT")
        
        # For existing users, set email = username if email is null
        cursor.execute("UPDATE users SET email = username WHERE email IS NULL")
        
        # Create unique index on email if it doesn't exist
        try:
            cursor.execute("CREATE UNIQUE INDEX idx_users_email ON users(email)")
            print("Created unique index on email column")
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e):
                raise
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
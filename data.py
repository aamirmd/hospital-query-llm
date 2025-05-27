import sqlite3
import os
import re
from pathlib import Path

class DatabaseError(Exception):
    """Custom exception for database operations"""
    pass

def validate_sql_file(file_path):
    """Validate that the SQL file exists and is readable"""
    if not os.path.exists(file_path):
        raise DatabaseError(f"SQL file not found: {file_path}")
    if not os.path.isfile(file_path):
        raise DatabaseError(f"Path is not a file: {file_path}")
    if os.path.getsize(file_path) == 0:
        raise DatabaseError(f"SQL file is empty: {file_path}")

def convert_mysql_to_sqlite(sql):
    """Convert MySQL syntax to SQLite compatible syntax"""
    if not sql.strip():
        raise DatabaseError("Empty SQL script provided")

    # Convert MySQL syntax to SQLite
    conversions = [
        (r'AUTO_INCREMENT', ''),  # Remove AUTO_INCREMENT
        (r'int\([0-9]+\)', 'INTEGER'),  # Convert int(N) to INTEGER
        (r'varchar\([0-9]+\)', 'TEXT'),  # Convert varchar(N) to TEXT
        (r'decimal[^,)]+', 'REAL'),  # Convert decimal types to REAL
        (r'double[^,)]+', 'REAL'),  # Convert double types to REAL
        (r'CREATE DATABASE.*?;', ''),  # Remove CREATE DATABASE
        (r'USE.*?;', ''),  # Remove USE database
        (r'ENGINE\s*=\s*\w+', ''),  # Remove ENGINE declarations
        (r'DEFAULT\s+CHARSET\s*=\s*\w+', ''),  # Remove CHARACTER SET declarations
        (r'COLLATE\s+\w+', ''),  # Remove COLLATE declarations
    ]
    
    try:
        for pattern, replacement in conversions:
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        return sql
    except re.error as e:
        raise DatabaseError(f"Error in SQL conversion: {str(e)}")

def split_sql_commands(sql_script):
    """Split SQL script into individual commands and validate them"""
    commands = []
    current_command = []
    
    # Handle both Windows and Unix line endings
    lines = sql_script.replace('\r\n', '\n').split('\n')
    
    for line in lines:
        # Skip empty lines and comments
        line = line.strip()
        if not line or line.startswith('--'):
            continue
            
        current_command.append(line)
        
        if line.endswith(';'):
            command = ' '.join(current_command)
            if command.strip('; '):  # Only add non-empty commands
                commands.append(command)
            current_command = []
    
    # Check for unfinished commands
    if current_command:
        remaining = ' '.join(current_command)
        if remaining.strip():
            print(f"Warning: Found incomplete SQL command: {remaining}")
    
    return commands

def create_database(db_name='hospital.db', sql_file='hospital.sql'):
    """Create SQLite database from SQL file with enhanced error handling"""
    db_path = Path(db_name)
    sql_path = Path(sql_file)
    
    try:
        # Validate SQL file
        validate_sql_file(sql_path)
        
        # Remove existing database if it exists
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                raise DatabaseError(f"Cannot delete existing database {db_name}. File may be in use.")
        
        # Connect to SQLite database
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        try:
            # Read and process the SQL file
            with open(sql_path, 'r', encoding='utf-8') as file:
                sql_script = file.read()
            
            # Convert MySQL syntax to SQLite
            sql_script = convert_mysql_to_sqlite(sql_script)
            
            # Split and validate commands
            commands = split_sql_commands(sql_script)
            
            if not commands:
                raise DatabaseError("No valid SQL commands found in the file")
            
            # Execute each command
            total_commands = len(commands)
            successful_commands = 0
            
            for i, command in enumerate(commands, 1):
                try:
                    cursor.execute(command)
                    successful_commands += 1
                except sqlite3.Error as e:
                    error_msg = str(e)
                    print(f"\nError executing command {i}/{total_commands}:")
                    print(f"Command: {command}")
                    print(f"Error: {error_msg}")
                    
                    # Specific error handling
                    if "syntax error" in error_msg.lower():
                        print("Hint: This appears to be a syntax error. Check the SQL command format.")
                    elif "no such table" in error_msg.lower():
                        print("Hint: Referenced table doesn't exist. Check table creation order.")
                    elif "foreign key" in error_msg.lower():
                        print("Hint: Foreign key constraint failed. Check referenced table and key.")
            
            # Commit the changes
            conn.commit()
            
            # Report results
            print(f"\nDatabase creation completed:")
            print(f"- Total commands: {total_commands}")
            print(f"- Successful commands: {successful_commands}")
            print(f"- Failed commands: {total_commands - successful_commands}")
            
            if successful_commands == total_commands:
                print("\nDatabase created successfully!")
            else:
                print("\nWarning: Database created with some errors.")
                
        except sqlite3.Error as e:
            raise DatabaseError(f"SQLite error: {str(e)}")
        finally:
            conn.close()
            
    except Exception as e:
        if isinstance(e, DatabaseError):
            raise
        raise DatabaseError(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    try:
        create_database()
    except DatabaseError as e:
        print(f"\nError: {str(e)}")
        exit(1)

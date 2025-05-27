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
    """Convert MySQL syntax to SQLite compatible syntax.
    Handles type conversions, removes MySQL-specific features, and adjusts syntax differences."""
    if not sql.strip():
        raise DatabaseError("Empty SQL script provided")

    # Each tuple contains (pattern_to_find, replacement_text)
    conversions = [
        # Data type conversions
        (r'int\([0-9]+\)', 'INTEGER'),  # MySQL allows size specification for int
        (r'varchar\([0-9]+\)', 'TEXT'),  # SQLite uses dynamic TEXT type
        (r'decimal\(.+\)', 'REAL'),  # Convert all decimal variants to REAL
        (r'double\(.+\)', 'REAL'),  # Convert all double variants to REAL
        
        # Remove MySQL-specific features
        (r'AUTO_INCREMENT', ''),  # SQLite uses AUTOINCREMENT keyword
        (r'CREATE DATABASE.*?;', ''),  # SQLite is serverless
        (r'USE.*?;', ''),  # SQLite uses file-based databases
        (r'ENGINE\s*=\s*\w+', ''),  # SQLite doesn't use storage engines
        (r'DEFAULT\s+CHARSET\s*=\s*\w+', ''),  # SQLite handles text encoding differently
        (r'COLLATE\s+\w+', ''),  # SQLite has different collation syntax
    ]
    
    try:
        for pattern, replacement in conversions:
            sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)
        return sql
    except re.error as e:
        raise DatabaseError(f"Error in SQL conversion: {str(e)}")

def split_sql_commands(sql_script):
    """Split SQL script into individual commands and validate them.
    Handles multi-line commands and skips comments."""
    commands = []
    current_command = []
    
    # Normalize line endings for cross-platform compatibility
    lines = sql_script.replace('\r\n', '\n').split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip comments and empty lines to avoid processing non-SQL content
        if not line or line.startswith('--'):
            continue
            
        current_command.append(line)
        
        # Complete command found
        if line.endswith(';'):
            command = ' '.join(current_command)
            if command.strip('; '):  # Avoid empty commands
                commands.append(command)
            current_command = []
    
    # Warn about potentially incomplete commands at end of file
    if current_command:
        remaining = ' '.join(current_command)
        if remaining.strip():
            print(f"Warning: Found incomplete SQL command: {remaining}")
    
    return commands

def create_database(db_name='hospital.db', sql_file='hospital.sql'):
    """Create SQLite database from SQL file with enhanced error handling.
    
    Args:
        db_name: Name of the SQLite database file to create
        sql_file: Path to the source SQL file with schema and data
    """
    db_path = Path(db_name)
    sql_path = Path(sql_file)
    
    try:
        # Initial validation and setup
        validate_sql_file(sql_path)
        
        # Clean up existing database if present
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                raise DatabaseError(f"Cannot delete existing database {db_name}. File may be in use.")
        
        # Initialize database connection
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # SQLite foreign keys are disabled by default
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        try:
            # Process and execute SQL commands
            with open(sql_path, 'r', encoding='utf-8') as file:
                sql_script = file.read()
            
            sql_script = convert_mysql_to_sqlite(sql_script)
            commands = split_sql_commands(sql_script)
            
            if not commands:
                raise DatabaseError("No valid SQL commands found in the file")
            
            # Execute commands and track progress
            total_commands = len(commands)
            successful_commands = 0
            
            for i, command in enumerate(commands, 1):
                try:
                    cursor.execute(command)
                    if command.strip().startswith('CREATE TABLE'):
                        print(command)
                    successful_commands += 1
                except sqlite3.Error as e:
                    error_msg = str(e)
                    print(f"\nError executing command {i}/{total_commands}:")
                    print(f"Command: {command}")
                    print(f"Error: {error_msg}")
                    
                    # Provide helpful hints for common errors
                    if "syntax error" in error_msg.lower():
                        print("Hint: This appears to be a syntax error. Check the SQL command format.")
                    elif "no such table" in error_msg.lower():
                        print("Hint: Referenced table doesn't exist. Check table creation order.")
                    elif "foreign key" in error_msg.lower():
                        print("Hint: Foreign key constraint failed. Check referenced table and key.")
            
            conn.commit()
            
            # Report final status
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

#!/usr/bin/env python3
"""
Setup and run script for Mental Health Chatbot
"""

import os
import sys
import subprocess
import sqlite3

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{'='*50}")
    print(f"🔧 {description}")
    print(f"{'='*50}")
    
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in {description}:")
        print(e.stderr)
        return False

def setup_project():
    """Setup the Django project"""
    print("🚀 Setting up Mental Health Chatbot")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    
    print(f"✅ Python version: {sys.version}")
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing requirements"):
        return False
    
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        env_content = """SECRET_KEY=django-insecure-your-secret-key-change-this-in-production
DEBUG=True
OPENAI_API_KEY=your-openai-api-key-here
DATABASE_URL=sqlite:///db.sqlite3
"""
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file - Please update with your settings")
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
    
    if not run_command("python manage.py migrate", "Running migrations"):
        return False
    
    # Create superuser (optional)
    print("\n" + "="*50)
    print("👤 Create superuser (optional)")
    print("="*50)
    create_superuser = input("Do you want to create a superuser? (y/n): ").lower().strip()
    if create_superuser == 'y':
        run_command("python manage.py createsuperuser", "Creating superuser")
    
    # Populate resources
    if not run_command("python manage.py populate_resources", "Populating support resources"):
        print("⚠️ Warning: Could not populate resources automatically")
    
    # Collect static files
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        print("⚠️ Warning: Could not collect static files")
    
    print("\n" + "="*60)
    print("🎉 Setup completed successfully!")
    print("="*60)
    print("📝 Next steps:")
    print("1. Update your .env file with proper values")
    print("2. If using OpenAI, add your API key to .env")
    print("3. Run: python manage.py runserver")
    print("4. Visit: http://127.0.0.1:8000")
    print("="*60)
    
    return True

def run_server():
    """Run the development server"""
    print("\n🚀 Starting development server...")
    try:
        subprocess.run("python manage.py runserver", shell=True, check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_server()
    else:
        if setup_project():
            run_choice = input("\nDo you want to start the server now? (y/n): ").lower().strip()
            if run_choice == 'y':
                run_server()
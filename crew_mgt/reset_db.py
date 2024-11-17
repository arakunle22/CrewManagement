import os
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crew_mgt.settings')
django.setup()

def reset_database():
    """Reset the database by removing migrations and recreating them"""
    
    # Get the list of all Django apps
    django_apps = [app.split('.')[-1] for app in settings.INSTALLED_APPS 
                  if not app.startswith('django.') and not app.startswith('rest_framework')]
    
    print("Starting database reset...")
    
    # Remove the database file
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("Removed existing database file")
    
    # Remove all migration files
    for app in django_apps:
        migrations_dir = os.path.join(app, 'migrations')
        if os.path.exists(migrations_dir):
            for filename in os.listdir(migrations_dir):
                if filename != '__init__.py' and filename.endswith('.py'):
                    os.remove(os.path.join(migrations_dir, filename))
                    print(f"Removed migration file: {app}/migrations/{filename}")
    
    # Make fresh migrations
    os.system('python manage.py makemigrations')
    print("Created new migrations")
    
    # Apply migrations
    os.system('python manage.py migrate')
    print("Applied migrations")
    
    # Create superuser if needed
    print("\nDo you want to create a superuser? (y/n)")
    if input().lower() == 'y':
        os.system('python manage.py createsuperuser')

if __name__ == "__main__":
    reset_database()

# 2. Save this file and run:
# python reset_db.py

# 3. Then run these commands:
# python manage.py makemigrations crew_app
# python manage.py migrate --run-syncdb
# python manage.py createsuperuser
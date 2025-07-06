------------------------------------------------------Project Setup Instructions--------------------------------------------------------

🔧 Step 0: Clone the Repository (if user is cloning)

git clone https://github.com/mandarkambli2005/project.git


📁 Step 1: Navigate to the project folder
Open a terminal or command prompt and move into the folder:

command:- cd path/to/file-share-webiste-django


🐍 Step 2: Create and activate a virtual environment

For Windows:
command:- python -m venv venv venv\Scripts\activate

For macOS/Linux:
command:- python3 -m venv venv source venv/bin/activate


📦 Step 3: Install all dependencies

command:- pip install django


🗄️ Step 4: Apply database migrations

command:- python manage.py makemigrations
          python manage.py migrate


🧑‍💼 Step 5: Create a superuser (for admin access)

command:- python manage.py createsuperuser
#It will prompt for username, email, and password.


📤 Step 6: Collect static files

command:-python manage.py collectstatic
#Type yes if it asks to overwrite files.


🚀 Step 7: Run the Django server

command:-python manage.py runserver

Now open your browser and go to:

🔗 http://127.0.0.1:8000/
🔗 Admin Panel: http://127.0.0.1:8000/admin/





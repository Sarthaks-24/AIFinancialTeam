# Project Setup Guide

Welcome to the AI Financial Team project! This guide will help you set up the project on your local machine.

## Prerequisites

Before you begin, ensure you have the following installed:
- [Python 3.8+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/)
- [PostgreSQL](https://www.postgresql.org/download/)

---

## 1. Environment Configuration

### Backend `.env`
1. In the root directory, you'll find a `.env.example` file. 
2. Create a copy of this file and name it `.env`.
3. Open the `.env` file and fill in the required credentials:
   - **Database Credentials**: For PostgreSQL, ensure you have created a database. Then provide your connection details:
     ```env
     Django_ENGINE=django.db.backends.postgresql
     Django_NAME=your_db_name
     Django_USER=postgres
     Django_PASSWORD=your_password
     Django_HOST=localhost
     Django_PORT=5432
     ```
   - **Gemini API Key** (`GEMINI_API_KEY`) - You can obtain this from Google AI Studio.
   - **Django Secret Key** (`Django_KEY`) - Generate a secure random string for development. You can quickly generate one by running this in your terminal:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```

### Frontend `.env`
1. Navigate to the `frontend/` directory.
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Open the `.env` file and update any required variables (e.g., `VITE_API_BASE_URL` pointing to your Django backend).

---

## 2. Backend Setup (Django)

The backend is built with Django, Django REST Framework, and integrates with Google Generative AI.

1. Open a terminal in the root directory of the project.
2. (Optional but recommended) Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```
3. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Ensure your PostgreSQL server is running and the database specified in your `.env` file exists.
5. Apply database migrations to create the necessary tables:
   ```bash
   python manage.py migrate
   ```
6. **Create a Superuser**: A superuser has full administrative privileges over the application. You'll need this to access the Django Admin panel. Run the following command and follow the prompts to set a username, email, and password:
   ```bash
   python manage.py createsuperuser
   ```
7. Start the Django development server:
   ```bash
   python manage.py runserver
   ```
   The backend should now be running on `http://127.0.0.1:8000/`.

8. **Access the Admin Panel**: With the development server running, navigate to [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin) in your browser. Log in using the superuser credentials you created in Step 6 to view and manage your data.

---

## 3. Frontend Setup (React + Vite)

The frontend is a React application built with Vite and MUI.

1. Open a **new** terminal window and navigate to the `frontend` directory:
   ```bash
   cd frontend
   ```
2. Install the Node.js dependencies:
   ```bash
   npm install
   ```
3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   The frontend should now be running, typically on `http://localhost:5173/`.

---

## Troubleshooting

- **Database Issues**: Make sure PostgreSQL is installed, the service is running, and the credentials in your `.env` exactly match your local postgres setup.
- **API Errors**: Ensure your `GEMINI_API_KEY` is valid and has the correct permissions. 
- **CORS Errors**: If you encounter CORS errors on the frontend, check that `Django_CORS_ALLOWED_ORIGINS` in your `.env` matches your Vite dev server URL.

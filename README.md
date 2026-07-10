# Bank Converter Project

## Overview
The Bank Converter project is a full-stack application designed to process and analyze bank statements. It provides a user-friendly interface for uploading and managing financial data, while leveraging a robust backend for data processing and storage. This project is ideal for showcasing your skills in modern web development, including React, TypeScript, FastAPI, and database management.

---

## Features

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: FastAPI Users for user management
- **Data Parsing**: Custom parsers for bank statements (e.g., Camelot for PDF parsing)
- **Asynchronous Processing**: Asyncio for efficient data handling
- **Migrations**: Alembic for database schema management

### Frontend
- **Framework**: React with TypeScript
- **Styling**: TailwindCSS for modern and responsive design
- **State Management**: React Context API
- **Routing**: React Router for navigation
- **Data Visualization**: Recharts for interactive charts
- **Build Tool**: Vite for fast development and optimized builds

---

## Project Structure

### Backend
Located in the `backend/` directory, the backend handles all server-side logic, including:
- **API Endpoints**: Defined in `main.py`
- **Database Models**: Defined in `models.py`
- **Authentication**: Managed in `auth.py`
- **Data Parsing**: Implemented in `parser.py` and `other_parsers/`
- **Migrations**: Managed with Alembic in `alembic/`

### Frontend
Located in the `frontend/` directory, the frontend provides the user interface, including:
- **Pages**: Defined in `src/pages/`
- **Components**: Reusable UI components in `src/components/`
- **Styles**: Global and component-specific styles in `src/styles/`
- **API Integration**: Handled in `src/api.ts`

---

## Installation

### Prerequisites
- Node.js and npm
- Python 3.10+
- PostgreSQL

### Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up the database:
   ```bash
   alembic upgrade head
   ```
5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm run dev
   ```

---

## Usage
1. Open the frontend in your browser at `http://localhost:3000`.
2. Use the interface to upload bank statements and view processed data.
3. The backend API is available at `http://localhost:8000`.

---

## Technologies Used

### Backend
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Camelot
- OpenCV
- Pandas

### Frontend
- React
- TypeScript
- TailwindCSS
- Vite
- Recharts

---

## License
This project is open-source and available under the MIT License.

---

# Airport API Service ✈️

![Python](https://img.shields.io/badge/Python-3.12-blue?style=flat&logo=python)
![Django](https://img.shields.io/badge/Django-5.0-green?style=flat&logo=django)
![Docker](https://img.shields.io/badge/Docker-Enabled-blue?style=flat&logo=docker)
[![Postgres](https://img.shields.io/badge/Postgres-%23316192.svg?logo=postgresql&logoColor=white)](#)

**Airport API Service** is a comprehensive RESTful API for managing airport infrastructure and flight operations. It allows administrators to manage resources like airplanes and crews, while providing users with functionality to search for flights and book tickets.

The project is built with Django REST Framework, fully containerized using Docker, and uses PostgreSQL as the database.

## ✨ Features

* **JWT Authentication:** Secure user registration and login.
* **Role-based Access:**
    * **Admin:** Full access to manage Airplanes, Routes, Flights, Crews, and Airports.
    * **User:** Can read flight information, manage their own orders and tickets.
* **Ticket Booking System:**
    * Automatic seat availability calculation.
    * Validation to prevent double booking or invalid seats.
* **Advanced Filtering:**
    * **Flights:** Filter by source/destination city, arrival/departure dates, and airplane ID.
    * **Routes:** Filter by min/max distance.
    * **Airplanes:** Filter by name or type.
* **Documentation:** Auto-generated Swagger & Redoc UI.

## 🛠 Technologies

* **Python 3.12**
* **Django 5 & Django REST Framework**
* **PostgreSQL**
* **Docker & Docker Compose**
* **Simple JWT** (Authentication)
* **Drf-spectacular** (Swagger / OpenAPI Documentation)

## 🚀 Getting Started

### Prerequisites

* Docker
* Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/Psychox1k/api-airport-service.git
cd api_airport_service
```


### 2. Environment Configuration
Create a .env file in the project root directory and add the following variables:

Code snippet
```
POSTGRES_DB=airport
POSTGRES_USER=airport
POSTGRES_PASSWORD=airport
POSTGRES_HOST=db
POSTGRES_PORT=5432
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```
### 3. Build and Run (Docker)
Start the application with Docker Compose:

```Bash
docker compose up --build
```


## ⚙️ Initial Setup
Once the containers are running, open a new terminal window to perform these steps.

Apply Migrations
(Usually applied automatically via entrypoint, but if needed manually):

```Bash

docker compose exec app python manage.py migrate
```
Create Superuser (Admin)
To access the Django Admin panel:

```Bash

docker compose exec app python manage.py createsuperuser
```
## Load Demo Data
Populate the database with initial data (airplanes, routes, etc.):

```Bash
docker compose exec app python manage.py loaddata airport_data.json
```
Demo Admin Credentials (if loaded from fixture):
```
login: admin@admin.com
password: admin
```

## 📚 Documentation
The project includes auto-generated API documentation. Once the server is running, you can access it here:

Swagger UI: http://127.0.0.1:8000/api/doc/swagger/

Redoc: http://127.0.0.1:8000/api/doc/redoc/

The API will be available at: http://127.0.0.1:8000/


## 🧪 Running Tests
To run the test suite inside the Docker container:

```Bash
docker compose exec app python manage.py test
```

## Developed by:
- Kyrylo Zhyhariev


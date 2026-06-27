# PetCare API

PetCare API is a Django REST Framework service for managing pet profiles and their medical records. It includes JWT-based authentication, user-specific data access, and soft delete behavior for medical records.

## Project Overview

- Framework: Django 6.0.5
- API layer: Django REST Framework
- Authentication: JWT via `djangorestframework_simplejwt`
- Database: SQLite by default, configurable through environment variables
- Primary app: `api`

## Core Models

- `User`
  - Custom user model extending Django's `AbstractUser`
  - Uses email as the login field
  - Includes `phone` and unique email validation

- `Pet`
  - Stores pet information: name, species, breed, birth date, status, owner
  - Enforces deletion rules: active pets cannot be deleted, and pets with active medical records must be cleared first

- `MedicalRecord`
  - Tracks pet care records such as vaccination, checkup, surgery, and deworming
  - Supports soft delete with `is_deleted` and `elimination_date`

## API Endpoints

- `POST /api/token/` — obtain JWT access and refresh tokens
- `POST /api/token/refresh/` — refresh JWT access token
- `POST /api/token/verify/` — verify JWT token validity
- `GET/POST /api/pets/` — list or create pets owned by the authenticated user
- `GET/PUT/PATCH/DELETE /api/pets/{id}/` — retrieve, update, or delete a pet
- `GET/POST /api/medical-records/` — list or create medical records for the user's pets
- `GET/PUT/PATCH/DELETE /api/medical-records/{id}/` — retrieve, update, or archive a medical record

## Authentication

All API routes under `/api/` require JWT authentication. The project uses `JWTAuthentication` as the default REST framework authentication class.

## Settings and Configuration

The app reads core settings from environment variables:

- `DJANGO_SECRET_KEY`
- `DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `DATABASE_ENGINE`
- `DATABASE_NAME`
- `DATABASE_USERNAME`
- `DATABASE_PASSWORD`
- `DATABASE_HOST`
- `DATABASE_PORT`

By default, SQLite is used with `db.sqlite3`.

## Requirements

Dependencies are listed in `requirements.txt` and include:

- Django
- Django REST Framework
- djangorestframework-simplejwt
- psycopg/psycopg2 for optional PostgreSQL support

## Notes

- The `Pet` deletion logic prevents removing active pets or pets with undeleted medical records.
- Medical records are archived instead of hard deleted.
- The `PetSerializer` includes nested serialized medical records for read operations.

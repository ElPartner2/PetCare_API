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
  - Enforces deletion rules: active pets and pets with any associated medical record cannot be physically deleted

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

### Query parameters

`GET /api/medical-records/` accepts:

- `pet={uuid}` — returns non-archived records for that pet. The owner restriction is always applied, so a user cannot retrieve another user's records through this filter.

### Response status codes

- `200 OK` — successful list, detail, full update, or partial update
- `201 Created` — successful pet or medical-record creation
- `204 No Content` — successful physical deletion of an eligible pet, or successful soft deletion of a medical record
- `400 Bad Request` — invalid input, including an invalid `pet` UUID or a `booster_date` earlier than `application_date`
- `401 Unauthorized` — missing or invalid JWT authentication
- `403 Forbidden` — attempted creation or reassignment of a medical record for another user's pet
- `404 Not Found` — resource does not exist, is outside the authenticated user's scope, or is an archived medical record
- `409 Conflict` — a pet cannot be deleted because it is active or has any associated medical record

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

- `MedicalRecord.pet` uses `PROTECT`. Archiving a record does not permit physical deletion of its pet; any associated record results in `409 Conflict`.
- Medical records are archived instead of hard deleted. Soft deletion preserves the row, sets `is_deleted=True`, and records `elimination_date`.
- Archived medical records are omitted from both medical-record endpoints and nested pet responses.
- `booster_date`, when supplied, must be equal to or later than the record's effective `application_date` on create, full update, and partial update.

# Order System API

A robust Django REST API for managing an e-commerce order system with user authentication, product management, and order processing.

## Features

- User Authentication with JWT
- Product Management
- Order Processing with Promo Codes
- Asynchronous Task Processing with Celery
- Containerized with Docker
- RESTful API with Django REST Framework

## Tech Stack

- Python 3.x
- Django 4.2.7
- Django REST Framework 3.14.0
- PostgreSQL
- Celery 5.3.4
- Redis 5.0.1
- Docker

## Project Structure

```
app/
├── manage.py
├── order/                 # Order management app
│   ├── models.py         # Product, Order, PromoCode models
│   ├── views.py          # API views
│   ├── serializers.py    # DRF serializers
│   ├── admin.py         # Admin configurations
│   └── tests/            # Unit tests
├── user/                 # User management app
│   ├── models.py         # CustomUser model
│   └── views.py          # User-related views
└── order_processing/     # Main project settings
    ├── settings.py
    ├── celery.py        # Celery configuration
    └── urls.py
```

## Models

### Product
- name: Product name
- price: Product price
- stock: Available quantity

### PromoCode
- Support for fixed amount and percentage-based discounts
- Time-based validity
- Maximum discount amount for percentage-based codes

### Order
- Status tracking (Pending, Shipped, Delivered, Cancelled)
- Promo code integration
- Automatic price calculation
- Order items management

## Setup

1. Clone the repository
2. Install Docker and Docker Compose
3. Build and run the containers:
   ```bash
   docker-compose up --build
   ```

## Environment Variables

Create a `.env` file with:

```
DEBUG=1
SECRET_KEY=your-secret-key
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1
SQL_ENGINE=django.db.backends.postgresql
SQL_DATABASE=your_db_name
SQL_USER=your_db_user
SQL_PASSWORD=your_db_password
SQL_HOST=db
SQL_PORT=5432

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-email-password

# Celery Configuration
CELERY_BROKER_URL=your-celery-broker-url
CELERY_RESULT_BACKEND=your-celery-result-backend
```

## Running with Docker

To run all services using Docker Compose:
```bash
docker-compose up --build
```

To run database migrations:
```bash
docker-compose exec app python manage.py migrate
```

To create a superuser:
```bash
docker-compose exec app python manage.py createsuperuser
```

To collect static files:
```bash
docker-compose exec app python manage.py collectstatic --noinput
```

To start Celery workers:
```bash
docker-compose exec app celery -A order_processing worker --loglevel=info
```

To start Celery beat scheduler:
```bash
docker-compose exec app celery -A order_processing beat --loglevel=info
```

## API Documentation

The API documentation is available at `/api/schema/swagger-ui/` when running the server.

## Testing

Run the tests using:
```bash
docker-compose exec app python manage.py test
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request


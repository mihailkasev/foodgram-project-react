# Foodgram

### Описание
- Foodgram является онлайн-сервисом, в котором пользователи могут публиковать рецепты, добавлять их в список "Избранные", подписываться на публикации других пользователей, также скачивать список продуктов, необходимых для приготовления одного или нескольких выбранных блюд. Реализован REST API для основных моделей проекта, а также система регистрации и аутентификации пользователей. Для аутентификации используются JWT-токены.
- Проект использует базу данных PostgreSQL. Проект запускается в трёх контейнерах (nginx, PostgreSQL и Django) (контейнер frontend используется лишь для подготовки файлов) через docker-compose на сервере. Образ с проектом загружается на Docker Hub.
### Технологии
- Python 3.10.7
- Django 2.2.16
- Django Rest Framework 3.12.4
- PyJWT 2.1.0
- Django-filter 2.4.0
- Python-dotenv 0.20.0
- gunicorn==20.0.4
- psycopg2-binary==2.8.6

### Бейдж

https://github.com/mihailkasev/foodgram-project-react/actions/workflows/foodgram.yml/badge.svg

### Запуск проекта 
- Клонируйте репозиторий:
```
git clone https://github.com/mihailkasev/foodgram-project-react.git
```
- Шаблон заполнения .env:
```
- DB_ENGINE=django.db.backends.postgresql
- POSTGRES_DB=postgres
- POSTGRES_USER=postgres
- POSTGRES_PASSWORD=postgres
- POSTGRES_HOST=postgres
- POSTGRES_PORT=5432
```
- Собрать и запустить контейнеры:
```
docker-compose up -d --build
```
- Запустить миграции:
```
docker-compose exec web python manage.py migrate
```
- Создать суперпользователя:
```
docker-compose exec web python manage.py createsuperuser
```
- Собрать статику:
```
docker-compose exec web python manage.py collectstatic --no-input
```
- Загрузить ингредиенты:
```
docker-compose exec web python manage.py load_ingredients
```
- Адреса сайта:
1) http://localhost/ - главная страница;
3) http://localhost/admin/ - администрирование;
4) http://localhost/api/ - API проекта;
5) http://localhost/api/docs/redoc.html - документация к API;

### Сайт http://whatsupdoggy.sytes.net/
- admin:
1) email = admin@gmail.com
2) password = admin
### Автор:
- [Михаил Касев](https://github.com/mihailkasev/)** - создание api, деплой.

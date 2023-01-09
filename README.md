## Foodgram - это...

Продуктовый помощник. Пользователи регистрируются в системе, где могут публиковать собственные рецепты блюд, подписываться на других пользователей и смотреть их рецепты, добавлять рецепты в избранное и формировать список покупок. Рецепты создаются на основе предзагруженного списка ингредиентов, на страницах с рецептами доступна фильтрация по тегам: завтрак/обед/ужин.

### Технологии
* Python 3.10
* Django 4.1.4
* Django REST framework 3.14
* React 17.0.1
* PostgreSQL
* Docker

### Юзер экспириенс
Проект запущен [ПО ЭТОЙ ССЫЛКЕ](http://aux.sytes.net)  
Пользователю с правами администратора доступна [АДМИН ЗОНА](http://aux.sytes.net/admin)  
API находится [ПО ЭТОЙ ССЫЛКЕ](http://aux.sytes.net/api)  
Документация API доступна [ПО ЭТОЙ ССЫЛКЕ](http://aux.sytes.net/api/docs/)  

##### Доступ с правами администратора
* Username: sasha
* Email: aux2@aux.aux
* Password: auxi7777

### Запуск приложения
Установите приложение Docker  
`> sudo apt install curl`  
`> curl -fsSL https://get.docker.com -o get-docker.sh`  
`> sh get-docker.sh`  

Перейдите в директорию, в которой находится docker-compose.yaml, и запустите его  
`> cd ./foodgram-project-react/infra/`  
`> docker-compose up`  

Выполните миграции и соберите статические файлы  
`> docker-compose exec backend python manage.py migrate`  
`> docker-compose exec backend python manage.py collectstatic`  

Чтобы заполнить БД данными из файла с фикстурами, выполните команду  
`> docker-compose exec backend python manage.py loaddata fixtures.json`  

### Шаблон наполнения env-файла
DB_ENGINE=django.db.backends.postgresql  
POSTGRES_DB=your_db_name  
POSTGRES_USER=your_username  
POSTGRES_PASSWORD=your_password  
DB_HOST=your_container_name  
DB_PORT=your_db_port  

### Пользовательские роли
* Аноним — может просматривать главную страницу и страницы рецептов, создавать аккаунт.  
* Аутентифицированный пользователь — может публиковать и редактировать свои рецепты, подписываться на пользователей, просматривать их рецепты, добавлять рецепты в избранное и корзину для покупок, сохранять список ингредиентов к покупке, сформированный из корзины, менять свой пароль.  
* Администратор обладает всеми правами авторизованного пользователя, а также ему доступна админ зона, где он может создавать, изменять и удалять пользователей, любые рецепты, ингредиенты и теги.  

### Ррегистрация пользователей
1. Пользователь отправляет POST-запрос с параметрами username, email, password, first_name, last_name на эндпоинт `/api/users/`.
2. Затем пользователь отправляет POST-запрос с параметрами email и password на эндпоинт `/api/auth/token/login/`, в ответе на который ему приходит auth_token. Далее токен необходимо отправлять с каждым запросом, чтобы работать с API проекта.  

### Примеры запросов и ответов API  

#### Добавление рецепта  

  `POST /api/recipes/`
##### Ответ API:

```json
{
  "ingredients": [
    {
      "id": 1123,
      "amount": 10
    }
  ],
  "tags": [
    1,
    2
  ],
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
  "name": "string",
  "text": "string",
  "cooking_time": 1
}
```
 
#### Получение информации о рецепте  

  `GET /api/recipes/{recipe_id}/`
##### Ответ API:

```json
{
  "id": 0,
  "tags": [
    {
      "id": 0,
      "name": "Завтрак",
      "color": "#E26C2D",
      "slug": "breakfast"
    }
  ],
  "author": {
    "email": "user@example.com",
    "id": 0,
    "username": "string",
    "first_name": "Вася",
    "last_name": "Пупкин",
    "is_subscribed": false
  },
  "ingredients": [
    {
      "id": 0,
      "name": "Картофель отварной",
      "measurement_unit": "г",
      "amount": 1
    }
  ],
  "is_favorited": true,
  "is_in_shopping_cart": true,
  "name": "string",
  "image": "http://foodgram.example.org/media/recipes/images/image.jpeg",
  "text": "string",
  "cooking_time": 1
}
```
#### Получение списка пользователей, на которых подписан текущий пользователь  

Для такого запроса доступна пагинация и ограничение по кол-ву рецептов пользователя.  

  `GET /api/users/subscriptions/?limit=2&page=1&recipes_limit=1`
##### Ответ API:

```json
{
  "count": 123,
  "next": "http://foodgram.example.org/api/users/subscriptions/?page=4",
  "previous": "http://foodgram.example.org/api/users/subscriptions/?page=2",
  "results": [
    {
      "email": "user@example.com",
      "id": 0,
      "username": "string",
      "first_name": "Вася",
      "last_name": "Пупкин",
      "is_subscribed": true,
      "recipes": [
        {
          "id": 0,
          "name": "string",
          "image": "http://foodgram.example.org/media/recipes/images/image.jpeg",
          "cooking_time": 1
        }
      ],
      "recipes_count": 12
    }
  ]
}
```

### Разработчики  
[Саша Смирнов](https://github.com/crush-on-anechka) - бэкенд, инфраструктура для деплоя проекта в Docker контейнерах.
[Неизвестный Герой](https://github.com/yandex-praktikum) - фронтэнд.

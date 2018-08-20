myfamily-shopping
======================

A full fledged and simple family shopping Python 3 based web project

0. Requirement
    This project is called myfamily, and the purpose is to store family shopping data and view it
    from browser.

1. Design
Backend:  MySQL + RESTful web framework
Frontend: MVVM get/post Http to backend

To handle 1 million requests, we use async in the backend, and also deploy the web in Ngnix
for static page.

2. Development
The implementation is on MacOS, it will be same as on Centos, or Ubuntu ...
2.1 Backend:
    (1) database provision: myfamily.sql is used create myfamily db and tables:
        users and shoppings

    (2) app.py and handler.py is a REST API, based on asyncio and aiohttp by
        adding @asyncio.coroutine. So in a single process, it can handle multiple requests
        without manually writing lock/unlock
        app.py works as main function.

    (3) Python code orm.py and models.py are used to map and access the users and shoppings tables.
        Since the web framework is using asyncio, the db access also needs to use aiomysql

2.2 Frontend:
    (1) uikit CSS and jQuery

    (2) use jinjia2 for the html template

    (3) use Vue.min.js for MVVM

3. Deploy
3.1 Install Myriadb (or MySQL) server, load myfamily database
    mysql -uroot -p < myfamily.sql
( you need to input password)

3.2 In Python 3 venv
    pip install aiohttp
    pip install jinja2
    pip install aiomysql

3.3 Project code structure

├── conf
│   ├── nginx
│   └── sql
└── www
    ├── apis.py
    ├── app.py
    ├── ...
    ├── orm.py
    ├── static
    │   ├── css
    │   ├── fonts
    │   └── js
    │       ├── myfamily.js
    │       └── vue.min.js
    └── templates
        ├── __base__.html
        ├── manage_shopping_edit.html
        ├── ...

4. Integration test on localhost
4.1 Server side
    in a python 3 venv terminal, python app.py

4.2 Client side, from a browser
    (1) sign in by credential as: yaohuangnt@yahoo.com / 123456
    http://127.0.0.1:9001/
    you can browse all the shoppings list

    (2) manage shopping list
    http://127.0.0.1:9001/manage/shoppings
    add / edit /delete

5. TODO
5.1 Add search feature in the web
5.2 Add dockfile for easy test

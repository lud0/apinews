# News Scraper and API

Simple Bing News scraper and API service - concept exercise.


## Tech Stack

- Django 2.1 with Django Rest Framework 3.8
- Python 3.6
- SQL database

## Azure API key

Edit `local.env` with your Azure API key (you can use a free trial API key: https://azure.microsoft.com/en-us/try/cognitive-services/). A free trial key has an hard cap of 1000 total requests and a rate limit of 3 req/s.

## Setup

Steps needed to get it up and running:

1. Prepare the virtual environment and install the modules:
```
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

2. Setup the db schemas: the default db is SQlite which requires no further setup and is well suited for demo purpose (but not for production!).
```
source local.env
./manage.py migrate
./manage.py makemigrations main
./manage.py migrate
```
To use PostgreSQL instead, edit the `local.env` file where a string specifies
the database settings using the format described: `https://github.com/kennethreitz/dj-database-url`. Also, you need a running PostgreSQL server and create an `apinews` database.

3. Run the API endpoints testing suite:
```
source local.env
./manage.py test
```

4. Run the scraper as well as the API server on port 8000
```
source local.env
./manage.py runserver --noreload
```

## Usage

Once the server is started, the scraping of an example set of queries is automatically executed via the Bing News API and data is stored in the database.
The pre-compiled queries are set in `main.fetcher.initial_scrape`, edit it at your convenience.

The data is exposed at `http://127.0.0.1:8000/` via the following API endpoints:

### API endpoints

#### News
```
GET api/v1/news
```
Returns a paginated list of all the news

* accepted query parameters:

`q=<search query>` to filter news containing the term (case insensitive)

`daterange=<start_date>-<end_date>` published news date range, where the date format is YYYYMMDD

`category=<category>` to filter only news within a given category. A list of available categories is returned in the following `api/v1/categories` endpoint

`limit=<number>` indicates the maximum number of items to return

`offset=<page offset>`  indicates the starting position of the query in relation to the complete set of unpaginated items

* examples:
```
GET http://127.0.0.1:8000/api/v1/news?category=Business
GET http://127.0.0.1:8000/api/v1/news?category=Business&daterange=20180901-20181001
GET http://127.0.0.1:8000/api/v1/news?q=spacex
```
* response:
```
GET http://127.0.0.1:8000/api/v1/news?q=spacex

{
    "count": 26,
    "next": "http://127.0.0.1:8000/api/v1/news?limit=10&offset=10&q=spacex",
    "previous": null,
    "results": [
        {
            "id": 175,
            "category": "ScienceAndTechnology",
            "date": "2018-09-28",
            "name": "Rocket Report: SpaceX gets Moon launches, South Korean rocket, BE-4 wins",
            "url": "https://arstechnica.com/science/2018/09/rocket-report-10-years-since-falcon-1-stratolaunch-engine-hybrid-rocket/",
            "content": "Welcome to Edition 1.19 of the Rocket Report! Lots of news this week about the development of rocket engines in the United States, South Korea, and elsewhere. There are also milestones for the ..."
        },
        {
            "id": 250,
            "category": "ScienceAndTechnology",
            "date": "2018-09-28",
            "name": "SpaceX Launched Falcon 1 A Decade Ago Today: Is Private Space Travel Still Viable?",
            "url": "https://www.newsweek.com/10-years-spacex-launched-falcon-1-private-space-travel-viable-1142103",
            "content": "Friday marks ten years since SpaceX launched its Falcon 1 rocket into orbit around Earth. A huge milestone for commercial space travel, this was the first time a privately-developed liquid fuel rocket had reached such a target. Although companies like ..."
        },
        ...
    }
}
```


#### Categories
```
GET api/v1/categories
```
Returns a paginated list of all the news categories available and their respective news counting

* accepted query parameters:

`limit=<number>` indicates the maximum number of items to return

`offset=<page offset>`  indicates the starting position of the query in relation to the complete set of unpaginated items


* response:
```
GET http://127.0.0.1:8000/api/v1/categories

{
    "count": 5,
    "next": null,
    "previous": null,
    "results": [
        {
            "category": "Business",
            "count": 95
        },
        {
            "category": "Entertainment",
            "count": 3
        },
        {
            "category": "ScienceAndTechnology",
            "count": 125
        },
        {
            "category": "Sports",
            "count": 50
        },
        {
            "category": "World",
            "count": 1
        }
    ]
}
```

## Code design

The Bing News scraper is spawned as an independent process upon starting the Django server (`main.fetcher.dispatcher`). It consists of an infinite loop consuming a process-safe queue containing the queries to be executed.
Each API query is delegated to a new thread. The thread executes the API request, parses the results and insert the news in the db.
A set of initial queries are inserted by the Django process in the queue to demonstrate its use (`main.fetcher.initial_scrape`).

The data is exposed via an API served by the Django server and built using the Django Rest Framework.

## Caveats and enhancements

- replace SQLite with a production db (PostgreSQL)
- add sorting parameter to API to sort exposed news
- add a POST endpoint to submit scrape requests, needs: authentication, data validation and query insertion in the `fetcher.query_queue` queue
- replace the query queue with an external service and make the scraper and the API server two independent microservices

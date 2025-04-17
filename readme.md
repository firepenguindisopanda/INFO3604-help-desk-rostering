# Help Desk Rostering & Claiming Project
The UWI DCIT Help Desk is currently managed manually, and our project aims to create a website that, with the help of a model, can generate the weekly schedules needed automate the other parts of Help Desk management.

To achieve this goal, we created a framework that can accept an optimization model to generate schedules, this framework is made in such a way that different models can be swapped in and out to deal with different situations.

Currently the Lab Assistant Sheduler model is also implemented, however only the schedule generation is set up for that at the moment.

## The Help Desk Model
This is currently the model that is being used for the Help Desk website:  

$$
\min \sum_{j}^{J} \sum_{k}^{K} \left( d_{j,k} - \sum_{i}^{I} x_{i,j} t_{i,k} \right) w_{j,k}
$$

### Subject to:

$$
\sum_{i}^{I} x_{i,j} t_{i,k} \leq d_{j,k}, \quad \text{for all } j,k \text{ pairs}
$$

$$
\sum_{j}^{J} x_{i,j} \geq 4, \quad \text{for all } i
$$

$$
\sum_{i}^{I} x_{i,j} \geq 2, \quad \text{for all } j
$$

$$
x_{i,j} \leq a_{i,j}, \quad \text{for all } i
$$



Where:  

*i* = staff index (*i* = 1 · · · *I*)  
*j* = shift index (*j* = 1 · · · *J*)  
*k* = course index (*k* = 1 · · · *K*)  
*t<sub>i,k</sub>* = 1 if staff *i* can help with course *k*, 0 otherwise  
*d<sub>j,k</sub>* = the desired number of tutors who can help with course *k* in shift *j*  
*w<sub>j,k</sub>* = a weight set by the administrator indicating how important an assignment to for course *k* is, default is *w<sub>j,k</sub>* = *d<sub>j,k<sub>*  
*a<sub>i,j</sub>* = 1 if tutor *i* is available to work shift *j*, 0 otherwise  
*x<sub>i,j</sub>* = 1 if staff *i* is assigned to shift *j*, 0 otherwise  

## The Lab Assistant Scheduler Model

$$
\max L
$$

### Subject to:

$$
L \leq \sum_{j=1}^{J} w_{i,j}x_{i,j} \quad \text{for all } i
$$

$$
x_{i,j} \leq a_{i,j} \quad \text{for all } i,j \text{ pairs}
$$

$$
\sum_{i=1}^{I} x_{i,j} \leq d_j \quad \text{for all } j
$$

$$
\sum_{j=1}^{J} x_{i,j} \leq 3(1-n_i) + n_i \quad \text{for all } i
$$

$$
\sum_{i=1}^{I} (1-n_i)x_{i,j} \geq 1 \quad \text{for all } j
$$

Where:

*i* = staff index (*i* = 1 · · · *I*)  
*j* = shift index (*j* = 1 · · · *J*)  
*d<sub>j</sub>* = the amount of staff needed for shift *j*  
*n<sub>i</sub>* = 1 if staff *i* is new, 0 otherwise  
*a<sub>i,j</sub>* = 1 if tutor *i* is available to work shift *j*, 0 otherwise  
*p<sub>i,j</sub>* = 0 ≤ *p<sub>i,j</sub>* ≤ 10, staff *i*'s preference for shift *j*  
*r<sub>i</sub>* = the amount of shifts staff *i* must vote on. Set by the administrator, generally 1 for new staff, 3 otherwise  
*w<sub>i,j</sub>* = $\frac{1}{r_i}\left(p_{i,j} - \frac{1}{J}\sum_{j=1}^{J} p_{i,j} + 5\right)$, the normalized preference of staff *i* for session *j*. These weights favor existing staff over new staff.  
*x<sub>i,j</sub>* = 1 if staff *i* is assigned to shift *j*, 0 otherwise  
*L* ∈ ℝ<sup>+</sup> the lowest sum of assigned preferences of any staff *i* over all sessions *j*  

## Startup
When the website is first opened you need to add /init to the url so the admin accounts are created, then you can login with the login info below.

## Login Information
The following accounts are created on initialization:  

**Help Desk Admin**  
Username: a  
Password: 123

**Lab Assistant Admin**  
Username: b  
Password: 123 

## Dependencies & Installation
* Python3/pip3
* Packages listed in requirements.txt

```bash
$ pip install -r requirements.txt
```

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/The-Allocators/INFO3604)
<a href="https://render.com/deploy?repo=https://github.com/uwidcit/flaskmvc">
  <img src="https://render.com/images/deploy-to-render-button.svg" alt="Deploy to Render">
</a>

![Tests](https://github.com/uwidcit/flaskmvc/actions/workflows/dev.yml/badge.svg)

# Flask MVC Template
A template for flask applications structured in the Model View Controller pattern [Demo](https://dcit-flaskmvc.herokuapp.com/). [Postman Collection](https://documenter.getpostman.com/view/583570/2s83zcTnEJ)


# Configuration Management


Configuration information such as the database url/port, credentials, API keys etc are to be supplied to the application. However, it is bad practice to stage production information in publicly visible repositories.
Instead, all config is provided by a config file or via [environment variables](https://linuxize.com/post/how-to-set-and-list-environment-variables-in-linux/).

## In Development

When running the project in a development environment (such as gitpod) the app is configured via default_config.py file in the App folder. By default, the config for development uses a sqlite database.

default_config.py
```python
SQLALCHEMY_DATABASE_URI = "sqlite:///temp-database.db"
SECRET_KEY = "secret key"
JWT_ACCESS_TOKEN_EXPIRES = 7
ENV = "DEVELOPMENT"
```

These values would be imported and added to the app in load_config() function in config.py

config.py
```python
# must be updated to inlude addtional secrets/ api keys & use a gitignored custom-config file instad
def load_config():
    config = {'ENV': os.environ.get('ENV', 'DEVELOPMENT')}
    delta = 7
    if config['ENV'] == "DEVELOPMENT":
        from .default_config import JWT_ACCESS_TOKEN_EXPIRES, SQLALCHEMY_DATABASE_URI, SECRET_KEY
        config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
        config['SECRET_KEY'] = SECRET_KEY
        delta = JWT_ACCESS_TOKEN_EXPIRES
...
```

## In Production

When deploying your application to production/staging you must pass
in configuration information via environment tab of your render project's dashboard.

![perms](./images/fig1.png)

# Flask Commands

wsgi.py is a utility script for performing various tasks related to the project. You can use it to import and test any code in the project. 
You just need create a manager command function, for example:

```python
# inside wsgi.py

user_cli = AppGroup('user', help='User object commands')

@user_cli.cli.command("create-user")
@click.argument("username")
@click.argument("password")
def create_user_command(username, password):
    create_user(username, password)
    print(f'{username} created!')

app.cli.add_command(user_cli) # add the group to the cli

```

Then execute the command invoking with flask cli with command name and the relevant parameters

```bash
$ flask user create bob bobpass
```


# Running the Project

_For development run the serve command (what you execute):_
```bash
$ flask run
```

_For production using gunicorn (what the production server executes):_
```bash
$ gunicorn wsgi:app
```

# Deploying
You can deploy your version of this app to render by clicking on the "Deploy to Render" link above.

# Initializing the Database
When connecting the project to a fresh empty database ensure the appropriate configuration is set then file then run the following command. This must also be executed once when running the app on heroku by opening the heroku console, executing bash and running the command in the dyno.

```bash
$ flask init
```

# Database Migrations
If changes to the models are made, the database must be'migrated' so that it can be synced with the new models.
Then execute following commands using manage.py. More info [here](https://flask-migrate.readthedocs.io/en/latest/)

```bash
$ flask db init
$ flask db migrate
$ flask db upgrade
$ flask db --help
```

# Testing

## Unit & Integration
Unit and Integration tests are created in the App/test. You can then create commands to run them. Look at the unit test command in wsgi.py for example

```python
@test.command("user", help="Run User tests")
@click.argument("type", default="all")
def user_tests_command(type):
    if type == "unit":
        sys.exit(pytest.main(["-k", "UserUnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "UserIntegrationTests"]))
    else:
        sys.exit(pytest.main(["-k", "User"]))
```

You can then execute all user tests as follows

```bash
$ flask test user
```

You can also supply "unit" or "int" at the end of the comand to execute only unit or integration tests.

You can run all application tests with the following command

```bash
$ pytest
```

## Test Coverage

You can generate a report on your test coverage via the following command

```bash
$ coverage report
```

You can also generate a detailed html report in a directory named htmlcov with the following comand

```bash
$ coverage html
```

# Troubleshooting

## Views 404ing

If your newly created views are returning 404 ensure that they are added to the list in main.py.

```python
from App.views import (
    user_views,
    index_views
)

# New views must be imported and added to this list
views = [
    user_views,
    index_views
]
```

## Cannot Update Workflow file

If you are running into errors in gitpod when updateding your github actions file, ensure your [github permissions](https://gitpod.io/integrations) in gitpod has workflow enabled ![perms](./images/gitperms.png)

## Database Issues

If you are adding models you may need to migrate the database with the commands given in the previous database migration section. Alternateively you can delete you database file.
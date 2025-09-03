"""WSGI entrypoint for Vercel.

Goal: keep import surface minimal so the serverless bundle excludes heavy,
optional dev/test or algorithm libraries (pytest, ortools, locust, etc.).

Heavy / dev-only imports have been moved inside CLI commands so they are
only pulled when running those commands locally, not during cold start in
the serverless environment.
"""

import sys
import click
from flask.cli import AppGroup

from App.database import get_migrate
from App.main import create_app

# This commands file allow you to create convenient CLI commands for testing controllers

app = create_app()
_migrate = get_migrate(app)  # noqa: F841 (referenced by Flask-Migrate CLI integration)

# This command creates and initializes the database
@app.cli.command("init", help="Creates and initializes the database")
def init():
    # Lazy import to avoid bundling initialization logic until needed
    from App.controllers import initialize  # local import
    initialize()
    print('database initialized')



'''
User Commands
'''
# Commands can be organized using groups
# create a group, it would be the first argument of the comand
# eg : flask user <command>
user_cli = AppGroup('user', help='User object commands') 

# Then define the command and any parameters and annotate it with the group (@)
@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
def create_user_command(username, password):
    from App.controllers import create_user  # lazy import
    create_user(username, password)
    print(f'{username} created!')

# this command will be : flask user create bob bobpass
@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    from App.controllers import get_all_users, get_all_users_json  # lazy imports
    if format == 'string':
        print(get_all_users())
    else:
        print(get_all_users_json())

app.cli.add_command(user_cli) # add the group to the cli



'''
Scheduling Commands
'''

# schedule = AppGroup('schedule', help='Scheduling algorithm commands')

# # This command will be flask schedule hdesk
# @schedule.command("help", help="Creates an optimal solution for the help desk scheduler")
# def schedule_help_desk_command():
#     print(generate_help_desk_schedule(10, 45, 1))

# app.cli.add_command(schedule) # add the group to the cli



'''
Test Commands
'''

test = AppGroup('test', help='Testing commands') 

@test.command("app", help="Run App tests")
@click.argument("type", default="all")
def app_tests_command(type):
    # Import pytest only when executing tests
    import pytest  # lazy import to keep runtime bundle small
    if type == "unit":
        sys.exit(pytest.main(["-k", "UnitTests"]))
    elif type == "int":
        sys.exit(pytest.main(["-k", "IntegrationTests"]))
    else:
        sys.exit(pytest.main([]))

app.cli.add_command(test)

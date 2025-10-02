import click, pytest, sys
from typing import Optional
from flask import Flask
from flask.cli import with_appcontext, AppGroup
from datetime import datetime

from App.database import db, get_migrate
from App.models import User
from App.main import create_app
from App.controllers import (create_user, get_all_users_json, get_all_users, initialize, 
    generate_help_desk_schedule, generate_lab_schedule)

import csv

app = create_app()
migrate = get_migrate(app)

@app.cli.command("init", help="Creates and initializes the database")
def init():
    initialize()
    print('database intialized')

# User Commands
user_cli = AppGroup('user', help='User object commands') 

@user_cli.command("create", help="Creates a user")
@click.argument("username", default="rob")
@click.argument("password", default="robpass")
def create_user_command(username, password):
    create_user(username, password)
    print(f'{username} created!')

@user_cli.command("list", help="Lists users in the database")
@click.argument("format", default="string")
def list_user_command(format):
    if format == 'string':
        print(get_all_users())
    else:
        print(get_all_users_json())

app.cli.add_command(user_cli)

# Schedule Commands

DATE_FORMAT = "%Y-%m-%d"


def _parse_date_arg(value: str, label: str) -> datetime:
    try:
        return datetime.strptime(value, DATE_FORMAT)
    except ValueError as exc:
        raise click.BadParameter(
            f"{label} must be in YYYY-MM-DD format"
        ) from exc


def _summarize_schedule(result: dict, schedule_type: str, generation_options: dict) -> str:
    details = result.get("details", {}) if isinstance(result, dict) else {}
    start = details.get("start_date", "?")
    end = details.get("end_date", "?")
    assignments = details.get("assignments_created")
    shifts = details.get("shifts_created")
    option_summary = ", ".join(f"{k}={v}" for k, v in generation_options.items()) if generation_options else "none"
    return (
        f"[{schedule_type}] Schedule {result.get('status', 'unknown')} for {start} to {end}. "
        f"Shifts: {shifts if shifts is not None else '?'} | "
        f"Assignments: {assignments if assignments is not None else '?'} | "
        f"Options: {option_summary}"
    )


schedule_cli = AppGroup('schedule', help='Help desk schedule operations')


def _validate_non_negative_option(option_name: str, value: Optional[int]):
    if value is not None and value < 0:
        label = option_name.replace("_", " ")
        raise click.BadParameter(f'{label} must be non-negative', param_hint=f'--{option_name.replace("_", "-")}')


def _validate_positive_option(option_name: str, value: Optional[int]):
    if value is not None and value <= 0:
        label = option_name.replace("_", " ")
        raise click.BadParameter(f'{label} must be greater than 0', param_hint=f'--{option_name.replace("_", "-")}')


def _validate_staff_hierarchy(minimum: Optional[int], preferred: Optional[int], maximum: Optional[int]):
    if minimum is not None and maximum is not None and minimum > maximum:
        raise click.BadParameter('minimum-staff cannot exceed maximum-staff', param_hint='--minimum-staff')
    if preferred is not None and maximum is not None and preferred > maximum:
        raise click.BadParameter('preferred-staff cannot exceed maximum-staff', param_hint='--preferred-staff')
    if minimum is not None and preferred is not None and minimum > preferred:
        raise click.BadParameter('minimum-staff cannot exceed preferred-staff', param_hint='--minimum-staff')


def _run_schedule_generation(schedule_type: str, start_dt: datetime, end_dt: datetime, quiet: bool, **options):
    if end_dt < start_dt:
        raise click.BadParameter('end_date must be on or after start_date', param_hint='end_date')

    for option_name in ('minimum_staff', 'preferred_staff', 'maximum_staff'):
        _validate_non_negative_option(option_name, options.get(option_name))

    _validate_positive_option('break_duration_minutes', options.get('break_duration_minutes'))
    _validate_positive_option('max_consecutive_hours', options.get('max_consecutive_hours'))

    _validate_staff_hierarchy(
        options.get('minimum_staff'),
        options.get('preferred_staff'),
        options.get('maximum_staff'),
    )

    generator_map = {
        'helpdesk': generate_help_desk_schedule,
        'lab': generate_lab_schedule,
    }

    generator = generator_map[schedule_type]
    filtered_options = {k: v for k, v in options.items() if v is not None}
    result = generator(start_dt, end_dt, **filtered_options)
    if not quiet:
        click.echo(_summarize_schedule(result, schedule_type, filtered_options))



@schedule_cli.command('generate-range', help='Generate schedule for an explicit date range')
@click.argument('start_date')
@click.argument('end_date')
@click.option('--schedule-type', 'schedule_type', required=True, type=click.Choice(['helpdesk', 'lab']), help='Type of schedule to generate')
@click.option('--minimum-staff', type=int, default=None, help='Minimum staff per shift')
@click.option('--preferred-staff', type=int, default=None, help='Preferred staff per shift')
@click.option('--maximum-staff', type=int, default=None, help='Maximum staff per shift')
@click.option('--break-duration-minutes', type=int, default=None, help='Break duration between shifts in minutes')
@click.option('--max-consecutive-hours', type=int, default=None, help='Maximum consecutive hours per staff member')
@click.option('--quiet', is_flag=True, help='Suppress summary output')
def generate_range_command(start_date, end_date, schedule_type, minimum_staff, preferred_staff, maximum_staff, break_duration_minutes, max_consecutive_hours, quiet):
    start_dt = _parse_date_arg(start_date, 'start_date')
    end_dt = _parse_date_arg(end_date, 'end_date')
    _run_schedule_generation(
        schedule_type,
        start_dt,
        end_dt,
        quiet,
        minimum_staff=minimum_staff,
        preferred_staff=preferred_staff,
        maximum_staff=maximum_staff,
        break_duration_minutes=break_duration_minutes,
        max_consecutive_hours=max_consecutive_hours,
    )


@schedule_cli.command('generate', help='Generate schedule with optional parameters')
@click.option('--schedule-type', 'schedule_type', required=True, type=click.Choice(['helpdesk', 'lab']), help='Type of schedule to generate')
@click.option('--start-date', 'start_date', required=True, help='Start date (YYYY-MM-DD)')
@click.option('--end-date', 'end_date', required=True, help='End date (YYYY-MM-DD)')
@click.option('--minimum-staff', type=int, default=None, help='Minimum staff per shift')
@click.option('--preferred-staff', type=int, default=None, help='Preferred staff per shift')
@click.option('--maximum-staff', type=int, default=None, help='Maximum staff per shift')
@click.option('--break-duration-minutes', type=int, default=None, help='Break duration between shifts in minutes')
@click.option('--max-consecutive-hours', type=int, default=None, help='Maximum consecutive hours per staff member')
@click.option('--quiet', is_flag=True, help='Suppress summary output')
def generate_command(schedule_type, start_date, end_date, minimum_staff, preferred_staff, maximum_staff, break_duration_minutes, max_consecutive_hours, quiet):
    start_dt = _parse_date_arg(start_date, 'start_date')
    end_dt = _parse_date_arg(end_date, 'end_date')
    _run_schedule_generation(
        schedule_type,
        start_dt,
        end_dt,
        quiet,
        minimum_staff=minimum_staff,
        preferred_staff=preferred_staff,
        maximum_staff=maximum_staff,
        break_duration_minutes=break_duration_minutes,
        max_consecutive_hours=max_consecutive_hours,
    )


app.cli.add_command(schedule_cli)

# Seed Helpers

def _seed_courses(limit=None):
    from App.controllers.course import create_course, get_all_course_codes
    added = 0
    existing = set(get_all_course_codes())
    with open('sample/courses.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['code'] in existing:
                continue
            create_course(code=row['code'], name=row['name'])
            added += 1
            existing.add(row['code'])
            if limit and added >= limit:
                break
    return added

def _seed_helpdesk(count=None):
    from App.controllers.student import create_student, get_student
    from App.controllers.help_desk_assistant import create_help_desk_assistant, get_help_desk_assistant
    from App.controllers.availability import create_availability
    from App.controllers.course import create_course_capability
    from datetime import time

    with open('sample/help_desk_assistants.csv', newline='') as f:
        rows = list(csv.DictReader(f))
    if count:
        rows = rows[:count]
    usernames = {r['username'] for r in rows}

    created_students = 0
    created_assistants = 0
    for r in rows:
        if not get_student(r['username']):
            create_student(r['username'], r['password'], r['degree'], r['name'])
            created_students += 1
        if not get_help_desk_assistant(r['username']):
            create_help_desk_assistant(r['username'])
            created_assistants += 1

    with open('sample/help_desk_assistants_availability.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['username'] in usernames:
                sh, sm, ss = map(int, row['start_time'].split(':'))
                eh, em, es = map(int, row['end_time'].split(':'))
                # Skip creation if availability already exists for that exact slot
                from App.models import Availability
                exists = Availability.query.filter_by(username=row['username'], day_of_week=int(row['day_of_week']), start_time=f"{sh:02d}:{sm:02d}:{ss:02d}", end_time=f"{eh:02d}:{em:02d}:{es:02d}").first()
                if not exists:
                    create_availability(row['username'], int(row['day_of_week']), time(sh, sm, ss), time(eh, em, es))

    with open('sample/help_desk_assistants_courses.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['username'] in usernames:
                from App.models import CourseCapability
                exists = CourseCapability.query.filter_by(assistant_username=row['username'], course_code=row['code']).first()
                if not exists:
                    create_course_capability(row['username'], row['code'])

    return {'students': created_students, 'assistants': created_assistants}


def _seed_lab(count=None):
    from App.controllers.student import create_student, get_student
    from App.controllers.lab_assistant import create_lab_assistant, get_lab_assistant
    from App.controllers.availability import create_availability
    from datetime import time

    with open('sample/lab_assistants.csv', newline='') as f:
        rows = list(csv.DictReader(f))
    if count:
        rows = rows[:count]
    usernames = {r['username'] for r in rows}

    created_students = 0
    created_lab = 0
    for r in rows:
        if not get_student(r['username']):
            create_student(r['username'], r['password'], r['degree'], r['name'])
            created_students += 1
        if not get_lab_assistant(r['username']):
            create_lab_assistant(r['username'], r.get('experience', ''))
            created_lab += 1

    with open('sample/lab_assistants_availability.csv', newline='') as f:
        for row in csv.DictReader(f):
            if row['username'] in usernames:
                sh, sm, ss = map(int, row['start_time'].split(':'))
                eh, em, es = map(int, row['end_time'].split(':'))
                from App.models import Availability
                exists = Availability.query.filter_by(username=row['username'], day_of_week=int(row['day_of_week']), start_time=f"{sh:02d}:{sm:02d}:{ss:02d}", end_time=f"{eh:02d}:{em:02d}:{es:02d}").first()
                if not exists:
                    create_availability(row['username'], int(row['day_of_week']), time(sh, sm, ss), time(eh, em, es))

    return {'students': created_students, 'lab_assistants': created_lab}

seed_cli = AppGroup('seed', help='Seed sample data partially')

@seed_cli.command('courses')
@click.option('--limit', type=int, default=None, help='Limit number of courses')
def seed_courses_cmd(limit):
    added = _seed_courses(limit)
    print(f'Seeded {added} courses')

@seed_cli.command('helpdesk')
@click.option('--count', type=int, default=None, help='Number of help desk assistants to seed')
def seed_helpdesk_cmd(count):
    added = _seed_helpdesk(count)
    print(f'Seeded {added} help desk assistants')

@seed_cli.command('lab')
@click.option('--count', type=int, default=None, help='Number of lab assistants to seed')
def seed_lab_cmd(count):
    added = _seed_lab(count)
    print(f'Seeded {added} lab assistants')

@seed_cli.command('reset')
@click.option('--type', type=click.Choice(['helpdesk', 'lab', 'all']), default='all', help='Which sample data to remove')
def seed_reset_cmd(type):
    from App.database import db
    from App.models import Student, HelpDeskAssistant, CourseCapability, Availability

    def _usernames_from_csv(path):
        with open(path, newline='') as f:
            return {r['username'] for r in csv.DictReader(f)}

    targets = set()
    if type in ('helpdesk', 'all'):
        targets |= _usernames_from_csv('sample/help_desk_assistants.csv')
    if type in ('lab', 'all'):
        targets |= _usernames_from_csv('sample/lab_assistants.csv')

    # Delete availability
    del_avail = Availability.__table__.delete().where(Availability.username.in_(list(targets)))
    res_a = db.session.execute(del_avail)
    # Delete course capabilities
    from App.models import CourseCapability as CC
    del_caps = CC.__table__.delete().where(CC.assistant_username.in_(list(targets)))
    res_c = db.session.execute(del_caps)
    # Delete assistants
    from App.models import HelpDeskAssistant as HDA
    del_hda = HDA.__table__.delete().where(HDA.username.in_(list(targets)))
    res_h = db.session.execute(del_hda)
    # Delete students (and users via inheritance)
    from App.models import Student as ST
    del_students = ST.__table__.delete().where(ST.username.in_(list(targets)))
    res_s = db.session.execute(del_students)

    db.session.commit()
    print(f'Removed sample data for {len(targets)} usernames (avail:{res_a.rowcount}, caps:{res_c.rowcount}, hda:{res_h.rowcount}, students:{res_s.rowcount})')

app.cli.add_command(seed_cli)

# Test Commands

test_cli = AppGroup('test', help='Testing commands')

@test_cli.command('app', help='Run tests (all/unit/int)')
@click.argument('type', default='all')
def run_tests(type):
    if type == 'unit':
        sys.exit(pytest.main(['-k', 'UnitTests']))
    elif type == 'int':
        sys.exit(pytest.main(['-k', 'IntegrationTests']))
    else:
        sys.exit(pytest.main([]))

app.cli.add_command(test_cli)
[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/firepenguindisopanda/INFO3604-help-desk-rostering)

![Tests](https://github.com/firepenguindisopanda/INFO3604-help-desk-rostering/actions/workflows/dev.yml/badge.svg)

# Help Desk Rostering & Claiming Project

## Overview
The UWI DCIT Help Desk is currently managed manually, and our project aims to create a website that, with the help of a model, can generate the weekly schedules needed automate the other parts of Help Desk management.

To achieve this goal, we created a framework that can accept an optimization model to generate schedules, this framework is made in such a way that different models can be swapped in and out to deal with different situations.

Currently the Lab Assistant Sheduler model is also implemented, however only the schedule generation is optimised for that at the moment.

## Key Features
- Automated schedule generation using optimization models.
- Role-based access for admins and students.
- Time tracking with clock-in/clock-out functionality.
- Notification system for shift approvals, missed shifts, etc.
- PDF generation for attendance and schedule reports.

## Standalone Linear Programming Scheduler
In addition to the in-app OR-Tools model, the repository now includes a
framework-agnostic mixed-integer linear programming module under
`scheduler_lp/`. It exposes typed helper classes (`Assistant`, `Shift`,
`CourseDemand`, etc.) plus a `solve_helpdesk_schedule` function powered by
[PuLP](https://coin-or.github.io/pulp/). The module is designed for quick
experiments in notebooks or scripts without needing to stand up the Flask app.

To try it out, install requirements and run the included demo:

```powershell
python -m scheduler_lp.examples
```

The script prints assignments, hour totals, and shortfall diagnostics for a
small synthetic instance, demonstrating the expected data structures for your
own experiments. If you prefer a notebook workflow, open
`notebooks/scheduler_lp_colab_demo.ipynb` locally or upload it to Google Colab
and follow the embedded steps to install dependencies and pull the latest
module files from GitHub.

## The Help Desk Model
This is currently the model that is being used for the Help Desk website:  

$$
\min \sum_{j}^{J} \sum_{k}^{K} \left( d_{j,k} - \sum_{i}^{I} x_{i,j} t_{i,k} \right) w_{j,k}
$$

Subject to:

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

Subject to:

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

## Development Setup

### Prerequisites
- Python 3.9+ and pip3
- Git
- A code editor

### 1. Clone and Setup Virtual Environment

```bash
# Clone the repository
git clone https://github.com/firepenguindisopanda/INFO3604-help-desk-rostering
cd help-desk-rostering

# Create and activate virtual environment (recommended)
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment (.env)

- Copy `.env.example` to `.env` and edit values.
- The app loads environment variables at startup (python-dotenv).
- Database precedence (first non-empty wins): `DATABASE_URI_SQLITE`, `DATABASE_URI_POSTGRES_LOCAL`, `DATABASE_URI_NEON`, `DATABASE_URL`, then `SQLALCHEMY_DATABASE_URI`.

Examples (Windows PowerShell):

```powershell
$env:DATABASE_URI_POSTGRES_LOCAL = "postgresql://postgres:password@localhost:5432/helpdesk"
$env:SECRET_KEY = "dev-secret"
flask --app wsgi run
```

Or place these in `.env`:

```
FLASK_APP=wsgi.py
SECRET_KEY=dev-secret
DATABASE_URI_POSTGRES_LOCAL=postgresql://postgres:password@localhost:5432/helpdesk
```

### 3. Environment Configuration

Create a `.env` file in the root directory (optional - defaults will be used if not provided):

```env
# Database Configuration
DATABASE_URI_SQLITE=sqlite:///instance/temp-database.db
SECRET_KEY=your-secret-key-here

# Development settings
FLASK_DEBUG=True
FLASK_RUN_PORT=8080

# Seeding Controls
# Set to true (or 1/yes) to skip loading sample help desk assistant
# users, their availability and course capability data. So real users can
# register themselves via the registration page.
SKIP_HELP_DESK_SAMPLE=true
```

### 4. Database Setup with Migrations

The project uses Flask-Migrate for database schema management. Follow these steps to set up the database:

```bash
# Initialize the migration repository (only needed once)
flask db init

# Create your first migration based on current models
flask db migrate -m "Initial migration"

# Apply the migration to create database tables
flask db upgrade

# Initialize the database with sample data
flask init
```

### 5. Running the Application

```bash
# Start the development server
flask run
```

The application will be available at `http://localhost:8080`

### 6. Initial Setup and Login

After starting the application:

1. Use one of the admin accounts to log in:

**Help Desk Admin:**
- Username: `a`
- Password: `123`

**Lab Assistant Admin:**
- Username: `b`  
- Password: `123`

If you enabled `SKIP_HELP_DESK_SAMPLE=true` only the two admin accounts (and any lab assistant sample data) will exist; no help desk assistants or their availability/course capability rows will be pre-populated so new testers can self‑register.

### Database Migration Workflow

When you make changes to the models, follow this workflow:

```bash
# Create a new migration after changing models
flask db migrate -m "Description of your changes"

# Review the generated migration file in migrations/versions/
# Edit if necessary, then apply the migration
flask db upgrade

# To rollback a migration if needed
flask db downgrade

# To view migration history
flask db history
```

### Common Development Commands

```bash
# Run all tests
pytest

# Run specific test types
flask test app          # All app tests
flask test app unit     # Unit tests only
flask test app int      # Integration tests only

# Create a new user (for testing)
flask user create <username> <password>

# List all users
flask user list

# Database utilities
flask db --help         # View all database commands
```

### Project Structure

```
App/
├── controllers/        # Business logic and data operations
├── models/            # Database models (SQLAlchemy)
├── views/             # Flask routes and view functions
├── templates/         # Jinja2 HTML templates
├── static/           # CSS, JS, images
├── tests/            # Unit and integration tests
└── utils/            # Helper functions

migrations/           # Database migration files
sample/              # Sample CSV data for initialization
```

### Troubleshooting

**Database Issues:**
- If you encounter database errors, try: `flask db upgrade`
- For fresh start: Delete `instance/temp-database.db` and re-run migration commands
- Check your DATABASE_URI configuration in `.env` or use default SQLite

**Migration Issues:**
- If migrations seem out of sync: `flask db stamp head` (use with caution)
- To create migration from scratch: Delete `migrations/` folder and start over with `flask db init`

**Port Issues:**
- If port 8080 is in use, set `FLASK_RUN_PORT=<another-port>` in `.env`

### Additional Notes

- The application uses SQLite by default for development
- Sample data is loaded from CSV files in the `sample/` directory
- The optimization models use linear programming for schedule generation
- JWT authentication is used with cookie-based sessions

## Testing

### Unit & Integration
You can run all application tests with the following command

```bash
$ pytest
```

Alternatively, you can run all app tests with the following commands

```bash
$ flask test app
$ flask test app unit # Run unit tests only
$ flask test app int # Run integration tests only
```

### Performance Testing
To run the performance tests, you can use the following command

```bash
$ locust -f App/tests/test_performance.py --host={host_url}
$ locust -f App/tests/test_performance.py --host=http://info3604.onrender.com # production
$ locust -f App/tests/test_performance.py --host=http://localhost:808 # development
```

The locust web dashboard can then be accessed through the following

```
http://localhost:8089
```


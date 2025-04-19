[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/The-Allocators/INFO3604)

![Tests](https://github.com/uwidcit/flaskmvc/actions/workflows/dev.yml/badge.svg)

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

## Dependencies & Installation
* Python3/pip3
* Packages listed in requirements.txt

When opening the project for the first time run the following command:

```bash
$ pip install -r requirements.txt
```

## Running the Project
When opening the project initialise the database and then run using the flask commands:

```bash
$ flask init
$ flask run
```

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


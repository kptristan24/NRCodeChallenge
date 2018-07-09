As a Python Agent engineer, it's often part of your job to reverse engineer and
debug unfamiliar code.

For this challenge, you are a maintainer of the [fuzzy worker](fuzzy_worker.py)
library. A user has recently reported a problem in your library where their
application crashes when using the `fuzzy_worker.FuzzyWorker` worker class in
gunicorn. You have been assigned to find and patch the problem.

The user has managed to create a reproduction of the crash ([p2.py](p2.py)) and
has enclosed the following detailed instructions to set it up.

Please submit:
1. A brief writeup in the form of a text file (as few as 3-4 sentences is
   sufficient) of the bug in the fuzzy worker that's causing the crash.
2. Attach a python file or diff containing a proposed bugfix for fuzzy worker.
   The proposed bugfix should _not_ contain any modifications to
   [p2.py](p2.py).


## FuzzyWorker crash
### Requirements
- [Python 3](https://www.python.org/downloads/)
- [PIP](https://pip.pypa.io/en/stable/installing/)

### Setup
- `pip3 install gunicorn==19.9.0`

### Usage
#### WSGIref (no crash)
1. `python3 p2.py`
2. Access 127.0.0.1:8000 through your web browser (or curl)

#### Gunicorn default worker (no crash)
1. `gunicorn p2:application`
2. Access 127.0.0.1:8000 through your web browser (or curl)

#### GunicornWebWorker (crash)
1. `gunicorn p2:application --worker-class fuzzy_worker.FuzzyWorker`
2. Access 127.0.0.1:8000 through your web browser (or curl)

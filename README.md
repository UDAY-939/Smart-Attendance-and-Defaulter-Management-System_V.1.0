# AttendWise — Student Attendance & Defaulter Management

Flask + MySQL starter application based on the provided ER diagram.

## Included
- Student and faculty registration, login, logout, password hashing.
- Admin account bootstrap from environment variables (no public admin registration).
- Admin can create classes and subjects, assign faculty to lecture/practical slots, and enable/disable users and slots.
- Faculty can mark attendance only for their assigned active slots.
- Student dashboard calculates subject-wise and overall attendance; below 75% is a defaulter.
- Attendance rows are unique per student/session; editing attendance updates the existing row.
- Light, responsive Bootstrap interface.

## Data-model decisions
`TeachingSlot` links class + subject + faculty + lecture/practical type. `Session` is a dated occurrence of a slot. `Attendance` links a student to a session with present/absent status. Summary counts and percentage are calculated rather than stored, avoiding stale duplicate data. Overall percentage is weighted by session counts (total present sessions / total sessions), not an average of subject percentages.

## Run locally on Windows
1. Install Python 3.10+ and MySQL 8+.
2. In MySQL run:
   ```sql
   CREATE DATABASE attendance_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   CREATE USER 'attendance_user'@'localhost' IDENTIFIED BY 'choose_a_strong_password';
   GRANT ALL PRIVILEGES ON attendance_db.* TO 'attendance_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. Copy `.env.example` to `.env`. Edit `DATABASE_URL`, `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`. Keep `.env` private.
4. In the project directory:
   ```powershell
   py -m venv .venv
   .venv\\Scripts\\Activate.ps1
   pip install -r requirements.txt
   python run.py
   ```
5. Visit http://127.0.0.1:5000 and log in with the admin credentials from `.env`.
6. Admin creates class and subject. Register faculty, assign faculty to lecture/practical slots, then register students into the created class.

## Host online
1. Push code to GitHub; do not commit `.env`.
2. Create a managed MySQL database with persistent storage and remote connectivity.
3. Deploy as a Python web service. Build command: `pip install -r requirements.txt`; start command: `gunicorn run:app`.
4. Configure `DATABASE_URL`, a long random `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in the hosting environment settings. Ensure the web host is allowed to connect to MySQL, and enable TLS if supported.
5. Test account roles, slot restrictions, attendance editing, and percentage calculations. Remove/rotate bootstrap admin credentials after the admin has been created.

Provider free plans change; check persistence, backup, connectivity, and sleep/expiry limits. Do not use real student data until you add CSRF protection, admin approval/email verification, audit logs, migrations, rate limiting, automated tests, secure cookie settings, and a verified backup/restore process.
"# attendance-defaulter-system" 

# Smart-Attendance-and-Defaulter-Management-System_V.1.0
A web-based attendance management system built with Python Flask and MySQL to track student attendance and automatically identify defaulters below 75% attendance.

# AttendWise — Student Attendance & Defaulter Management

Flask + MySQL starter application based on the provided ER diagram.

## Included
- Student and faculty registration, login, logout, password hashing.
- Admin account bootstrap from environment variables (no public admin registration).
- Admin can create classes and subjects, assign faculty to lecture/practical slots, and enable/disable users and slots.
- Faculty can mark attendance only for their assigned active slots.
- Student dashboard calculates subject-wise and overall attendance; below 75% is a defaulter.
- Attendance rows are unique per student/session; editing attendance updates the existing row.
- Light, responsive Bootstrap interface.

## Data-model decisions
`TeachingSlot` links class + subject + faculty + lecture/practical type. `Session` is a dated occurrence of a slot. `Attendance` links a student to a session with present/absent status. Summary counts and percentage are calculated rather than stored, avoiding stale duplicate data. Overall percentage is weighted by session counts (total present sessions / total sessions), not an average of subject percentages.

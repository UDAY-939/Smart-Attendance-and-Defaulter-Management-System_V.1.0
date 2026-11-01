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

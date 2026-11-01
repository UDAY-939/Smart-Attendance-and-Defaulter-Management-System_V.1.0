from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db, login_manager

class User(UserMixin, db.Model):
    __tablename__='users'
    id=db.Column(db.Integer, primary_key=True)
    name=db.Column(db.String(120), nullable=False)
    email=db.Column(db.String(190), unique=True, nullable=False, index=True)
    password_hash=db.Column(db.String(255), nullable=False)
    role=db.Column(db.String(20), nullable=False)
    active=db.Column(db.Boolean, nullable=False, default=True)
    student=db.relationship('Student', uselist=False, back_populates='user')
    faculty=db.relationship('Faculty', uselist=False, back_populates='user')
    def set_password(self, value): self.password_hash=generate_password_hash(value)
    def check_password(self, value): return check_password_hash(self.password_hash, value)

@login_manager.user_loader
def load_user(uid): return db.session.get(User, int(uid))

class ClassRoom(db.Model):
    __tablename__='classes'
    id=db.Column(db.Integer, primary_key=True)
    class_name=db.Column(db.String(80), nullable=False)
    division=db.Column(db.String(30), nullable=False, default='A')

    @property
    def students_count(self):
        return Student.query.filter_by(class_id=self.id).count()

    @property
    def slots_count(self):
        return TeachingSlot.query.filter_by(class_id=self.id).count()

class Student(db.Model):
    __tablename__='students'
    roll_no=db.Column(db.String(30), primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    class_id=db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    user=db.relationship('User', back_populates='student')
    classroom=db.relationship('ClassRoom')
    attendance=db.relationship('Attendance', back_populates='student')

class Faculty(db.Model):
    __tablename__='faculty'
    id=db.Column(db.Integer, primary_key=True)
    user_id=db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    user=db.relationship('User', back_populates='faculty')

class Subject(db.Model):
    __tablename__='subjects'
    code=db.Column(db.String(30), primary_key=True)
    name=db.Column(db.String(120), nullable=False)

    @property
    def slots_count(self):
        return TeachingSlot.query.filter_by(subject_code=self.code).count()

class TeachingSlot(db.Model):
    __tablename__='teaching_slots'
    id=db.Column(db.Integer, primary_key=True)
    subject_code=db.Column(db.String(30), db.ForeignKey('subjects.code'), nullable=False)
    class_id=db.Column(db.Integer, db.ForeignKey('classes.id'), nullable=False)
    faculty_id=db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    slot_type=db.Column(db.String(20), nullable=False)
    slot_name=db.Column(db.String(100), nullable=False)
    lecture_time=db.Column(db.String(50), nullable=True, default='10:00 AM - 11:00 AM')
    active=db.Column(db.Boolean, nullable=False, default=True)
    subject=db.relationship('Subject')
    classroom=db.relationship('ClassRoom')
    faculty=db.relationship('Faculty')

class Session(db.Model):
    __tablename__='sessions'
    id=db.Column(db.Integer, primary_key=True)
    slot_id=db.Column(db.Integer, db.ForeignKey('teaching_slots.id'), nullable=False)
    session_date=db.Column(db.Date, nullable=False, default=date.today)
    lecture_time=db.Column(db.String(50), nullable=True, default='10:00 AM - 11:00 AM')
    topic=db.Column(db.String(200))
    slot=db.relationship('TeachingSlot')
    attendance=db.relationship('Attendance', back_populates='session', cascade='all, delete-orphan')
    __table_args__=(db.UniqueConstraint('slot_id','session_date','lecture_time',name='uq_slot_date_time'),)

class Attendance(db.Model):
    __tablename__='attendance'
    id=db.Column(db.Integer, primary_key=True)
    session_id=db.Column(db.Integer, db.ForeignKey('sessions.id'), nullable=False)
    roll_no=db.Column(db.String(30), db.ForeignKey('students.roll_no'), nullable=False)
    status=db.Column(db.String(10), nullable=False)
    marked_by=db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    marked_at=db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    session=db.relationship('Session', back_populates='attendance')
    student=db.relationship('Student', back_populates='attendance')
    __table_args__=(db.UniqueConstraint('session_id','roll_no',name='uq_session_student'), db.CheckConstraint("status IN ('present','absent')", name='ck_attendance_status'))

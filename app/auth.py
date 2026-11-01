import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from . import db
from .models import User, Student, Faculty, ClassRoom

bp = Blueprint('auth', __name__)

ALLOWED_EMAIL_DOMAINS = ('gmail.com', 'college.edu', 'outlook.com', 'yahoo.com', 'hotmail.com', 'icloud.com')
ALLOWED_DOMAIN_SUFFIXES = ('.college.edu', '.edu', '.edu.in', '.ac.in')

def validate_email_domain(email_str):
    """
    Validates that an email is well-formed and belongs to an approved domain
    (e.g., @gmail.com, @college.edu, @outlook.com, or educational domains ending with .edu or .ac.in).
    Returns (is_valid: bool, error_message: str).
    """
    if not email_str or not isinstance(email_str, str):
        return False, 'Email address is required.'

    email_clean = email_str.strip().lower()
    email_pattern = r'^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$'
    match = re.match(email_pattern, email_clean)
    if not match:
        return False, 'Please enter a valid email format (e.g., user@gmail.com or prof@college.edu).'

    domain = match.group(1).lower()
    is_allowed = (
        domain in ALLOWED_EMAIL_DOMAINS or
        any(domain.endswith(suffix) for suffix in ALLOWED_DOMAIN_SUFFIXES)
    )

    if not is_allowed:
        return False, f"Domain '@{domain}' is not accepted. Please use an official email ending in @gmail.com, @college.edu, .edu, or .ac.in."

    return True, ''

@bp.route('/login')
def login_portal():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.dashboard'))
    return render_template('login_portal.html')

@bp.route('/login/<role>', methods=['GET', 'POST'])
def login(role='student'):
    if role not in ('student', 'faculty', 'admin'):
        return redirect(url_for('auth.login_portal'))

    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.index'))
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '')

        if not identifier or not password:
            flash('Please enter both your identifier and password.', 'warning')
            return render_template('login.html', role=role, identifier=identifier)

        # Validation for email domain
        if role in ('faculty', 'admin') or '@' in identifier:
            is_valid, err = validate_email_domain(identifier)
            if not is_valid:
                flash(err, 'warning')
                return render_template('login.html', role=role, identifier=identifier)
        else:
            # Student logging in with Roll Number
            if not re.match(r'^[A-Za-z0-9\-_/]+$', identifier):
                flash('Please enter a valid Roll Number (alphanumeric, hyphens) or email address.', 'warning')
                return render_template('login.html', role=role, identifier=identifier)

        user = None
        # Allow student to log in using roll number OR email
        if role == 'student':
            student_record = Student.query.filter_by(roll_no=identifier).first()
            if student_record and student_record.user:
                user = student_record.user
            else:
                user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(email=identifier.lower()).first()

        if user and user.check_password(password):
            if not user.active:
                flash('Your account has been deactivated. Please contact an administrator.', 'danger')
                return render_template('login.html', role=role, identifier=identifier)

            if user.role != role:
                flash(f'Notice: This account has the role "{user.role.title()}". Please sign in via the {user.role.title()} Portal.', 'info')
                return redirect(url_for('auth.login', role=user.role))

            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            if user.role == 'admin':
                return redirect(url_for('admin.index'))
            return redirect(url_for('main.dashboard'))

        flash('Invalid credentials. Please verify your login details and try again.', 'danger')

    return render_template('login.html', role=role)

@bp.route('/register/<role>', methods=['GET', 'POST'])
def register(role):
    if role not in ('student', 'faculty'):
        return redirect(url_for('auth.login_portal'))

    classes = ClassRoom.query.order_by(ClassRoom.class_name, ClassRoom.division).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').lower().strip()
        password = request.form.get('password', '')
        roll = request.form.get('roll_no', '').strip().upper() if role == 'student' else ''
        class_id = request.form.get('class_id', type=int) if role == 'student' else None

        # 1. Name validation
        if not name or len(name) < 2:
            flash('Please enter a valid full name (minimum 2 characters).', 'warning')
            return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

        # 2. Email domain validation
        is_valid_email, email_err = validate_email_domain(email)
        if not is_valid_email:
            flash(email_err, 'warning')
            return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

        # 3. Password validation
        if not password or len(password) < 8:
            flash('Password must be at least 8 characters long.', 'warning')
            return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

        if User.query.filter_by(email=email).first():
            flash('An account with this email address already exists. Please log in.', 'warning')
            return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

        if role == 'student':
            if not roll or len(roll) < 2 or not re.match(r'^[A-Z0-9\-_/]+$', roll):
                flash('Please enter a valid Roll Number with at least 2 alphanumeric characters (e.g. 101, CS-01).', 'warning')
                return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

            classroom = db.session.get(ClassRoom, class_id) if class_id else None
            if not classroom:
                flash('Please select a valid class assigned by the administrator.', 'warning')
                return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

            if db.session.get(Student, roll):
                flash(f'Roll number "{roll}" is already registered. Please check or contact faculty.', 'warning')
                return render_template('register.html', role=role, classes=classes, name=name, email=email, roll_no=roll, class_id=class_id)

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        if role == 'student':
            db.session.add(Student(roll_no=roll, user_id=user.id, class_id=classroom.id))
        else:
            db.session.add(Faculty(user_id=user.id))

        db.session.commit()
        flash(f'Registration successful! You can now log into the {role.title()} portal.', 'success')
        return redirect(url_for('auth.login', role=role))

    return render_template('register.html', role=role, classes=classes)

@bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login_portal'))

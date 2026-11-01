from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import User, ClassRoom, Subject, Faculty, TeachingSlot, Student, Session, Attendance

bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin():
    if not current_user.is_authenticated or current_user.role != 'admin':
        abort(403)

@bp.route('/')
@login_required
def index():
    require_admin()
    users = User.query.order_by(User.role, User.name).all()
    classes = ClassRoom.query.order_by(ClassRoom.class_name, ClassRoom.division).all()
    subjects = Subject.query.order_by(Subject.code).all()
    faculty_list = Faculty.query.all()
    slots = TeachingSlot.query.all()
    sessions = Session.query.order_by(Session.session_date.desc(), Session.id.desc()).all()

    session_logs = []
    for sess in sessions:
        p_count = sum(1 for a in sess.attendance if a.status == 'present')
        a_count = sum(1 for a in sess.attendance if a.status == 'absent')
        tot = p_count + a_count
        pct = round((p_count * 100.0) / tot, 1) if tot else 0
        session_logs.append({
            'session': sess,
            'present_count': p_count,
            'absent_count': a_count,
            'total_marked': tot,
            'percentage': pct,
            'records': sess.attendance
        })
    
    stats = {
        'total_users': len(users),
        'students_count': Student.query.count(),
        'faculty_count': len(faculty_list),
        'classes_count': len(classes),
        'subjects_count': len(subjects),
        'slots_count': len(slots),
        'sessions_count': len(sessions)
    }

    return render_template('admin.html',
                           users=users,
                           classes=classes,
                           subjects=subjects,
                           faculty=faculty_list,
                           slots=slots,
                           session_logs=session_logs,
                           stats=stats)

@bp.route('/class', methods=['POST'])
@login_required
def add_class():
    require_admin()
    name = request.form.get('class_name', '').strip()
    division = request.form.get('division', 'A').strip().upper()
    if name and division:
        existing = ClassRoom.query.filter_by(class_name=name, division=division).first()
        if existing:
            flash(f'Class "{name} (Div {division})" already exists.', 'warning')
        else:
            db.session.add(ClassRoom(class_name=name, division=division))
            db.session.commit()
            flash(f'Class "{name} / Div {division}" created successfully.', 'success')
    else:
        flash('Class name and division are required.', 'warning')
    return redirect(url_for('admin.index', _anchor='classes-pane'))

@bp.route('/subject', methods=['POST'])
@login_required
def add_subject():
    require_admin()
    code = request.form.get('code', '').strip().upper()
    name = request.form.get('name', '').strip()
    if not code or not name:
        flash('Subject code and subject name are required.', 'warning')
    elif db.session.get(Subject, code):
        flash(f'Subject code "{code}" already exists.', 'warning')
    else:
        db.session.add(Subject(code=code, name=name))
        db.session.commit()
        flash(f'Subject "{code} — {name}" created successfully.', 'success')
    return redirect(url_for('admin.index', _anchor='classes-pane'))

@bp.route('/slot', methods=['POST'])
@login_required
def add_slot():
    require_admin()
    try:
        slot_type = request.form.get('slot_type', 'lecture')
        if slot_type not in ('lecture', 'practical'):
            raise ValueError('Invalid slot type')
        
        subject_code = request.form['subject_code'].strip()
        class_id = int(request.form['class_id'])
        faculty_id = int(request.form['faculty_id'])
        slot_name = request.form['slot_name'].strip()
        lecture_time = request.form.get('lecture_time', '').strip() or '10:00 AM - 11:00 AM'

        if not slot_name:
            raise ValueError('Slot name is required')

        slot = TeachingSlot(
            subject_code=subject_code,
            class_id=class_id,
            faculty_id=faculty_id,
            slot_type=slot_type,
            slot_name=slot_name,
            lecture_time=lecture_time
        )
        db.session.add(slot)
        db.session.commit()
        flash(f'Teaching slot "{slot_name}" assigned successfully with scheduled time {lecture_time}.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to assign teaching slot. Please verify subject, class, faculty, and time.', 'danger')
    return redirect(url_for('admin.index', _anchor='slots-pane'))

@bp.route('/user/<int:uid>/toggle', methods=['POST'])
@login_required
def toggle_user(uid):
    require_admin()
    user = db.session.get(User, uid)
    if user and user.role != 'admin':
        user.active = not user.active
        db.session.commit()
        status_text = 'activated' if user.active else 'disabled'
        flash(f'Account for {user.name} ({user.role.title()}) has been {status_text}.', 'success')
    return redirect(url_for('admin.index', _anchor='users-pane'))

@bp.route('/slot/<int:sid>/toggle', methods=['POST'])
@login_required
def toggle_slot(sid):
    require_admin()
    slot = db.session.get(TeachingSlot, sid)
    if slot:
        slot.active = not slot.active
        db.session.commit()
        status_text = 'activated' if slot.active else 'disabled'
        flash(f'Slot "{slot.slot_name}" has been {status_text}.', 'success')
    return redirect(url_for('admin.index', _anchor='slots-pane'))

@bp.route('/slot/<int:sid>/delete', methods=['POST'])
@login_required
def delete_slot(sid):
    require_admin()
    slot = db.session.get(TeachingSlot, sid)
    if not slot:
        flash('Teaching slot not found.', 'warning')
        return redirect(url_for('admin.index', _anchor='slots-pane'))
    
    slot_name = slot.slot_name
    try:
        # 1. Clean up sessions & attendance for this slot
        sessions = Session.query.filter_by(slot_id=slot.id).all()
        session_ids = [s.id for s in sessions]
        if session_ids:
            Attendance.query.filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
            Session.query.filter(Session.slot_id == slot.id).delete(synchronize_session=False)
        
        # 2. Delete teaching slot
        db.session.delete(slot)
        db.session.commit()
        flash(f'Teaching slot "{slot_name}" and its associated attendance records were permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete teaching slot: {str(e)}', 'danger')
    return redirect(url_for('admin.index', _anchor='slots-pane'))

@bp.route('/class/<int:cid>/delete', methods=['POST'])
@login_required
def delete_class(cid):
    require_admin()
    classroom = db.session.get(ClassRoom, cid)
    if not classroom:
        flash('Classroom not found.', 'warning')
        return redirect(url_for('admin.index', _anchor='classes-pane'))
    
    class_label = f"{classroom.class_name} (Div {classroom.division})"
    try:
        # 1. Clean up teaching slots belonging to this class
        slots = TeachingSlot.query.filter_by(class_id=classroom.id).all()
        slot_ids = [s.id for s in slots]
        if slot_ids:
            sessions = Session.query.filter(Session.slot_id.in_(slot_ids)).all()
            session_ids = [sess.id for sess in sessions]
            if session_ids:
                Attendance.query.filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
                Session.query.filter(Session.id.in_(session_ids)).delete(synchronize_session=False)
            TeachingSlot.query.filter(TeachingSlot.id.in_(slot_ids)).delete(synchronize_session=False)

        # 2. Clean up students belonging to this class (and their users + attendance)
        students = Student.query.filter_by(class_id=classroom.id).all()
        for st in students:
            Attendance.query.filter_by(roll_no=st.roll_no).delete(synchronize_session=False)
            uid = st.user_id
            db.session.delete(st)
            if uid:
                usr = db.session.get(User, uid)
                if usr:
                    db.session.delete(usr)

        # 3. Delete classroom
        db.session.delete(classroom)
        db.session.commit()
        flash(f'Classroom "{class_label}" and all linked slots and student records were permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete classroom: {str(e)}', 'danger')
    return redirect(url_for('admin.index', _anchor='classes-pane'))

@bp.route('/subject/<code>/delete', methods=['POST'])
@login_required
def delete_subject(code):
    require_admin()
    subject = db.session.get(Subject, code)
    if not subject:
        flash('Subject not found.', 'warning')
        return redirect(url_for('admin.index', _anchor='classes-pane'))
    
    subject_label = f"{subject.code} — {subject.name}"
    try:
        # 1. Clean up teaching slots belonging to this subject
        slots = TeachingSlot.query.filter_by(subject_code=subject.code).all()
        slot_ids = [s.id for s in slots]
        if slot_ids:
            sessions = Session.query.filter(Session.slot_id.in_(slot_ids)).all()
            session_ids = [sess.id for sess in sessions]
            if session_ids:
                Attendance.query.filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
                Session.query.filter(Session.id.in_(session_ids)).delete(synchronize_session=False)
            TeachingSlot.query.filter(TeachingSlot.id.in_(slot_ids)).delete(synchronize_session=False)

        # 2. Delete subject
        db.session.delete(subject)
        db.session.commit()
        flash(f'Subject "{subject_label}" and its associated teaching slots were permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete subject: {str(e)}', 'danger')
    return redirect(url_for('admin.index', _anchor='classes-pane'))

@bp.route('/user/<int:uid>/delete', methods=['POST'])
@login_required
def delete_user(uid):
    require_admin()
    if uid == current_user.id:
        flash('You cannot delete your own active administrator account.', 'danger')
        return redirect(url_for('admin.index', _anchor='users-pane'))
    
    user = db.session.get(User, uid)
    if not user:
        flash('User account not found.', 'warning')
        return redirect(url_for('admin.index', _anchor='users-pane'))
    
    user_name = user.name
    role = user.role
    try:
        if role == 'student':
            student = Student.query.filter_by(user_id=user.id).first()
            if student:
                Attendance.query.filter_by(roll_no=student.roll_no).delete(synchronize_session=False)
                db.session.delete(student)
        elif role == 'faculty':
            faculty = Faculty.query.filter_by(user_id=user.id).first()
            if faculty:
                # 1. Slots assigned to this faculty
                slots = TeachingSlot.query.filter_by(faculty_id=faculty.id).all()
                slot_ids = [s.id for s in slots]
                if slot_ids:
                    sessions = Session.query.filter(Session.slot_id.in_(slot_ids)).all()
                    session_ids = [sess.id for sess in sessions]
                    if session_ids:
                        Attendance.query.filter(Attendance.session_id.in_(session_ids)).delete(synchronize_session=False)
                        Session.query.filter(Session.id.in_(session_ids)).delete(synchronize_session=False)
                    TeachingSlot.query.filter(TeachingSlot.id.in_(slot_ids)).delete(synchronize_session=False)

                # 2. Attendance records marked by this faculty
                Attendance.query.filter_by(marked_by=faculty.id).delete(synchronize_session=False)
                db.session.delete(faculty)
        
        # 3. Delete user
        db.session.delete(user)
        db.session.commit()
        flash(f'User account "{user_name}" ({role.title()}) has been permanently deleted.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete user account: {str(e)}', 'danger')
    return redirect(url_for('admin.index', _anchor='users-pane'))

@bp.route('/session/<int:sess_id>/delete', methods=['POST'])
@login_required
def delete_session(sess_id):
    require_admin()
    sess = db.session.get(Session, sess_id)
    if not sess:
        flash('Lecture session not found.', 'warning')
        return redirect(url_for('admin.index', _anchor='sessions-pane'))
    
    date_str = sess.session_date.strftime('%d %b %Y')
    time_str = sess.lecture_time or 'Scheduled Time'
    slot_name = sess.slot.slot_name if sess.slot else 'Slot'
    try:
        Attendance.query.filter_by(session_id=sess.id).delete(synchronize_session=False)
        db.session.delete(sess)
        db.session.commit()
        flash(f'Lecture session for {slot_name} on {date_str} ({time_str}) and its attendance records were deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to delete lecture session: {str(e)}', 'danger')
    return redirect(url_for('admin.index', _anchor='sessions-pane'))

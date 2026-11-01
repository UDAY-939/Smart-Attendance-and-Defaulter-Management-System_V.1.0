import math
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from . import db
from .models import User, Student, Faculty, TeachingSlot, Session, Attendance, ClassRoom, Subject

bp = Blueprint('main', __name__)

@bp.route('/health')
def health():
    return {'status': 'ok'}

@bp.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login_portal'))
    if current_user.role == 'admin':
        return redirect(url_for('admin.index'))
    return redirect(url_for('main.dashboard'))

@bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin.index'))

    # ==========================
    # FACULTY DASHBOARD LOGIC
    # ==========================
    if current_user.role == 'faculty':
        faculty = current_user.faculty
        if not faculty:
            flash('Faculty profile not found. Please contact the administrator.', 'warning')
            return render_template('dashboard.html', role='faculty', slots_data=[], summary_stats={})

        slots = TeachingSlot.query.filter_by(faculty_id=faculty.id, active=True).all()
        slots_data = []
        total_conducted_sessions = 0
        total_defaulters_across_slots = 0
        total_students_across_slots = 0

        for slot in slots:
            # All active students in this classroom
            students = Student.query.filter_by(class_id=slot.class_id).join(User).filter(User.active.is_(True)).order_by(Student.roll_no).all()
            total_students = len(students)
            total_students_across_slots += total_students

            # All sessions conducted for this slot
            sessions = Session.query.filter_by(slot_id=slot.id).all()
            total_sessions = len(sessions)
            total_conducted_sessions += total_sessions

            defaulter_count = 0
            safe_count = 0
            total_present_sum = 0

            for student in students:
                present_count = Attendance.query.join(Session).filter(
                    Session.slot_id == slot.id,
                    Attendance.roll_no == student.roll_no,
                    Attendance.status == 'present'
                ).count()
                total_present_sum += present_count

                if total_sessions > 0:
                    pct = (present_count * 100.0) / total_sessions
                    if pct < 75.0:
                        defaulter_count += 1
                    else:
                        safe_count += 1

            slot_avg_pct = round((total_present_sum * 100.0) / (total_sessions * total_students), 1) if (total_sessions and total_students) else 0

            total_defaulters_across_slots += defaulter_count

            slots_data.append({
                'slot': slot,
                'total_students': total_students,
                'total_sessions': total_sessions,
                'defaulter_count': defaulter_count,
                'safe_count': safe_count,
                'average_percentage': slot_avg_pct,
                'lecture_time': slot.lecture_time or '10:00 AM - 11:00 AM'
            })

        summary_stats = {
            'total_slots': len(slots),
            'total_sessions': total_conducted_sessions,
            'total_defaulters': total_defaulters_across_slots
        }

        return render_template('dashboard.html',
                               role='faculty',
                               slots_data=slots_data,
                               summary_stats=summary_stats)

    # ==========================
    # STUDENT DASHBOARD LOGIC
    # ==========================
    student = current_user.student
    summaries = []
    total_sessions_all = 0
    total_present_all = 0

    if student:
        # Fetch all active slots for student's class
        slots = TeachingSlot.query.filter_by(class_id=student.class_id, active=True).all()
        # Group by subject code
        subject_codes = sorted(list(set(slot.subject_code for slot in slots)))

        for code in subject_codes:
            representative = next(s for s in slots if s.subject_code == code)
            sessions = Session.query.join(TeachingSlot).filter(
                TeachingSlot.class_id == student.class_id,
                TeachingSlot.subject_code == code,
                TeachingSlot.active.is_(True)
            ).all()

            total = len(sessions)
            present = Attendance.query.join(Session).join(TeachingSlot).filter(
                Attendance.roll_no == student.roll_no,
                Attendance.status == 'present',
                TeachingSlot.subject_code == code,
                TeachingSlot.class_id == student.class_id
            ).count()

            absent = total - present
            pct = round((present * 100.0) / total, 2) if total else 0
            is_defaulter = bool(total > 0 and pct < 75.0)

            # Calculate classes needed or buffer
            classes_needed = 0
            safe_margin = 0
            if total > 0:
                if is_defaulter:
                    # (present + x) / (total + x) >= 0.75  =>  x >= 3*total - 4*present
                    classes_needed = max(1, math.ceil(3 * total - 4 * present))
                else:
                    # present / (total + y) >= 0.75  =>  y <= (4*present - 3*total)/3
                    safe_margin = max(0, math.floor((4 * present - 3 * total) / 3))

            summaries.append({
                'subject': representative.subject.name,
                'code': code,
                'total': total,
                'attended': present,
                'absent': absent,
                'percentage': pct,
                'defaulter': is_defaulter,
                'classes_needed': classes_needed,
                'safe_margin': safe_margin
            })

            total_sessions_all += total
            total_present_all += present

    overall_pct = round((total_present_all * 100.0) / total_sessions_all, 2) if total_sessions_all else 0
    overall_defaulter = bool(total_sessions_all > 0 and overall_pct < 75.0)

    # Calculate overall classes needed to reach 75%
    overall_classes_needed = 0
    overall_safe_margin = 0
    if total_sessions_all > 0:
        if overall_defaulter:
            overall_classes_needed = max(1, math.ceil(3 * total_sessions_all - 4 * total_present_all))
        else:
            overall_safe_margin = max(0, math.floor((4 * total_present_all - 3 * total_sessions_all) / 3))

    recent_attendance = Attendance.query.filter_by(roll_no=student.roll_no).join(Session).order_by(Session.session_date.desc(), Session.id.desc()).limit(25).all()

    return render_template('dashboard.html',
                           role='student',
                           student=student,
                           summaries=summaries,
                           recent_attendance=recent_attendance,
                           overall=overall_pct,
                           overall_total=total_sessions_all,
                           overall_attended=total_present_all,
                           overall_defaulter=overall_defaulter,
                           overall_classes_needed=overall_classes_needed,
                           overall_safe_margin=overall_safe_margin)

# ==========================
# FACULTY ATTENDANCE ROUTE
# ==========================
@bp.route('/slot/<int:slot_id>/take', methods=['GET', 'POST'])
@login_required
def take_attendance(slot_id):
    if current_user.role != 'faculty' or not current_user.faculty:
        abort(403)

    slot = TeachingSlot.query.filter_by(id=slot_id, faculty_id=current_user.faculty.id, active=True).first_or_404()
    students = Student.query.filter_by(class_id=slot.class_id).join(User).filter(User.active.is_(True)).order_by(Student.roll_no).all()

    # Restriction: Attendance can only be marked for the present date (today)
    today = date.today()
    selected_date = today
    selected_date_str = today.isoformat()
    requested_date = request.values.get('session_date')
    if requested_date and requested_date != selected_date_str:
        flash('Notice: Attendance can only be recorded for today (present date). Past or future dates cannot be selected.', 'info')

    selected_time = request.values.get('lecture_time', slot.lecture_time or '10:00 AM - 11:00 AM').strip()

    # Check if a session already exists for this slot, date, and lecture time
    existing_session = Session.query.filter_by(slot_id=slot.id, session_date=selected_date, lecture_time=selected_time).first()
    
    # If not found by lecture_time, check if there's a session for that date (migration backwards compatibility)
    if not existing_session:
        existing_session = Session.query.filter_by(slot_id=slot.id, session_date=selected_date).first()

    existing_attendance = {}
    topic_value = ''
    if existing_session:
        topic_value = existing_session.topic or ''
        for att in existing_session.attendance:
            existing_attendance[att.roll_no] = att.status

    # Compute current overall standing for each student in this slot so faculty sees who is currently a defaulter
    total_slot_sessions = Session.query.filter_by(slot_id=slot.id).count()
    student_rows = []
    for s in students:
        attended = Attendance.query.join(Session).filter(
            Session.slot_id == slot.id,
            Attendance.roll_no == s.roll_no,
            Attendance.status == 'present'
        ).count()
        current_pct = round((attended * 100.0) / total_slot_sessions, 1) if total_slot_sessions else 100.0
        is_defaulter = bool(total_slot_sessions > 0 and current_pct < 75.0)

        # Pre-select status: existing if recorded, otherwise 'present' by default
        status = existing_attendance.get(s.roll_no, 'present')

        student_rows.append({
            'student': s,
            'attended': attended,
            'percentage': current_pct,
            'is_defaulter': is_defaulter,
            'current_status': status
        })

    # Fetch recent sessions for this slot
    recent_sessions = Session.query.filter_by(slot_id=slot.id).order_by(Session.session_date.desc(), Session.id.desc()).limit(8).all()
    recent_sessions_data = []
    for rs in recent_sessions:
        p_count = sum(1 for a in rs.attendance if a.status == 'present')
        a_count = sum(1 for a in rs.attendance if a.status == 'absent')
        total_m = p_count + a_count
        pct = round((p_count * 100.0) / total_m, 1) if total_m else 0
        recent_sessions_data.append({
            'session': rs,
            'present_count': p_count,
            'absent_count': a_count,
            'total_marked': total_m,
            'percentage': pct
        })

    if request.method == 'POST':
        lecture_time_form = request.form.get('lecture_time', selected_time).strip() or (slot.lecture_time or '10:00 AM - 11:00 AM')
        topic_form = request.form.get('topic', '').strip() or None

        session = Session.query.filter_by(slot_id=slot.id, session_date=selected_date, lecture_time=lecture_time_form).first()
        if not session:
            session = Session(
                slot_id=slot.id,
                session_date=selected_date,
                lecture_time=lecture_time_form,
                topic=topic_form
            )
            db.session.add(session)
            db.session.flush()
        else:
            session.topic = topic_form

        # Save attendance for each student
        marked_count = 0
        for s in students:
            status = request.form.get(f'status_{s.roll_no}')
            if status not in ('present', 'absent'):
                continue

            record = Attendance.query.filter_by(session_id=session.id, roll_no=s.roll_no).first()
            if record:
                record.status = status
                record.marked_by = current_user.faculty.id
                record.marked_at = datetime.utcnow()
            else:
                db.session.add(Attendance(
                    session_id=session.id,
                    roll_no=s.roll_no,
                    status=status,
                    marked_by=current_user.faculty.id
                ))
            marked_count += 1

        db.session.commit()
        flash(f'Attendance recorded successfully for {len(students)} students! Lecture Time: {lecture_time_form} on {selected_date_str}.', 'success')
        return redirect(url_for('main.take_attendance', slot_id=slot.id, session_date=selected_date_str, lecture_time=lecture_time_form))

    return render_template('take_attendance.html',
                           slot=slot,
                           students=student_rows,
                           session_date=selected_date_str,
                           lecture_time=selected_time,
                           topic=topic_value,
                           is_edit=bool(existing_session),
                           recent_sessions=recent_sessions_data)

# ============================================
# FACULTY / ADMIN DEFAULTER & ATTENDANCE REPORT
# ============================================
@bp.route('/slot/<int:slot_id>/report')
@login_required
def slot_report(slot_id):
    if current_user.role == 'faculty':
        if not current_user.faculty:
            abort(403)
        slot = TeachingSlot.query.filter_by(id=slot_id, faculty_id=current_user.faculty.id).first_or_404()
    elif current_user.role == 'admin':
        slot = TeachingSlot.query.get_or_404(slot_id)
    else:
        abort(403)

    # All students enrolled in this slot's class
    students = Student.query.filter_by(class_id=slot.class_id).join(User).filter(User.active.is_(True)).order_by(Student.roll_no).all()
    sessions = Session.query.filter_by(slot_id=slot.id).order_by(Session.session_date).all()
    total_sessions = len(sessions)

    report_list = []
    defaulters_count = 0
    safe_count = 0
    total_attended_all = 0

    for st in students:
        attended = Attendance.query.join(Session).filter(
            Session.slot_id == slot.id,
            Attendance.roll_no == st.roll_no,
            Attendance.status == 'present'
        ).count()
        absent = total_sessions - attended
        total_attended_all += attended

        if total_sessions > 0:
            pct = round((attended * 100.0) / total_sessions, 2)
            is_defaulter = (pct < 75.0)
            if is_defaulter:
                defaulters_count += 1
                classes_needed = max(1, math.ceil(3 * total_sessions - 4 * attended))
                safe_margin = 0
            else:
                safe_count += 1
                classes_needed = 0
                safe_margin = max(0, math.floor((4 * attended - 3 * total_sessions) / 3))
        else:
            pct = 0.0
            is_defaulter = False
            classes_needed = 0
            safe_margin = 0

        report_list.append({
            'roll_no': st.roll_no,
            'name': st.user.name,
            'email': st.user.email,
            'attended': attended,
            'absent': absent,
            'total': total_sessions,
            'percentage': pct,
            'is_defaulter': is_defaulter,
            'classes_needed': classes_needed,
            'safe_margin': safe_margin
        })

    class_avg = round((total_attended_all * 100.0) / (total_sessions * len(students)), 1) if (total_sessions and students) else 0

    sessions_data = []
    for sess in Session.query.filter_by(slot_id=slot.id).order_by(Session.session_date.desc(), Session.id.desc()).all():
        p_count = sum(1 for a in sess.attendance if a.status == 'present')
        a_count = sum(1 for a in sess.attendance if a.status == 'absent')
        tot = p_count + a_count
        pct = round((p_count * 100.0) / tot, 1) if tot else 0
        sessions_data.append({
            'session': sess,
            'present_count': p_count,
            'absent_count': a_count,
            'total_marked': tot,
            'percentage': pct,
            'records': sess.attendance
        })

    return render_template('slot_report.html',
                           slot=slot,
                           total_sessions=total_sessions,
                           students=report_list,
                           sessions_data=sessions_data,
                           defaulters_count=defaulters_count,
                           safe_count=safe_count,
                           class_avg=class_avg)

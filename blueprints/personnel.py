from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from db import query_db, execute_db
from blueprints.auth import role_required

personnel_bp = Blueprint('personnel', __name__)

# ---------------------------------------------------------------------------
# Persons
# ---------------------------------------------------------------------------

@personnel_bp.route('/persons')
@login_required
@role_required('event_coordinator')
def persons_list():
    persons = query_db('SELECT * FROM persons ORDER BY person_id ASC')
    return render_template('personnel/persons.html', persons=persons)


@personnel_bp.route('/persons/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def persons_add():
    execute_db(
        'INSERT INTO persons (first_name, last_name, email, phone, person_type, role_name, hire_date, status, birthday, gender, created_date) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date("now"))',
        [
            request.form['first_name'],
            request.form['last_name'],
            request.form['email'],
            request.form['phone'],
            request.form['person_type'],
            request.form['role_name'],
            request.form['hire_date'],
            request.form['status'],
            request.form.get('birthday', ''),
            request.form.get('gender', ''),
        ]
    )
    flash('Person added successfully', 'success')
    return redirect(url_for('personnel.persons_list'))


@personnel_bp.route('/persons/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def persons_edit(id):
    execute_db(
        'UPDATE persons SET first_name=?, last_name=?, email=?, phone=?, person_type=?, role_name=?, hire_date=?, status=?, birthday=?, gender=? '
        'WHERE person_id=?',
        [
            request.form['first_name'],
            request.form['last_name'],
            request.form['email'],
            request.form['phone'],
            request.form['person_type'],
            request.form['role_name'],
            request.form['hire_date'],
            request.form['status'],
            request.form.get('birthday', ''),
            request.form.get('gender', ''),
            id,
        ]
    )
    flash('Person updated successfully', 'success')
    return redirect(url_for('personnel.persons_list'))


@personnel_bp.route('/persons/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def persons_delete(id):
    execute_db('DELETE FROM persons WHERE person_id=?', [id])
    flash('Person deleted', 'success')
    return redirect(url_for('personnel.persons_list'))

# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------

def _clean_schedules(rows):
    """Convert Row objects and normalise the is_absent column (has trailing tab)."""
    schedules = []
    for r in rows:
        d = dict(r)
        for k in d:
            if k.startswith('is_absent'):
                d['is_absent'] = d[k]
                break
        schedules.append(d)
    return schedules


@personnel_bp.route('/schedules')
@login_required
@role_required('event_coordinator')
def schedules_list():
    rows = query_db(
        'SELECT s.*, p.first_name, p.last_name '
        'FROM schedules s LEFT JOIN persons p ON s.person_id = p.person_id '
        'ORDER BY s.schedule_id ASC'
    )
    schedules = _clean_schedules(rows)
    persons = query_db('SELECT person_id, first_name, last_name FROM persons ORDER BY last_name')
    return render_template('personnel/schedules.html', schedules=schedules, persons=persons)


@personnel_bp.route('/schedules/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def schedules_add():
    is_absent = 1 if request.form.get('is_absent') else 0
    execute_db(
        'INSERT INTO schedules (person_id, event_id, availibile_time, shift_date, start_time, end_time, '
        '"is_absent\t", overtime, schedule_type, status, notes, created_date) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, date("now"))',
        [
            request.form['person_id'],
            request.form.get('event_id') or None,
            request.form.get('availibile_time') or None,
            request.form['shift_date'],
            request.form['start_time'],
            request.form['end_time'],
            is_absent,
            request.form.get('overtime') or 0,
            request.form['schedule_type'],
            request.form['status'],
            request.form.get('notes', ''),
        ]
    )
    flash('Schedule added successfully', 'success')
    return redirect(url_for('personnel.schedules_list'))


@personnel_bp.route('/schedules/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def schedules_edit(id):
    is_absent = 1 if request.form.get('is_absent') else 0
    execute_db(
        'UPDATE schedules SET person_id=?, event_id=?, availibile_time=?, shift_date=?, start_time=?, end_time=?, '
        '"is_absent\t"=?, overtime=?, schedule_type=?, status=?, notes=? '
        'WHERE schedule_id=?',
        [
            request.form['person_id'],
            request.form.get('event_id') or None,
            request.form.get('availibile_time') or None,
            request.form['shift_date'],
            request.form['start_time'],
            request.form['end_time'],
            is_absent,
            request.form.get('overtime') or 0,
            request.form['schedule_type'],
            request.form['status'],
            request.form.get('notes', ''),
            id,
        ]
    )
    flash('Schedule updated successfully', 'success')
    return redirect(url_for('personnel.schedules_list'))


@personnel_bp.route('/schedules/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def schedules_delete(id):
    execute_db('DELETE FROM schedules WHERE schedule_id=?', [id])
    flash('Schedule deleted', 'success')
    return redirect(url_for('personnel.schedules_list'))

# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

@personnel_bp.route('/payments')
@login_required
@role_required('event_coordinator')
def payments_list():
    payments = query_db(
        'SELECT pay.*, p.first_name, p.last_name '
        'FROM payments pay LEFT JOIN persons p ON pay.person_id = p.person_id '
        'ORDER BY pay.payment_id ASC'
    )
    persons = query_db('SELECT person_id, first_name, last_name FROM persons ORDER BY last_name')
    return render_template('personnel/payments.html', payments=payments, persons=persons)


@personnel_bp.route('/payments/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def payments_add():
    execute_db(
        'INSERT INTO payments (person_id, payment_date, amount, payment_type, description, '
        'payment_period_start, payment_period_end, created_date) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, date("now"))',
        [
            request.form['person_id'],
            request.form['payment_date'],
            request.form['amount'],
            request.form['payment_type'],
            request.form.get('description', ''),
            request.form.get('payment_period_start') or None,
            request.form.get('payment_period_end') or None,
        ]
    )
    flash('Payment record added successfully', 'success')
    return redirect(url_for('personnel.payments_list'))


@personnel_bp.route('/payments/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def payments_edit(id):
    execute_db(
        'UPDATE payments SET person_id=?, payment_date=?, amount=?, payment_type=?, description=?, '
        'payment_period_start=?, payment_period_end=? WHERE payment_id=?',
        [
            request.form['person_id'],
            request.form['payment_date'],
            request.form['amount'],
            request.form['payment_type'],
            request.form.get('description', ''),
            request.form.get('payment_period_start') or None,
            request.form.get('payment_period_end') or None,
            id,
        ]
    )
    flash('Payment record updated successfully', 'success')
    return redirect(url_for('personnel.payments_list'))


@personnel_bp.route('/payments/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def payments_delete(id):
    execute_db('DELETE FROM payments WHERE payment_id=?', [id])
    flash('Payment record deleted', 'success')
    return redirect(url_for('personnel.payments_list'))


# ---------------------------------------------------------------------------
# Schedule Board  (event-based Kanban-style view)
# ---------------------------------------------------------------------------

@personnel_bp.route('/schedule-board')
@login_required
@role_required('event_coordinator')
def schedule_board():
    events = query_db(
        "SELECT * FROM events ORDER BY "
        "CASE status WHEN 'active' THEN 0 WHEN 'planned' THEN 1 ELSE 2 END, start_date DESC"
    )
    return render_template('personnel/schedule_board.html', events=events)


@personnel_bp.route('/api/schedule-board/<int:event_id>')
@login_required
def schedule_board_data(event_id):
    """Return shifts for a given event, grouped by status."""
    rows = query_db(
        'SELECT s.schedule_id, s.shift_date, s.start_time, s.end_time, '
        's.schedule_type, s.status, s.notes, s.overtime, '
        's."is_absent\t" AS is_absent, '
        'p.first_name, p.last_name, p.role_name '
        'FROM schedules s '
        'LEFT JOIN persons p ON s.person_id = p.person_id '
        'WHERE s.event_id = ? '
        'ORDER BY s.shift_date, s.start_time',
        [event_id]
    )
    scheduled, in_progress, completed, absent = [], [], [], []
    for r in rows:
        item = dict(r)
        # normalise is_absent key
        for k in list(item.keys()):
            if k.startswith('is_absent'):
                item['is_absent'] = item.pop(k)
                break
        st = (item.get('status') or '').lower()
        if st == 'completed':
            completed.append(item)
        elif st == 'in_progress':
            in_progress.append(item)
        elif st == 'absent':
            absent.append(item)
        else:
            scheduled.append(item)
    return jsonify(scheduled=scheduled, in_progress=in_progress,
                   completed=completed, absent=absent)

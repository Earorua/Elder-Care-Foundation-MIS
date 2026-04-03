from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import query_db, execute_db
from blueprints.auth import role_required

events_bp = Blueprint('events', __name__)


# ── Events ──────────────────────────────────────────────

@events_bp.route('/events')
@login_required
@role_required('event_coordinator')
def events_list():
    rows = query_db('SELECT * FROM events ORDER BY event_id DESC')
    return render_template('events/events.html', events=rows)


@events_bp.route('/events/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def events_add():
    execute_db(
        'INSERT INTO events (event_name, event_type, decription, location, '
        'start_date, end_date, status, target_amount, actual_amount, notes, created_date) '
        'VALUES (?,?,?,?,?,?,?,?,?,?,date("now"))',
        [
            request.form['event_name'],
            request.form['event_type'],
            request.form['decription'],
            request.form['location'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            request.form.get('target_amount', 0),
            request.form.get('actual_amount', 0),
            request.form['notes'],
        ]
    )
    flash('Event added successfully', 'success')
    return redirect(url_for('events.events_list'))


@events_bp.route('/events/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def events_edit(id):
    execute_db(
        'UPDATE events SET event_name=?, event_type=?, decription=?, location=?, '
        'start_date=?, end_date=?, status=?, target_amount=?, actual_amount=?, notes=? '
        'WHERE event_id=?',
        [
            request.form['event_name'],
            request.form['event_type'],
            request.form['decription'],
            request.form['location'],
            request.form['start_date'],
            request.form['end_date'],
            request.form['status'],
            request.form.get('target_amount', 0),
            request.form.get('actual_amount', 0),
            request.form['notes'],
            id,
        ]
    )
    flash('Event updated successfully', 'success')
    return redirect(url_for('events.events_list'))


@events_bp.route('/events/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def events_delete(id):
    execute_db('DELETE FROM events WHERE event_id=?', [id])
    flash('Event deleted', 'success')
    return redirect(url_for('events.events_list'))


# ── Donors–Events ───────────────────────────────────────

@events_bp.route('/donors-events')
@login_required
@role_required('event_coordinator')
def donors_events_list():
    rows = query_db(
        'SELECT de.*, d.first_name || " " || d.last_name as donor_name, e.event_name '
        'FROM donors_events de '
        'LEFT JOIN donors d ON de.donor_id = d.donor_id '
        'LEFT JOIN events e ON de.event_id = e.event_id '
        'ORDER BY de.donors_events_id DESC'
    )
    donors = query_db('SELECT donor_id, first_name || " " || last_name as donor_name FROM donors ORDER BY last_name')
    events = query_db('SELECT event_id, event_name FROM events ORDER BY event_name')
    return render_template('events/donors_events.html', rows=rows, donors=donors, events=events)


@events_bp.route('/donors-events/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def donors_events_add():
    execute_db(
        'INSERT INTO donors_events (donor_id, event_id, notes) VALUES (?,?,?)',
        [request.form['donor_id'], request.form['event_id'], request.form['notes']]
    )
    flash('Donor-event association added successfully', 'success')
    return redirect(url_for('events.donors_events_list'))


@events_bp.route('/donors-events/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def donors_events_edit(id):
    execute_db(
        'UPDATE donors_events SET donor_id=?, event_id=?, notes=? WHERE donors_events_id=?',
        [request.form['donor_id'], request.form['event_id'], request.form['notes'], id]
    )
    flash('Donor-event association updated successfully', 'success')
    return redirect(url_for('events.donors_events_list'))


@events_bp.route('/donors-events/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def donors_events_delete(id):
    execute_db('DELETE FROM donors_events WHERE donors_events_id=?', [id])
    flash('Donor-event association deleted', 'success')
    return redirect(url_for('events.donors_events_list'))

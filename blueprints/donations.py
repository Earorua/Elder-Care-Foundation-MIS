from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import query_db, execute_db
from blueprints.auth import role_required

donations_bp = Blueprint('donations', __name__)


# --------------- Donations ---------------

@donations_bp.route('/donations')
@login_required
@role_required('finance')
def donations_list():
    rows = query_db(
        'SELECT d.*, dn.first_name, dn.last_name '
        'FROM donations d LEFT JOIN donors dn ON d.donor_id = dn.donor_id '
        'ORDER BY d.donation_id ASC'
    )
    donors = query_db('SELECT donor_id, first_name, last_name FROM donors ORDER BY last_name')
    gifts = query_db('SELECT gift_id, gift_name FROM gifts WHERE is_active = 1 ORDER BY gift_id')
    return render_template('donations/donations.html', donations=rows, donors=donors, gifts=gifts)


@donations_bp.route('/donations/add', methods=['POST'])
@login_required
@role_required('finance')
def donations_add():
    try:
        execute_db(
            'INSERT INTO donations (donor_id, donation_type, amount, donation_date, '
            'is_tax_deductible, gift_given, description, created_date) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, date("now"))',
            [request.form['donor_id'], request.form['donation_type'],
             request.form['amount'], request.form['donation_date'],
             1 if request.form.get('is_tax_deductible') else 0,
             request.form.get('gift_given', ''), request.form.get('description', '')]
        )
        flash('Donation record added successfully', 'success')
    except Exception as e:
        flash(f'Failed to add: {e}', 'danger')
    return redirect(url_for('donations.donations_list'))


@donations_bp.route('/donations/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def donations_edit(id):
    try:
        execute_db(
            'UPDATE donations SET donor_id=?, donation_type=?, amount=?, donation_date=?, '
            'is_tax_deductible=?, gift_given=?, description=? WHERE donation_id=?',
            [request.form['donor_id'], request.form['donation_type'],
             request.form['amount'], request.form['donation_date'],
             1 if request.form.get('is_tax_deductible') else 0,
             request.form.get('gift_given', ''), request.form.get('description', ''), id]
        )
        flash('Donation record updated successfully', 'success')
    except Exception as e:
        flash(f'Failed to update: {e}', 'danger')
    return redirect(url_for('donations.donations_list'))


@donations_bp.route('/donations/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def donations_delete(id):
    try:
        execute_db('DELETE FROM donations WHERE donation_id=?', [id])
        flash('Donation record deleted', 'success')
    except Exception as e:
        flash(f'Failed to delete: {e}', 'danger')
    return redirect(url_for('donations.donations_list'))


# --------------- Donors ---------------

@donations_bp.route('/donors')
@login_required
@role_required('finance')
def donors_list():
    from blueprints.dashboard import US_STATES
    rows = query_db('SELECT * FROM donors ORDER BY donor_id ASC')
    sorted_states = sorted(US_STATES.items(), key=lambda x: x[1])
    return render_template('donations/donors.html', donors=rows,
                           us_states=sorted_states, us_states_map=US_STATES)


@donations_bp.route('/donors/add', methods=['POST'])
@login_required
@role_required('finance')
def donors_add():
    try:
        execute_db(
            'INSERT INTO donors (first_name, last_name, email, age, gender, location, created_date) '
            'VALUES (?, ?, ?, ?, ?, ?, date("now"))',
            [request.form['first_name'], request.form['last_name'],
             request.form.get('email', ''), request.form.get('age', 0),
             request.form.get('gender', ''), request.form.get('location', '')]
        )
        flash('Donor added successfully', 'success')
    except Exception as e:
        flash(f'Failed to add: {e}', 'danger')
    return redirect(url_for('donations.donors_list'))


@donations_bp.route('/donors/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def donors_edit(id):
    try:
        execute_db(
            'UPDATE donors SET first_name=?, last_name=?, email=?, age=?, gender=?, location=? '
            'WHERE donor_id=?',
            [request.form['first_name'], request.form['last_name'],
             request.form.get('email', ''), request.form.get('age', 0),
             request.form.get('gender', ''), request.form.get('location', ''), id]
        )
        flash('Donor updated successfully', 'success')
    except Exception as e:
        flash(f'Failed to update: {e}', 'danger')
    return redirect(url_for('donations.donors_list'))


@donations_bp.route('/donors/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def donors_delete(id):
    try:
        execute_db('DELETE FROM donors WHERE donor_id=?', [id])
        flash('Donor deleted', 'success')
    except Exception as e:
        flash(f'Failed to delete: {e}', 'danger')
    return redirect(url_for('donations.donors_list'))


# --------------- Categories ---------------

@donations_bp.route('/categories')
@login_required
@role_required('finance')
def categories_list():
    rows = query_db('SELECT * FROM donation_categories ORDER BY category_id ASC')
    return render_template('donations/categories.html', categories=rows)


@donations_bp.route('/categories/add', methods=['POST'])
@login_required
@role_required('finance')
def categories_add():
    try:
        parent = request.form.get('parent_category_id') or None
        execute_db(
            'INSERT INTO donation_categories (parent_category_id, category_name, description, is_active, created_date) '
            'VALUES (?, ?, ?, ?, date("now"))',
            [parent, request.form['category_name'],
             request.form.get('description', ''), 1 if request.form.get('is_active') else 0]
        )
        flash('Category added successfully', 'success')
    except Exception as e:
        flash(f'Failed to add: {e}', 'danger')
    return redirect(url_for('donations.categories_list'))


@donations_bp.route('/categories/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def categories_edit(id):
    try:
        parent = request.form.get('parent_category_id') or None
        execute_db(
            'UPDATE donation_categories SET parent_category_id=?, category_name=?, description=?, is_active=? '
            'WHERE category_id=?',
            [parent, request.form['category_name'],
             request.form.get('description', ''), 1 if request.form.get('is_active') else 0, id]
        )
        flash('Category updated successfully', 'success')
    except Exception as e:
        flash(f'Failed to update: {e}', 'danger')
    return redirect(url_for('donations.categories_list'))


@donations_bp.route('/categories/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def categories_delete(id):
    try:
        execute_db('DELETE FROM donation_categories WHERE category_id=?', [id])
        flash('Category deleted', 'success')
    except Exception as e:
        flash(f'Failed to delete: {e}', 'danger')
    return redirect(url_for('donations.categories_list'))


# --------------- Feedback ---------------

@donations_bp.route('/feedback')
@login_required
@role_required('finance')
def feedback_list():
    rows = query_db(
        'SELECT f.*, d.donation_type, d.amount FROM donor_feedback f '
        'LEFT JOIN donations d ON f.donation_id = d.donation_id '
        'ORDER BY f.feedback_id ASC'
    )
    donations = query_db('SELECT donation_id, donation_type, amount FROM donations ORDER BY donation_date DESC')
    return render_template('donations/feedback.html', feedbacks=rows, donations=donations)


@donations_bp.route('/feedback/add', methods=['POST'])
@login_required
@role_required('finance')
def feedback_add():
    try:
        execute_db(
            'INSERT INTO donor_feedback (donation_id, feedback_date, feedback_type, feedback_text, status) '
            'VALUES (?, ?, ?, ?, ?)',
            [request.form['donation_id'], request.form['feedback_date'],
             request.form['feedback_type'], request.form.get('feedback_text', ''),
             request.form.get('status', 'Pending')]
        )
        flash('Feedback added successfully', 'success')
    except Exception as e:
        flash(f'Failed to add: {e}', 'danger')
    return redirect(url_for('donations.feedback_list'))


@donations_bp.route('/feedback/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def feedback_edit(id):
    try:
        execute_db(
            'UPDATE donor_feedback SET donation_id=?, feedback_date=?, feedback_type=?, '
            'feedback_text=?, status=? WHERE feedback_id=?',
            [request.form['donation_id'], request.form['feedback_date'],
             request.form['feedback_type'], request.form.get('feedback_text', ''),
             request.form.get('status', 'Pending'), id]
        )
        flash('Feedback updated successfully', 'success')
    except Exception as e:
        flash(f'Failed to update: {e}', 'danger')
    return redirect(url_for('donations.feedback_list'))


@donations_bp.route('/feedback/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def feedback_delete(id):
    try:
        execute_db('DELETE FROM donor_feedback WHERE feedback_id=?', [id])
        flash('Feedback deleted', 'success')
    except Exception as e:
        flash(f'Failed to delete: {e}', 'danger')
    return redirect(url_for('donations.feedback_list'))


# --------------- Tax Receipts ---------------

@donations_bp.route('/receipts')
@login_required
@role_required('finance')
def receipts_list():
    rows = query_db(
        'SELECT r.*, d.donation_type, d.amount as donation_amount FROM tax_receipts r '
        'LEFT JOIN donations d ON r.donation_id = d.donation_id '
        'ORDER BY r.receipt_id ASC'
    )
    donations = query_db('SELECT donation_id, donation_type, amount FROM donations ORDER BY donation_date DESC')
    return render_template('donations/receipts.html', receipts=rows, donations=donations)


@donations_bp.route('/receipts/add', methods=['POST'])
@login_required
@role_required('finance')
def receipts_add():
    try:
        execute_db(
            'INSERT INTO tax_receipts (donation_id, receipt_date, amount, receipt_number, issued_by, created_date) '
            'VALUES (?, ?, ?, ?, ?, date("now"))',
            [request.form['donation_id'], request.form['receipt_date'],
             request.form['amount'], request.form['receipt_number'],
             request.form.get('issued_by', '')]
        )
        flash('Receipt added successfully', 'success')
    except Exception as e:
        flash(f'Failed to add: {e}', 'danger')
    return redirect(url_for('donations.receipts_list'))


@donations_bp.route('/receipts/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def receipts_edit(id):
    try:
        execute_db(
            'UPDATE tax_receipts SET donation_id=?, receipt_date=?, amount=?, receipt_number=?, issued_by=? '
            'WHERE receipt_id=?',
            [request.form['donation_id'], request.form['receipt_date'],
             request.form['amount'], request.form['receipt_number'],
             request.form.get('issued_by', ''), id]
        )
        flash('Receipt updated successfully', 'success')
    except Exception as e:
        flash(f'Failed to update: {e}', 'danger')
    return redirect(url_for('donations.receipts_list'))


@donations_bp.route('/receipts/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def receipts_delete(id):
    try:
        execute_db('DELETE FROM tax_receipts WHERE receipt_id=?', [id])
        flash('Receipt deleted', 'success')
    except Exception as e:
        flash(f'Failed to delete: {e}', 'danger')
    return redirect(url_for('donations.receipts_list'))

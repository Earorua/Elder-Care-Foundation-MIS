from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from db import query_db, execute_db
from blueprints.auth import role_required

gifts_bp = Blueprint('gifts', __name__)


# ── Gifts ────────────────────────────────────────────────────────────────────

@gifts_bp.route('/gifts')
@login_required
@role_required('event_coordinator')
def gifts_list():
    rows = query_db('SELECT * FROM gifts ORDER BY gift_id ASC')
    return render_template('gifts/gifts.html', rows=rows)


@gifts_bp.route('/gifts/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def gifts_add():
    execute_db(
        'INSERT INTO gifts (gift_name, gift_type, unit_cost, description, current_stock, min_stock_level, is_active) '
        'VALUES (?,?,?,?,?,?,?)',
        (request.form['gift_name'], request.form['gift_type'],
         request.form['unit_cost'], request.form['description'],
         request.form['current_stock'], request.form['min_stock_level'],
         request.form.get('is_active', '1'))
    )
    flash('Gift added successfully', 'success')
    return redirect(url_for('gifts.gifts_list'))


@gifts_bp.route('/gifts/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def gifts_edit(id):
    execute_db(
        'UPDATE gifts SET gift_name=?, gift_type=?, unit_cost=?, description=?, '
        'current_stock=?, min_stock_level=?, is_active=? WHERE gift_id=?',
        (request.form['gift_name'], request.form['gift_type'],
         request.form['unit_cost'], request.form['description'],
         request.form['current_stock'], request.form['min_stock_level'],
         request.form.get('is_active', '1'), id)
    )
    flash('Gift updated successfully', 'success')
    return redirect(url_for('gifts.gifts_list'))


@gifts_bp.route('/gifts/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def gifts_delete(id):
    execute_db('DELETE FROM gifts WHERE gift_id=?', (id,))
    flash('Gift deleted', 'success')
    return redirect(url_for('gifts.gifts_list'))


# ── Batches ──────────────────────────────────────────────────────────────────

@gifts_bp.route('/batches')
@login_required
@role_required('event_coordinator')
def batches_list():
    rows = query_db(
        'SELECT b.*, g.gift_name, s.supplier_name '
        'FROM gift_batch b '
        'LEFT JOIN gifts g ON b.gift_id = g.gift_id '
        'LEFT JOIN suppliers s ON b.supplier_id = s.supplier_id '
        'ORDER BY b.batch_id ASC'
    )
    gifts = query_db('SELECT gift_id, gift_name FROM gifts ORDER BY gift_name')
    suppliers = query_db('SELECT supplier_id, supplier_name FROM suppliers ORDER BY supplier_name')
    return render_template('gifts/batches.html', rows=rows, gifts=gifts, suppliers=suppliers)


@gifts_bp.route('/batches/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def batches_add():
    execute_db(
        'INSERT INTO gift_batch (supplier_id, gift_id, batch_quantity, batch_type, batch_date) '
        'VALUES (?,?,?,?,?)',
        (request.form['supplier_id'], request.form['gift_id'],
         request.form['batch_quantity'], request.form['batch_type'],
         request.form['batch_date'])
    )
    flash('Batch added successfully', 'success')
    return redirect(url_for('gifts.batches_list'))


@gifts_bp.route('/batches/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def batches_edit(id):
    execute_db(
        'UPDATE gift_batch SET supplier_id=?, gift_id=?, batch_quantity=?, batch_type=?, batch_date=? '
        'WHERE batch_id=?',
        (request.form['supplier_id'], request.form['gift_id'],
         request.form['batch_quantity'], request.form['batch_type'],
         request.form['batch_date'], id)
    )
    flash('Batch updated successfully', 'success')
    return redirect(url_for('gifts.batches_list'))


@gifts_bp.route('/batches/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def batches_delete(id):
    execute_db('DELETE FROM gift_batch WHERE batch_id=?', (id,))
    flash('Batch deleted', 'success')
    return redirect(url_for('gifts.batches_list'))


# ── Distribution ─────────────────────────────────────────────────────────────

@gifts_bp.route('/distribution')
@login_required
@role_required('event_coordinator')
def distribution_list():
    rows = query_db(
        'SELECT d.*, b.batch_quantity, b.batch_type, '
        'dl.delivery_company, dl.delivery_status '
        'FROM gift_distribution d '
        'LEFT JOIN gift_batch b ON d.batch_id = b.batch_id '
        'LEFT JOIN delivery dl ON d.delivery_id = dl.delivery_id '
        'ORDER BY d.distribution_id ASC'
    )
    batches = query_db('SELECT batch_id, batch_type, batch_date FROM gift_batch ORDER BY batch_id DESC')
    deliveries = query_db('SELECT delivery_id, delivery_company, delivery_date FROM delivery ORDER BY delivery_id DESC')
    donations = query_db('SELECT donation_id, donation_date, amount FROM donations ORDER BY donation_id DESC')
    return render_template('gifts/distribution.html', rows=rows,
                           batches=batches, deliveries=deliveries, donations=donations)


@gifts_bp.route('/distribution/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def distribution_add():
    execute_db(
        'INSERT INTO gift_distribution (batch_id, donation_id, delivery_id, distribution_date, '
        'quantity, is_free, distribution_reason, distributed_by, notes) '
        'VALUES (?,?,?,?,?,?,?,?,?)',
        (request.form['batch_id'],
         request.form.get('donation_id') or None,
         request.form.get('delivery_id') or None,
         request.form['distribution_date'],
         request.form['quantity'],
         request.form.get('is_free', '0'),
         request.form['distribution_reason'],
         request.form['distributed_by'],
         request.form['notes'])
    )
    flash('Distribution record added successfully', 'success')
    return redirect(url_for('gifts.distribution_list'))


@gifts_bp.route('/distribution/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def distribution_edit(id):
    execute_db(
        'UPDATE gift_distribution SET batch_id=?, donation_id=?, delivery_id=?, distribution_date=?, '
        'quantity=?, is_free=?, distribution_reason=?, distributed_by=?, notes=? '
        'WHERE distribution_id=?',
        (request.form['batch_id'],
         request.form.get('donation_id') or None,
         request.form.get('delivery_id') or None,
         request.form['distribution_date'],
         request.form['quantity'],
         request.form.get('is_free', '0'),
         request.form['distribution_reason'],
         request.form['distributed_by'],
         request.form['notes'], id)
    )
    flash('Distribution record updated successfully', 'success')
    return redirect(url_for('gifts.distribution_list'))


@gifts_bp.route('/distribution/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def distribution_delete(id):
    execute_db('DELETE FROM gift_distribution WHERE distribution_id=?', (id,))
    flash('Distribution record deleted', 'success')
    return redirect(url_for('gifts.distribution_list'))


# ── Delivery ─────────────────────────────────────────────────────────────────

@gifts_bp.route('/delivery')
@login_required
@role_required('event_coordinator')
def delivery_list():
    rows = query_db('SELECT * FROM delivery ORDER BY delivery_id ASC')
    return render_template('gifts/delivery.html', rows=rows)


@gifts_bp.route('/delivery/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def delivery_add():
    execute_db(
        'INSERT INTO delivery (delivery_company, delivery_date, delivery_status, delivery_fee) '
        'VALUES (?,?,?,?)',
        (request.form['delivery_company'], request.form['delivery_date'],
         request.form['delivery_status'], request.form['delivery_fee'])
    )
    flash('Delivery added successfully', 'success')
    return redirect(url_for('gifts.delivery_list'))


@gifts_bp.route('/delivery/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def delivery_edit(id):
    execute_db(
        'UPDATE delivery SET delivery_company=?, delivery_date=?, delivery_status=?, delivery_fee=? '
        'WHERE delivery_id=?',
        (request.form['delivery_company'], request.form['delivery_date'],
         request.form['delivery_status'], request.form['delivery_fee'], id)
    )
    flash('Delivery updated successfully', 'success')
    return redirect(url_for('gifts.delivery_list'))


@gifts_bp.route('/delivery/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def delivery_delete(id):
    execute_db('DELETE FROM delivery WHERE delivery_id=?', (id,))
    flash('Delivery deleted', 'success')
    return redirect(url_for('gifts.delivery_list'))


# ── Suppliers ────────────────────────────────────────────────────────────────

@gifts_bp.route('/suppliers')
@login_required
@role_required('event_coordinator')
def suppliers_list():
    rows = query_db(
        'SELECT s.*, '
        'COALESCE(SUM(b.batch_quantity * g.unit_cost), 0) as accounts_payable '
        'FROM suppliers s '
        'LEFT JOIN gift_batch b ON s.supplier_id = b.supplier_id '
        'LEFT JOIN gifts g ON b.gift_id = g.gift_id '
        'GROUP BY s.supplier_id '
        'ORDER BY s.supplier_id ASC'
    )
    # Detailed payable breakdown: per supplier, per gift
    payable_detail = query_db(
        'SELECT s.supplier_id, s.supplier_name, g.gift_name, g.unit_cost, '
        'SUM(b.batch_quantity) as total_qty, '
        'SUM(b.batch_quantity * g.unit_cost) as line_total '
        'FROM gift_batch b '
        'JOIN suppliers s ON b.supplier_id = s.supplier_id '
        'JOIN gifts g ON b.gift_id = g.gift_id '
        'GROUP BY s.supplier_id, g.gift_id '
        'ORDER BY s.supplier_name, g.gift_name'
    )
    total_payable = sum(r['accounts_payable'] for r in rows)
    return render_template('gifts/suppliers.html', rows=rows,
                           payable_detail=payable_detail, total_payable=total_payable)


@gifts_bp.route('/suppliers/add', methods=['POST'])
@login_required
@role_required('event_coordinator')
def suppliers_add():
    execute_db(
        'INSERT INTO suppliers (supplier_name, address, phone, company, contact_name, contact_email) VALUES (?,?,?,?,?,?)',
        (request.form['supplier_name'], request.form['address'],
         request.form['phone'], request.form['company'], request.form.get('contact_name', ''),
         request.form.get('contact_email', ''))
    )
    flash('Supplier added successfully', 'success')
    return redirect(url_for('gifts.suppliers_list'))


@gifts_bp.route('/suppliers/edit/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def suppliers_edit(id):
    execute_db(
        'UPDATE suppliers SET supplier_name=?, address=?, phone=?, company=?, contact_name=?, contact_email=? WHERE supplier_id=?',
        (request.form['supplier_name'], request.form['address'],
         request.form['phone'], request.form['company'], request.form.get('contact_name', ''),
         request.form.get('contact_email', ''), id)
    )
    flash('Supplier updated successfully', 'success')
    return redirect(url_for('gifts.suppliers_list'))


@gifts_bp.route('/suppliers/delete/<int:id>', methods=['POST'])
@login_required
@role_required('event_coordinator')
def suppliers_delete(id):
    execute_db('DELETE FROM suppliers WHERE supplier_id=?', (id,))
    flash('Supplier deleted', 'success')
    return redirect(url_for('gifts.suppliers_list'))

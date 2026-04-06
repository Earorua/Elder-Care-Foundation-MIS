from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from db import query_db, execute_db
from blueprints.auth import role_required
from datetime import date

finance_bp = Blueprint('finance', __name__)


# ── Grants ──────────────────────────────────────────────

@finance_bp.route('/grants')
@login_required
@role_required('finance')
def grants_list():
    rows = query_db('SELECT rowid as _rowid, * FROM grants ORDER BY rowid ASC')
    return render_template('finance/grants.html', grants=rows)


@finance_bp.route('/grants/add', methods=['POST'])
@login_required
@role_required('finance')
def grants_add():
    execute_db(
        'INSERT INTO grants (grant_name, funding_org, grant_code, amount, received_date, created_date) '
        'VALUES (?,?,?,?,?,date("now"))',
        [
            request.form['grant_name'],
            request.form['funding_org'],
            request.form['grant_code'],
            request.form['amount'],
            request.form['received_date'],
        ]
    )
    flash('Grant added successfully', 'success')
    return redirect(url_for('finance.grants_list'))


@finance_bp.route('/grants/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def grants_edit(id):
    execute_db(
        'UPDATE grants SET grant_name=?, funding_org=?, grant_code=?, amount=?, received_date=? '
        'WHERE rowid=?',
        [
            request.form['grant_name'],
            request.form['funding_org'],
            request.form['grant_code'],
            request.form['amount'],
            request.form['received_date'],
            id,
        ]
    )
    flash('Grant updated successfully', 'success')
    return redirect(url_for('finance.grants_list'))


@finance_bp.route('/grants/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def grants_delete(id):
    execute_db('DELETE FROM grants WHERE rowid=?', [id])
    flash('Grant deleted', 'success')
    return redirect(url_for('finance.grants_list'))


# ── Other Income ────────────────────────────────────────

@finance_bp.route('/other-income')
@login_required
@role_required('finance')
def other_income_list():
    rows = query_db('SELECT * FROM other_income ORDER BY other_income_id ASC')
    return render_template('finance/other_income.html', incomes=rows)


@finance_bp.route('/other-income/add', methods=['POST'])
@login_required
@role_required('finance')
def other_income_add():
    execute_db(
        'INSERT INTO other_income (income_name, income_type, amount, source_name, recevied_date, created_date) '
        'VALUES (?,?,?,?,?,date("now"))',
        [
            request.form['income_name'],
            request.form['income_type'],
            request.form['amount'],
            request.form['source_name'],
            request.form['recevied_date'],
        ]
    )
    flash('Other income added successfully', 'success')
    return redirect(url_for('finance.other_income_list'))


@finance_bp.route('/other-income/edit/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def other_income_edit(id):
    execute_db(
        'UPDATE other_income SET income_name=?, income_type=?, amount=?, source_name=?, recevied_date=? '
        'WHERE other_income_id=?',
        [
            request.form['income_name'],
            request.form['income_type'],
            request.form['amount'],
            request.form['source_name'],
            request.form['recevied_date'],
            id,
        ]
    )
    flash('Other income updated successfully', 'success')
    return redirect(url_for('finance.other_income_list'))


@finance_bp.route('/other-income/delete/<int:id>', methods=['POST'])
@login_required
@role_required('finance')
def other_income_delete(id):
    execute_db('DELETE FROM other_income WHERE other_income_id=?', [id])
    flash('Other income deleted', 'success')
    return redirect(url_for('finance.other_income_list'))


# ── Reports ─────────────────────────────────────────────

@finance_bp.route('/reports')
@login_required
@role_required('finance')
def reports():
    total_donations = query_db('SELECT COALESCE(SUM(amount),0) as v FROM donations', one=True)['v']
    total_grants = query_db('SELECT COALESCE(SUM(amount),0) as v FROM grants', one=True)['v']
    total_other = query_db('SELECT COALESCE(SUM(amount),0) as v FROM other_income', one=True)['v']
    total_payments = query_db('SELECT COALESCE(SUM(amount),0) as v FROM payments', one=True)['v']
    total_delivery = query_db('SELECT COALESCE(SUM(delivery_fee),0) as v FROM delivery', one=True)['v']
    total_gift_cost = query_db(
        'SELECT COALESCE(SUM(b.batch_quantity * g.unit_cost),0) as v '
        'FROM gift_batch b JOIN gifts g ON b.gift_id = g.gift_id', one=True
    )['v']
    total_income = total_donations + total_grants + total_other
    total_expenses = total_payments + total_delivery + total_gift_cost
    return render_template('finance/reports.html',
        total_income=total_income, total_expenses=total_expenses,
        total_donations=total_donations, total_grants=total_grants,
        total_other=total_other, total_payments=total_payments,
        total_delivery=total_delivery, total_gift_cost=total_gift_cost)


@finance_bp.route('/reports/income-statement')
@login_required
@role_required('finance')
def income_statement():
    # Revenue by type
    donations_by_type = query_db(
        'SELECT donation_type, SUM(amount) as total FROM donations GROUP BY donation_type ORDER BY total DESC')
    grants_by_org = query_db(
        'SELECT funding_org, SUM(amount) as total FROM grants GROUP BY funding_org ORDER BY total DESC')
    other_by_type = query_db(
        'SELECT income_type, SUM(amount) as total FROM other_income GROUP BY income_type ORDER BY total DESC')
    # Expenses
    payments_by_type = query_db(
        'SELECT payment_type, SUM(amount) as total FROM payments GROUP BY payment_type ORDER BY total DESC')
    total_delivery = query_db('SELECT COALESCE(SUM(delivery_fee),0) as v FROM delivery', one=True)['v']
    total_gift_cost = query_db(
        'SELECT COALESCE(SUM(b.batch_quantity * g.unit_cost),0) as v '
        'FROM gift_batch b JOIN gifts g ON b.gift_id = g.gift_id', one=True)['v']
    # Totals
    sum_donations = sum(r['total'] for r in donations_by_type)
    sum_grants = sum(r['total'] for r in grants_by_org)
    sum_other = sum(r['total'] for r in other_by_type)
    sum_payments = sum(r['total'] for r in payments_by_type)
    total_revenue = sum_donations + sum_grants + sum_other
    total_expenses = sum_payments + total_delivery + total_gift_cost
    # Monthly trend
    monthly = _monthly_trend()
    return render_template('finance/income_statement.html',
        donations_by_type=donations_by_type, grants_by_org=grants_by_org,
        other_by_type=other_by_type, payments_by_type=payments_by_type,
        total_delivery=total_delivery, total_gift_cost=total_gift_cost,
        sum_donations=sum_donations, sum_grants=sum_grants, sum_other=sum_other,
        sum_payments=sum_payments, total_revenue=total_revenue,
        total_expenses=total_expenses, net_income=total_revenue - total_expenses,
        months=monthly['months'], income_data=monthly['income'], expense_data=monthly['expense'],
        report_date=date.today(), fiscal_year='2025')


@finance_bp.route('/reports/balance-sheet')
@login_required
@role_required('finance')
def balance_sheet():
    total_income = (
        query_db('SELECT COALESCE(SUM(amount),0) as v FROM donations', one=True)['v']
        + query_db('SELECT COALESCE(SUM(amount),0) as v FROM grants', one=True)['v']
        + query_db('SELECT COALESCE(SUM(amount),0) as v FROM other_income', one=True)['v']
    )
    total_expenses = (
        query_db('SELECT COALESCE(SUM(amount),0) as v FROM payments', one=True)['v']
        + query_db('SELECT COALESCE(SUM(delivery_fee),0) as v FROM delivery', one=True)['v']
        + query_db('SELECT COALESCE(SUM(b.batch_quantity * g.unit_cost),0) as v '
                   'FROM gift_batch b JOIN gifts g ON b.gift_id = g.gift_id', one=True)['v']
    )
    cash = total_income - total_expenses
    inventory = query_db(
        'SELECT COALESCE(SUM(current_stock * unit_cost),0) as v FROM gifts', one=True)['v']
    inventory_detail = query_db(
        'SELECT gift_name, current_stock, unit_cost, (current_stock * unit_cost) as value '
        'FROM gifts WHERE current_stock > 0 ORDER BY value DESC')
    total_assets = cash + inventory
    return render_template('finance/balance_sheet.html',
        cash=cash, inventory=inventory, inventory_detail=inventory_detail,
        total_assets=total_assets, fund_balance=total_assets,
        total_income=total_income, total_expenses=total_expenses,
        report_date=date.today(), fiscal_year='2025')


@finance_bp.route('/reports/expenditure')
@login_required
@role_required('finance')
def expenditure():
    payments_by_type = query_db(
        'SELECT payment_type, SUM(amount) as total, COUNT(*) as cnt '
        'FROM payments GROUP BY payment_type ORDER BY total DESC')
    delivery_total = query_db('SELECT COALESCE(SUM(delivery_fee),0) as v FROM delivery', one=True)['v']
    gift_cost_total = query_db(
        'SELECT COALESCE(SUM(b.batch_quantity * g.unit_cost),0) as v '
        'FROM gift_batch b JOIN gifts g ON b.gift_id = g.gift_id', one=True)['v']
    # Per-person salary detail
    salary_detail = query_db(
        'SELECT p.first_name || " " || p.last_name as name, '
        'pay.payment_type, SUM(pay.amount) as total '
        'FROM payments pay JOIN persons p ON pay.person_id = p.person_id '
        'GROUP BY p.person_id, pay.payment_type ORDER BY total DESC')
    # Monthly expense trend
    monthly_payments = query_db(
        "SELECT strftime('%%Y-%%m', payment_date) as month, SUM(amount) as total "
        "FROM payments GROUP BY month ORDER BY month")
    months = [r['month'] for r in monthly_payments]
    amounts = [r['total'] for r in monthly_payments]
    # Category labels/values for pie chart
    categories = [r['payment_type'] for r in payments_by_type]
    cat_values = [r['total'] for r in payments_by_type]
    if delivery_total:
        categories.append('Delivery & Logistics')
        cat_values.append(delivery_total)
    if gift_cost_total:
        categories.append('Gift Procurement')
        cat_values.append(gift_cost_total)
    return render_template('finance/expenditure.html',
        payments_by_type=payments_by_type, delivery_total=delivery_total,
        gift_cost_total=gift_cost_total, salary_detail=salary_detail,
        months=months, amounts=amounts,
        categories=categories, cat_values=cat_values,
        grand_total=sum(cat_values),
        report_date=date.today(), fiscal_year='2025')


def _monthly_trend():
    """Helper: merge monthly income/expense data."""
    monthly_income = query_db(
        "SELECT strftime('%%Y-%%m', donation_date) as month, SUM(amount) as total "
        "FROM donations GROUP BY month ORDER BY month")
    monthly_grants = query_db(
        "SELECT strftime('%%Y-%%m', received_date) as month, SUM(amount) as total "
        "FROM grants GROUP BY month ORDER BY month")
    monthly_other = query_db(
        "SELECT strftime('%%Y-%%m', recevied_date) as month, SUM(amount) as total "
        "FROM other_income GROUP BY month ORDER BY month")
    monthly_expenses = query_db(
        "SELECT strftime('%%Y-%%m', payment_date) as month, SUM(amount) as total "
        "FROM payments GROUP BY month ORDER BY month")
    months_set = set()
    inc, exp = {}, {}
    for src in [monthly_income, monthly_grants, monthly_other]:
        for r in src:
            months_set.add(r['month'])
            inc[r['month']] = inc.get(r['month'], 0) + r['total']
    for r in monthly_expenses:
        months_set.add(r['month'])
        exp[r['month']] = exp.get(r['month'], 0) + r['total']
    months = sorted(months_set)
    return {'months': months, 'income': [inc.get(m, 0) for m in months],
            'expense': [exp.get(m, 0) for m in months]}

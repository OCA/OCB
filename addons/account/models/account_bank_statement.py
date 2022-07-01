# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import float_is_zero, pycompat
from odoo.tools import float_compare, float_round, float_repr
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import UserError, ValidationError

import time
import math

class AccountCashboxLine(models.Model):
    """ Cash Box Details """
    _name = 'account.cashbox.line'
    _description = 'CashBox Line'
    _rec_name = 'coin_value'
    _order = 'coin_value'

    @api.one
    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        self.subtotal = self.coin_value * self.number

    coin_value = fields.Float(string='Coin/Bill Value', required=True, digits=0)
    number = fields.Integer(string='Number of Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox")


class AccountBankStmtCashWizard(models.Model):
    """
    Account Bank Statement popup that allows entering cash details.
    """
    _name = 'account.bank.statement.cashbox'
    _description = 'Bank Statement Cashbox'

    cashbox_lines_ids = fields.One2many('account.cashbox.line', 'cashbox_id', string='Cashbox Lines')

    @api.multi
    def validate(self):
        bnk_stmt_id = self.env.context.get('bank_statement_id', False) or self.env.context.get('active_id', False)
        bnk_stmt = self.env['account.bank.statement'].browse(bnk_stmt_id)
        total = 0.0
        for lines in self.cashbox_lines_ids:
            total += lines.subtotal
        if self.env.context.get('balance', False) == 'start':
            #starting balance
            bnk_stmt.write({'balance_start': total, 'cashbox_start_id': self.id})
        else:
            #closing balance
            bnk_stmt.write({'balance_end_real': total, 'cashbox_end_id': self.id})
        return {'type': 'ir.actions.act_window_close'}


class AccountBankStmtCloseCheck(models.TransientModel):
    """
    Account Bank Statement wizard that check that closing balance is correct.
    """
    _name = 'account.bank.statement.closebalance'
    _description = 'Bank Statement Closing Balance'

    @api.multi
    def validate(self):
        bnk_stmt_id = self.env.context.get('active_id', False)
        if bnk_stmt_id:
            self.env['account.bank.statement'].browse(bnk_stmt_id).button_confirm_bank()
        return {'type': 'ir.actions.act_window_close'}


class AccountBankStatement(models.Model):

    @api.one
    @api.depends('line_ids', 'balance_start', 'line_ids.amount', 'balance_end_real')
    def _end_balance(self):
        self.total_entry_encoding = sum([line.amount for line in self.line_ids])
        self.balance_end = self.balance_start + self.total_entry_encoding
        self.difference = self.balance_end_real - self.balance_end

    @api.multi
    def _is_difference_zero(self):
        for bank_stmt in self:
            bank_stmt.is_difference_zero = float_is_zero(bank_stmt.difference, precision_digits=bank_stmt.currency_id.decimal_places)

    @api.one
    @api.depends('journal_id')
    def _compute_currency(self):
        self.currency_id = self.journal_id.currency_id or self.company_id.currency_id

    @api.one
    @api.depends('line_ids.journal_entry_ids')
    def _check_lines_reconciled(self):
        self.all_lines_reconciled = all([line.journal_entry_ids.ids or line.account_id.id for line in self.line_ids if not self.currency_id.is_zero(line.amount)])

    @api.depends('move_line_ids')
    def _get_move_line_count(self):
        for payment in self:
            payment.move_line_count = len(payment.move_line_ids)

    @api.model
    def _default_journal(self):
        journal_type = self.env.context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('account.bank.statement').id
        if journal_type:
            journals = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company_id)])
            if journals:
                return journals[0]
        return self.env['account.journal']

    @api.multi
    def _get_opening_balance(self, journal_id):
        last_bnk_stmt = self.search([('journal_id', '=', journal_id)], limit=1)
        if last_bnk_stmt:
            return last_bnk_stmt.balance_end
        return 0

    @api.multi
    def _set_opening_balance(self, journal_id):
        self.balance_start = self._get_opening_balance(journal_id)

    @api.model
    def _default_opening_balance(self):
        #Search last bank statement and set current opening balance as closing balance of previous one
        journal_id = self._context.get('default_journal_id', False) or self._context.get('journal_id', False)
        if journal_id:
            return self._get_opening_balance(journal_id)
        return 0

    _name = "account.bank.statement"
    _description = "Bank Statement"
    _order = "date desc, id desc"
    _inherit = ['mail.thread']

    name = fields.Char(string='Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True)
    reference = fields.Char(string='External Reference', states={'open': [('readonly', False)]}, copy=False, readonly=True, help="Used to hold the reference of the external mean that created this statement (name of imported file, reference of online synchronization...)")
    date = fields.Date(required=True, states={'confirm': [('readonly', True)]}, index=True, copy=False, default=fields.Date.context_today)
    date_done = fields.Datetime(string="Closed On")
    balance_start = fields.Monetary(string='Starting Balance', states={'confirm': [('readonly', True)]}, default=_default_opening_balance)
    balance_end_real = fields.Monetary('Ending Balance', states={'confirm': [('readonly', True)]})
    accounting_date = fields.Date(string="Accounting Date", help="If set, the accounting entries created during the bank statement reconciliation process will be created at this date.\n"
        "This is useful if the accounting period in which the entries should normally be booked is already closed.",
        states={'open': [('readonly', False)]}, readonly=True)
    state = fields.Selection([('open', 'New'), ('confirm', 'Validated')], string='Status', required=True, readonly=True, copy=False, default='open')
    currency_id = fields.Many2one('res.currency', compute='_compute_currency', oldname='currency', string="Currency")
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states={'confirm': [('readonly', True)]}, default=_default_journal)
    journal_type = fields.Selection(related='journal_id.type', help="Technical field used for usability purposes", readonly=False)
    company_id = fields.Many2one('res.company', related='journal_id.company_id', string='Company', store=True, readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('account.bank.statement'))

    total_entry_encoding = fields.Monetary('Transactions Subtotal', compute='_end_balance', store=True, help="Total of transaction lines.")
    balance_end = fields.Monetary('Computed Balance', compute='_end_balance', store=True, help='Balance as calculated based on Opening Balance and transaction lines')
    difference = fields.Monetary(compute='_end_balance', store=True, help="Difference between the computed ending balance and the specified ending balance.")

    line_ids = fields.One2many('account.bank.statement.line', 'statement_id', string='Statement lines', states={'confirm': [('readonly', True)]}, copy=True)
    move_line_ids = fields.One2many('account.move.line', 'statement_id', string='Entry lines', states={'confirm': [('readonly', True)]})
    move_line_count = fields.Integer(compute="_get_move_line_count")

    all_lines_reconciled = fields.Boolean(compute='_check_lines_reconciled')
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    cashbox_start_id = fields.Many2one('account.bank.statement.cashbox', string="Starting Cashbox")
    cashbox_end_id = fields.Many2one('account.bank.statement.cashbox', string="Ending Cashbox")
    is_difference_zero = fields.Boolean(compute='_is_difference_zero', string='Is zero', help="Check if difference is zero.")

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self._set_opening_balance(self.journal_id.id)

    @api.multi
    def _balance_check(self):
        for stmt in self:
            if not stmt.currency_id.is_zero(stmt.difference):
                if stmt.journal_type == 'cash':
                    if stmt.difference < 0.0:
                        account = stmt.journal_id.loss_account_id
                        name = _('Loss')
                    else:
                        # statement.difference > 0.0
                        account = stmt.journal_id.profit_account_id
                        name = _('Profit')
                    if not account:
                        raise UserError(_('There is no account defined on the journal %s for %s involved in a cash difference.') % (stmt.journal_id.name, name))

                    values = {
                        'statement_id': stmt.id,
                        'account_id': account.id,
                        'amount': stmt.difference,
                        'name': _("Cash difference observed during the counting (%s)") % name,
                    }
                    self.env['account.bank.statement.line'].create(values)
                else:
                    balance_end_real = formatLang(self.env, stmt.balance_end_real, currency_obj=stmt.currency_id)
                    balance_end = formatLang(self.env, stmt.balance_end, currency_obj=stmt.currency_id)
                    raise UserError(_('The ending balance is incorrect !\nThe expected balance (%s) is different from the computed one. (%s)')
                        % (balance_end_real, balance_end))
        return True

    @api.multi
    def unlink(self):
        for statement in self:
            if statement.state != 'open':
                raise UserError(_('In order to delete a bank statement, you must first cancel it to delete related journal items.'))
            # Explicitly unlink bank statement lines so it will check that the related journal entries have been deleted first
            statement.line_ids.unlink()
        return super(AccountBankStatement, self).unlink()

    @api.multi
    def open_cashbox_id(self):
        context = dict(self.env.context or {})
        if context.get('cashbox_id'):
            context['active_id'] = self.id
            return {
                'name': _('Cash Control'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.bank.statement.cashbox',
                'view_id': self.env.ref('account.view_account_bnk_stmt_cashbox').id,
                'type': 'ir.actions.act_window',
                'res_id': self.env.context.get('cashbox_id'),
                'context': context,
                'target': 'new'
            }

    @api.multi
    def check_confirm_bank(self):
        if self.journal_type == 'cash' and not self.currency_id.is_zero(self.difference):
            action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_view_account_bnk_stmt_check')
            if action_rec:
                action = action_rec.read([])[0]
                return action
        return self.button_confirm_bank()

    @api.multi
    def button_confirm_bank(self):
        self._balance_check()
        statements = self.filtered(lambda r: r.state == 'open')
        for statement in statements:
            moves = self.env['account.move']
            # `line.journal_entry_ids` gets invalidated from the cache during the loop
            # because new move lines are being created at each iteration.
            # The below dict is to prevent the ORM to permanently refetch `line.journal_entry_ids`
            line_journal_entries = {line: line.journal_entry_ids for line in statement.line_ids}
            for st_line in statement.line_ids:
                #upon bank statement confirmation, look if some lines have the account_id set. It would trigger a journal entry
                #creation towards that account, with the wanted side-effect to skip that line in the bank reconciliation widget.
                journal_entries = line_journal_entries[st_line]
                st_line.fast_counterpart_creation()
                if not st_line.account_id and not journal_entries.ids and not st_line.statement_id.currency_id.is_zero(st_line.amount):
                    raise UserError(_('All the account entries lines must be processed in order to close the statement.'))
            moves = statement.mapped('line_ids.journal_entry_ids.move_id')
            if moves:
                moves.filtered(lambda m: m.state != 'posted').post()
            statement.message_post(body=_('Statement %s confirmed, journal items were created.') % (statement.name,))
        statements.write({'state': 'confirm', 'date_done': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def button_journal_entries(self):
        return {
            'name': _('Journal Entries'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', self.mapped('move_line_ids').mapped('move_id').ids)],
            'context': {
                'journal_id': self.journal_id.id,
            }
        }

    @api.multi
    def button_open(self):
        """ Changes statement state to Running."""
        for statement in self:
            if not statement.name:
                context = {'ir_sequence_date': statement.date}
                if statement.journal_id.sequence_id:
                    st_number = statement.journal_id.sequence_id.with_context(**context).next_by_id()
                else:
                    SequenceObj = self.env['ir.sequence']
                    st_number = SequenceObj.with_context(**context).next_by_code('account.bank.statement')
                statement.name = st_number
            statement.state = 'open'


class AccountBankStatementLine(models.Model):
    _name = "account.bank.statement.line"
    _description = "Bank Statement Line"
    _order = "statement_id desc, date, sequence, id desc"

    name = fields.Char(string='Label', required=True)
    date = fields.Date(required=True, default=lambda self: self._context.get('date', fields.Date.context_today(self)))
    amount = fields.Monetary(digits=0, currency_field='journal_currency_id')
    journal_currency_id = fields.Many2one('res.currency', string="Journal's Currency", related='statement_id.currency_id',
        help='Utility field to express amount currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    account_number = fields.Char(string='Bank Account Number', help="Technical field used to store the bank account number before its creation, upon the line's processing")
    bank_account_id = fields.Many2one('res.partner.bank', string='Bank Account', help="Bank account that was used in this transaction.")
    account_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated', '=', False)],
        help="This technical field can be used at the statement line creation/import time in order to avoid the reconciliation"
             " process on it later on. The statement line will simply create a counterpart on this account")
    statement_id = fields.Many2one('account.bank.statement', string='Statement', index=True, required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', related='statement_id.journal_id', string='Journal', store=True, readonly=True)
    partner_name = fields.Char(help="This field is used to record the third party name when importing bank statement in electronic format,"
             " when the partner doesn't exist yet in the database (or cannot be found).")
    ref = fields.Char(string='Reference')
    note = fields.Text(string='Notes')
    sequence = fields.Integer(index=True, help="Gives the sequence order when displaying a list of bank statement lines.", default=1)
    company_id = fields.Many2one('res.company', related='statement_id.company_id', string='Company', store=True, readonly=True)
    journal_entry_ids = fields.One2many('account.move.line', 'statement_line_id', 'Journal Items', copy=False, readonly=True)
    amount_currency = fields.Monetary(help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    currency_id = fields.Many2one('res.currency', string='Currency', help="The optional other currency if it is a multi-currency entry.")
    state = fields.Selection(related='statement_id.state', string='Status', readonly=True)
    move_name = fields.Char(string='Journal Entry Name', readonly=True,
        default=False, copy=False,
        help="Technical field holding the number given to the journal entry, automatically set when the statement line is reconciled then stored to set the same number again if the line is cancelled, set to draft and re-processed again.")

    @api.one
    @api.constrains('amount')
    def _check_amount(self):
        # Allow to enter bank statement line with an amount of 0,
        # so that user can enter/import the exact bank statement they have received from their bank in Odoo
        if self.journal_id.type != 'bank' and self.currency_id.is_zero(self.amount):
            raise ValidationError(_('The amount of a cash transaction cannot be 0.'))

    @api.one
    @api.constrains('amount', 'amount_currency')
    def _check_amount_currency(self):
        if self.amount_currency != 0 and self.amount == 0:
            raise ValidationError(_('If "Amount Currency" is specified, then "Amount" must be as well.'))

    @api.constrains('currency_id', 'journal_id')
    def _check_currency_id(self):
        for line in self:
            if not line.currency_id:
                continue

            statement_currency = line.journal_id.currency_id or line.company_id.currency_id
            if line.currency_id == statement_currency:
                raise ValidationError(_('The currency of the bank statement line must be different than the statement currency.'))

    @api.model
    def create(self, vals):
        line = super(AccountBankStatementLine, self).create(vals)
        # The most awesome fix you will ever see is below.
        # Explanation: during a 'create', the 'convert_to_cache' method is not called. Moreover, at
        # that point 'journal_currency_id' is not yet known since it is a related field. It means
        # that the 'amount' field will not be properly rounded. The line below triggers a write on
        # the 'amount' field, which will trigger the 'convert_to_cache' method, and ultimately round
        # the field correctly.
        # This is obviously an awful workaround, but at the time of writing, the ORM does not
        # provide a clean mechanism to fix the issue.
        line.amount = line.amount
        return line

    @api.multi
    def unlink(self):
        for line in self:
            if line.journal_entry_ids.ids:
                raise UserError(_('In order to delete a bank statement line, you must first cancel it to delete related journal items.'))
        return super(AccountBankStatementLine, self).unlink()

    @api.multi
    def button_cancel_reconciliation(self):

        for st_line in self:
            if not st_line.partner_id:
                move_id = st_line.journal_entry_ids.mapped('move_id')
                move_id.button_cancel()
                st_line.journal_entry_ids.unlink()
                move_id.unlink()
            else:
                created_move_ids = st_line.journal_entry_ids.filtered(lambda r: r.move_id.journal_id.id in [10, 53]).mapped('move_id')

                payment = self.env['account.payment'].search([('statement_line_id', '=', st_line.id),
                                                              ('state', '!=', 'cancelled')])
                if payment:
                    payment.move_line_ids.filtered(lambda x: x.full_reconcile_id).remove_move_reconcile()
                    payment.cancel()
                # todo: ara devirleri sil
                st_line.write({
                    'journal_entry_ids': [(6, 0, [])], # Empty account move lines
                })
                if created_move_ids:
                    created_move_ids.button_cancel()
                    created_move_ids.mapped('line_ids').unlink()
                    created_move_ids.unlink()


    ####################################################
    # Reconciliation methods
    ####################################################

    def _get_common_sql_query(self, overlook_partner = False, excluded_ids = None, split = False):
        acc_type = "acc.reconcile = true"
        select_clause = "SELECT aml.id "
        from_clause = "FROM account_move_line aml JOIN account_account acc ON acc.id = aml.account_id "
        account_clause = ''
        if self.journal_id.default_credit_account_id and self.journal_id.default_debit_account_id:
            account_clause = "(aml.statement_id IS NULL AND aml.account_id IN %(account_payable_receivable)s AND aml.payment_id IS NOT NULL) OR"
        where_clause = """WHERE aml.company_id = %(company_id)s
                          AND (
                                    """ + account_clause + """
                                    ("""+acc_type+""" AND aml.reconciled = false)
                          )"""
        where_clause = where_clause + ' AND aml.partner_id = %(partner_id)s' if self.partner_id else where_clause
        where_clause = where_clause + ' AND aml.id NOT IN %(excluded_ids)s' if excluded_ids else where_clause
        if split:
            return select_clause, from_clause, where_clause
        return select_clause + from_clause + where_clause

    def _prepare_reconciliation_move(self, move_ref):
        """ Prepare the dict of values to create the move from a statement line. This method may be overridden to adapt domain logic
            through model inheritance (make sure to call super() to establish a clean extension chain).

           :param char move_ref: will be used as the reference of the generated account move
           :return: dict of value to create() the account.move
        """
        ref = move_ref or ''
        if self.ref:
            ref = move_ref + ' - ' + self.ref if move_ref else self.ref
        data = {
            'journal_id': self.statement_id.journal_id.id,
            'date': self.statement_id.accounting_date or self.date,
            'ref': ref,
        }
        if self.move_name:
            data.update(name=self.move_name)
        return data

    def _prepare_reconciliation_move_line(self, move, amount):
        """ Prepare the dict of values to balance the move.

            :param recordset move: the account.move to link the move line
            :param dict move: a dict of vals of a account.move which will be created later
            :param float amount: the amount of transaction that wasn't already reconciled
        """
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency
        amount_currency = False
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        if isinstance(move, dict):
            amount_sum = sum(x[2].get('amount_currency', 0) for x in move['line_ids'])
        else:
            amount_sum = sum(x.amount_currency for x in move.line_ids)
        # We have several use case here to compare the currency and amount currency of counterpart line to balance the move:
        if st_line_currency != company_currency and st_line_currency == statement_currency:
            # company in currency A, statement in currency B and transaction in currency B
            # counterpart line must have currency B and correct amount is inverse of already existing lines
            amount_currency = -amount_sum
        elif st_line_currency != company_currency and statement_currency == company_currency:
            # company in currency A, statement in currency A and transaction in currency B
            # counterpart line must have currency B and correct amount is inverse of already existing lines
            amount_currency = -amount_sum
        elif st_line_currency != company_currency and st_line_currency != statement_currency:
            # company in currency A, statement in currency B and transaction in currency C
            # counterpart line must have currency B and use rate between B and C to compute correct amount
            amount_currency = -amount_sum/st_line_currency_rate
        elif st_line_currency == company_currency and statement_currency != company_currency:
            # company in currency A, statement in currency B and transaction in currency A
            # counterpart line must have currency B and amount is computed using the rate between A and B
            amount_currency = amount/st_line_currency_rate

        # last case is company in currency A, statement in currency A and transaction in currency A
        # and in this case counterpart line does not need any second currency nor amount_currency

        aml_dict = {
            'name': self.name,
            'partner_id': self.partner_id and self.partner_id.id or False,
            'account_id': amount >= 0 \
                and self.statement_id.journal_id.default_credit_account_id.id \
                or self.statement_id.journal_id.default_debit_account_id.id,
            'credit': amount < 0 and -amount or 0.0,
            'debit': amount > 0 and amount or 0.0,
            'statement_line_id': self.id,
            'currency_id': statement_currency != company_currency and statement_currency.id or (st_line_currency != company_currency and st_line_currency.id or False),
            'amount_currency': amount_currency,
        }
        if isinstance(move, self.env['account.move'].__class__):
            aml_dict['move_id'] = move.id
        return aml_dict

    @api.multi
    def fast_counterpart_creation(self):
        """This function is called when confirming a bank statement and will allow to automatically process lines without
        going in the bank reconciliation widget. By setting an account_id on bank statement lines, it will create a journal
        entry using that account to counterpart the bank account
        """
        payment_list = []
        move_list = []
        account_type_receivable = self.env.ref('account.data_account_type_receivable')
        already_done_stmt_line_ids = [a['statement_line_id'][0] for a in self.env['account.move.line'].read_group([('statement_line_id', 'in', self.ids)], ['statement_line_id'], ['statement_line_id'])]
        managed_st_line = []
        for st_line in self:
            # Technical functionality to automatically reconcile by creating a new move line
            if st_line.account_id and not st_line.id in already_done_stmt_line_ids:
                managed_st_line.append(st_line.id)
                # Create payment vals
                total = st_line.amount
                payment_methods = (total > 0) and st_line.journal_id.inbound_payment_method_ids or st_line.journal_id.outbound_payment_method_ids
                currency = st_line.journal_id.currency_id or st_line.company_id.currency_id
                partner_type = 'customer' if st_line.account_id.user_type_id == account_type_receivable else 'supplier'
                payment_list.append({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total > 0 and 'inbound' or 'outbound',
                    'partner_id': st_line.partner_id.id,
                    'partner_type': partner_type,
                    'journal_id': st_line.statement_id.journal_id.id,
                    'payment_date': st_line.date,
                    'state': 'reconciled',
                    'currency_id': currency.id,
                    'amount': abs(total),
                    'communication': st_line._get_communication(payment_methods[0] if payment_methods else False),
                    'name': st_line.statement_id.name or _("Bank Statement %s") % st_line.date,
                })

                # Create move and move line vals
                move_vals = st_line._prepare_reconciliation_move(st_line.statement_id.name)
                aml_dict = {
                    'name': st_line.name,
                    'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                    'credit': st_line.amount > 0 and st_line.amount or 0.0,
                    'account_id': st_line.account_id.id,
                    'partner_id': st_line.partner_id.id,
                    'statement_line_id': st_line.id,
                }
                st_line._prepare_move_line_for_currency(aml_dict, st_line.date or fields.Date.context_today())
                move_vals['line_ids'] = [(0, 0, aml_dict)]
                balance_line = self._prepare_reconciliation_move_line(
                    move_vals, -aml_dict['debit'] if st_line.amount < 0 else aml_dict['credit'])
                move_vals['line_ids'].append((0, 0, balance_line))
                move_list.append(move_vals)

        # Creates
        payment_ids = self.env['account.payment'].create(payment_list)
        for payment_id, move_vals in pycompat.izip(payment_ids, move_list):
            for line in move_vals['line_ids']:
                line[2]['payment_id'] = payment_id.id
        move_ids = self.env['account.move'].create(move_list)
        move_ids.post()

        for move, st_line, payment in pycompat.izip(move_ids, self.browse(managed_st_line), payment_ids):
            st_line.write({'move_name': move.name})
            payment.write({'payment_reference': move.name})

    def _get_communication(self, payment_method_id):
        return self.name or ''


    def process_reconciliation(self, counterpart_aml_dicts=None, payment_aml_rec=None, new_aml_dicts=None):
        """ Match statement lines with existing payments (eg. checks) and/or payables/receivables (eg. invoices and credit notes) and/or new move lines (eg. write-offs).
            If any new journal item needs to be created (via new_aml_dicts or counterpart_aml_dicts), a new journal entry will be created and will contain those
            items, as well as a journal item for the bank statement line.
            Finally, mark the statement line as reconciled by putting the matched moves ids in the column journal_entry_ids.

            :param self: browse collection of records that are supposed to have no accounting entries already linked.
            :param (list of dicts) counterpart_aml_dicts: move lines to create to reconcile with existing payables/receivables.
                The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'move_line'
                    # The move line to reconcile (partially if specified debit/credit is lower than move line's credit/debit)

            :param (list of recordsets) payment_aml_rec: recordset move lines representing existing payments (which are already fully reconciled)

            :param (list of dicts) new_aml_dicts: move lines to create. The expected keys are :
                - 'name'
                - 'debit'
                - 'credit'
                - 'account_id'
                - (optional) 'tax_ids'
                - (optional) Other account.move.line fields like analytic_account_id or analytics_id

            :returns: The journal entries with which the transaction was matched. If there was at least an entry in counterpart_aml_dicts or new_aml_dicts, this list contains
                the move created by the reconciliation, containing entries for the statement.line (1), the counterpart move lines (0..*) and the new move lines (0..*).
        """
        payable_account_type = self.env.ref('account.data_account_type_payable')
        receivable_account_type = self.env.ref('account.data_account_type_receivable')
        counterpart_aml_dicts = counterpart_aml_dicts or []
        payment_aml_rec = payment_aml_rec or self.env['account.move.line']
        new_aml_dicts = new_aml_dicts or []
        no_full_reconcile = False
        aml_obj = self.env['account.move.line']
        # Check and prepare received data
        if any(rec.statement_id for rec in payment_aml_rec):
            raise UserError(_('A selected move line was already reconciled.'))
        for aml_dict in counterpart_aml_dicts:
            if aml_dict['move_line'].reconciled:
                raise UserError(_('A selected move line was already reconciled.'))
            if isinstance(aml_dict['move_line'], pycompat.integer_types):
                aml_dict['move_line'] = aml_obj.browse(aml_dict['move_line'])

        account_types = self.env['account.account.type']
        for aml_dict in (counterpart_aml_dicts + new_aml_dicts):
            if aml_dict.get('tax_ids') and isinstance(aml_dict['tax_ids'][0], pycompat.integer_types):
                # Transform the value in the format required for One2many and Many2many fields
                aml_dict['tax_ids'] = [(4, id, None) for id in aml_dict['tax_ids']]

            user_type_id = self.env['account.account'].browse(aml_dict.get('account_id')).user_type_id
            if user_type_id in [payable_account_type, receivable_account_type] and user_type_id not in account_types:
                account_types |= user_type_id
        if any(line.journal_entry_ids for line in self):
            raise UserError(_('A selected statement line was already reconciled with an account move.'))
        # Fully reconciled moves are just linked to the bank statement
        amls_to_check = aml_obj
        for aml in counterpart_aml_dicts:
            amls_to_check |= aml.get('move_line', aml_obj)
        if len(amls_to_check.mapped('account_id')) > 1:
            raise UserError(_('You can only reconcile journal items with the same account.'))
        total = self.amount
        date = self.date or fields.Date.today()

        # Create move line(s). Either matching an existing journal entry (eg. invoice), in which
        # case we reconcile the existing and the new move lines together, or being a write-off.
        if self.partner_id:

            # Create the move
            self.sequence = self.statement_id.line_ids.ids.index(self.id) + 1

            # Create The payment
            payment = self.env['account.payment']
            partner_id = self.partner_id or (aml_dict.get('move_line') and aml_dict['move_line'].partner_id) or self.env['res.partner']
            if abs(total) > 0.00001:
                partner_type = False
                if partner_id and len(account_types) == 1:
                    partner_type = 'customer' if account_types == receivable_account_type else 'supplier'
                if partner_id and not partner_type:
                    if total < 0:
                        partner_type = 'supplier'
                    else:
                        partner_type = 'customer'

                payment_methods = (total>0) and self.journal_id.inbound_payment_method_ids or self.journal_id.outbound_payment_method_ids
                currency = self.journal_id.currency_id or self.company_id.currency_id

                payment = self.env['account.payment'].create({
                    'payment_method_id': payment_methods and payment_methods[0].id or False,
                    'payment_type': total > 0 and 'inbound' or 'outbound',
                    'partner_id': partner_id.id,
                    'partner_type': partner_type,
                    'journal_id': self.statement_id.journal_id.id,
                    'payment_date': self.date,
                    'statement_line_id': self.id,
                    'state': 'draft',
                    'payment_reference': self.name,
                    'currency_id': currency.id,
                    'amount': abs(total),
                    'communication': self._get_communication(payment_methods[0] if payment_methods else False),
                    'name': self.statement_id.name or _("Bank Statement %s") % self.date,
                })
                payment.post()
                self.write({
                    'journal_entry_ids': [(6, 0, payment.move_line_ids.ids)],
                    'move_name': self.name,
                })
                # todo payment move id will be written in self.move_line_ids

            journal_accounts = self.journal_id.default_debit_account_id + self.journal_id.default_credit_account_id

            amls_to_reconcile = payment.move_line_ids.filtered(lambda r: r.account_id not in journal_accounts)

            for aml in counterpart_aml_dicts:
                amls_to_reconcile |= aml.get('move_line', aml_obj)

            # Create write-offs
            for aml_dict in new_aml_dicts:
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['statement_line_id'] = self.id

                account_id = self.env['account.account'].browse(aml_dict['account_id'])
                if account_id.code == '100.D':
                    aml_dict['journal_id'] = 10
                elif account_id.code == '679':
                    aml_dict['journal_id'] = 53
                else:
                    aml_dict['journal_id'] = self.statement_id.journal_id.id
                # swap  debit and credit values
                debit = aml_dict['debit']
                aml_dict['debit'] = aml_dict['credit']
                aml_dict['credit'] = debit
                self._prepare_move_line_for_currency(aml_dict, date)
                if account_id not in self.partner_id.property_account_receivable_id + self.partner_id.property_account_payable_id:
                    amls_to_reconcile |= amls_to_reconcile._create_writeoff([aml_dict])
                else:
                    no_full_reconcile = True

            if not no_full_reconcile:
                amls_to_reconcile.reconcile()
                if not amls_to_reconcile.mapped('full_reconcile_id'):
                    raise UserError(_('Full reconcilation process is failed. Aborted.\n'))
        else:
            move_vals = self._prepare_reconciliation_move(self.statement_id.name)
            aml_to_create = []
            for st_line in self:
                account_id = st_line.amount > 0 and st_line.journal_id.default_credit_account_id.id or\
                             st_line.journal_id.default_debit_account_id.id
                aml_dict = {
                    'name': st_line.name,
                    'debit': st_line.amount > 0 and st_line.amount or 0.0,
                    'credit': st_line.amount < 0 and -st_line.amount or 0.0,
                    'account_id': account_id,
                    'partner_id': st_line.partner_id.id,
                    'statement_line_id': st_line.id,
                }
                st_line._prepare_move_line_for_currency(aml_dict, st_line.date or fields.Date.today())
                aml_to_create.append(aml_dict)

            for aml_dict in new_aml_dicts:
                aml_dict['partner_id'] = self.partner_id.id
                aml_dict['statement_line_id'] = self.id
                account_id = self.env['account.account'].browse(aml_dict['account_id'])
                if account_id.code == '100.D':
                    aml_dict['journal_id'] = 10
                elif account_id.code == '679':
                    aml_dict['journal_id'] = 53
                else:
                    aml_dict['journal_id'] = self.statement_id.journal_id.id
                self._prepare_move_line_for_currency(aml_dict, date)
                aml_to_create.append(aml_dict)

            move_vals['line_ids'] = [(0, 0, line) for line in aml_to_create]
            move = self.env['account.move'].create(move_vals)
            move.post()
            self.write({'move_name': move.display_name, 'journal_entry_ids': [(6, 0, move.line_ids.ids)]})
            return move

        #create the res.partner.bank if needed
        if self.account_number and self.partner_id and not self.bank_account_id:
            # Search bank account without partner to handle the case the res.partner.bank already exists but is set
            # on a different partner.
            bank_account = self.env['res.partner.bank'].search([('company_id', '=', self.company_id.id),('acc_number', '=', self.account_number)])
            if not bank_account:
                bank_account = self.env['res.partner.bank'].create({
                    'acc_number': self.account_number, 'partner_id': self.partner_id.id
                })
            self.bank_account_id = bank_account

        return True

    @api.multi
    def _prepare_move_line_for_currency(self, aml_dict, date):
        self.ensure_one()
        company_currency = self.journal_id.company_id.currency_id
        statement_currency = self.journal_id.currency_id or company_currency
        st_line_currency = self.currency_id or statement_currency
        st_line_currency_rate = self.currency_id and (self.amount_currency / self.amount) or False
        company = self.company_id

        partner_currency = self.partner_id and self.partner_id.partner_currency_id or company_currency

        if partner_currency != company_currency and partner_currency != statement_currency:
            if aml_dict.get('move_line', False):
                aml_dict['amount_currency'] = aml_dict['move_line'].amount_residual_currency
                aml_dict['currency_id'] = aml_dict['move_line'].currency_id.id
                aml_dict['debit'] = aml_dict['move_line'].debit
                aml_dict['credit'] = aml_dict['move_line'].credit
            else:
                aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
                aml_dict['currency_id'] = partner_currency.id
                aml_dict['debit'] = partner_currency._convert(aml_dict['debit'] , company_currency, company, date)
                aml_dict['credit'] = partner_currency._convert(aml_dict['credit'] , company_currency, company, date)


        if st_line_currency.id != company_currency.id:
            aml_dict['amount_currency'] = aml_dict['debit'] - aml_dict['credit']
            aml_dict['currency_id'] = st_line_currency.id
            if self.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                # Statement is in company currency but the transaction is in foreign currency
                aml_dict['debit'] = company_currency.round(aml_dict['debit'] / st_line_currency_rate)
                aml_dict['credit'] = company_currency.round(aml_dict['credit'] / st_line_currency_rate)
            elif self.currency_id and st_line_currency_rate:
                # Statement is in foreign currency and the transaction is in another one
                aml_dict['debit'] = statement_currency._convert(aml_dict['debit'] / st_line_currency_rate, company_currency, company, date)
                aml_dict['credit'] = statement_currency._convert(aml_dict['credit'] / st_line_currency_rate, company_currency, company, date)
            else:
                # Statement is in foreign currency and no extra currency is given for the transaction
                aml_dict['debit'] = st_line_currency._convert(aml_dict['debit'], company_currency, company, date)
                aml_dict['credit'] = st_line_currency._convert(aml_dict['credit'], company_currency, company, date)
        elif statement_currency.id != company_currency.id:
            # Statement is in foreign currency but the transaction is in company currency
            prorata_factor = (aml_dict['debit'] - aml_dict['credit']) / self.amount_currency
            aml_dict['amount_currency'] = prorata_factor * self.amount
            aml_dict['currency_id'] = statement_currency.id

    def _check_invoice_state(self, invoice):
        if invoice.state == 'in_payment' and all([payment.state == 'reconciled' for payment in invoice.mapped('payment_move_line_ids.payment_id')]):
           invoice.write({'state': 'paid'})

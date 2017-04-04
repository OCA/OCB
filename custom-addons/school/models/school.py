# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import date, datetime
from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.modules import get_module_resource
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, image_colorize,\
    image_resize_image_big
from odoo.exceptions import except_orm, Warning as UserError


class BoardBoard(models.AbstractModel):
    _name = "board.board"


class AcademicYear(models.Model):
    ''' Defines an academic year '''
    _name = "academic.year"
    _description = "Academic Year"
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True,
                              help="Sequence order you want to see this year.")
    name = fields.Char('Name', required=True,
                       help='Name of academic year')
    code = fields.Char('Code', required=True,
                       help='Code of academic year')
    date_start = fields.Date('Start Date', required=True,
                             help='Starting date of academic year')
    date_stop = fields.Date('End Date', required=True,
                            help='Ending of academic year')
    month_ids = fields.One2many('academic.month', 'year_id', 'Months',
                                help="related Academic months")
    grade_id = fields.Many2one('grade.master', "Grade")
    description = fields.Text('Description')

    @api.model
    def next_year(self, sequence):
        year_ids = self.search([('sequence', '>', sequence)],
                               order='id ASC', limit=1)
        if year_ids:
            return year_ids.id
        return False

    @api.multi
    def name_get(self):
        res = []
        for acd_year_rec in self:
            name = "[" + acd_year_rec['code'] + "]" + acd_year_rec['name']
            res.append((acd_year_rec['id'], name))
        return res

    @api.constrains('date_start', 'date_stop')
    def _check_academic_year(self):
        obj_academic_ids = self.search([])
        academic_list = []
        for rec_academic in obj_academic_ids:
            academic_list.append(rec_academic.id)
        for current_academic_yr in self:
            academic_list.remove(current_academic_yr.id)
            data_academic_yr = self.browse(academic_list)
            for old_ac in data_academic_yr:
                if old_ac.date_start <= self.date_start <= old_ac.date_stop\
                   or old_ac.date_start <= self.date_stop <= old_ac.date_stop:
                        raise UserError(_('Error! You cannot define\
                                         overlapping academic years.'))

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if (self.date_stop and self.date_start and
                self.date_stop < self.date_start):
            raise UserError(_('Error! The duration of the academic year\
                             is invalid.'))


class AcademicMonth(models.Model):
    ''' Defining a month of an academic year '''
    _name = "academic.month"
    _description = "Academic Month"
    _order = "date_start"

    name = fields.Char('Name', required=True, help='Name of Academic month')
    code = fields.Char('Code', required=True, help='Code of Academic month')
    date_start = fields.Date('Start of Period', required=True,
                             help='Starting of academic month')
    date_stop = fields.Date('End of Period', required=True,
                            help='Ending of academic month')
    year_id = fields.Many2one('academic.year', 'Academic Year', required=True,
                              help="Related academic year ")
    description = fields.Text('Description')

    @api.constrains('date_start', 'date_stop')
    def _check_duration(self):
        if (self.date_stop and self.date_start and self.date_stop <
                self.date_start):
            raise UserError(_('Error ! The duration of the Month(s)\
                             is/are invalid.'))

    @api.constrains('year_id', 'date_start', 'date_stop')
    def _check_year_limit(self):
        if self.year_id and self.date_start and self.date_stop:
            if (self.year_id.date_stop < self.date_stop or
                    self.year_id.date_stop < self.date_start or
                    self.year_id.date_start > self.date_start or
                    self.year_id.date_start > self.date_stop):
                raise UserError(_('Invalid Months ! Some months overlap or\
                                   the date period is not in the scope of the\
                                   academic year.'))


class StandardMedium(models.Model):
    ''' Defining a medium(ENGLISH, HINDI, GUJARATI) related to standard'''
    _name = "standard.medium"
    _description = "Standard Medium"
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')


class StandardDivision(models.Model):
    ''' Defining a division(A, B, C) related to standard'''
    _name = "standard.division"
    _description = "Standard Division"
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')


class StandardStandard(models.Model):
    ''' Defining Standard Information '''
    _name = 'standard.standard'
    _description = 'Standard Information'
    _order = "sequence"

    sequence = fields.Integer('Sequence', required=True)
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    description = fields.Text('Description')

    @api.model
    def next_standard(self, sequence):
        stand_ids = self.search([('sequence', '>', sequence)],
                                order='id ASC', limit=1)
        if stand_ids:
            return stand_ids.id
        return False


class SchoolStandard(models.Model):
    ''' Defining a standard related to school '''
    _name = 'school.standard'
    _description = 'School Standards'
    _rec_name = "school_id"

    @api.multi
    @api.depends('standard_id')
    def _compute_student(self):
        self.student_ids = False
        domain = [('standard_id', '=', self.standard_id.id)]
        if self.standard_id:
            self.student_ids = self.env['student.student'].search(domain)

    @api.multi
    def import_subject(self):
        for im_ob in self:
            domain = [('standard_id', '=', int(im_ob.standard_id) - 1)]
            import_sub_ids = self.search(domain)
            val = [last.id for sub in import_sub_ids
                   for last in sub.subject_ids]
            self.write({'subject_ids': [(6, 0, val)]})
        return True

    school_id = fields.Many2one('school.school', 'School', required=True)
    standard_id = fields.Many2one('standard.standard', 'Class', required=True)
    division_id = fields.Many2one('standard.division', 'Division',
                                  required=True)
    medium_id = fields.Many2one('standard.medium', 'Medium', required=True)
    subject_ids = fields.Many2many('subject.subject', 'subject_standards_rel',
                                   'subject_id', 'standard_id', 'Subject')
    user_id = fields.Many2one('hr.employee', 'Class Teacher')
    student_ids = fields.One2many('student.student', 'standard_id',
                                  'Student In Class',
                                  compute='_compute_student', store=True)
    color = fields.Integer('Color Index')
    passing = fields.Integer('No Of ATKT', help="Allowed No of ATKTs")
    cmp_id = fields.Many2one('res.company', 'Company Name',
                             related='school_id.company_id', store=True)

    @api.multi
    def name_get(self):
        res = []
        for standard in self:
            div_n = "[" + standard.division_id.name + "]"
            name = standard.standard_id.name + div_n
            res.append((standard.id, name))
        return res


class SchoolSchool(models.Model):
    ''' Defining School Information '''
    _name = 'school.school'
    _inherits = {'res.company': 'company_id'}
    _description = 'School Information'
    _rec_name = "com_name"

    @api.model
    def _lang_get(self):
        languages = self.env['res.lang'].search([])
        return [(language.code, language.name) for language in languages]

    company_id = fields.Many2one('res.company', 'Company', ondelete="cascade",
                                 required=True)
    com_name = fields.Char('School Name', related='company_id.name',
                           store=True)
    code = fields.Char('Code', required=True)
    standards = fields.One2many('school.standard', 'school_id',
                                'Standards')
    lang = fields.Selection(_lang_get, 'Language',
                            help='If the selected language is loaded\
                            in the system, all documents related to this\
                            partner will be printed in this language.\
                            If not, it will be English.')


class SubjectSubject(models.Model):
    '''Defining a subject '''
    _name = "subject.subject"
    _description = "Subjects"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    maximum_marks = fields.Integer("Maximum marks")
    minimum_marks = fields.Integer("Minimum marks")
    weightage = fields.Integer("WeightAge")
    teacher_ids = fields.Many2many('hr.employee', 'subject_teacher_rel',
                                   'subject_id', 'teacher_id', 'Teachers')
    standard_ids = fields.Many2many('school.standard', 'subject_standards_rel',
                                    'standard_id', 'subject_id', 'Standards')
    standard_id = fields.Many2one('standard.standard', 'Class')
    is_practical = fields.Boolean('Is Practical',
                                  help='Check this if subject is practical.')
    no_exam = fields.Boolean("No Exam",
                             help='Check this if subject has no exam.')
    elective_id = fields.Many2one('subject.elective')
    student_ids = fields.Many2many('student.student',
                                   'elective_subject_student_rel',
                                   'subject_id', 'student_id', 'Students')
    syllabus_ids = fields.One2many('subject.syllabus', 'subject_id',
                                   'Syllabus')


class SubjectSyllabus(models.Model):
    '''Defining a  syllabus'''
    _name = "subject.syllabus"
    _description = "Syllabus"
    _rec_name = "duration"

    subject_id = fields.Many2one('subject.subject', 'Subject')
    duration = fields.Char("Duration")
    topic = fields.Text("Topic")


class SubjectElective(models.Model):
    ''' Defining Subject Elective '''
    _name = 'subject.elective'

    name = fields.Char("Name")
    subject_ids = fields.One2many('subject.subject', 'elective_id',
                                  'Elective Subjects')


class StudentStudent(models.Model):
    ''' Defining a student information '''
    _name = 'student.student'
    _table = "student_student"
    _description = 'Student Information'
    _inherits = {'res.users': 'user_id'}

    @api.multi
    @api.depends('date_of_birth')
    def _calc_age(self):
        self.age = 0
        if self.date_of_birth:
            start = datetime.strptime(self.date_of_birth,
                                      DEFAULT_SERVER_DATE_FORMAT)
            end = datetime.strptime(time.strftime(DEFAULT_SERVER_DATE_FORMAT),
                                    DEFAULT_SERVER_DATE_FORMAT)
            self.age = ((end - start).days / 365)

    @api.model
    def create(self, vals):
        if vals.get('pid', False):
            vals['login'] = vals['pid']
            vals['password'] = vals['pid']
        else:
            raise except_orm(_('Error!'),
                             _('PID not valid'
                               'so record will not be saved.'))
        result = super(StudentStudent, self).create(vals)
        return result

    @api.model
    def _get_default_image(self, is_company, colorize=False):
        img_path = get_module_resource('base', 'static/src/img', 'avatar.png')
        image = None
        with open(img_path, 'rb') as f:
            image = f.read()
        image = image_colorize(image)
        return image_resize_image_big(image.encode('base64'))

    user_id = fields.Many2one('res.users', 'User ID', ondelete="cascade",
                              required=True)
    student_name = fields.Char('Student Name', related='user_id.name',
                               store=True, readonly=True)
    pid = fields.Char('Student ID', required=True, default=lambda obj:
                      obj.env['ir.sequence'].next_by_code('student.student'),
                      help='Personal IDentification Number')
    reg_code = fields.Char('Registration Code',
                           help='Student Registration Code')
    student_code = fields.Char('Student Code')
    contact_phone1 = fields.Char('Phone no.',)
    contact_mobile1 = fields.Char('Mobile no',)
    roll_no = fields.Integer('Roll No.', readonly=True)
    photo = fields.Binary('Photo', default=lambda self: self._get_default_image
                          (self._context.get('default_is_company',
                                             False)))
    year = fields.Many2one('academic.year', 'Academic Year', required=True,
                           states={'done': [('readonly', True)]})
    cast_id = fields.Many2one('student.cast', 'Religion')
    admission_date = fields.Date('Admission Date', default=date.today())
    middle = fields.Char('Middle Name', required=True,
                         states={'done': [('readonly', True)]})
    last = fields.Char('Surname', required=True,
                       states={'done': [('readonly', True)]})
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              'Gender', states={'done': [('readonly', True)]})
    date_of_birth = fields.Date('BirthDate', required=True,
                                states={'done': [('readonly', True)]})
    mother_tongue = fields.Many2one('mother.toungue', "Mother Tongue")
    age = fields.Integer('Age', _compute_='_calc_age', readonly=True)
    maritual_status = fields.Selection([('unmarried', 'Unmarried'),
                                        ('married', 'Married')],
                                       'Marital Status',
                                       states={'done': [('readonly', True)]})
    reference_ids = fields.One2many('student.reference', 'reference_id',
                                    'References',
                                    states={'done': [('readonly', True)]})
    previous_school_ids = fields.One2many('student.previous.school',
                                          'previous_school_id',
                                          'Previous School Detail',
                                          states={'done': [('readonly',
                                                            True)]})
    family_con_ids = fields.One2many('student.family.contact',
                                     'family_contact_id',
                                     'Family Contact Detail',
                                     states={'done': [('readonly', True)]})
    doctor = fields.Char('Doctor Name', states={'done': [('readonly', True)]})
    designation = fields.Char('Designation')
    doctor_phone = fields.Char('Phone')
    blood_group = fields.Char('Blood Group',)
    height = fields.Float('Height')
    weight = fields.Float('Weight')
    eye = fields.Boolean('Eyes')
    ear = fields.Boolean('Ears')
    nose_throat = fields.Boolean('Nose & Throat')
    respiratory = fields.Boolean('Respiratory')
    cardiovascular = fields.Boolean('Cardiovascular')
    neurological = fields.Boolean('Neurological')
    muskoskeletal = fields.Boolean('Musculoskeletal')
    dermatological = fields.Boolean('Dermatological')
    blood_pressure = fields.Boolean('Blood Pressure')
    remark = fields.Text('Remark', states={'done': [('readonly', True)]})
    school_id = fields.Many2one('school.school', 'School',
                                states={'done': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'),
                              ('done', 'Done'),
                              ('terminate', 'Terminate'),
                              ('alumni', 'Alumni')],
                             'State', readonly=True, default='draft')
    history_ids = fields.One2many('student.history', 'student_id', 'History')
    certificate_ids = fields.One2many('student.certificate', 'student_id',
                                      'Certificate')
    student_discipline_line = fields.One2many('student.descipline',
                                              'student_id', 'Descipline')
    address_ids = fields.One2many('res.partner', 'student_id', 'Contacts')
    document = fields.One2many('student.document', 'doc_id', 'Documents')
    description = fields.One2many('student.description', 'des_id',
                                  'Description')
    student_id = fields.Many2one('student.student', 'name')
    contact_phone = fields.Char('Phone No', related='student_id.phone')
    contact_mobile = fields.Char('Mobile No', related='student_id.mobile')
    student_id = fields.Many2one('student.student', 'Name')
    contact_phone = fields.Char('Phone No', related='student_id.phone',
                                readonly=True)
    contact_mobile = fields.Char('Mobile No', related='student_id.mobile',
                                 readonly=True)
    contact_email = fields.Char('Email', related='student_id.email',
                                readonly=True)
    contact_website = fields.Char('WebSite', related='student_id.website',
                                  readonly=True)
    award_list = fields.One2many('student.award', 'award_list_id',
                                 'Award List')
    student_status = fields.Selection('Status', related='student_id.state',
                                      help="Shows Status Of Student",
                                      readonly=True)
    stu_name = fields.Char('First Name', related='user_id.name',
                           readonly=True)
    Acadamic_year = fields.Char('Academic Year', related='year.name',
                                help='Academic Year', readonly=True)
    grn_number = fields.Many2one('student.grn', 'GR No.',
                                 help="General Register No.")
    standard_id = fields.Many2one('standard.standard', 'Class')
    division_id = fields.Many2one('standard.division', 'Division')
    medium_id = fields.Many2one('standard.medium', 'Medium')
    cmp_id = fields.Many2one('res.company', 'Company Name',
                             related='school_id.company_id', store=True)
    standard_id = fields.Many2one('school.standard', 'Standard')
    parent_id = fields.Many2many('res.partner', 'student_parent_rel',
                                 'student_id', 'parent_id', 'Parent(s)',
                                 states={'done': [('readonly', True)]})

    _sql_constraints = [('grn_unique', 'unique(grn_number)',
                         'GRN Number must be unique!')]

    @api.multi
    def set_to_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def set_alumni(self):
        self.write({'state': 'alumni'})
        return True

    @api.multi
    def set_terminate(self):
        self.write({'state': 'terminate'})
        return True

    @api.multi
    def set_done(self):
        self.write({'state': 'done'})
        return True

    @api.multi
    def admission_draft(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def admission_done(self):
        school_standard_obj = self.env['school.standard']
        for student_data in self:
            if student_data.age <= 5:
                raise except_orm(_('Warning'),
                                 _('The student is not eligible.'
                                   'Age is not valid.'))
            domain = [('standard_id', '=', student_data.standard_id.id)]
            school_standard_search_ids = school_standard_obj.search(domain)
            if not school_standard_search_ids:
                raise except_orm(_('Warning'),
                                 _('The standard is not defined'
                                   'in a school'))
            student_search_ids = self.search(domain)
            number = 1
            if student_search_ids:
                self.write({'roll_no': number})
                number += 1
            reg_code = self.env['ir.sequence'].\
                next_by_code('student.registration')
            registation_code = str(student_data.school_id.state_id.name)\
                + str('/') + str(student_data.school_id.city)\
                + str('/')\
                + str(student_data.school_id.name) + str('/')\
                + str(reg_code)
            stu_code = self.env['ir.sequence'].next_by_code('student.code')
            student_code = str(student_data.school_id.code) + str('/')\
                + str(student_data.year.code) + str('/') + str(stu_code)
        self.write({'state': 'done',
                    'admission_date': time.strftime('%Y-%m-%d'),
                    'student_code': student_code,
                    'reg_code': registation_code})
        return True


class StudentGrn(models.Model):
    _name = "student.grn"
    _rec_name = "grn_no"

    @api.multi
    def _grn_no(self):
        for stud_grn in self:
            grn_no1 = " "
            grn_no2 = " "
            grn_no1 = stud_grn['grn']
            if stud_grn['prefix'] == 'static':
                grn_no1 = stud_grn['static_prefix'] + stud_grn['grn']
            elif stud_grn['prefix'] == 'school':
                a = stud_grn.schoolprefix_id.code
                grn_no1 = a + stud_grn['grn']
            elif stud_grn['prefix'] == 'year':
                grn_no1 = time.strftime('%Y') + stud_grn['grn']
            elif stud_grn['prefix'] == 'month':
                grn_no1 = time.strftime('%m') + stud_grn['grn']
            grn_no2 = grn_no1
            if stud_grn['postfix'] == 'static':
                grn_no2 = grn_no1 + stud_grn['static_postfix']
            elif stud_grn['postfix'] == 'school':
                b = stud_grn.schoolpostfix_id.code
                grn_no2 = grn_no1 + b
            elif stud_grn['postfix'] == 'year':
                grn_no2 = grn_no1 + time.strftime('%Y')
            elif stud_grn['postfix'] == 'month':
                grn_no2 = grn_no1 + time.strftime('%m')
            self.grn_no = grn_no2

    grn = fields.Char('GR no', help='General Reg Number', readonly=True,
                      default=lambda obj:
                      obj.env['ir.sequence'].next_by_code('student.grn'))
    name = fields.Char('GRN Format Name', required=True)
    prefix = fields.Selection([('school', 'School Name'),
                               ('year', 'Year'), ('month', 'Month'),
                               ('static', 'Static String')], 'Prefix')
    schoolprefix_id = fields.Many2one('school.school',
                                      'School Name For Prefix')
    schoolpostfix_id = fields.Many2one('school.school',
                                       'School Name For Suffix')
    postfix = fields.Selection([('school', 'School Name'),
                                ('year', 'Year'), ('month', 'Month'),
                                ('static', 'Static String')], 'Suffix')
    static_prefix = fields.Char('Static String for Prefix')
    static_postfix = fields.Char('Static String for Suffix')
    grn_no = fields.Char('Generated GR No.', _compute_='_grn_no')


class MotherTongue(models.Model):
    _name = 'mother.toungue'

    name = fields.Char("Mother Tongue")


class StudentAward(models.Model):
    _name = 'student.award'

    award_list_id = fields.Many2one('student.student', 'Student')
    name = fields.Char('Award Name')
    description = fields.Char('Description')


class AttendanceType(models.Model):
    _name = "attendance.type"
    _description = "School Type"

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)


class StudentDocument(models.Model):
    _name = 'student.document'
    _rec_name = "doc_type"

    doc_id = fields.Many2one('student.student', 'Student')
    file_no = fields.Char('File No', readonly="1", default=lambda obj:
                          obj.env['ir.sequence'].
                          next_by_code('student.document'))
    submited_date = fields.Date('Submitted Date')
    doc_type = fields.Many2one('document.type', 'Document Type', required=True)
    file_name = fields.Char('File Name',)
    return_date = fields.Date('Return Date')
    new_datas = fields.Binary('Attachments')


class DocumentType(models.Model):
    ''' Defining a Document Type(SSC,Leaving)'''
    _name = "document.type"
    _description = "Document Type"
    _rec_name = "doc_type"
    _order = "seq_no"

    seq_no = fields.Char('Sequence', readonly=True, default=lambda obj:
                         obj.env['ir.sequence'].next_by_code('document.type'))
    doc_type = fields.Char('Document Type', required=True)


class StudentDescription(models.Model):
    ''' Defining a Student Description'''
    _name = 'student.description'

    des_id = fields.Many2one('student.student', 'Description')
    name = fields.Char('Name')
    description = fields.Char('Description')


class StudentDescipline(models.Model):
    _name = 'student.descipline'

    student_id = fields.Many2one('student.student', 'Student')
    teacher_id = fields.Many2one('hr.employee', 'Teacher')
    date = fields.Date('Date')
    class_id = fields.Many2one('standard.standard', 'Class')
    note = fields.Text('Note')
    action_taken = fields.Text('Action Taken')


class StudentHistory(models.Model):
    _name = "student.history"

    student_id = fields.Many2one('student.student', 'Student')
    academice_year_id = fields.Many2one('academic.year', 'Academic Year',
                                        required=True)
    standard_id = fields.Many2one('school.standard', 'Standard', required=True)
    percentage = fields.Float("Percentage", readonly=True)
    result = fields.Char('Result', readonly=True, store=True)


class StudentCertificate(models.Model):
    _name = "student.certificate"

    student_id = fields.Many2one('student.student', 'Student')
    description = fields.Char('Description')
    certi = fields.Binary('Certificate', required=True)


class HrEmployee(models.Model):
    ''' Defining a teacher information '''
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    _description = 'Teacher Information'

    @api.multi
    def _compute_subject(self):
        ''' This function will automatically computes the subjects related to\
            particular teacher.'''
        subject_obj = self.env['subject.subject']
        subject_ids = subject_obj.search([('teacher_ids', '=', self.id)])
        sub_list = []
        for sub_rec in subject_ids:
            sub_list.append(sub_rec.id)
        self.subject_ids = sub_list

    subject_ids = fields.Many2many('subject.subject', 'hr_employee_rel',
                                   'Subjects', compute='_compute_subject')


class ResPartner(models.Model):
    '''Defining a address information '''
    _inherit = 'res.partner'
    _description = 'Address Information'

    student_id = fields.Many2one('student.student', 'Student')
    parent_school = fields.Boolean('Is A Parent')
    student_ids = fields.Many2many('student.student', 'res_partner_rel',
                                   'parent_id', 'student_id', 'Children')


class StudentReference(models.Model):
    ''' Defining a student reference information '''
    _name = "student.reference"
    _description = "Student Reference"

    reference_id = fields.Many2one('student.student', 'Student')
    name = fields.Char('First Name', required=True)
    middle = fields.Char('Middle Name', required=True)
    last = fields.Char('Surname', required=True)
    designation = fields.Char('Designation', required=True)
    phone = fields.Char('Phone', required=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')],
                              'Gender')


class StudentPreviousSchool(models.Model):
    ''' Defining a student previous school information '''
    _name = "student.previous.school"
    _description = "Student Previous School"

    previous_school_id = fields.Many2one('student.student', 'Student')
    name = fields.Char('Name', required=True)
    registration_no = fields.Char('Registration No.', required=True)
    admission_date = fields.Date('Admission Date')
    exit_date = fields.Date('Exit Date')
    course_id = fields.Many2one('standard.standard', 'Course', required=True)
    add_sub = fields.One2many('academic.subject', 'add_sub_id', 'Add Subjects')


class AcademicSubject(models.Model):
    ''' Defining a student previous school information '''
    _name = "academic.subject"
    _description = "Student Previous School"

    add_sub_id = fields.Many2one('student.previous.school', 'Add Subjects',
                                 invisible=True)
    name = fields.Char('Name', required=True)
    maximum_marks = fields.Integer("Maximum marks")
    minimum_marks = fields.Integer("Minimum marks")


class StudentFamilyContact(models.Model):
    ''' Defining a student emergency contact information '''
    _name = "student.family.contact"
    _description = "Student Family Contact"

    family_contact_id = fields.Many2one('student.student', 'Student')
    rel_name = fields.Selection([('exist', 'Link to Existing Student'),
                                 ('new', 'Create New Relative Name')],
                                'Related Student', help="Select Name",
                                required=True)
    user_id = fields.Many2one('res.users', 'User ID', ondelete="cascade",
                              required=True)
    stu_name = fields.Char('Name', related='user_id.name',
                           help="Select Student From Existing List")
    name = fields.Char('Name')
    relation = fields.Many2one('student.relation.master', 'Relation',
                               required=True)
    phone = fields.Char('Phone', required=True)
    email = fields.Char('E-Mail')


class StudentRelationMaster(models.Model):
    ''' Student Relation Information '''
    _name = "student.relation.master"
    _description = "Student Relation Master"

    name = fields.Char('Name', required=True, help="Enter Relation name")
    seq_no = fields.Integer('Sequence')


class GradeMaster(models.Model):
    _name = 'grade.master'

    name = fields.Char('Grade', required=True)
    grade_ids = fields.One2many('grade.line', 'grade_id', 'Grade Name')


class GradeLine(models.Model):
    _name = 'grade.line'

    from_mark = fields.Integer('From Marks', required=True,
                               help='The grade will starts from this marks.')
    to_mark = fields.Integer('To Marks', required=True,
                             help='The grade will ends to this marks.')
    grade = fields.Char('Grade', required=True, help="Grade")
    sequence = fields.Integer('Sequence', help="Sequence order of the grade.")
    fail = fields.Boolean('Fail', help='If fail field is set to True,\
                                  it will allow you to set the grade as fail.')
    grade_id = fields.Many2one("grade.master", 'Grade')
    name = fields.Char('Name')


class StudentNews(models.Model):
    _name = 'student.news'
    _description = 'Student News'
    _rec_name = 'subject'

    subject = fields.Char('Subject', required=True,
                          help='Subject of the news.')
    description = fields.Text('Description', help="Description")
    date = fields.Datetime('Expiry Date', help='Expiry date of the news.')
    user_ids = fields.Many2many('res.users', 'user_news_rel', 'id', 'user_ids',
                                'User News',
                                help='Name to whom this news is related.')
    color = fields.Integer('Color Index', default=0)

    @api.multi
    def news_update(self):
        emp_obj = self.env['hr.employee']
        obj_mail_server = self.env['ir.mail_server']
        mail_server_ids = obj_mail_server.search([])
        if not mail_server_ids:
            raise except_orm(_('Mail Error'),
                             _('No mail outgoing mail server'
                               'specified!'))
        mail_server_record = mail_server_ids[0]
        email_list = []
        for news in self:
            if news.user_ids:
                for user in news.user_ids:
                    if user.email:
                        email_list.append(user.email)
                if not email_list:
                    raise except_orm(_('User Email Configuration '),
                                     _("Email not found in users !"))
            else:
                for employee in emp_obj.search([]):
                    if employee.work_email:
                        email_list.append(employee.work_email)
                    elif employee.user_id and employee.user_id.email:
                        email_list.append(employee.user_id.email)
                if not email_list:
                    raise except_orm(_('Mail Error'), _("Email not defined!"))
            t = datetime.strptime(news.date, '%Y-%m-%d %H:%M:%S')
            body = 'Hi,<br/><br/> \
                    This is a news update from <b>%s</b>posted at %s<br/><br/>\
                    %s <br/><br/>\
                    Thank you.' % (self._cr.dbname,
                                   t.strftime('%d-%m-%Y %H:%M:%S'),
                                   news.description)
            smtp_user = mail_server_record.smtp_user
            notification = 'Notification for news update.'
            message = obj_mail_server.build_email(email_from=smtp_user,
                                                  email_to=email_list,
                                                  subject=notification,
                                                  body=body,
                                                  body_alternative=body,
                                                  email_cc=None,
                                                  email_bcc=None,
                                                  reply_to=smtp_user,
                                                  attachments=None,
                                                  references=None,
                                                  object_id=None,
                                                  subtype='html',
                                                  subtype_alternative=None,
                                                  headers=None)
            obj_mail_server.send_email(message=message,
                                       mail_server_id=mail_server_ids[0].id)
        return True


class StudentReminder(models.Model):
    _name = 'student.reminder'

    stu_id = fields.Many2one('student.student', 'Student Name', required=True)
    name = fields.Char('Title')
    date = fields.Date('Date')
    description = fields.Text('Description')
    color = fields.Integer('Color Index', default=0)


class StudentCast(models.Model):
    _name = "student.cast"

    name = fields.Char("Name", required=True)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def create(self, vals):
        vals.update({'employee_ids': False})
        res = super(ResUsers, self).create(vals)
        return res

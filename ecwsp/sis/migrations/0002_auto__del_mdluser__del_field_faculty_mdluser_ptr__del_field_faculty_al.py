# -*- coding: utf-8 -*-
import datetime
import sys
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings

class Migration(SchemaMigration):
    no_dry_run = True
    def forwards(self, orm):
        # These are all the tables and columns that referenced auth_user.id
        # under the old schema. Retrieved via:
        #    tables_and_columns = \
        #    [(field.m2m_db_table(), field.m2m_column_name()) for field in User._meta.many_to_many] + \
        #    [(ob.field.model._meta.db_table, ob.field.column) for ob in User._meta.get_all_related_objects()] + \
        #    [(ob.field.m2m_db_table(), ob.field.m2m_reverse_name()) for ob in User._meta.get_all_related_many_to_many_objects()]
        
        if db.execute('select count(*) from sis_student')[0][0] or db.execute('select count(*) from sis_faculty')[0][0]:
            new_db = False
        else:
            new_db = True
        if new_db:
            # Deleting model 'MdlUser'
            db.delete_table(u'sis_mdluser')

            # Deleting model 'ReportField'
            db.delete_table(u'sis_reportfield')

            # Deleting field 'Faculty.mdluser_ptr'
            db.delete_column(u'sis_faculty', u'mdluser_ptr_id')

            # Deleting field 'Faculty.alt_email'
            db.delete_column(u'sis_faculty', 'alt_email')

            # Adding field 'Faculty.user_ptr'
            db.add_column(u'sis_faculty', u'user_ptr',
                          self.gf('django.db.models.fields.related.OneToOneField')(default='', to=orm['auth.User'], unique=True, primary_key=True),
                          keep_default=False)

            # Removing M2M table for field additional_report_fields on 'UserPreference'
            db.delete_table(db.shorten_name(u'sis_userpreference_additional_report_fields'))

            # Deleting field 'Student.mdluser_ptr'
            db.delete_column(u'sis_student', u'mdluser_ptr_id')

            # Adding field 'Student.user_ptr'
            db.add_column(u'sis_student', u'user_ptr',
                          self.gf('django.db.models.fields.related.OneToOneField')(default='', to=orm['auth.User'], unique=True, primary_key=True),
                          keep_default=False)

            # Adding field 'Student.city'
            db.add_column(u'sis_student', 'city',
                          self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                          keep_default=False)
            return
        tables_and_columns = [
            (u'auth_user_groups', 'user_id'),
            (u'auth_user_user_permissions', 'user_id'),
            (u'reversion_revision', 'user_id'),
            (u'administration_accesslog', 'login_id'),
            (u'sis_userpreference', 'user_id'),
            (u'sis_importlog', 'user_id'),
            (u'work_study_cracontact', 'name_id'),
            (u'work_study_studentinteraction', 'reported_by_id'),
            (u'admissions_applicant', 'application_decision_by_id'),
            (u'admissions_contactlog', 'user_id'),
            (u'alumni_alumninote', 'user_id'),
            (u'alumni_alumniaction', 'user_id'),
            (u'attendance_attendancelog', 'user_id'),
            (u'counseling_studentmeeting', 'reported_by_id'),
            (u'counseling_referralform', 'classroom_teacher_id'),
            (u'counseling_referralform', 'referred_by_id'),
            (u'django_admin_log', 'user_id'),
            (u'report_builder_report', 'user_created_id'),
            (u'report_builder_report', 'user_modified_id'),
            (u'responsive_dashboard_userdashboard', 'user_id'),
            (u'simple_import_importsetting', 'user_id'),
            (u'simple_import_importlog', 'user_id'),
            (u'report_builder_report_starred', 'user_id')
        ]

        # Add columns
        db.add_column('sis_student', 'user_ptr_id', models.IntegerField(null=True))
        db.add_column('sis_faculty', 'user_ptr_id', models.IntegerField(null=True))
        print 1
        db.add_column(u'sis_student', 'city',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=255, blank=True),
                      keep_default=False)
        print 2

        # Migrate data if there's any to migrate
        if not new_db:
            db.execute('update sis_student set user_ptr_id = mdluser_ptr_id;')
            db.execute('update sis_faculty set user_ptr_id = mdluser_ptr_id;')
            db.execute('update sis_student, sis_mdluser set sis_student.city = sis_mdluser.city \
                where sis_student.mdluser_ptr_id = sis_mdluser.id')

            # Get all students and faculty
            results = db.execute('select mdluser_ptr_id, username, fname, lname, inactive from sis_student \
                left join sis_mdluser on sis_mdluser.id=sis_student.mdluser_ptr_id;')
            # Lname can't be blank, so if it is it's database crud and we can ignore it.
            results += db.execute('select mdluser_ptr_id, sis_mdluser.username, fname, lname, inactive \
                from sis_faculty left join sis_mdluser on sis_mdluser.id=sis_faculty.mdluser_ptr_id \
                join auth_user on sis_mdluser.username=auth_user.username where lname!=""and sis_mdluser.id != auth_user.id;')
            print 3
            
            for (mdluser_ptr_id, username, fname, lname, inactive) in results:
                user_collision = db.execute('select id, username from auth_user where id = %s;', [mdluser_ptr_id])
                if user_collision:
                    # All sis_mdluser.ids must be retained! If one collides with an auth_user.id,
                    # the auth_user will be moved to a new id. A faculty auth_user.id may be changed twice,
                    # once to accommodate a collided student, and then finally to match its sis_mdluser.id.
                    (collided_id, collided_username) = user_collision[0]
                    sys.stdout.write(u'User {} ({}) collides with student {} ({}) and will be moved...'.\
                        format(collided_username, collided_id, username, mdluser_ptr_id).encode('utf-8'))
                    new_id = db.execute('select max(id) + 1 from auth_user')[0][0]
                    db.execute('update auth_user set id = %s where id = %s', [new_id, collided_id])
                    db.execute('alter table auth_user auto_increment = %s', [new_id + 1]) # doesn't happen automatically
                    sys.stdout.write(u' New ID for {} is {}'.format(collided_username, new_id).encode('utf-8'))
                    # Update all references to auth_user id in other tables
                    for table, column in tables_and_columns:
                       db.execute(u'update `{0}` set `{1}` = %s where `{1}` = %s'.format(table, column), [new_id, collided_id])
                       sys.stdout.write('.')
                    print ' All references updated.'
                # Now it's safe to switch the ID that we know is free.
                old_student_id = db.execute('select id from auth_user where username=%s', [username])[0][0]
                sys.stdout.write(u"Will change auth_user id from {} to {} for student/faculty {}".\
                    format(old_student_id, mdluser_ptr_id, username).encode('utf-8'))
                db.execute(u'update auth_user set id=%s, first_name=%s, last_name=%s where username=%s',
                    [mdluser_ptr_id, unicode(fname), unicode(lname), username])
                # Translate inactive flag
                if inactive:
                    db.execute(u'update auth_user set is_active = False where username=%s', [username])
                # Update all references to auth_user id in other tables
                for table, column in tables_and_columns:
                   db.execute(u'update `{0}` set `{1}` = %s where `{1}` = %s'.format(table, column), [mdluser_ptr_id, old_student_id])
                   sys.stdout.write('.')
                print ' All references updated.'
        else:
            print 'No student or faculty records found to migrate.'
             
        db.delete_column(u'sis_student', u'mdluser_ptr_id')
        print 6
        db.delete_table(u'sis_mdluser')
        print 7
        db.delete_column(u'sis_faculty', u'mdluser_ptr_id')
        db.delete_column(u'sis_faculty', 'alt_email')
        
        db.execute('ALTER TABLE sis_faculty MODIFY COLUMN user_ptr_id INT NOT NULL AUTO_INCREMENT primary key;')
        
        print 8
        db.execute('ALTER TABLE sis_student MODIFY COLUMN user_ptr_id INT NOT NULL AUTO_INCREMENT primary key;')
        
        # Clear sessions
        from django.contrib.sessions.models import Session
        Session.objects.all().delete()

        # Fix foreign key constraints
        # Maybe these should be split into migrations for different apps?
        # Still, we (sis) are causing the mess and need to clean it up immediately.
        # Source:
        # First, run manage.py --syncdb all on a fresh db with the new schema
        # Beware that KEY_COLUMN_USAGE includes all databases, and execute:
        # use information_schema;
        # select TABLE_NAME,COLUMN_NAME,CONSTRAINT_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME
        # from KEY_COLUMN_USAGE where REFERENCED_COLUMN_NAME='user_ptr_id';
        foreign_key_constraints = (
            #('APP', 'TABLE_NAME', 'COLUMN_NAME', 'CONSTRAINT_NAME', 'REFERENCED_TABLE_NAME', 'REFERENCED_COLUMN_NAME'),
            ('ecwsp.admissions', 'admissions_applicant', 'sis_student_id', 'sis_student_id_refs_user_ptr_id_a71f4c9d', 'sis_student', 'user_ptr_id'),
            ('ecwsp.admissions', 'admissions_applicant_siblings', 'student_id', 'student_id_refs_user_ptr_id_8d9d9181', 'sis_student', 'user_ptr_id'),
            ('ecwsp.alumni', 'alumni_alumni', 'student_id', 'student_id_refs_user_ptr_id_4e3f1555', 'sis_student', 'user_ptr_id'),
            ('ecwsp.attendance', 'attendance_courseattendance', 'student_id', 'student_id_refs_user_ptr_id_2e0dedd7', 'sis_student', 'user_ptr_id'),
            ('ecwsp.attendance', 'attendance_studentattendance', 'student_id', 'student_id_refs_user_ptr_id_c5f69a8a', 'sis_student', 'user_ptr_id'),
            ('ecwsp.benchmark_grade', 'benchmark_grade_aggregate', 'student_id', 'student_id_refs_user_ptr_id_284aef5c', 'sis_student', 'user_ptr_id'),
            ('ecwsp.benchmark_grade', 'benchmark_grade_mark', 'student_id', 'student_id_refs_user_ptr_id_956a0ff6', 'sis_student', 'user_ptr_id'),
            ('ecwsp.counseling', 'counseling_referralform', 'student_id', 'student_id_refs_user_ptr_id_6cecab43', 'sis_student', 'user_ptr_id'),
            ('ecwsp.counseling', 'counseling_studentmeeting_students', 'student_id', 'student_id_refs_user_ptr_id_2b8f10d3', 'sis_student', 'user_ptr_id'),
            ('ecwsp.discipline', 'discipline_studentdiscipline', 'teacher_id', 'teacher_id_refs_user_ptr_id_b15fa949', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.discipline', 'discipline_studentdiscipline_students', 'student_id', 'student_id_refs_user_ptr_id_bf2eaf11', 'sis_student', 'user_ptr_id'),
            ('ecwsp.engrade_sync', 'engrade_sync_teachersync', 'teacher_id', 'teacher_id_refs_user_ptr_id_ba04cd3a', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.grades', 'grades_grade', 'student_id', 'student_id_refs_user_ptr_id_c8c6f848', 'sis_student', 'user_ptr_id'),
            ('ecwsp.omr', 'omr_test_teachers', 'faculty_id', 'faculty_id_refs_user_ptr_id_74cc6686', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.omr', 'omr_testinstance', 'student_id', 'student_id_refs_user_ptr_id_3b3dfc2b', 'sis_student', 'user_ptr_id'),
            ('ecwsp.omr', 'omr_testinstance_teachers', 'faculty_id', 'faculty_id_refs_user_ptr_id_dd34476f', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.schedule', 'schedule_awardstudent', 'student_id', 'student_id_refs_user_ptr_id_0a705f6c', 'sis_student', 'user_ptr_id'),
            ('ecwsp.schedule', 'schedule_course', 'teacher_id', 'teacher_id_refs_user_ptr_id_ab6ba283', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.schedule', 'schedule_course_secondary_teachers', 'faculty_id', 'faculty_id_refs_user_ptr_id_e9b8cc1f', 'sis_faculty', 'user_ptr_id'),
            ('ecwsp.schedule', 'schedule_omitcoursegpa', 'student_id', 'student_id_refs_user_ptr_id_ed8ee2e3', 'sis_student', 'user_ptr_id'),
            ('ecwsp.schedule', 'schedule_omityeargpa', 'student_id', 'student_id_refs_user_ptr_id_b51b9a96', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_asphistory', 'student_id', 'student_id_refs_user_ptr_id_f3a1c69c', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_student_emergency_contacts', 'student_id', 'student_id_refs_user_ptr_id_3764101d', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_student_family_access_users', 'student_id', 'student_id_refs_user_ptr_id_9713a33d', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_student_siblings', 'to_student_id', 'to_student_id_refs_user_ptr_id_4b6d8b84', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_student_siblings', 'from_student_id', 'from_student_id_refs_user_ptr_id_4b6d8b84', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_studentcohort', 'student_id', 'student_id_refs_user_ptr_id_99c0bf0d', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_studentfile', 'student_id', 'student_id_refs_user_ptr_id_12e8be34', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_studenthealthrecord', 'student_id', 'student_id_refs_user_ptr_id_3b6a60e0', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_studentnumber', 'student_id', 'student_id_refs_user_ptr_id_b34a53be', 'sis_student', 'user_ptr_id'),
            ('ecwsp.sis', 'sis_transcriptnote', 'student_id', 'student_id_refs_user_ptr_id_7472610e', 'sis_student', 'user_ptr_id'),
            ('ecwsp.standard_test', 'standard_test_standardtestresult', 'student_id', 'student_id_refs_user_ptr_id_a9e23d56', 'sis_student', 'user_ptr_id'),
            ('ecwsp.volunteer_track', 'volunteer_track_volunteer', 'student_id', 'student_id_refs_user_ptr_id_82c8545b', 'sis_student', 'user_ptr_id'),
            ('ecwsp.work_study', 'work_study_studentworker', 'student_ptr_id', 'student_ptr_id_refs_user_ptr_id_0a4d0e06', 'sis_student', 'user_ptr_id'),
        )
        for app, table_name, column_name, constraint_name, referenced_table_name, referenced_column_name in foreign_key_constraints:
            if not app in settings.INSTALLED_APPS:
                continue
            db.execute('alter table `{}` add constraint `{}` foreign key (`{}`) references `{}` (`{}`)'.format(
                table_name, constraint_name, column_name, referenced_table_name, referenced_column_name))
        print 9


    def backwards(self, orm):
        pass


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'schedule.course': {
            'Meta': {'object_name': 'Course'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'credits': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'department': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Department']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'enrollments': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['auth.User']", 'null': 'True', 'through': u"orm['schedule.CourseEnrollment']", 'blank': 'True'}),
            'fullname': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'graded': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'homeroom': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_grade_submission': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'level': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.GradeLevel']", 'null': 'True', 'blank': 'True'}),
            'marking_period': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['schedule.MarkingPeriod']", 'symmetrical': 'False', 'blank': 'True'}),
            'periods': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['schedule.Period']", 'symmetrical': 'False', 'through': u"orm['schedule.CourseMeet']", 'blank': 'True'}),
            'secondary_teachers': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'secondary_teachers'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['sis.Faculty']"}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'teacher': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'ateacher'", 'null': 'True', 'to': u"orm['sis.Faculty']"})
        },
        u'schedule.courseenrollment': {
            'Meta': {'unique_together': "(('course', 'user', 'role'),)", 'object_name': 'CourseEnrollment'},
            'attendance_note': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'cache_grade': ('django.db.models.fields.CharField', [], {'max_length': '8', 'blank': 'True'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Course']"}),
            'exclude_days': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['schedule.Day']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'default': "'Student'", 'max_length': '255', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'year': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.GradeLevel']", 'null': 'True', 'blank': 'True'})
        },
        u'schedule.coursemeet': {
            'Meta': {'object_name': 'CourseMeet'},
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Course']"}),
            'day': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'location': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Location']", 'null': 'True', 'blank': 'True'}),
            'period': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Period']"})
        },
        u'schedule.day': {
            'Meta': {'ordering': "('day',)", 'object_name': 'Day'},
            'day': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'schedule.department': {
            'Meta': {'ordering': "('order_rank', 'name')", 'object_name': 'Department'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'order_rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        u'schedule.location': {
            'Meta': {'object_name': 'Location'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        u'schedule.markingperiod': {
            'Meta': {'ordering': "('-start_date',)", 'object_name': 'MarkingPeriod'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'friday': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'grades_due': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'monday': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'saturday': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'school_days': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'school_year': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.SchoolYear']"}),
            'shortname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'show_reports': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {}),
            'sunday': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'thursday': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tuesday': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'wednesday': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'weight': ('django.db.models.fields.DecimalField', [], {'default': '1', 'max_digits': '5', 'decimal_places': '3'})
        },
        u'schedule.period': {
            'Meta': {'ordering': "('start_time',)", 'object_name': 'Period'},
            'end_time': ('django.db.models.fields.TimeField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'start_time': ('django.db.models.fields.TimeField', [], {})
        },
        u'sis.asphistory': {
            'Meta': {'object_name': 'ASPHistory'},
            'asp': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            'enroll': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']"})
        },
        u'sis.classyear': {
            'Meta': {'object_name': 'ClassYear'},
            'full_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'year': ('ecwsp.sis.models.IntegerRangeField', [], {'unique': 'True'})
        },
        u'sis.cohort': {
            'Meta': {'object_name': 'Cohort'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'long_name': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'students': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['sis.Student']", 'null': 'True', 'db_table': "'sis_studentcohort'", 'blank': 'True'})
        },
        u'sis.emergencycontact': {
            'Meta': {'ordering': "('primary_contact', 'lname')", 'object_name': 'EmergencyContact'},
            'city': ('django.db.models.fields.CharField', [], {'default': "u''", 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'emergency_only': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lname': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'mname': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'primary_contact': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'relationship_to_student': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'state': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'street': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'sync_schoolreach': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'})
        },
        u'sis.emergencycontactnumber': {
            'Meta': {'object_name': 'EmergencyContactNumber'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.EmergencyContact']"}),
            'ext': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'number': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'})
        },
        u'sis.faculty': {
            'Meta': {'ordering': "('last_name', 'first_name')", 'object_name': 'Faculty', '_ormbases': [u'auth.User']},
            'ext': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            'number': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'blank': 'True'}),
            'teacher': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'})
        },
        u'sis.gradelevel': {
            'Meta': {'ordering': "('id',)", 'object_name': 'GradeLevel'},
            'id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        u'sis.importlog': {
            'Meta': {'object_name': 'ImportLog'},
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'errors': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'import_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'sql_backup': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'user_note': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'})
        },
        u'sis.languagechoice': {
            'Meta': {'object_name': 'LanguageChoice'},
            'default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iso_code': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'sis.messagetostudent': {
            'Meta': {'object_name': 'MessageToStudent'},
            'end_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('ckeditor.fields.RichTextField', [], {}),
            'start_date': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today'})
        },
        u'sis.percoursecohort': {
            'Meta': {'object_name': 'PerCourseCohort', '_ormbases': [u'sis.Cohort']},
            u'cohort_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['sis.Cohort']", 'unique': 'True', 'primary_key': 'True'}),
            'course': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['schedule.Course']"})
        },
        u'sis.reasonleft': {
            'Meta': {'object_name': 'ReasonLeft'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'sis.reportfield': {
            'Meta': {'object_name': 'ReportField'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'sis.schoolyear': {
            'Meta': {'ordering': "('-start_date',)", 'object_name': 'SchoolYear'},
            'active_year': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'benchmark_grade': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'end_date': ('django.db.models.fields.DateField', [], {}),
            'grad_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'start_date': ('django.db.models.fields.DateField', [], {})
        },
        u'sis.student': {
            'Meta': {'object_name': 'Student', '_ormbases': [u'auth.User']},
            'alert': ('django.db.models.fields.CharField', [], {'max_length': '500', 'blank': 'True'}),
            'alt_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'bday': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'cache_cohort': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'cache_cohorts'", 'null': 'True', 'on_delete': 'models.SET_NULL', 'to': u"orm['sis.Cohort']"}),
            'cache_gpa': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'city': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'class_of_year': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.ClassYear']", 'null': 'True', 'blank': 'True'}),
            'cohorts': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['sis.Cohort']", 'symmetrical': 'False', 'through': u"orm['sis.StudentCohort']", 'blank': 'True'}),
            'date_dismissed': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'emergency_contacts': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['sis.EmergencyContact']", 'symmetrical': 'False', 'blank': 'True'}),
            'family_access_users': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'+'", 'blank': 'True', 'to': u"orm['auth.User']"}),
            'family_preferred_language': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['sis.LanguageChoice']", 'null': 'True', 'blank': 'True'}),
            'grad_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'individual_education_program': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'mname': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'parent_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'parent_guardian': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'pic': ('ecwsp.sis.thumbs.ImageWithThumbsField', [], {'blank': 'True', 'max_length': '100', 'null': 'True', 'sizes': '((70, 65), (530, 400))'}),
            'reason_left': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.ReasonLeft']", 'null': 'True', 'blank': 'True'}),
            'sex': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'siblings': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['sis.Student']", 'symmetrical': 'False', 'blank': 'True'}),
            'ssn': ('django.db.models.fields.CharField', [], {'max_length': '11', 'null': 'True', 'blank': 'True'}),
            'state': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'street': ('django.db.models.fields.CharField', [], {'max_length': '150', 'blank': 'True'}),
            'unique_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'null': 'True', 'blank': 'True'}),
            u'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'primary_key': 'True'}),
            'year': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.GradeLevel']", 'null': 'True', 'on_delete': 'models.SET_NULL', 'blank': 'True'}),
            'zip': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'})
        },
        u'sis.studentcohort': {
            'Meta': {'object_name': 'StudentCohort'},
            'cohort': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Cohort']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'primary': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']"})
        },
        u'sis.studentfile': {
            'Meta': {'object_name': 'StudentFile'},
            'file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']"})
        },
        u'sis.studenthealthrecord': {
            'Meta': {'object_name': 'StudentHealthRecord'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'record': ('django.db.models.fields.TextField', [], {}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']"})
        },
        u'sis.studentnumber': {
            'Meta': {'object_name': 'StudentNumber'},
            'ext': ('django.db.models.fields.CharField', [], {'max_length': '10', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'number': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']", 'null': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'})
        },
        u'sis.transcriptnote': {
            'Meta': {'object_name': 'TranscriptNote'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'predefined_note': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.TranscriptNoteChoices']", 'null': 'True', 'blank': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sis.Student']"})
        },
        u'sis.transcriptnotechoices': {
            'Meta': {'object_name': 'TranscriptNoteChoices'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {})
        },
        u'sis.userpreference': {
            'Meta': {'object_name': 'UserPreference'},
            'additional_report_fields': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['sis.ReportField']", 'null': 'True', 'blank': 'True'}),
            'course_sort': ('django.db.models.fields.CharField', [], {'default': "'department'", 'max_length': '64'}),
            'gradebook_preference': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_deleted_students': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'omr_default_number_answers': ('django.db.models.fields.IntegerField', [], {'default': '2', 'blank': 'True'}),
            'omr_default_point_value': ('django.db.models.fields.IntegerField', [], {'default': '1', 'blank': 'True'}),
            'omr_default_save_question_to_bank': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'prefered_file_format': ('django.db.models.fields.CharField', [], {'default': "'o'", 'max_length': "'1'"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['sis']

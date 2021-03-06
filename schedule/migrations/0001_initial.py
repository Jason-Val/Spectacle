# Generated by Django 2.0.2 on 2018-05-12 20:48

from django.db import migrations, models
import django.db.models.deletion
import schedule.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Course',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Enter the descriptive course title', max_length=200)),
                ('number', models.CharField(help_text="Enter the course's title number (220 in COMPSCI 220)", max_length=6)),
                ('description', models.TextField(help_text='Enter the course description', max_length=1000)),
                ('reqs', models.TextField(blank=True, default='', help_text='Enter the course requirements', max_length=1000)),
                ('credits', models.CharField(help_text='Enter # of credits', max_length=4)),
                ('honors', models.BooleanField(verbose_name='Enter whether this class is an honors course')),
                ('career', models.CharField(blank=True, choices=[('u', 'Undergraduate'), ('g', 'Graduate'), ('c', 'Non-Credit'), ('d', 'Non-Degree')], default='u', help_text='The course career', max_length=1)),
                ('session', models.CharField(blank=True, choices=[('un', 'University'), ('uc', 'University Eligible/CPE'), ('ud', 'University Non-standard Dates'), ('ce', 'CPE Continuing Education'), ('cu', 'CPE Non-Standard Dates'), ('c1', 'CPE Summer Session 1'), ('c2', 'CPE Summer Session 2'), ('c3', 'CPE Summer Session 3')], default='u', help_text='The course career', max_length=2)),
                ('start_date', models.DateField(help_text='Enter the starting date of the course')),
                ('end_date', models.DateField(help_text='Enter the ending date of the course')),
            ],
        ),
        migrations.CreateModel(
            name='Department',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Enter a department name', max_length=200, unique=True)),
                ('code', models.CharField(help_text='Enter the department abbreviation', max_length=12)),
            ],
        ),
        migrations.CreateModel(
            name='Gened',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Enter a gened category', max_length=200)),
                ('code', models.CharField(help_text='Enter the gened abbreviation', max_length=2)),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='User-set title for this schedule', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='ScheduleCourse',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('color', models.CharField(choices=[('red', 'red'), ('#157ddf9f', 'blue'), ('green', 'green'), ('orange', 'orange'), ('purple', 'purple'), ('pink', 'pink'), ('brown', 'brown')], default=schedule.models.get_color, help_text='Enter the color for this course', max_length=15)),
                ('title', models.CharField(blank=True, default='', help_text='Enter the title of this event', max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='Section',
            fields=[
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('sid', models.IntegerField(default=0, help_text='The 5 digit spire course number')),
                ('days', models.CharField(help_text='Days the course is taught', max_length=10)),
                ('mon', models.BooleanField(default=False)),
                ('tue', models.BooleanField(default=False)),
                ('wed', models.BooleanField(default=False)),
                ('thu', models.BooleanField(default=False)),
                ('fri', models.BooleanField(default=False)),
                ('start', models.TimeField(help_text='The starting time of the class')),
                ('ending', models.TimeField(help_text='The ending time of the class')),
                ('professor', models.CharField(max_length=200)),
                ('room', models.CharField(max_length=200)),
                ('open', models.BooleanField(default=True, verbose_name='Enter whether this class is currently open')),
                ('cap', models.IntegerField(help_text='The class maximum capacity')),
                ('enrolled', models.IntegerField(help_text='The current number of students enrolled')),
                ('wcap', models.IntegerField(help_text='The maximum size of the waitlist')),
                ('wenrolled', models.IntegerField(help_text='The current size of the waitlist')),
                ('component', models.CharField(choices=[('LEC', 'Lecture'), ('DIS', 'Discussion'), ('LAB', 'Laboratory'), ('COL', 'Colloquium'), ('DST', 'Dissertation / Thesis'), ('IND', 'Individualized Study'), ('PRA', 'Practicum'), ('SEM', 'Seminar'), ('STS', 'Studio / Skills'), ('CUS', 'Custom')], max_length=3)),
                ('clss', models.ForeignKey(blank=True, help_text='The corresponding generic class for this section', null=True, on_delete=django.db.models.deletion.CASCADE, to='schedule.Course')),
            ],
        ),
        migrations.CreateModel(
            name='Student',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_email', models.EmailField(default='', max_length=254, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season', models.CharField(choices=[('w', 'Winter'), ('t', 'Summer'), ('s', 'Spring'), ('f', 'Fall')], max_length=1)),
                ('year', models.IntegerField()),
            ],
        ),
        migrations.AddField(
            model_name='section',
            name='term',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='schedule.Term'),
        ),
        migrations.AddField(
            model_name='schedulecourse',
            name='course',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='schedule.Section'),
        ),
        migrations.AddField(
            model_name='schedulecourse',
            name='schedule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='schedule.Schedule'),
        ),
        migrations.AddField(
            model_name='schedule',
            name='student',
            field=models.ForeignKey(help_text='The user this schedule belongs to', on_delete=django.db.models.deletion.CASCADE, to='schedule.Student'),
        ),
        migrations.AddField(
            model_name='course',
            name='dept',
            field=models.ForeignKey(help_text="Enter the course's department", on_delete=django.db.models.deletion.CASCADE, to='schedule.Department'),
        ),
        migrations.AddField(
            model_name='course',
            name='gened',
            field=models.ManyToManyField(blank=True, help_text='Enter any gened categories this course satisfies', to='schedule.Gened'),
        ),
    ]

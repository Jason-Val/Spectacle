from django import forms
from django.core.exceptions import ValidationError
from .models import Course, Department, Term, Gened
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
import pickle

from django.db.models import Q
from .models import ScheduleCourse

# ============== START custom widget and field for geneds =================== #
# multivaluefield based off https://gist.github.com/elena/3915748
class MultiWidgetCheckbox(forms.MultiWidget):
    def __init__(self, choices=[], attrs=None):
        self.choices = choices
        widgets = [forms.CheckboxInput() for c in choices]
        super(MultiWidgetCheckbox, self).__init__(widgets, attrs)
        
    def decompress(self, value):
        if value:
            return pickle.loads(value)
        else:
            return [False for c in self.choices]
    
    # in-house to avoid dependencies
    # returns a list where each element is a tag
    def parse_html(self, html):
        tags = []
        curr = html
        start = 0
        end = 0
        while '/>' in curr:
            start = curr.index('<')
            end = curr.index('/>') + start
            tags.append(curr[start:end+2])
            curr = curr[end+2:]
        return tags
    
    # This is very fragile!! TODO: make this more robust or probably just migrate to React
    # Also I'm sorry...
    def render(self, name, value, attrs=None):
        html = super(MultiWidgetCheckbox, self).render(name, value, attrs)
        #print(html)
        #print(self.parse_html(html))
        labeled_html = '<div class=\'row\'>'
        tags = self.parse_html(html)
        for i in range(len(tags)):
            if i % 4 == 0:
                if i != 0:
                    labeled_html += '</div>'
                labeled_html += '<div class=\'col-4\'>'
            label = "<label>"+self.choices[i][0]+":</label> "
            labeled_html += label
            labeled_html += tags[i]
            labeled_html += '<br>'
        labeled_html += '</div></div>'
        
        return mark_safe(labeled_html)
    
class MultiBooleanField(forms.MultiValueField):
    
    def __init__(self, choices=[], *args, **kwargs):
        widgets = MultiWidgetCheckbox(choices=choices)
        self.choices = choices
        list_fields = [forms.BooleanField(required=False) for c in choices]
        
        super(MultiBooleanField, self).__init__(list_fields, widget=widgets, *args, **kwargs)

    def compress(self, values):
        result = {}
        for i in range(len(values)):
            result[self.choices[i][0]] = values[i]
        return pickle.dumps(result)
# ============== END custom widget and field for geneds =================== #
        
# form for searching for courses
class ScheduleForm(forms.Form):

    keywords = forms.CharField(required=False, initial="Enter keywords...", help_text="Enter keywords to search for", max_length=200)
    
    depts = list(map(lambda obj: (obj.code, obj.name), Department.objects.all()))
    depts = [('NULL','Pick a department...')] + depts
    departments = forms.TypedChoiceField(choices=depts, coerce=str, initial='NULL', empty_value='NULL', help_text="Enter department to search within")
    
    terms = list(map(lambda term: (term.id, list(filter(lambda season: season[0]==term.season, Term.SEASONS))[0][1] + " " + str(term.year) ), Term.objects.all()))
    course_term = forms.ChoiceField(choices=terms, help_text="Enter term to search within")


    # Sihua's Edit start
    l100 = forms.BooleanField(required=False)
    l200 = forms.BooleanField(required=False)
    l300 = forms.BooleanField(required=False)
    l400 = forms.BooleanField(required=False)
    l500 = forms.BooleanField(required=False)
    levels = ["l100", "l200", "l300", "l400", "l500"]

    cr1 = forms.BooleanField(required=False)
    cr2 = forms.BooleanField(required=False)
    cr3 = forms.BooleanField(required=False)
    cr4 = forms.BooleanField(required=False)
    cr5 = forms.BooleanField(required=False)
    credits = ["cr1", "cr2", "cr3", "cr4", "cr5"]

    closed = forms.BooleanField(required=False)
    conflicted = forms.BooleanField(required=False, initial=True)
    honors_only = forms.BooleanField(required=False)

    Mon = forms.BooleanField(required=False)
    Tus = forms.BooleanField(required=False)
    Wed = forms.BooleanField(required=False)
    Thu = forms.BooleanField(required=False)
    Fri = forms.BooleanField(required=False)
    days = ["Mon", "Tus", "Wed", "Thu", "Fri"]
    
    #Sihua's Edit End
    
    gened_list = list(map(lambda gened: (gened.code, gened.code + ": " + gened.name), Gened.objects.all()))
    #see custom field above
    geneds = MultiBooleanField(choices=gened_list, required=False)
    
    start_time = forms.TimeField(required=False, label="Start time")
    end_time = forms.TimeField(required=False, label="End time")
    
    def __init__(self, schedule, *args, **kwargs):
        self.schedule = schedule
        super(ScheduleForm, self).__init__(*args, **kwargs)
    
    # retrieve courses and throw error if too many or none at all
    def clean(self):
        super().clean()
        
        #retrieve all courses in requested term
        term = Term.objects.get(id=self.cleaned_data['course_term'])
        results = Course.objects.select_related().filter(section__term=term).order_by('dept__code', 'number')
        
        #filter based on department
        if self.cleaned_data['departments'] != 'NULL':
            results = results.filter(dept__code=self.cleaned_data['departments'])
        
        #filter based on keywords
        if self.cleaned_data['keywords'] != '' and self.cleaned_data['keywords'] != 'Enter keywords...':
            keys = self.cleaned_data['keywords']
            title_filter = Q(title__icontains=keys)
            desc_filter = Q(description__icontains=keys)
            level_filter = Q(number=keys)
            
            results = results.filter(title_filter | desc_filter | level_filter).distinct()
        
        #filter based on days
        #if a course has at least one related section with days
        #  containing day, keep it in the results.
        #TODO: this should have more intelligent filtering. What about courses with a lab on Fri, but no lectures?
        #      it probably shouldn't show up, but it will
        days_filter = None
        for day in self.days:
            if self.cleaned_data[day]:
                if days_filter == None:
                    days_filter = Q(section__days__contains=day[:2])
                else:
                    days_filter = days_filter | Q(section__days__contains=day[:2])
        
        if days_filter != None:
            results = results.select_related().filter(days_filter).distinct()
        
        #filter based on course level
        levels_filter = None
        for level in self.levels:
            if self.cleaned_data[level]:
                course_level = level[1]
                if course_level == '5':
                    course_level = '[5-9]'
                regex = r'\w*' + course_level + '\d{2}\w*'
                if levels_filter == None:
                    levels_filter = Q(number__iregex=regex)
                else:
                    levels_filter = levels_filter | Q(number__iregex=regex)
        if levels_filter != None:
            results = results.filter(levels_filter)
            
        #filter based on number of credits
        credits_filter = None
        for credit in self.credits:
            if self.cleaned_data[credit]:
                credit_level = credit[2]
                regex = credit_level + '|[1-' + credit_level +' ]-[' + credit_level + '-9]'
                if credit_level == '5':
                    regex = r'[' + credit_level + '-9]|[1-' + credit_level +' ]-[' + credit_level + '-9]'
                if credits_filter == None:
                    credits_filter = Q(credits__iregex=regex)
                else:
                    credits_filter = credits_filter | Q(credits__iregex=regex)
        if credits_filter != None:
            results = results.filter(credits_filter)
            
        # filter based on whether a course has open sections
        if not self.cleaned_data['closed']:
            results = results.select_related().filter(section__open=True).distinct()
        
        # filter out all non-honors courses
        if self.cleaned_data['honors_only']:
            results = results.filter(honors=True)
        
        # filter based on whether course satisfies one of the requested geneds
        # TODO: order by number of geneds satisfied
        if self.cleaned_data['geneds']:
            geneds = pickle.loads(self.cleaned_data['geneds'])
            gened_filter = None
            any_selected = False
            for gened, selected in geneds.items():
                if selected:
                    any_selected = True
                    if gened_filter == None:
                        gened_filter = Q(gened__code=gened)
                    else:
                        gened_filter = gened_filter | Q(gened__code=gened)
            if any_selected:
                results = results.filter(gened_filter)
                
                
        if self.cleaned_data['start_time']:
            results = results.select_related().filter(section__start__gte=self.cleaned_data['start_time'])
        
        if self.cleaned_data['end_time']:
            results = results.select_related().filter(section__ending__lte=self.cleaned_data['end_time'])
        
        # filter out all courses that conflict with current courses
        if not self.cleaned_data['conflicted']:
            current_courses = ScheduleCourse.objects.filter(schedule=self.schedule)
            # for every course in results, display it if:
            #   it has at least one section with a time/day that does not conflict with any
            #   of the courses in current_courses
            
            # option 1: regex. option 2: boolean fields
            conflicts = current_courses.values_list('course__days', 'course__start', 'course__ending').distinct()
            #conflicts = current_courses.values_list('course__mon', 'course__tue', 'course__wed', 'course__thu', 'course__fri', 'course__start', 'course__ending').distinct()
            
            #enable for regex:
            days = set()
            for day_set, start, end in conflicts:
                for i in range(0, len(day_set), 2):
                    if not day_set[i:i+2] in days:
                        days.add((day_set[i:i+2], start, end))
            
            
            # A list of tuples which current courses can't conflict with [(day, start, end), ...]
            conflicts = days
            
            
            for section in conflicts:
                # uses regex
                day_filter = Q(section__days__iregex=r'(\w\w)*(' + section[0] + ')(\w\w)*')
                
                #regex
                start_filter = Q(section__start__gte=section[2]) # the new course starts after the old course ends
                end_filter = Q(section__ending__lte=section[1])  # the new course ends before the old course starts
                
                results = results.select_related().exclude(day_filter &  ~(start_filter | end_filter)).distinct()
                
                
        results = results.distinct()
        self.cleaned_data['results'] = results
        self.cleaned_data
        
        print("**************8Length of results is: ", len(results))
        
        if len(results) == 0:
            msg = forms.ValidationError("Search was too narrow; no courses match filters", code='narrow')            
            raise ValidationError([
                msg,
            ])
            
        if len(results) > 300:
            msg = forms.ValidationError("Too many courses match. Narrow your search criteria.", code='wide')            
            raise ValidationError([
                msg,
            ])
            
        else:
            return self.cleaned_data

# form for creating a new schedule
class NewScheduleForm(forms.Form):
    title = forms.CharField(required=True, max_length=200)
    
    def clean_title(self):
        return self.cleaned_data['title']
        
# form for adding a custom, user event
class UserEventForm(forms.Form):
    title = forms.CharField(required=True, label="Title of event", max_length=50)
    
    mon = forms.BooleanField(required=False, label="Monday")
    tue = forms.BooleanField(required=False, label="Tuesday")
    wed = forms.BooleanField(required=False, label="Wednesday")
    thu = forms.BooleanField(required=False, label="Thursday")
    fri = forms.BooleanField(required=False, label="Friday")
    
    start_time = forms.TimeField(required=True, label="Start time")
    end_time = forms.TimeField(required=True, label="End time")
    
    def clean(self):
        super().clean()
        days = ''
        errors = []
        
        #make sure at least one day is filled in, and reformat to "MoWeFr" etc
        any_selected = False
        if self.cleaned_data['mon']:
            days += 'Mo'
            any_selected = True
        if self.cleaned_data['tue']:
            days += 'Tu'
            any_selected = True
        if self.cleaned_data['wed']:
            days += 'We'
            any_selected = True
        if self.cleaned_data['thu']:
            days += 'Th'
            any_selected = True
        if self.cleaned_data['fri']:
            days += 'Fr'
            any_selected = True
        if not any_selected:
            errors.append(forms.ValidationError("At least one day must be selected.", code='nodays'))
        self.cleaned_data['days'] = days
        
        # make sure start and end times are sequential
        if self.cleaned_data['start_time'] > self.cleaned_data['end_time']:
            errors.append(forms.ValidationError("Start time can't be after end time", code='nodays'))
        
        if len(errors) > 0:
            raise ValidationError(errors)
        
        return self.cleaned_data
    
class flowchartForm(forms.Form):
	depts = map(lambda obj: (obj.code, obj.name), Department.objects.all())
	
	departments = forms.TypedChoiceField(choices=depts, coerce=str, empty_value='', help_text="Enter Department")
    
class UserForm(UserCreationForm):
    error_css_class = "error"
    email = forms.EmailField(required=True)
    
    class Meta:
        model = User
        fields = (
            'password1',
            'password2',
            'email',
        )
        
    def clean(self):
        super().clean()
        errors = []
        email = self.cleaned_data['email']
        email = email.split('@')
        if len(email) == 2 and email[1] == 'umass.edu':
            return self.cleaned_data
        else:
            errors.append(forms.ValidationError("Email must be a valid umass.edu email", code='email_violation'))
        
        if len(errors) > 0:
            raise ValidationError(errors)
        
    def save(self, commit=True):
        user = super(UserForm, self).save(commit=False)
        user.username = self.cleaned_data['email']
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user
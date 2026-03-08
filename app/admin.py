from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html, escape
from django.urls import reverse
from .models import Group, User, Subject, Test, Question, Answer, UserAnswer, CheatingLog

# 1. Userlarni boshqarish
class MyUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'first_name', 'last_name', 'group', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'middle_name']
    list_filter = ['group']

    fieldsets = (
        ("Foydalanuvchi ma'lumotlari", {
            'fields': ('username', 'password', 'first_name', 'last_name', 'middle_name', 'email', 'group')
        }),
        ("Tizim ruxsatlari", {
            'fields': ('is_active', 'is_staff', 'is_superuser'),
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Qo‘shimcha ma‘lumotlar', {'fields': ('first_name', 'last_name', 'middle_name', 'group')}),
    )

# 2. Fanlar
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'point_value']
    search_fields = ['name']
    filter_horizontal = ('groups',)

# 3. Savollar va javoblar (Inline)
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2

class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    # 'text' o'rniga 'short_text' metodini chiqaramiz
    list_display = ['short_text', 'test', 'subject'] 
    search_fields = ['text']
    list_filter = ['test', 'subject']

    def short_text(self, obj):
        # Matndagi {} kabi maxsus belgilarni xavfsiz ko'rsatish
        text = str(obj.text) if obj.text else "Matnsiz savol"
        short = text[:80] + "..." if len(text) > 80 else text
        return escape(short) # format_html dagi xatoni oldini oladi
    
    short_text.short_description = "Savol matni"

# 4. Testlar va Bulk Upload tugmasi
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'get_subjects', 'duration_minutes', 'upload_questions_link']
    filter_horizontal = ('subjects',)

    def get_subjects(self, obj):
        return ", ".join([str(s.name) for s in obj.subjects.all()])
    get_subjects.short_description = 'Subjects'

    def save_model(self, request, obj, form, change):
        is_new = not change
        super().save_model(request, obj, form, change)
        if is_new:
            subs = form.cleaned_data.get('subjects', [])
            if subs:
                for subj in subs:
                    existing = Question.objects.filter(subject=subj)
                    for q in existing:
                        if not Question.objects.filter(test=obj, text=q.text, subject=q.subject).exists():
                            new_q = Question.objects.create(test=obj, text=q.text, subject=q.subject)
                            for ans in q.answers.all():
                                Answer.objects.create(question=new_q, text=ans.text, is_correct=ans.is_correct)

    def upload_questions_link(self, obj):
        url = reverse('bulk_upload', args=[obj.pk])
        return format_html('<a class="button" style="background-color: #447e9b; color: white; padding: 5px 10px; border-radius: 4px;" href="{}">Bulk Upload</a>', url)

    upload_questions_link.short_description = "Amallar"

@admin.register(CheatingLog)
class CheatingLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'test', 'event_type', 'created_at')
    list_filter = ('event_type', 'test', 'created_at')
    search_fields = ('user__username', 'test__title', 'details')

# Ro'yxatdan o'tkazish
admin.site.register(User, MyUserAdmin)
admin.site.register(Group)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(UserAnswer)
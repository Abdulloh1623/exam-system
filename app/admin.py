from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import Group, User, Subject, Test, Question, Answer

# 1. Userlarni boshqarish
# app/admin.py

class MyUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'first_name', 'last_name', 'group', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'middle_name']
    list_filter = ['group']

    # Standart fieldsetlarni override qilamiz (bu tablarni kamaytiradi/tartibga soladi)
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
    list_display = ['name']
    search_fields = ['name']
    filter_horizontal = ('groups',)

# 3. Savollar va javoblar (Inline)
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2

class QuestionAdmin(admin.ModelAdmin):
    inlines = [AnswerInline]
    list_display = ['text', 'test']
    search_fields = ['text']
    list_filter = ['test']

# 4. Testlar va Bulk Upload tugmasi
class TestAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'duration_minutes', 'upload_questions_link']

    def upload_questions_link(self, obj):
        url = reverse('bulk_upload', args=[obj.pk])
        return format_html('<a class="button" style="background-color: #447e9b; color: white; padding: 5px 10px; border-radius: 4px;" href="{}">Bulk Upload</a>', url)

    upload_questions_link.short_description = "Savollarni yuklash"

# Ro'yxatdan o'tkazish
admin.site.register(User, MyUserAdmin)
admin.site.register(Group)
admin.site.register(Subject, SubjectAdmin)
admin.site.register(Test, TestAdmin)
admin.site.register(Question, QuestionAdmin)
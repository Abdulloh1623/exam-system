from django.db import models
from django.contrib.auth.models import AbstractUser


# 1. Guruhlar
class Group(models.Model):
    name = models.CharField(max_length=100, verbose_name="Guruh nomi")
    class Meta:
        verbose_name = "Guruh"
        verbose_name_plural = "Guruhlar"
    def __str__(self):
        return self.name

# 2. Userlar (Ism, Familiya, Otasining ismi, Login, Parol)
class User(AbstractUser):
    session_token = models.CharField(max_length=100, blank=True, null=True)
    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True)
    # Ushbu qatorni qo'shing:
    middle_name = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Otasining ismi"
    )

# 3. Fanlar
class Subject(models.Model):
    name = models.CharField(max_length=100, verbose_name="Fan nomi")
    # yeni: vaznli ballar uchun decimal maydon
    point_value = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=1.0,
        verbose_name="Ball qiymati",
        help_text="Savol uchun to‘g‘ri javob bo‘lganda qancha ball qo‘shilishini belgilaydi"
    )

    class Meta:
        verbose_name = "Fan"
        verbose_name_plural = "Fanlar"
    # E019 xatosini tuzatish uchun 'groups' maydoni:
    groups = models.ManyToManyField(Group, related_name='subjects') 
    
    def __str__(self):
        return self.name

# 4. Testlar va Vaqt (Timer uchun)
class Test(models.Model):
    class Meta:
        verbose_name = "Test"
        verbose_name_plural = "Testlar"

    # eski field (saqlab qolamiz, yangi testlar uchun bo‘sh bo‘lishi mumkin)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)

    # yangi: bir nechta fanlardan tashkil topgan testlar uchun
    subjects = models.ManyToManyField(Subject, blank=True, related_name='tests')

    title = models.CharField(max_length=200)
    # E108 xatosini tuzatish uchun 'duration_minutes' maydoni:
    duration_minutes = models.PositiveIntegerField(default=30) 
    
    def __str__(self):
        # bir nechta fan bo‘lsa ularning nomlarini birlashtiramiz
        if self.subjects.exists():
            subj_names = ", ".join([s.name for s in self.subjects.all()])
            return f"{subj_names} | {self.title}"
        if self.subject:
            return f"{self.subject.name} | {self.title}"
        return self.title

# 5. Savollar
class Question(models.Model):
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    # yangi: har bir savol qaysi fanga tegishli ekanini saqlash (ballar uchun)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, null=True, blank=True)
    text = models.TextField()
    def __str__(self):
        # Savolning birinchi 50 ta harfini ko'rsatadi
        return self.text[:50] + "..." if len(self.text) > 50 else self.text

# 6. Javoblar (To'g'ri javob bitta yoki bir nechta bo'lishi mumkin)
class Answer(models.Model):
    class Meta:
        verbose_name = "Javob"
        verbose_name_plural = "Javoblar"
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    text = models.CharField("Javob varianti", max_length=255)
    is_correct = models.BooleanField("To'g'ri javobmi?", default=False)

class Result(models.Model):
    class Meta:
        verbose_name = "Natija"
        verbose_name_plural = "Natijalar"
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    test = models.ForeignKey(Test, on_delete=models.CASCADE)
    correct_answers = models.IntegerField()
    total_questions = models.IntegerField()
    percentage = models.FloatField()
    # og'irlik bo'yicha hisoblangan umumiy ball (Multi-subject testlar uchun)
    weighted_score = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"

class UserAnswer(models.Model):
    class Meta:
        verbose_name = "Foydalanuvchi javobi"
        verbose_name_plural = "Foydalanuvchi javoblari"

    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(
        Answer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tanlangan javob"
    )
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.result.user.username} - Savol {self.question.id}"
    
class CheatingLog(models.Model):
    class Meta:
        verbose_name = "Cheating log"
        verbose_name_plural = "Cheating logs"
        ordering = ['-created_at']

    EVENT_TYPES = [
        ('tab_switch', 'Boshqa tabga o‘tdi'),
        ('fullscreen_exit', 'Fullscreen’dan chiqdi'),
        ('right_click', 'Right click qildi'),
        ('copy_attempt', 'Copy urindi'),
        ('paste_attempt', 'Paste urindi'),
        ('cut_attempt', 'Cut urindi'),
        ('devtools_attempt', 'DevTools urindi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cheating_logs')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='cheating_logs')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.test.title} - {self.event_type}"
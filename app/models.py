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
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    # E108 xatosini tuzatish uchun 'duration_minutes' maydoni:
    duration_minutes = models.PositiveIntegerField(default=30) 
    
    def __str__(self):
        return f"{self.subject.name} | {self.title}"

# 5. Savollar
class Question(models.Model):
    class Meta:
        verbose_name = "Savol"
        verbose_name_plural = "Savollar"
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
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
    date_taken = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"
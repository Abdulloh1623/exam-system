from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Avg, Q # Avg va Q filtrlash va hisoblash uchun kerak

# BU YERGA Group VA Subject QO'SHILDI:
from .models import Test, Question, Subject, Answer, Result, Group 
from .utils import parse_bulk_questions

import openpyxl
from django.http import HttpResponse
from .models import Result # Boshqa modellar allaqachon import qilingan deb hisoblaymiz

# 1. Admin uchun savollarni ommaviy yuklash
def bulk_upload_view(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    if request.method == 'POST':
        text_data = request.POST.get('bulk_data')
        if text_data:
            parse_bulk_questions(test_id, text_data)
            messages.success(request, f"Savollar '{test.title}'ga muvaffaqiyatli qo'shildi!")
            return redirect('/admin/app/test/')
    return render(request, 'admin/bulk_upload.html', {'test': test})

# 2. Foydalanuvchi asboblar paneli (Dashboard)
@login_required
def dashboard(request):
    if request.user.group:
        # Guruhga tegishli fanlarni yuklash
        subjects = Subject.objects.filter(groups=request.user.group).prefetch_related('test_set')
        # Foydalanuvchi topshirgan testlar ID ro'yxati
        finished_test_ids = list(Result.objects.filter(user=request.user).values_list('test_id', flat=True))
    else:
        subjects = Subject.objects.none()
        finished_test_ids = []
    
    return render(request, 'user/dashboard.html', {
        'subjects': subjects,
        'finished_test_ids': finished_test_ids
    })

# 3. Test yechish oynasi va 1 martalik cheklov
@login_required
def take_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    # Avval topshirgan bo'lsa kirishni taqiqlash
    if Result.objects.filter(user=request.user, test=test).exists():
        return HttpResponse("""
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h1 style="color:#d93025;">Xato!</h1>
                <p>Siz ushbu testni topshirib bo'lgansiz.</p>
                <a href="/">Dashboardga qaytish</a>
            </div>
        """)

    questions = test.questions.all().prefetch_related('answers')

    if request.method == 'POST':
        correct_answers = 0
        total_questions = questions.count()

        for q in questions:
            selected_answer_id = request.POST.get(f'q{q.id}')
            if selected_answer_id:
                is_correct = Answer.objects.filter(id=selected_answer_id, is_correct=True).exists()
                if is_correct:
                    correct_answers += 1
        
        percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        
        # Natijani saqlash
        Result.objects.create(
            user=request.user,
            test=test,
            correct_answers=correct_answers,
            total_questions=total_questions,
            percentage=round(percentage, 2)
        )
        
        return HttpResponse(f"""
            <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                <h1>Test yakunlandi!</h1>
                <p>To'g'ri javoblar: {correct_answers} / {total_questions}</p>
                <p>Natija: {percentage:.1f}%</p>
                <a href="/">Dashboardga qaytish</a>
            </div>
        """)

    return render(request, 'user/take_test.html', {
        'test': test,
        'questions': questions,
        'duration_seconds': test.duration_minutes * 60
    })

# 4. Admin uchun statistika sahifasi
@login_required
def admin_statistics(request):
    if not request.user.is_staff:
        return HttpResponse("Ruxsat yo'q")

    # Barcha guruh va fanlarni dropdown (tanlov) uchun olish
    groups = Group.objects.all()
    subjects = Subject.objects.all()

    # Filtrlarni olish
    search_query = request.GET.get('name', '')
    group_id = request.GET.get('group', '')
    subject_id = request.GET.get('subject', '')

    # Boshlang'ich natijalar (optimallashtirilgan)
    results = Result.objects.select_related('user', 'test', 'user__group', 'test__subject').all()

    # Filtrlash mantiqi
    if search_query:
        results = results.filter(
            Q(user__first_name__icontains=search_query) | 
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    if group_id:
        results = results.filter(user__group_id=group_id)
    if subject_id:
        results = results.filter(test__subject_id=subject_id)

    # O'rtacha natijani hisoblash (Serverda)
    average_score = results.aggregate(Avg('percentage'))['percentage__avg'] or 0

    return render(request, 'admin/statistics.html', {
        'results': results,
        'groups': groups,
        'subjects': subjects,
        'average_score': round(average_score, 1),
        'total_count': results.count(),
        # Tanlangan qiymatlarni qaytarish (shablonda saqlab qolish uchun)
        's_name': search_query,
        's_group': group_id,
        's_subject': subject_id,
    })

@login_required
def export_results_excel(request):
    if not request.user.is_staff:
        return HttpResponse("Ruxsat yo'q")

    # Statistika sahifasidagi filtrlarni qabul qilish
    name = request.GET.get('name', '')
    group_id = request.GET.get('group', '')
    subject_id = request.GET.get('subject', '')

    results = Result.objects.select_related('user', 'test', 'user__group', 'test__subject').all()

    # Filtrlarni qo'llash (Statistics view bilan bir xil mantiq)
    if name:
        results = results.filter(Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name))
    if group_id:
        results = results.filter(user__group_id=group_id)
    if subject_id:
        results = results.filter(test__subject_id=subject_id)

    # Excel faylini yaratish
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Natijalari"

    # Ustun sarlavhalari
    columns = ['F.I.SH', 'Guruh', 'Fan', 'Test nomi', 'To\'g\'ri javoblar', 'Jami savollar', 'Foiz', 'Sana']
    ws.append(columns)

    # Ma'lumotlarni yozish
    for r in results:
        ws.append([
            r.user.get_full_name() or r.user.username,
            r.user.group.name if r.user.group else "--",
            r.test.subject.name,
            r.test.title,
            r.correct_answers,
            r.total_questions,
            f"{r.percentage}%",
            r.date_taken.strftime("%d.%m.%Y %H:%M")
        ])

    # Faylni yuklab olish uchun javob qaytarish
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Natijalar.xlsx'
    wb.save(response)
    return response
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Avg, Q # Avg va Q filtrlash va hisoblash uchun kerak

# BU YERGA Group VA Subject QO'SHILDI:
from .models import Test, Question, Subject, Answer, Result, Group 
from .utils import parse_bulk_questions

try:
    import openpyxl
except ImportError:
    openpyxl = None

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
        # Guruhga tegishli fanlarni yuklash; old tests subject orqali, yangi multi-subject tests esa subjects m2m orqali
        subjects = Subject.objects.filter(groups=request.user.group).prefetch_related('test_set', 'tests')
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

    # collect all questions connected to this test
    # for multi‑subject tests some questions may belong to different subjects
    questions = test.questions.select_related('subject').prefetch_related('answers')

    if request.method == 'POST':
        # tally correct answers per subject
        per_subj = {}  # subject -> {correct, total}
        total_questions = questions.count()

        for q in questions:
            subj = q.subject or test.subject
            if subj not in per_subj:
                per_subj[subj] = {'correct': 0, 'total': 0}
            per_subj[subj]['total'] += 1

            selected_answer_id = request.POST.get(f'q{q.id}')
            if selected_answer_id:
                is_correct = Answer.objects.filter(id=selected_answer_id, is_correct=True).exists()
                if is_correct:
                    per_subj[subj]['correct'] += 1

        # compute weighted score and maximum possible
        weighted_score = 0
        max_score = 0
        breakdown_lines = []
        for subj, vals in per_subj.items():
            pv = subj.point_value if subj else 0
            subj_score = vals['correct'] * pv
            subj_max = vals['total'] * pv
            weighted_score += subj_score
            max_score += subj_max
            breakdown_lines.append((subj.name if subj else '---', vals['correct'], vals['total'], pv, subj_score))

        percentage = (weighted_score / max_score) * 100 if max_score > 0 else 0

        # Natijani saqlash
        Result.objects.create(
            user=request.user,
            test=test,
            correct_answers=sum(v['correct'] for v in per_subj.values()),
            total_questions=total_questions,
            percentage=round(percentage, 2),
            weighted_score=round(weighted_score, 2)
        )

        # build simple breakdown html
        breakdown_html = """
            <ul style='text-align:left; display:inline-block;'>
        """
        for name, corr, tot, pv, score in breakdown_lines:
            breakdown_html += f"<li>{name}: {corr}/{tot} × {pv} = {score:.1f}</li>"
        breakdown_html += "</ul>"

        return HttpResponse(f"""
            <div style="font-family: sans-serif; text-align: center; margin-top: 50px;">
                <h1>Test yakunlandi!</h1>
                <p>To'g'ri javoblar: {sum(v['correct'] for v in per_subj.values())} / {total_questions}</p>
                <p>Umumiy ball: {weighted_score:.1f}  (maksimal {max_score:.1f})</p>
                <p>Natija: {percentage:.1f}%</p>
                {breakdown_html}
                <br><a href="/">Dashboardga qaytish</a>
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
        results = results.filter(
            Q(test__subject_id=subject_id) | Q(test__subjects__id=subject_id)
        )

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
    if openpyxl is None:
        return HttpResponse("Excel eksport uchun openpyxl o'rnatilmagan.")

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
        results = results.filter(
            Q(test__subject_id=subject_id) | Q(test__subjects__id=subject_id)
        )

    # Excel faylini yaratish
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Test Natijalari"

    # Ustun sarlavhalari
    columns = ['F.I.SH', 'Guruh', 'Fan', 'Test nomi', 'To\'g\'ri javoblar', 'Jami savollar', 'Foiz', 'Umumiy ball', 'Sana']
    ws.append(columns)

    # Ma'lumotlarni yozish
    for r in results:
        ws.append([
            r.user.get_full_name() or r.user.username,
            r.user.group.name if r.user.group else "--",
            # subject could be FK or multiple
            (r.test.subject.name if r.test.subject else ", ".join([s.name for s in r.test.subjects.all()])),
            r.test.title,
            r.correct_answers,
            r.total_questions,
            f"{r.percentage}%",
            float(r.weighted_score) if hasattr(r, 'weighted_score') else "",
            r.date_taken.strftime("%d.%m.%Y %H:%M")
        ])

    # Faylni yuklab olish uchun javob qaytarish
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Natijalar.xlsx'
    wb.save(response)
    return response
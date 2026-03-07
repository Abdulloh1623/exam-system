from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Avg, Q
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm 

import json
import random
import uuid

from .models import (
    Test,
    Question,
    Subject,
    Answer,
    Result,
    Group,
    UserAnswer,
    CheatingLog
)

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
    subject_cards = []

    if request.user.group:
        subjects = Subject.objects.filter(groups=request.user.group).prefetch_related('test_set', 'tests')
        finished_results = Result.objects.filter(user=request.user).select_related('test')
        result_by_test_id = {result.test_id: result.id for result in finished_results}

        for subject in subjects:
            tests = []
            seen_ids = set()

            for t in subject.test_set.all():
                tests.append({
                    'id': t.id,
                    'title': t.title,
                    'is_finished': t.id in result_by_test_id,
                    'result_id': result_by_test_id.get(t.id)
                })
                seen_ids.add(t.id)

            for t in subject.tests.all():
                if t.id not in seen_ids:
                    tests.append({
                        'id': t.id,
                        'title': t.title,
                        'is_finished': t.id in result_by_test_id,
                        'result_id': result_by_test_id.get(t.id)
                    })

            subject_cards.append({
                'name': subject.name,
                'tests': tests
            })

    return render(request, 'user/dashboard.html', {
        'subject_cards': subject_cards,
    })

# 3. Test yechish oynasi va 1 martalik cheklov
@login_required
def take_test(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    if Result.objects.filter(user=request.user, test=test).exists():
        return HttpResponse("""
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h1 style="color:#d93025;">Xato!</h1>
                <p>Siz ushbu testni topshirib bo'lgansiz.</p>
                <a href="/">Dashboardga qaytish</a>
            </div>
        """)

    session_key = f"test_session_{request.user.id}_{test.id}"

    all_questions = list(
        test.questions.select_related('subject').prefetch_related('answers')
    )

    if not all_questions:
        return HttpResponse("""
            <div style="text-align:center; margin-top:50px; font-family:sans-serif;">
                <h1>Testda savollar yo'q</h1>
                <a href="/">Dashboardga qaytish</a>
            </div>
        """)

    if request.method == 'GET':
        if len(all_questions) > 30:
            selected_questions = random.sample(all_questions, 30)
        else:
            selected_questions = all_questions[:]

        random.shuffle(selected_questions)

        session_data = {
            "question_ids": [q.id for q in selected_questions],
            "answers_order": {}
        }

        for q in selected_questions:
            answer_ids = list(q.answers.values_list('id', flat=True))
            random.shuffle(answer_ids)
            session_data["answers_order"][str(q.id)] = answer_ids

        request.session[session_key] = session_data
        request.session.modified = True

    session_data = request.session.get(session_key)

    if not session_data:
        return redirect('take_test', test_id=test.id)

    question_ids = session_data.get("question_ids", [])
    answers_order = session_data.get("answers_order", {})

    questions_dict = {
        q.id: q
        for q in test.questions.select_related('subject').prefetch_related('answers').filter(id__in=question_ids)
    }

    ordered_questions = []
    for qid in question_ids:
        q = questions_dict.get(qid)
        if not q:
            continue

        answer_map = {a.id: a for a in q.answers.all()}
        ordered_answers = []

        for aid in answers_order.get(str(q.id), []):
            ans = answer_map.get(aid)
            if ans:
                ordered_answers.append(ans)

        q.shuffled_answers = ordered_answers
        ordered_questions.append(q)

    if request.method == 'POST':
        total_questions = len(ordered_questions)
        user_answers_to_create = []

        correct_count = 0
        weighted_score = 0
        max_score = 0

        for q in ordered_questions:
            subj = q.subject or getattr(test, 'subject', None)

            selected_answer_id = request.POST.get(f'q{q.id}')
            selected_answer = None
            is_correct = False

            if selected_answer_id:
                selected_answer = Answer.objects.filter(
                    id=selected_answer_id,
                    question=q
                ).first()

                if selected_answer and selected_answer.is_correct:
                    is_correct = True
                    correct_count += 1

            point_value = getattr(subj, 'point_value', 0) if subj else 0
            max_score += point_value
            if is_correct:
                weighted_score += point_value

            user_answers_to_create.append({
                'question': q,
                'selected_answer': selected_answer,
                'is_correct': is_correct,
            })

        if max_score > 0:
            percentage = (weighted_score / max_score) * 100
        else:
            percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0

        result = Result.objects.create(
            user=request.user,
            test=test,
            correct_answers=correct_count,
            total_questions=total_questions,
            percentage=round(percentage, 2),
            weighted_score=round(weighted_score, 2)
        )

        for item in user_answers_to_create:
            UserAnswer.objects.create(
                result=result,
                question=item['question'],
                selected_answer=item['selected_answer'],
                is_correct=item['is_correct']
            )

        if session_key in request.session:
            del request.session[session_key]
            request.session.modified = True

        return redirect('result_detail', result_id=result.id)

    return render(request, 'user/take_test.html', {
        'test': test,
        'questions': ordered_questions,
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

@login_required
def result_detail(request, result_id):
    result = get_object_or_404(
        Result.objects.select_related('test', 'user'),
        id=result_id,
        user=request.user
    )

    user_answers = result.user_answers.select_related(
        'question',
        'selected_answer'
    ).prefetch_related(
        'question__answers'
    )

    detailed_answers = []

    for item in user_answers:
        correct_answers = item.question.answers.filter(is_correct=True)

        detailed_answers.append({
            'question_text': item.question.text,
            'selected_answer': item.selected_answer.text if item.selected_answer else "Javob belgilanmagan",
            'is_correct': item.is_correct,
            'correct_answers': [a.text for a in correct_answers],
        })

    return render(request, 'user/result_detail.html', {
        'result': result,
        'detailed_answers': detailed_answers,
    })

@login_required
@require_POST
def log_cheating_event(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    try:
        data = json.loads(request.body)
        event_type = data.get('event_type')
        details = data.get('details', '')
    except Exception:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    allowed_events = {
        'tab_switch',
        'fullscreen_exit',
        'right_click',
        'copy_attempt',
        'paste_attempt',
        'cut_attempt',
        'devtools_attempt',
    }

    if event_type not in allowed_events:
        return JsonResponse({'success': False, 'error': 'Invalid event type'}, status=400)

    CheatingLog.objects.create(
        user=request.user,
        test=test,
        event_type=event_type,
        details=details
    )

    return JsonResponse({'success': True})

def leaderboard(request, test_id):
    test = get_object_or_404(Test, id=test_id)

    top_results = (
        Result.objects.filter(test=test)
        .select_related('user')
        .order_by('-percentage', '-weighted_score', 'date_taken')[:10]
    )

    return render(request, 'user/leaderboard.html', {
        'test': test,
        'top_results': top_results,
    })
    
def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Sessiya tokenini yaratish
            user.session_token = str(uuid.uuid4())
            user.save(update_fields=['session_token'])
            request.session['session_token'] = user.session_token

            # Yo'naltirish (admin yoki o'quvchi)
            next_url = request.POST.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Login yoki parol noto'g'ri")
    else:
        form = AuthenticationForm()

    return render(request, 'registration/login.html', {'form': form})
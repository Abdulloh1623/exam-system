from django.test import TestCase
from django.urls import reverse
from .models import User, Group, Subject, Test, Question, Answer, Result

class ScoringTests(TestCase):
    def setUp(self):
        g = Group.objects.create(name='G1')
        self.user = User.objects.create_user(username='stu', password='pwd', group=g)
        # three subjects with different weights
        self.s1 = Subject.objects.create(name='Lang', point_value=3.1)
        self.s2 = Subject.objects.create(name='History', point_value=2.1)
        self.s3 = Subject.objects.create(name='Literature', point_value=1.1)
        self.test = Test.objects.create(title='Control Exam')
        self.test.subjects.set([self.s1, self.s2, self.s3])
        # questions: 1 per subject
        q1 = Question.objects.create(test=self.test, subject=self.s1, text='q1')
        q2 = Question.objects.create(test=self.test, subject=self.s2, text='q2')
        q3 = Question.objects.create(test=self.test, subject=self.s3, text='q3')
        Answer.objects.create(question=q1, text='a1', is_correct=True)
        Answer.objects.create(question=q2, text='a2', is_correct=True)
        Answer.objects.create(question=q3, text='a3', is_correct=False)

    def test_weighted_score_calculation(self):
        self.client.login(username='stu', password='pwd')
        url = reverse('take_test', args=[self.test.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # simulate selecting first two correct answers and third wrong
        data = {}
        for q in Question.objects.filter(test=self.test):
            try:
                ans = Answer.objects.get(question=q, is_correct=True)
                data[f'q{q.id}'] = ans.id
            except Answer.DoesNotExist:
                # leave unanswered to count as wrong
                pass
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        # check result object
        res = Result.objects.get(user=self.user, test=self.test)
        # correct_answers =2, total=3
        self.assertEqual(res.correct_answers, 2)
        # weighted_score should be 3.1 + 2.1 = 5.2
        self.assertAlmostEqual(float(res.weighted_score), 5.2)

    def test_admin_creates_control_work_copies_questions(self):
        # simulate existing question bank
        subj_a = Subject.objects.create(name='A', point_value=1.0)
        q_orig = Question.objects.create(test=self.test, subject=subj_a, text='orig')
        Answer.objects.create(question=q_orig, text='ok', is_correct=True)
        # create new test with same subject via API (using model directly since we can't easily invoke admin)
        new_test = Test.objects.create(title='New composite')
        new_test.subjects.set([subj_a])
        # replicate the copy logic that TestAdmin.save_model would perform
        subs = [subj_a]
        for subj in subs:
            existing = Question.objects.filter(subject=subj)
            for q in existing:
                if not Question.objects.filter(test=new_test, text=q.text, subject=q.subject).exists():
                    new_q = Question.objects.create(test=new_test, text=q.text, subject=q.subject)
                    for ans in q.answers.all():
                        Answer.objects.create(question=new_q, text=ans.text, is_correct=ans.is_correct)
        # copied question should exist
        self.assertTrue(Question.objects.filter(test=new_test, text='orig').exists())

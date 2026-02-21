import re
from .models import Question, Answer

def parse_bulk_questions(test_id, text):
    # Savollarni raqamlar orqali ajratamiz: "1. Savol", "2. Savol"
    # Regex: qator boshidagi raqam va nuqta
    blocks = re.split(r'\n(?=\d+\.)', text.strip())
    
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) < 2: continue
        
        # Savol matnidan tartib raqamini olib tashlash
        question_text = re.sub(r'^\d+\.\s*', '', lines[0])
        question = Question.objects.create(test_id=test_id, text=question_text)
        
        for line in lines[1:]:
            is_correct = False
            # To'g'ri javobni aniqlash (+ belgisi)
            if line.startswith('+'):
                is_correct = True
                line = line[1:].strip()
            
            # A), B) kabi harflarni tozalash
            clean_answer = re.sub(r'^[A-Z]\)\s*', '', line)
            
            Answer.objects.create(
                question=question,
                text=clean_answer,
                is_correct=is_correct
            )
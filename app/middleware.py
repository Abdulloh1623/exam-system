from django.contrib.auth import logout
from django.shortcuts import redirect

class OneSessionPerUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            session_token = request.session.get('session_token')
            user_token = getattr(request.user, 'session_token', None)

            if user_token and session_token and session_token != user_token:
                logout(request)
                return redirect('login')

        response = self.get_response(request)
        return response
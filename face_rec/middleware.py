from django.shortcuts import redirect

class PreventBackMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path == '/login/' and request.user.is_authenticated:
            return redirect('dashboard')

        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
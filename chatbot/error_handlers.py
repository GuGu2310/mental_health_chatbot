from django.shortcuts import render
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

def handler404(request, exception):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    
    if request.path.startswith('/api/') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({'error': 'Resource not found'}, status=404)
    
    return render(request, 'chatbot/errors/404.html', status=404)

def handler500(request):
    """Handle 500 errors"""
    logger.error(f"500 error on path: {request.path}")
    
    if request.path.startswith('/api/') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({'error': 'Internal server error'}, status=500)
    
    return render(request, 'chatbot/errors/500.html', status=500)

def handler403(request, exception):
    """Handle 403 errors"""
    logger.warning(f"403 error: {request.path}")
    
    if request.path.startswith('/api/') or 'application/json' in request.META.get('HTTP_ACCEPT', ''):
        return JsonResponse({'error': 'Access forbidden'}, status=403)
    
    return render(request, 'chatbot/errors/403.html', status=403)
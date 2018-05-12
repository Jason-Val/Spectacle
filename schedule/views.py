from django.shortcuts import render

# Create your views here.

def index(request):
    """
    View function for home page of site.
    """
    highlight_index = True
    
    return render(
        request,
        'index.html',
        context={'highlight_index':highlight_index}
    )
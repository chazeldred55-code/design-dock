from django.shortcuts import render

def view_bag(request):
    """ A view to render the shopping bag contents page """
    return render(request, 'bag/bag.html')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from .models import Product, Category, Review, Cart, Favorite
from .forms import ProductForm




class ProductAddView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_staff

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class ProductEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_staff

class ProductDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Product
    template_name = 'shop/product_confirm_delete.html'
    success_url = reverse_lazy('home')

    def test_func(self):
        return self.request.user.is_staff


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff

class ProductAddView(StaffRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class ProductEditView(StaffRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'shop/product_form.html'
    success_url = reverse_lazy('home')

# Удаление товара
class ProductDeleteView(StaffRequiredMixin, DeleteView):
    model = Product
    template_name = 'shop/product_confirm_delete.html'
    success_url = reverse_lazy('home')

@login_required
def get_cart_count(request):
    count = Cart.objects.filter(user=request.user).count()
    return JsonResponse({'count': count})



def home(request):
    search_query = request.GET.get('q', '')  # Изменяем параметр с 'search' на 'q'

    # Основной запрос для товаров
    products = Product.objects.filter(is_active=True).select_related('category')

    # Применяем поиск, если есть запрос
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Получаем данные для виджетов (только если нет поискового запроса)
    if not search_query:
        popular_products = Product.objects.annotate(
            order_count=Count('orderitem')
        ).filter(is_active=True).order_by('-order_count')[:5]

        new_products = Product.objects.filter(
            is_active=True).order_by('-created_at')[:4]

        discounted_products = Product.objects.filter(
            discount__gt=0, is_active=True).order_by('-discount')[:3]

        recent_reviews = Review.objects.select_related(
            'product', 'user').order_by('-created_at')[:3]
    else:
        popular_products = new_products = discounted_products = recent_reviews = None

    categories = Category.objects.all()

    context = {
        'products': products,
        'popular_products': popular_products,
        'new_products': new_products,
        'discounted_products': discounted_products,
        'recent_reviews': recent_reviews,
        'search_query': search_query,
        'categories': categories,
    }
    return render(request, 'shop/home.html', context)


def product_detail(request, pk):
    product = Product.objects.get(pk=pk)
    reviews = Review.objects.filter(product=product).order_by('-created_at')
    similar_products = Product.objects.filter(
        category=product.category
    ).exclude(pk=product.pk)[:4]

    is_author_or_staff = request.user.is_authenticated and (
            request.user.is_staff or
            (hasattr(product, 'created_by') and product.created_by == request.user
             ))

    favorite_product_ids = []
    if request.user.is_authenticated:
        favorite_product_ids = request.user.favorites.values_list('product_id', flat=True)



    context = {
        'product': product,
        'is_author_or_staff': is_author_or_staff,
        'reviews': reviews,
        'similar_products': similar_products,
        'favorite_product_ids': favorite_product_ids,
    }
    return render(request, 'shop/product_detail.html', context)

def category_products(request, slug):
    category = Category.objects.get(slug=slug)
    products = Product.objects.filter(
        category=category, is_active=True).order_by('-created_at')

    context = {
        'category': category,
        'products': products,
    }
    return render(request, 'shop/category_products.html', context)


@login_required
def favorites(request):
    # Получаем ID товаров в избранном для текущего пользователя
    favorite_product_ids = Favorite.objects.filter(
        user=request.user
    ).values_list('product_id', flat=True)

    # Получаем сами товары
    favorite_products = Product.objects.filter(
        id__in=favorite_product_ids
    ).select_related('category')

    context = {
        'favorite_products': favorite_products,
    }
    return render(request, 'shop/favorites.html', context)


@login_required
def add_to_favorites(request, product_id):
    if request.method == 'POST':
        product = Product.objects.get(id=product_id)
        favorite, created = Favorite.objects.get_or_create(
            user=request.user,
            product=product
        )
        return JsonResponse({
            'success': True,
            'action': 'added' if created else 'already_exists'
        })
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def remove_from_favorites(request, product_id):
    if request.method == 'POST':
        deleted, _ = Favorite.objects.filter(
            user=request.user,
            product_id=product_id
        ).delete()
        return JsonResponse({
            'success': True,
            'action': 'removed' if deleted else 'not_found'
        })
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def cart_view(request):
    cart_items = Cart.objects.filter(user=request.user).select_related('product')
    total_price = sum(item.total_price for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'shop/cart.html', context)


@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': 1}
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f'Товар "{product.name}" добавлен в корзину')
    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def remove_from_cart(request, cart_item_id):
    cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'Товар "{product_name}" удален из корзины')
    return redirect('cart_view')


@login_required
def update_cart_item(request, cart_item_id):
    if request.method == 'POST':
        cart_item = get_object_or_404(Cart, id=cart_item_id, user=request.user)
        quantity = int(request.POST.get('quantity', 1))

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Количество обновлено')
        else:
            cart_item.delete()
            messages.success(request, 'Товар удален из корзины')

    return redirect('cart_view')

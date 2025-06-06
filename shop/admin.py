from django.contrib import admin
from django.utils.html import format_html
from .models import User, Category, Product, Order, OrderItem, Review, Cart, Favorite  # Добавляем Favorite в импорт


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    raw_id_fields = ['product']
    readonly_fields = ['item_total']

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['price_at_purchase'].widget.can_add_related = False
        return formset

    @admin.display(description='Сумма')
    def item_total(self, obj):
        if obj.pk and obj.price_at_purchase:
            return obj.quantity * obj.price_at_purchase
        return "0.00"


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'phone', 'registration_date', 'orders_count']
    list_display_links = ['username', 'email']
    list_filter = ['is_staff', 'is_superuser', 'registration_date']
    search_fields = ['username', 'email', 'phone', 'first_name', 'last_name']
    filter_horizontal = ['groups', 'user_permissions']
    readonly_fields = ['registration_date']
    date_hierarchy = 'registration_date'

    @admin.display(description='Заказы')
    def orders_count(self, obj):
        return obj.orders.count()


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'products_count']
    list_filter = ['parent']
    search_fields = ['name']
    prepopulated_fields = {'slug': ['name']}

    @admin.display(description='Товаров')
    def products_count(self, obj):
        return obj.products.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'image_preview', 'created_at', 'is_active']
    list_display_links = ['name']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    raw_id_fields = ['category']
    readonly_fields = ['created_at', 'image_preview']
    date_hierarchy = 'created_at'

    @admin.display(description='Изображение')
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'display_total', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'id']
    raw_id_fields = ['user']
    date_hierarchy = 'created_at'
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'display_total']

    @admin.display(description='Общая сумма')
    def display_total(self, obj):
        if obj.pk:
            return sum(item.quantity * item.price_at_purchase for item in obj.items.all())
        return "0.00"

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.total_amount = 0
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        order = form.instance
        order.total_amount = sum(
            item.quantity * item.price_at_purchase
            for item in order.items.all()
        )
        order.save(update_fields=['total_amount'])


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price_at_purchase', 'item_total']
    raw_id_fields = ['order', 'product']

    @admin.display(description='Сумма')
    def item_total(self, obj):
        return obj.quantity * obj.price_at_purchase

    def save_model(self, request, obj, form, change):
        if not obj.price_at_purchase:
            obj.price_at_purchase = obj.product.price
        super().save_model(request, obj, form, change)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'created_at', 'short_text']
    list_filter = ['rating', 'created_at']
    search_fields = ['product__name', 'user__username', 'text']
    raw_id_fields = ['product', 'user']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    @admin.display(description='Текст')
    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'quantity', 'added_at', 'total_price']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    raw_id_fields = ['user', 'product']
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'

    @admin.display(description='Общая стоимость')
    def total_price(self, obj):
        return obj.quantity * obj.product.price


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'added_at']
    list_filter = ['added_at']
    search_fields = ['user__username', 'product__name']
    raw_id_fields = ['user', 'product']
    readonly_fields = ['added_at']
    date_hierarchy = 'added_at'

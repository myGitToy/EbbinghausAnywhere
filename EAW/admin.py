from django.contrib import admin
from django.contrib.admin import AdminSite
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from .models import (
    Category, Item, ReviewDay,
    UserPoints, PointHistory, UserPointsConfig, PointRedemption, UserStreak,
    ModelPricing, DeepSeekUsageLog
)
from .forms import CategoryAdminForm, ItemAdminForm, ReviewDayAdminForm
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.utils.html import format_html
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .translate import baidu_translate, check_api_keys
from django.template.response import TemplateResponse
import re
import logging
import difflib
from .utils import fetch_and_merge_translation

logger = logging.getLogger(__name__)

class BaseAdmin(admin.ModelAdmin):
    """
    自定义基类Admin，用于实现普通用户只能看到自己的条目，
    超级用户可以看到所有条目。
    """
    exclude = ('user',)

    def get_queryset(self, request):
        """
        限制普通用户只能查看自己的条目，超级用户可以查看所有条目。
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # 超级用户可以看到所有条目
        return qs.filter(user=request.user)  # 普通用户只能看到自己的条目

    def save_model(self, request, obj, form, change):
        """
        保存模型时，普通用户只能修改自己的条目，超级用户可以修改所有条目。
        """
        if not obj.pk:  # 如果是新创建的对象
            obj.user = request.user
        elif not request.user.is_superuser and obj.user != request.user:
            raise PermissionError("普通用户不能修改其他用户的条目。")
        obj.save()

class UserCategoryFilter(admin.SimpleListFilter):
    """
    自定义过滤器，确保普通用户只能看到自己创建的类别，超级用户可以看到所有类别。
    """
    title = _('Category')  # 过滤器标题
    parameter_name = 'category'  # 过滤器参数名称

    def lookups(self, request, model_admin):
        """
        提供过滤器的选择项，普通用户只能看到自己创建的类别，超级用户可以看到所有类别。
        """
        if request.user.is_superuser:
            # 超级用户可以看到所有的类别
            return [(category.id, category.name) for category in Category.objects.all()]
        else:
            # 普通用户只能看到自己创建的类别
            return [(category.id, category.name) for category in Category.objects.filter(user=request.user)]

    def queryset(self, request, queryset):
        """
        根据过滤条件进行查询集过滤
        """
        if self.value():
            # 如果有选择的值，则按category进行过滤
            return queryset.filter(category_id=self.value())
        return queryset


class CategoryAdmin(BaseAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'user')  # 超级用户可以在列表中看到用户信息
    ordering = ('sort_order', 'name')  # 默认按排序顺序和名称排序

    def get_list_filter(self, request):
        """
        动态调整过滤器，普通用户只能按类别筛选，超级用户能够按 user 筛选。
        """
        filters = ['sort_order']
        if request.user.is_superuser:
            filters.append('user')  # 超级用户可以按 user 筛选
        return filters

    def get_queryset(self, request):
        """
        普通用户只能看到自己创建的Category，超级用户可以看到所有的Category。
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # 超级用户可以看到所有类别
        return qs.filter(user=request.user)  # 普通用户只能看到自己创建的类别
    
    def save_model(self, request, obj, form, change):
        """
        自定义保存逻辑，阻止非法操作。
        """
        if change and obj.is_default and 'name' in form.changed_data:
            messages.error(request, "Cannot modify the name of the default category.")
            return  # 中断保存操作
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        自定义删除逻辑，阻止删除默认分类。
        """
        if obj.is_default:
            messages.error(request, "Cannot delete the default category.")
            return  # 中断删除操作
        super().delete_model(request, obj)

    def response_change(self, request, obj):
        """
        自定义修改后的响应，避免阻止字段修改时显示保存成功的提示。
        """
        # 检测是否试图修改默认分类的名称
        if obj.is_default and 'name' in request.POST:
            submitted_name = request.POST.get('name', '').strip()
            if submitted_name != obj.name:
                # 阻止保存，添加错误消息
                messages.error(request, "Cannot modify the name of the default category.")
                # 重新渲染页面，无保存成功提示
                return self.render_change_form(
                    request,
                    context=self.get_changeform_initial_data(request, obj),
                    obj=obj,
                    form_url=None,
                    add=False,
                    change=True,
                )

        # 对于合法操作，调用父类方法，显示正常提示
        return super().response_change(request, obj)



class ItemAdmin(BaseAdmin):
    form = ItemAdminForm
    list_display = ('item', 'proficiency', 'category', 'user')  # 超级用户可看到用户信息
    search_fields = ('item', 'content')  # 支持按单词和内容搜索
    change_form_template = 'admin/item_change_form.html'  # 添加自定义模板

    def get_list_filter(self, request):
        filters = ['proficiency', UserCategoryFilter]  # 默认只显示类别和掌握程度的过滤器
        if request.user.is_superuser:
            filters.append('user')  # 超级用户可以根据 `user` 过滤
        return filters

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            if not request.user.is_superuser:
                kwargs["queryset"] = Category.objects.filter(user=request.user)  # 普通用户只能看到自己的类别
            else:
                kwargs["queryset"] = Category.objects.all()  # 超级用户可以看到所有类别
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(user=request.user)  # 普通用户只能看到自己创建的条目
        return qs  # 超级用户可以看到所有条目

    # 添加翻译按钮
    def get_translate_button(self, obj):
        if obj.category.name == "单词":
            return format_html(
                '<button class="button translate-button" data-id="{}">获取释义</button>',
                obj.id
            )
        return "-"

    get_translate_button.short_description = "操作"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('translate/<int:item_id>/', self.translate_item, name='translate_item'),
        ]
        return custom_urls + urls
    
    def translate_item(self, request, item_id):
        """
        调用翻译函数，逐行比较释义并合并新内容。
        """
        logger.debug(f"Received item_id: {item_id}")
        item = get_object_or_404(Item, id=item_id)
        if item.category.name != "单词":
            return JsonResponse({"success": False, "message": "当前类别不是 '单词'，无法翻译。"})

        # 使用工具函数来获取和合并翻译
        updated_content, src_tts, phonetic_am, phonetic_en = fetch_and_merge_translation(item.item, item.content)

        if not updated_content:
            return JsonResponse({"success": False, "message": "翻译失败，请稍后重试。"})

        # 更新条目
        item.content = updated_content
        item.src_tts = src_tts
        item.us_phonetic = phonetic_am
        item.uk_phonetic = phonetic_en
        item.save()

        # 返回结果
        return JsonResponse({
            "success": True,
            "definition": updated_content,
            "src_tts": src_tts,
            "phonetic_am": phonetic_am,
            "phonetic_en": phonetic_en
        })

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # 检查 API 配置状态
        api_status = "available" if check_api_keys() else "unavailable"

        # 将 API 状态传入模板上下文
        extra_context = extra_context or {}
        extra_context['api_status'] = api_status
        return super().change_view(request, object_id, form_url, extra_context=extra_context)




class ReviewDayAdmin(BaseAdmin):
    form = ReviewDayAdminForm
    list_display = ('day', 'user')  # 超级用户可看到用户信息

    def get_list_filter(self, request):
        """
        动态调整ReviewDay的过滤器，超级用户能看到按 user 筛选。
        """
        filters = []
        if request.user.is_superuser:
            filters.append('user')  # 超级用户能够按 user 筛选
        return filters

    def get_queryset(self, request):
        """
        普通用户只能看到自己创建的ReviewDay，超级用户可以看到所有的ReviewDay。
        """
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # 超级用户可以看到所有复习天
        return qs.filter(user=request.user)  # 普通用户只能看到自己创建的复习天


# 注册所有模型到admin
admin.site.register(Category, CategoryAdmin)
admin.site.register(Item, ItemAdmin)
admin.site.register(ReviewDay, ReviewDayAdmin)


# ==================== 积分系统 Admin ====================

class UserPointsAdmin(BaseAdmin):
    """用户积分账户管理"""
    list_display = ('user', 'current_points', 'total_earned', 'total_spent', 'last_updated')
    list_filter = ('last_updated',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('last_updated',)

    def has_add_permission(self, request):
        # 不允许手动添加，系统自动创建
        return False

    def has_delete_permission(self, request, obj=None):
        # 不允许删除积分账户
        return False


class PointHistoryAdmin(BaseAdmin):
    """积分历史记录管理"""
    list_display = ('user', 'change_type', 'points', 'reason', 'balance_after', 'created_at')
    list_filter = ('change_type', 'created_at')
    search_fields = ('user__username', 'reason', 'reference_id')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        # 不允许手动添加历史记录
        return False

    def has_change_permission(self, request, obj=None):
        # 历史记录不可修改
        return False

    def has_delete_permission(self, request, obj=None):
        # 历史记录不可删除
        return False


class UserPointsConfigAdmin(BaseAdmin):
    """用户积分配置管理"""
    list_display = ('user', 'minutes_per_point', 'redemption_step',
                    'daily_checkin_enabled', 'streak_reward_enabled', 'updated_at')
    list_filter = ('daily_checkin_enabled', 'streak_reward_enabled', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('基本信息', {
            'fields': ('user',)
        }),
        ('兑换规则', {
            'fields': ('minutes_per_point', 'redemption_step',
                      'min_redemption_minutes', 'max_redemption_minutes')
        }),
        ('签到奖励', {
            'fields': ('daily_checkin_enabled', 'daily_checkin_points')
        }),
        ('连续学习奖励', {
            'fields': ('streak_reward_enabled', 'streak_reward_points', 'streak_reward_days')
        }),
        ('时间信息', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class PointRedemptionAdmin(BaseAdmin):
    """兑换记录管理"""
    list_display = ('user', 'points_spent', 'game_minutes', 'exchange_rate',
                    'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'notes')
    readonly_fields = ('created_at',)

    def has_add_permission(self, request):
        # 不允许手动添加兑换记录
        return False

    def has_change_permission(self, request, obj=None):
        # 已完成的兑换记录不可修改
        if obj and obj.status == 'COMPLETED':
            return False
        return super().has_change_permission(request, obj)


class UserStreakAdmin(BaseAdmin):
    """用户连续学习记录管理"""
    list_display = ('user', 'current_streak', 'longest_streak',
                    'current_checkin_streak', 'longest_checkin_streak',
                    'last_study_date', 'last_checkin_date', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)

    fieldsets = (
        ('连续学习', {
            'fields': ('current_streak', 'longest_streak', 'last_study_date')
        }),
        ('连续签到', {
            'fields': ('current_checkin_streak', 'longest_checkin_streak', 'last_checkin_date')
        }),
        ('奖励记录', {
            'fields': ('last_streak_reward_date',)
        }),
        ('时间信息', {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # 不允许手动添加，系统自动创建
        return False


# 注册积分系统模型
admin.site.register(UserPoints, UserPointsAdmin)
admin.site.register(PointHistory, PointHistoryAdmin)
admin.site.register(UserPointsConfig, UserPointsConfigAdmin)
admin.site.register(PointRedemption, PointRedemptionAdmin)
admin.site.register(UserStreak, UserStreakAdmin)


# ==================== DeepSeek 峰谷计费 Admin ====================

class ModelPricingAdmin(admin.ModelAdmin):
    """模型峰谷价格表：可编辑，保存时自动刷新 pricing_updated_at（调价留痕）"""
    list_display = ('model_name', 'cache_hit_display', 'cache_miss_display',
                    'output_display', 'pricing_updated_at', 'price_source')
    readonly_fields = ('pricing_updated_at',)
    search_fields = ('model_name',)
    fieldsets = (
        ('模型', {
            'fields': ('model_name', 'price_source')
        }),
        ('闲时价（元/百万 tokens）', {
            'fields': ('offpeak_cache_hit_price', 'offpeak_cache_miss_price', 'offpeak_output_price')
        }),
        ('高峰价（元/百万 tokens，三列全为 0 表示不启用峰时计费）', {
            'fields': ('peak_cache_hit_price', 'peak_cache_miss_price', 'peak_output_price')
        }),
        ('元数据', {
            'fields': ('pricing_updated_at',),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        # 官方调价后管理员改价时自动留痕
        obj.pricing_updated_at = timezone.now()
        super().save_model(request, obj, form, change)

    def cache_hit_display(self, obj):
        from .billing import display_price_pair
        return format_html(
            "{}", display_price_pair(
                obj.offpeak_cache_hit_price, obj.peak_cache_hit_price, obj.peak_enabled
            )
        )
    cache_hit_display.short_description = '输入·缓存命中'

    def cache_miss_display(self, obj):
        from .billing import display_price_pair
        return format_html(
            "{}", display_price_pair(
                obj.offpeak_cache_miss_price, obj.peak_cache_miss_price, obj.peak_enabled
            )
        )
    cache_miss_display.short_description = '输入·缓存未命中'

    def output_display(self, obj):
        from .billing import display_price_pair
        return format_html(
            "{}", display_price_pair(
                obj.offpeak_output_price, obj.peak_output_price, obj.peak_enabled
            )
        )
    output_display.short_description = '输出'


class DeepSeekUsageLogAdmin(BaseAdmin):
    """DeepSeek 用量流水：只读审计，普通用户仅见自己的流水（同 PointHistoryAdmin 风格）"""
    list_display = ('user', 'model', 'band_display', 'prompt_tokens', 'cached_tokens',
                    'output_tokens', 'cost_display', 'billed_at')
    list_filter = ('band', 'model', 'billed_at')
    search_fields = ('user__username', 'model')
    date_hierarchy = 'billed_at'

    def band_display(self, obj):
        return obj.get_band_display()
    band_display.short_description = '时段'

    def cost_display(self, obj):
        # 展示 4 位小数（存储 10 位精确）
        return f"¥{obj.cost.quantize(Decimal('0.0001')):f}"
    cost_display.short_description = '费用（元）'

    def has_add_permission(self, request):
        # 流水由系统写入，不允许手工添加
        return False

    def has_change_permission(self, request, obj=None):
        # 审计流水不可修改
        return False

    def has_delete_permission(self, request, obj=None):
        # 审计流水不可删除（永久保留）
        return False


# 注册计费模型
admin.site.register(ModelPricing, ModelPricingAdmin)
admin.site.register(DeepSeekUsageLog, DeepSeekUsageLogAdmin)



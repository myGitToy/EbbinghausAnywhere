from django.shortcuts import render
from django.core.paginator import Paginator
from django.views import generic
from django.db.models import Avg, Max, Min, Count, Sum
from datetime import datetime
from datetime import timedelta
from django.utils.timezone import now
from django import forms
from .forms import InputForm,  CustomUserCreationForm, EmailUpdateForm, UpdateNameForm, CustomPasswordChangeForm, DeepSeekConfigForm
from django.utils.decorators import method_decorator
from django.views.generic.detail import DetailView
from django.contrib.auth.decorators import permission_required
from django.core.cache import cache
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required

from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, JsonResponse
from django.http import HttpResponse
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import json
import csv
from time import sleep
import logging
import re
from django.views.decorators.csrf import csrf_exempt
import json
from django.template.loader import render_to_string
from .translate import baidu_translate, parse_json_to_string, check_api_keys
from .deepseek import deepseek_translate, check_deepseek_keys, call_deepseek_api
import openpyxl
from django.db import transaction
from .models import Item, Category, Proficiency, ReviewDay, DeepSeekConfig
import difflib
import uuid
from .utils import fetch_and_merge_translation
import markdown
from django.conf import settings
import os

logger = logging.getLogger(__name__)

# Create your views here.
from .models import Item, Proficiency, Category, ReviewDay

def custom_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # 使用 authenticate 进行身份验证
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # 如果用户验证通过，则登录并重定向
            login(request, user)
            return redirect('home')  # 登录成功后可以重定向到首页或其他页面
        else:
            # 如果用户名或密码错误，使用消息框架显示错误信息
            messages.error(request, "用户名或密码无效，请检查后重试。")

    return render(request, 'registration/login.html')


def register(request):
    if request.method == 'POST':
        random_id = request.POST.get('random_id', None)  # 获取随机 ID
        # 重构 POST 数据，将动态字段映射回标准字段
        if random_id:
            mapped_post = {
                'username': request.POST.get(f'random_username_{random_id}', ''),
                'email': request.POST.get('email', ''),
                'first_name': request.POST.get('first_name', ''),
                'last_name': request.POST.get('last_name', ''),
                'password1': request.POST.get(f'random_password1_{random_id}', ''),
                'password2': request.POST.get(f'random_password2_{random_id}', ''),
            }
            form = CustomUserCreationForm(mapped_post)
        else:
            form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            try:
                user = form.save()
                username = form.cleaned_data.get('username')

                # 加入 Public 组
                public_group, created = Group.objects.get_or_create(name='Public')
                user.groups.add(public_group)
                user.is_staff = True
                user.save()

                # 创建默认类别和复习计划
                Category.objects.create(user=user, name="单词", sort_order=1, is_default=True)
                review_days = [1, 2, 4, 7, 15, 30, 90, 180, 365]
                ReviewDay.objects.bulk_create(
                    [ReviewDay(user=user, day=day) for day in review_days]
                )

                messages.success(request, f'Account {username} created successfully!')
                return redirect('login')

            except Exception as e:
                logger.error(f"Error during registration: {e}")
                messages.error(request, f"Registration failed: {e}")
        else:
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    if field == 'password2':
                        error = error.replace('password2', 'Password confirmation')
                    error_messages.append(f"<p>{error}</p>")

            form_errors = "".join(error_messages)
            logger.warning(f"Form validation failed: {form.errors}")
            messages.error(request, f"<p>Please fix the following errors: {form_errors}</p>")
    else:
        random_id = uuid.uuid4().hex  # 生成一个随机 ID
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form, 'random_id': random_id})


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

@login_required
def user_profile(request):
    if request.method == 'POST':
        # Update email
        if 'update_email' in request.POST:
            email_form = EmailUpdateForm(request.user, request.POST)
            if email_form.is_valid():
                request.user.email = email_form.cleaned_data.get('email')
                request.user.save()
                messages.success(request, "Email updated successfully.")
            else:
                messages.error(request, "Failed to update email. Please check the errors.")

        # Update name
        elif 'update_profile' in request.POST:
            name_form = UpdateNameForm(request.POST, instance=request.user)
            if name_form.is_valid():
                name_form.save()
                messages.success(request, "Name updated successfully.")
            else:
                messages.error(request, "Failed to update name. Please check the errors.")

        # Update password
        elif 'change_password' in request.POST:
            password_form = CustomPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in
                messages.success(request, "Password updated successfully.")
            else:
                messages.error(request, "Failed to update password. Please check the errors.")

        return redirect('user_profile')

    else:
        email_form = EmailUpdateForm(request.user)
        name_form = UpdateNameForm(instance=request.user)
        password_form = CustomPasswordChangeForm(user=request.user)

    return render(request, 'user_profile.html', {
        'email_form': email_form,
        'name_form': name_form,
        'password_form': password_form,
    })


def home(request):
    # 检查用户是否登录
    if request.user.is_authenticated:
        # 获取当前用户的所有 items
        items = Item.objects.filter(user=request.user)
        # 统计数据
        total_items = items.count()
        if total_items > 0:
            first_item_date = items.order_by('inputDate').first().inputDate
            days_since_first_item = (now().date() - first_item_date).days
        else:
            days_since_first_item = 0
        
        # 判断如何显示用户名
        if request.user.first_name and request.user.last_name:
            display_name = f"{request.user.first_name} {request.user.last_name}"  # 合并 first_name 和 last_name
        elif request.user.first_name:
            display_name = request.user.first_name  # 只有 first_name
        elif request.user.last_name:
            display_name = request.user.last_name  # 只有 last_name
        else:
            display_name = request.user.username  # 都没有，使用 username
        
        context = {
            'display_name': display_name,  # 修改为 display_name
            'total_items': total_items,
            'days_since_first_item': days_since_first_item,
        }
        # 用户已登录，返回登录后的首页
        return render(request, 'home_logged_in.html', context)
    else:
        # 用户未登录，返回未登录的首页
        return render(request, 'home_logged_out.html')


# @login_required
# def index(request):
#     """
#     Index view to show the total count of items and the count for each category.
#     """
#     # 获取当前登录用户
#     user = request.user

#     # 查询用户的所有条目和分类
#     total_items = Item.objects.filter(user=user).count()  # 总条目数
#     categories = Category.objects.filter(user=user)  # 当前用户的所有分类
#     category_counts = {
#         category.name: Item.objects.filter(user=user, category=category).count()
#         for category in categories
#     }

#     # 渲染上下文
#     context = {
#         'total_items': total_items,
#         'category_counts': category_counts,
#     }

#     return render(request, 'index.html', context)

@login_required
def item_list(request):
    # 获取当前登录用户的所有 Item
    item_list = Item.objects.filter(user=request.user).order_by('-inputDate')

    # 统计每个类别下的条目数量
    category_stats = item_list.values('category__name').annotate(count=Count('category')).order_by('-count')

    # 确保 item_list 不为空时才进行分页
    if item_list.exists():
        paginator = Paginator(item_list, 50)  # 每页 50 个
        page_number = request.GET.get('page')  # 获取当前页码
        page_obj = paginator.get_page(page_number)
    else:
        # 如果 item_list 为空，设置 page_obj 为一个空列表或自定义的对象
        page_obj = []

    # 渲染模板，传递分页对象和类别统计信息
    return render(request, 'list.html', {'page_obj': page_obj, 'category_stats': category_stats})


@method_decorator(login_required, name='dispatch')  # 确保用户已登录
class ItemDetailView(DetailView):
    model = Item
    template_name = 'item_detail.html'  # 设置模板路径

    def get_queryset(self):
        # 只允许当前登录用户访问属于自己的 Item
        return Item.objects.filter(user=self.request.user)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # 验证是否属于当前用户
        if obj.user != self.request.user:
            # 返回自定义提示页面
            return render(self.request, 'EAW/item_not_found.html', status=404)
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = context.get('object')
        from datetime import date, timedelta

        # 与其他地方保持一致的间隔定义
        intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]

        # 基准日期：优先使用 initDate，否则使用 inputDate，若都无则使用今天
        base_date = item.initDate or item.inputDate or date.today()

        # unfamiliar_history 可能为 None
        uh = item.unfamiliar_history or []

        schedule = []
        today = date.today()
        # 计算当前的索引（如果 current_interval 存的是天数）
        try:
            current_index = intervals.index(item.current_interval) if item.current_interval is not None else None
        except ValueError:
            current_index = None

        for idx, days in enumerate(intervals):
            scheduled_date = None
            try:
                scheduled_date = base_date + timedelta(days=days)
            except Exception:
                scheduled_date = None

            # 是否已完成：根据 current_index（interval 的索引）判断
            completed = False
            if current_index is not None and current_index > idx:
                completed = True

            # 是否逾期（已过计划日但未完成）
            overdue = False
            if scheduled_date and scheduled_date < today and not completed:
                overdue = True

            # 熟悉判断：如果 completed 并且 unfamiliar_history 中没有该 interval 的记录，则视为熟悉
            unfamiliar_records = [r for r in uh if r.get('interval') == days or r.get('interval') == idx]
            if completed:
                familiar = (len(unfamiliar_records) == 0)
            else:
                familiar = None

            schedule.append({
                'index': idx,
                'days': days,
                'scheduled_date': scheduled_date,
                'completed': completed,
                'overdue': overdue,
                'familiar': familiar,
                'unfamiliar_records': unfamiliar_records,
            })

        context['review_schedule'] = schedule
        return context


@method_decorator(login_required, name='dispatch')
class ItemUpdateView(generic.UpdateView):
    model = Item
    template_name = 'item_form.html'
    fields = ['item', 'content', 'category', 'uk_phonetic', 'us_phonetic', 'src_tts', 'inputDate', 'initDate', 'proficiency']
    
    def get_queryset(self):
        # 只允许用户编辑自己的Item
        return Item.objects.filter(user=self.request.user)
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # 限制category只显示当前用户的类别
        form.fields['category'].queryset = Category.objects.filter(user=self.request.user)
        # 添加Bootstrap样式
        for field_name, field in form.fields.items():
            if field.widget.__class__.__name__ != 'CheckboxInput':
                field.widget.attrs['class'] = 'form-control'
        return form
    
    def form_valid(self, form):
        messages.success(self.request, f'单词 "{form.instance.item}" 已成功更新！')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('item-list')


@method_decorator(login_required, name='dispatch')
class ItemDeleteView(generic.DeleteView):
    model = Item
    template_name = 'item_confirm_delete.html'
    
    def get_queryset(self):
        # 只允许用户删除自己的Item
        return Item.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        item = self.get_object()
        messages.success(request, f'单词 "{item.item}" 已成功删除！')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('item-list')


@login_required
def SearchView(request):
    word = ''
    query = Item.objects.none()

    # 获取搜索关键词
    search_input = request.GET.get('q', '').strip()
    logger.debug(f"Search input received: {search_input}")

    if search_input == '':  # 如果没有输入关键词
        if 'q' in request.GET:
            word = 'No search input.'
        return render(
            request,
            'search.html',
            context={'word': word},
        )
    else:
        # 在当前用户的数据库中搜索 item 字段包含搜索关键词的条目
        try:
            query = Item.objects.filter(user=request.user, item__icontains=search_input)
            if not query.exists():
                word = 'No search result.'
        except Exception as e:
            logger.error(f"Error during search query: {e}")
            return JsonResponse({'error': 'Error processing your search query'}, status=500)

    # 如果是 AJAX 请求，返回 JSON 数据
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # 渲染搜索结果的 HTML
            html = render_to_string('search_results.html', {'query': query, 'word': word})
            logger.debug(f"Generated HTML for search results.")
            return JsonResponse({'html': html})
        except Exception as e:
            logger.error(f'Error during search result rendering: {e}')
            return JsonResponse({'error': 'Failed to generate results.'}, status=500)

    # 如果不是 AJAX 请求，返回正常的 HTML 页面
    return render(
        request,
        'search_results.html',
        context={'query': query, 'word': word},
    )

#复习单词的功能
@login_required
def ReviewHomeView(request):
    # print("Request routed to ReviewHomeView")  # 调试
    today = datetime.today().date()
    #print(today)
    return render(
        request,
        'review_home.html',
        context={'today': today}
    )

@login_required
def ReviewView(request, year, month, day):
    from django.db.models import Q
    
    # 创建选择的复习日期
    d1 = f"{year}-{month}-{day}"
    reviewDate = datetime.strptime(d1, '%Y-%m-%d').date()
    
    # 如果是POST请求，处理用户选择的日期
    if request.method == 'POST':
        review_date_str = request.POST.get('review_date')
        if review_date_str:
            reviewDate = datetime.strptime(review_date_str, '%Y-%m-%d').date()
    
    # 获取URL参数
    show_mastered = request.GET.get('show_mastered', 'false').lower() == 'true'
    per_page = int(request.GET.get('per_page', 10))
    page_number = request.GET.get('page', 1)
    
    # 查询需要复习的单词
    review_items_query = Item.objects.filter(user=request.user).filter(
        Q(next_review_date__lte=reviewDate) |  # 正式复习日到了
        Q(needs_extra_review=True, extra_review_since__lte=reviewDate, next_review_date__gt=reviewDate)  # 额外复习期内且未到正式复习日
    )
    
    # 收集复习items信息
    # 注意：只要next_review_date到了就应该复习，不管proficiency是什么
    # proficiency只是记录上次复习的结果，不影响是否需要复习
    review_items_list = []
    
    for item in review_items_query:
        # 计算逾期天数
        overdue_days = 0
        if item.next_review_date and item.next_review_date < reviewDate:
            overdue_days = (reviewDate - item.next_review_date).days
        
        # 判断复习类型
        is_regular = item.next_review_date and item.next_review_date <= reviewDate
        is_extra = item.needs_extra_review and item.extra_review_since and item.extra_review_since <= reviewDate
        
        # 统计当前周期的不熟悉次数（兼容记录中存的是索引或天数）
        unfamiliar_count = 0
        if item.unfamiliar_history:
            try:
                intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
                # 如果 current_interval 是天数，尝试获取对应的索引；否则如果是索引，则获取对应天数
                if item.current_interval in intervals:
                    cur_day = item.current_interval
                    try:
                        cur_idx = intervals.index(cur_day)
                    except ValueError:
                        cur_idx = None
                else:
                    # 可能是索引值
                    try:
                        cur_idx = int(item.current_interval)
                        cur_day = intervals[cur_idx] if 0 <= cur_idx < len(intervals) else item.current_interval
                    except Exception:
                        cur_idx = None
                        cur_day = item.current_interval

                unfamiliar_count = sum(
                    1 for record in item.unfamiliar_history
                    if record.get('interval') == cur_day or record.get('interval') == cur_idx
                )
            except Exception:
                unfamiliar_count = 0

        # 如果该 item 在今天已经被点评（unfamiliar_history 里有今天的记录），则标记为已点评但仍显示
        reviewed_today = False
        last_review_type = None
        if item.unfamiliar_history:
            for record in item.unfamiliar_history:
                try:
                    if record.get('date') == reviewDate.isoformat():
                        reviewed_today = True
                        last_review_type = record.get('review_type')
                        break
                except Exception:
                    continue
        
        # 计算如果点YES，下次复习日期是什么
        next_review_after_yes = None
        if is_regular:
            # 正式复习：会进入下一个间隔
            intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
            try:
                current_index = intervals.index(item.current_interval)
                if current_index < len(intervals) - 1:
                    next_interval = intervals[current_index + 1]
                    current_interval_value = intervals[current_index]
                    days_until_next = next_interval - current_interval_value
                    next_review_after_yes = reviewDate + timedelta(days=days_until_next)
                else:
                    # 已经是最后一个间隔
                    next_review_after_yes = reviewDate + timedelta(days=365)
            except ValueError:
                next_review_after_yes = reviewDate + timedelta(days=1)
        else:
            # 只是额外复习：next_review_date不变
            next_review_after_yes = item.next_review_date
        
        # 生成详细页面URL
        detail_url = reverse('item-detail', args=[item.pk])
        
        review_items_list.append({
            'item': item,
            'category_name': item.category.name,
            'interval_day': item.current_interval,
            'next_review_date': item.next_review_date or reviewDate,
            'next_review_after_yes': next_review_after_yes,
            'overdue_days': overdue_days,
            'is_regular': is_regular,
            'is_extra': is_extra,
            'unfamiliar_count': unfamiliar_count,
            'reviewed_today': reviewed_today,
            'last_review_type': last_review_type,
            'detail_url': detail_url
        })
    
    # 排序：额外复习优先，然后按类别和间隔
    review_items_list.sort(key=lambda x: (not x['is_extra'], x['category_name'], x['interval_day']))
    
    # 分页处理
    paginator = Paginator(review_items_list, per_page)
    page_obj = paginator.get_page(page_number)
    
    # 构建context
    context = {
        'page_obj': page_obj,
        'reviewdate': reviewDate,
        'show_mastered': show_mastered,
        'per_page': per_page
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return HttpResponse(render_to_string('review_day.html', context, request))

    return render(request, 'review_day.html', context)


@login_required
def ReviewFeedbackYes(request):
    """
    更新指定 Item 的 proficiency 为 MASTERED（熟练）。
    根据新逻辑：正式复习进入下一周期，额外复习只清除标记。
    """
    try:
        if request.method == "POST":
            # 解析请求数据
            data = json.loads(request.body.decode("utf-8"))
            item_id = data.get('id')
            review_date_str = data.get('date')
            
            if review_date_str:
                review_date = datetime.strptime(str(review_date_str), '%Y-%m-%d').date()
            else:
                review_date = datetime.today().date()

            # 获取当前用户的 Item
            curword = Item.objects.get(user=request.user, id=item_id)
            
            # 判断是否为正式复习
            is_regular_review = curword.next_review_date and curword.next_review_date <= review_date
            
            # 更新 proficiency 为 MASTERED
            curword.proficiency = Proficiency.MASTERED
            
            if is_regular_review:
                # 正式复习：进入下一个周期
                intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
                try:
                    current_index = intervals.index(curword.current_interval)
                    if current_index < len(intervals) - 1:
                        # 进入下一个间隔
                        next_index = current_index + 1
                        next_interval = intervals[next_index]
                        current_interval_value = intervals[current_index]
                        
                        # 更新间隔
                        curword.current_interval = next_interval
                        
                        # 计算距离下次复习的天数 = 下个间隔 - 当前间隔
                        # 例如：Day 0→Day 1: 1-0=1天后
                        #      Day 1→Day 2: 2-1=1天后
                        #      Day 2→Day 4: 4-2=2天后
                        days_until_next = next_interval - current_interval_value
                        curword.next_review_date = review_date + timedelta(days=days_until_next)
                    else:
                        # 已经是最后一个间隔（Day 365），保持365天周期
                        curword.next_review_date = review_date + timedelta(days=365)
                except ValueError:
                    # 如果current_interval不在列表中，重置为Day 0，下次是明天Day 1
                    curword.current_interval = 1
                    curword.next_review_date = review_date + timedelta(days=1)
                
                # 清除额外复习标记，并仅移除与刚完成周期相关的不熟悉记录（保留其它周期历史）
                curword.needs_extra_review = False
                curword.extra_review_since = None
                try:
                    uh = curword.unfamiliar_history or []
                    # current_interval_value / current_index 表示刚完成的周期（在上面已定义）
                    filtered = [r for r in uh if r.get('interval') != current_interval_value and r.get('interval') != current_index]
                    curword.unfamiliar_history = filtered
                except Exception:
                    # 如果发生错误，作为回退直接清空历史以保证一致性
                    curword.unfamiliar_history = []
            else:
                # 只是额外复习：清除额外复习标记，正式日期不变
                pass
            
            # 无论是正式复习还是额外复习，点YES后都清除额外复习标记
            curword.needs_extra_review = False
            curword.extra_review_since = None
            
            # 幂等性：如果当天已存在相同日期的记录，返回已点评信息而不重复修改
            try:
                if curword.unfamiliar_history:
                    for r in curword.unfamiliar_history:
                        if r.get('date') == review_date.isoformat():
                            curword.save()
                            return JsonResponse({
                                'success': True,
                                'message': 'Already reviewed today',
                                'mastery': curword.get_proficiency_display(),
                                'reviewed_today': True,
                            })
            except Exception:
                pass

            curword.save()

            return JsonResponse({
                'success': True,
                'message': 'Proficiency updated to MASTERED.',
                'mastery': curword.get_proficiency_display(),
                'reviewed_today': True,
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def ReviewFeedbackNo(request):
    """
    更新指定 Item 的 proficiency 为 UNFAMILIAR（不熟练）。
    根据新逻辑：记录不熟悉，如果达到3次则重启周期，否则进入下一周期并设置额外复习。
    """
    try:
        if request.method == "POST":
            # 解析请求数据
            data = json.loads(request.body.decode("utf-8"))
            item_id = data.get('id')
            review_date_str = data.get('date')
            
            if review_date_str:
                review_date = datetime.strptime(str(review_date_str), '%Y-%m-%d').date()
            else:
                review_date = datetime.today().date()

            # 获取当前用户的 Item
            curword = Item.objects.get(user=request.user, id=item_id)
            
            # 判断是否为正式复习
            is_regular_review = curword.next_review_date and curword.next_review_date <= review_date
            
            # 记录不熟悉
            if not curword.unfamiliar_history:
                curword.unfamiliar_history = []
            
            # 规范化存储：尽量把 interval 存为间隔天数（比如 0,1,2,4...），兼容旧的索引值
            try:
                intervals = [0, 1, 2, 4, 7, 15, 30, 90, 180]
                if curword.current_interval in intervals:
                    interval_value = curword.current_interval
                else:
                    # 如果 current_interval 看起来像索引，尝试转换为对应天数
                    try:
                        idx = int(curword.current_interval)
                        interval_value = intervals[idx] if 0 <= idx < len(intervals) else curword.current_interval
                    except Exception:
                        interval_value = curword.current_interval
            except Exception:
                interval_value = curword.current_interval

            # 在添加前检查是否已存在当天的记录以保证幂等性
            exists_today = False
            try:
                if curword.unfamiliar_history:
                    for r in curword.unfamiliar_history:
                        if r.get('date') == review_date.isoformat():
                            exists_today = True
                            break
            except Exception:
                exists_today = False

            if not exists_today:
                curword.unfamiliar_history.append({
                    "date": review_date.isoformat(),
                    "interval": interval_value,
                    "review_type": "regular" if is_regular_review else "extra"
                })
            
            # 更新 proficiency 为 UNFAMILIAR
            curword.proficiency = Proficiency.UNFAMILIAR
            
            # 统计当前周期的不熟悉次数（基于规范化的 interval_value）
            try:
                current_cycle_count = sum(
                    1 for record in curword.unfamiliar_history
                    if record.get('interval') == interval_value
                )
            except Exception:
                current_cycle_count = 0
            
            message = 'Proficiency updated to UNFAMILIAR.'
            
            if current_cycle_count >= 3:
                # 达到3次，重新开始周期
                old_interval = curword.current_interval
                curword.current_interval = 0
                curword.next_review_date = review_date  # Day 0就是今天
                curword.unfamiliar_history = []
                curword.needs_extra_review = False
                curword.extra_review_since = None
                message = f'该单词在Day {old_interval}已标记3次不熟悉，将从今天重新开始复习周期（Day 0）。'
                
            elif is_regular_review:
                # 正式复习日点NO：不进入下一周期，保持当前周期 + 设置额外复习
                # 等到点YES后才进入下一周期
                # 设置额外复习
                curword.needs_extra_review = True
                curword.extra_review_since = review_date + timedelta(days=1)
                # next_review_date 保持不变，继续在当前周期
            
            # else: 额外复习期间点NO，继续额外复习，next_review_date 不变
            
            curword.save()

            # 如果当天已存在记录，向前端说明为已点评
            resp = {
                'success': True,
                'message': message,
                'mastery': curword.get_proficiency_display(),
                'unfamiliar_count': current_cycle_count,
                'reviewed_today': exists_today or True,
            }

            return JsonResponse(resp)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
def ReviewFeedbackReset(request):
    """
    重置指定 Item 的复习周期，从Day 0重新开始。
    """
    try:
        if request.method == "POST":
            # 解析请求数据
            data = json.loads(request.body.decode("utf-8"))
            item_id = data.get('id')

            # 获取当前用户的 Item
            curword = Item.objects.get(user=request.user, id=item_id)

            # 重置复习周期
            today = datetime.today().date()
            curword.current_interval = 0
            curword.next_review_date = today  # 今天就开始Day 0
            curword.proficiency = Proficiency.UNFAMILIAR
            curword.unfamiliar_history = []
            curword.needs_extra_review = False
            curword.extra_review_since = None
            curword.save()

            return JsonResponse({
                'success': True,
                'message': 'Review cycle has been reset. Starting from Day 0.',
                'mastery': curword.get_proficiency_display()
            })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

#BAIDU API调试页面
def translate_test(request):
    return render(request, 'translate.html')  # 渲染index.html页面
@csrf_exempt
def translate(request):
    if request.method == 'POST':
        try:
            # 获取前端传来的查询词
            data = json.loads(request.body)
            query = data.get('query', '')

            if not query:
                return JsonResponse({'success': False, 'message': 'No query provided'})

            # 调用百度翻译接口
            result = baidu_translate(query)
            
            if result:
                return JsonResponse({'success': True, 'result': result})
            else:
                return JsonResponse({'success': False, 'message': 'Translation failed'})
        
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})
def check_api_keys_view(request):
    """
    检查是否配置了百度 API 密钥
    :return: JsonResponse
    """
    if check_api_keys():
        return JsonResponse({"success": True, "message": "百度 API 密钥已配置"})
    else:
        return JsonResponse({"success": False, "message": "百度 API 密钥未配置"}, status=400)
    

@login_required
def InputView(request):
    if request.method == 'POST':
        form = InputForm(request.POST, user=request.user)  # 传递当前用户
        if form.is_valid():
            data = {
                'input_date': form.cleaned_data['input_date'],
                'category': form.cleaned_data['category'].name,
                'input': form.cleaned_data['input']
            }
            split = data['input'].split('\r\n')
            category_object = Category.objects.get(name=data['category'], user=request.user)  # 仅查找当前用户的类别

            # 获取是否勾选了翻译复选框，并且类别为"单词"
            translate = 'translate' in request.POST and data['category'] == '单词'

            for item in split:
                explain_txt = ''
                result_dict = None
                translated_content = ''
                simple_meaning = ''
                item_name = item
                item_name, explain_txt = split_string(item)  # 如果有拆分功能
                item_name = item_name.strip()
                # 初始化 phonetic_am 和 phonetic_en 为 None
                phonetic_am = phonetic_en = None
                src_tts = None

                # 如果勾选了 "获取释义" 复选框，则调用百度翻译函数
                if translate:
                    result_dict = baidu_translate(item_name)
                    if result_dict:  # 如果返回的字典非空
                        # 从 result_dict 中提取各个部分
                        phonetic = result_dict.get('phonetic', [])
                        phonetic_am = phonetic[1] if len(phonetic) > 1 else None  # 美式音标
                        phonetic_en = phonetic[0] if len(phonetic) > 0 else None  # 英式音标
                        src_tts = result_dict.get('src_tts', None)  # TTS URL
                        translated_content = result_dict.get('parts_and_means', [])  # 词性和释义
                        simple_meaning = result_dict.get('simple_meaning', [])  # 简明释义

                        # 拼接解释文本
                    # 确保是字符串并避免空行
                        if translated_content:
                            if explain_txt:  # 如果原来已有内容，才添加换行
                                explain_txt += "\n\n"
                            explain_txt += "\n".join([str(item) for item in translated_content])  # 拼接详细释义

                        # 如果有 translated_content 或音标，则不存储 simple_meaning
                        if not translated_content:
                            # 如果没有翻译内容才拼接简明释义
                            if simple_meaning:
                                if explain_txt:  # 如果原来已有内容，才添加换行
                                    explain_txt += "\n\n"
                                explain_txt += "\n".join([str(item) for item in simple_meaning])  # 拼接简明释义
                    else:
                        phonetic_am = phonetic_en = src_tts = None

                # 创建 Item 实例，并保存到数据库
                Item.objects.create(
                    user=request.user,
                    item=item_name,
                    inputDate=data['input_date'],
                    initDate=data['input_date'],
                    category=category_object,
                    content=explain_txt,
                    src_tts=src_tts if translate else None,  # 如果未勾选翻译，TTS 地址为 None
                    us_phonetic=phonetic_am,  # 存储美式音标
                    uk_phonetic=phonetic_en,   # 存储英式音标
                    # 新增复习系统字段
                    current_interval=0,
                    next_review_date=data['input_date'],  # Day 0从录入日期开始
                    needs_extra_review=False,
                    unfamiliar_history=[]
                )

            return redirect(reverse('item-list'))  # 重定向到项列表页面
    else:
        form = InputForm(user=request.user)  # 传递当前用户

    return render(request, 'input.html', {'form': form})



def split_string(s):
    # 查找第一个出现的英文冒号或中文冒号的位置
    pos = s.find(":")
    pos_cn = s.find("：")
    
    # 找到最先出现的冒号位置
    if pos == -1 or (pos_cn != -1 and pos_cn < pos):
        pos = pos_cn
    
    # 如果没有冒号，返回原字符串和空字符串
    if pos == -1:
        return s, ""
    
    # 根据位置分割字符串
    return s[:pos], s[pos + 1:]


@login_required
def export_user_data_to_excel(request):
    # 获取当前用户数据
    user = request.user
    items = Item.objects.filter(user=user)

    # 创建一个新的 Excel 工作簿
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "User Data"

    # 写入表头
    headers = ["Item", "Content", "Input Date", "Init Date", "Proficiency", "Category", "TTS URL", "US Phonetic", "UK Phonetic"]
    sheet.append(headers)

    # 写入用户数据
    for item in items:
        sheet.append([
            item.item,
            item.content,
            item.inputDate,
            item.initDate,
            item.get_proficiency_display(),
            item.category.name if item.category else "",
            item.src_tts,
            item.us_phonetic,
            item.uk_phonetic,
        ])

    # 创建 HTTP 响应
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="user_data.xlsx"'

    # 将工作簿保存到响应中
    workbook.save(response)

    return response
    


@login_required
def import_items_from_excel(request):
    if request.method == "POST" and request.FILES.get("file"):
        file = request.FILES["file"]
        user = request.user

        # 检查是否选择了“获取释义”选项
        fetch_definitions = "fetch_definitions" in request.POST

        try:
            workbook = openpyxl.load_workbook(file)
            sheet = workbook.active
        except Exception as e:
            messages.error(request, f"文件读取失败: {str(e)}")
            return render(request, "import_data.html")

        headers = [cell.value for cell in sheet[1]]
        required_columns = ["Item"]
        if not all(col in headers for col in required_columns):
            messages.error(request, "文件格式错误，缺少必要的列。")
            return render(request, "import_data.html")

        column_index = {header: headers.index(header) for header in headers}
        items_to_create = []
        errors = []

        # Proficiency 字段的映射
        proficiency_map = {
            "Unfamiliar": Proficiency.UNFAMILIAR,
            "Mastered": Proficiency.MASTERED,
        }

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                item_name = row[column_index["Item"]]
                if not item_name:
                    errors.append(f"第 {row_idx} 行缺少 Item 字段，已跳过。")
                    continue

                content_index = column_index.get("Content")
                content = row[content_index] if content_index is not None else ""
                # 替换 _x000D_ 字符为换行符，先检查是否为 None
                if content:
                    content = content.replace("_x000D_", "\n")
                else:
                    content = ""  # 如果 content 为 None，赋空字符串

                input_date_index = column_index.get("Input Date")
                input_date = row[input_date_index] if input_date_index is not None else now().date()

                init_date_index = column_index.get("Init Date")
                init_date = row[init_date_index] if init_date_index is not None else now().date()

                # 处理 Proficiency 字段
                proficiency_name = row[column_index.get("Proficiency", None)] or "Unfamiliar"
                proficiency_degree = proficiency_map.get(proficiency_name, Proficiency.UNFAMILIAR)

                category_index = column_index.get("Category")
                category_name = row[category_index] if category_index is not None else ""

                # 获取分类对象
                category = None
                if category_name:
                    categories = Category.objects.filter(name=category_name, user=user)
                    if categories.exists():
                        category = categories.first()
                    else:
                        category = Category.objects.create(name=category_name, user=user)

                # 初始化这些字段为默认值
                src_tts = ""
                phonetic_am = ""
                phonetic_en = ""

                # 只有类别为“单词”的条目才调用获取翻译的功能
                if fetch_definitions and category and category.name == "单词":
                    updated_content, src_tts, phonetic_am, phonetic_en = fetch_and_merge_translation(item_name, content)
                    # 更新内容
                    content = updated_content

                item = Item(
                    user=user,
                    item=item_name,
                    content=content,
                    inputDate=input_date,
                    initDate=init_date,
                    proficiency=proficiency_degree,
                    category=category,
                    src_tts=src_tts,
                    us_phonetic=phonetic_am,
                    uk_phonetic=phonetic_en,
                )
                items_to_create.append(item)

            except Exception as e:
                errors.append(f"第 {row_idx} 行处理失败: {str(e)}")

        try:
            with transaction.atomic():
                Item.objects.bulk_create(items_to_create)
            success_message = f"导入完成。成功导入 {len(items_to_create)} 条记录，{len(errors)} 条记录跳过。"
            messages.success(request, success_message)
        except Exception as e:
            messages.error(request, f"保存失败: {str(e)}")

        return render(request, "import_data.html", {
            "import_results": {
                "success_count": len(items_to_create),
                "errors": errors,
            }
        })

    messages.error(request, "请求无效，请上传文件。")
    return render(request, "import_data.html")




@staticmethod
def compare_lines(existing_lines, new_lines):
    existing = [line.strip() for line in existing_lines.splitlines() if line.strip()]
    new = [line.strip() for line in new_lines.splitlines() if line.strip()]

    result = []
    existing_set = set(existing)

    # 逐行比较
    for line in existing:
        result.append(line)

    for new_line in new:
        if not any(difflib.SequenceMatcher(None, new_line, e_line).ratio() > 0.8 for e_line in existing_set):
            result.append(new_line)

    return "\n".join(result)
def about(request):
    return render(request, 'about.html')  # 渲染 about.html 页面

def readme_view(request):
    # 使用 BASE_DIR 获取 README.md 文件的路径
    readme_path = os.path.join(settings.BASE_DIR, 'README.md')

    # 读取文件内容
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()

    # 将 Markdown 转换为 HTML，并启用 fenced_code 扩展
    html_content = markdown.markdown(readme_content, extensions=['fenced_code'])

    # 渲染模板
    return render(request, 'readme.html', {'content': html_content})


# ==================== DeepSeek API 相关视图 ====================

@login_required
def deepseek_config_view(request):
    """DeepSeek API 配置页面"""
    # 获取或创建用户的配置
    config, created = DeepSeekConfig.objects.get_or_create(
        user=request.user,
        defaults={
            'model': 'deepseek-chat',
            'temperature': 1.0,
            'system_prompt': '你是英语词典助手。输入：英文单词。输出：JSON格式包含uk_phonetic(英音标)、us_phonetic(美音标)、meaning(中文释义)、example_sentences(2-3个例句数组，每个包含english和chinese字段)。目标用户：小学5年级。严格按照JSON格式输出，不要添加任何其他文字或markdown代码块标记。',
            'is_active': True
        }
    )
    
    if request.method == 'POST':
        form = DeepSeekConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'DeepSeek 配置已成功保存！')
            return redirect('deepseek-config')
        else:
            messages.error(request, '配置保存失败，请检查输入。')
    else:
        form = DeepSeekConfigForm(instance=config)
    
    return render(request, 'deepseek_config.html', {'form': form})


@login_required
def deepseek_query_view(request):
    """DeepSeek 查询页面"""
    if request.method == 'GET':
        return render(request, 'deepseek_query.html')
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            word = data.get('word', '').strip()
            
            if not word:
                return JsonResponse({'success': False, 'error': '请输入单词'})
            
            # 调用 DeepSeek API
            result = call_deepseek_api(word, user=request.user)
            
            if not result:
                return JsonResponse({'success': False, 'error': 'API 调用失败或返回空结果'})
            
            # 解析结果
            uk_phonetic = result.get('phonetic', [])[0] if result.get('phonetic') else ''
            us_phonetic = result.get('phonetic', [])[1] if len(result.get('phonetic', [])) > 1 else ''
            
            # 提取简明释义
            simple_meaning = result.get('simple_meaning', [])
            meaning = simple_meaning[0].replace('简明释义: ', '') if simple_meaning else ''
            
            # 提取例句（从 parts_and_means）
            parts_and_means = result.get('parts_and_means', [])
            example_sentences = []
            
            if parts_and_means:
                # 解析例句
                content = '\n'.join(parts_and_means)
                lines = content.split('\n')
                current_example = {}
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('例句'):
                        if current_example:
                            example_sentences.append(current_example)
                        current_example = {'english': line.split(': ', 1)[1] if ': ' in line else line}
                    elif line.startswith('翻译'):
                        current_example['chinese'] = line.split(': ', 1)[1] if ': ' in line else line
                
                if current_example and 'chinese' in current_example:
                    example_sentences.append(current_example)
            
            response_data = {
                'success': True,
                'data': {
                    'uk_phonetic': uk_phonetic,
                    'us_phonetic': us_phonetic,
                    'meaning': meaning,
                    'example_sentences': example_sentences
                }
            }
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON 解析失败'})
        except Exception as e:
            logger.error(f"DeepSeek query error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})


@login_required
def deepseek_save_view(request):
    """保存 DeepSeek 查询结果到数据库"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            word = data.get('word', '').strip()
            query_data = data.get('data', {})
            
            if not word:
                return JsonResponse({'success': False, 'error': '单词不能为空'})
            
            # 获取默认分类"单词"
            category = Category.objects.filter(
                user=request.user, 
                name='单词'
            ).first()
            
            # 如果没有找到"单词"分类，创建或使用第一个分类
            if not category:
                category, _ = Category.objects.get_or_create(
                    user=request.user,
                    name='单词',
                    defaults={'is_default': True, 'sort_order': 0}
                )
            
            # 构建内容
            content_parts = []
            
            # 添加释义
            if query_data.get('meaning'):
                content_parts.append(f"释义: {query_data['meaning']}")
            
            # 添加例句
            if query_data.get('example_sentences'):
                content_parts.append("\n例句:")
                for idx, example in enumerate(query_data['example_sentences'], 1):
                    content_parts.append(f"{idx}. {example.get('english', '')}")
                    content_parts.append(f"   {example.get('chinese', '')}")
            
            content = '\n'.join(content_parts)
            
            # 获取今天的日期
            today = now().date()
            
            # 创建 Item
            item = Item.objects.create(
                user=request.user,
                item=word,
                content=content,
                inputDate=today,
                initDate=today,
                proficiency=Proficiency.UNFAMILIAR,
                category=category,
                uk_phonetic=query_data.get('uk_phonetic', ''),
                us_phonetic=query_data.get('us_phonetic', ''),
                src_tts=f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=en&q={word}",
                # 新增复习系统字段
                current_interval=0,
                next_review_date=today,  # Day 0从今天开始
                needs_extra_review=False,
                unfamiliar_history=[]
            )
            
            return JsonResponse({
                'success': True,
                'message': '保存成功',
                'item_id': item.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'JSON 解析失败'})
        except Exception as e:
            logger.error(f"DeepSeek save error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': '仅支持 POST 请求'})


def check_deepseek_keys_view(request):
    """检查 DeepSeek API Key 是否配置"""
    configured = check_deepseek_keys()
    return JsonResponse({'configured': configured})



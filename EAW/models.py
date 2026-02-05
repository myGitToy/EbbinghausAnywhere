from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from dirtyfields import DirtyFieldsMixin

# Create your models here.
# Word Category defined by user
class Category(DirtyFieldsMixin, models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, editable=False)  # 关联用户
    name = models.CharField(max_length=200, help_text="Enter a category (e.g., word, phrase, etc.)")
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Order of display. Lower numbers appear first."
    )
    is_default = models.BooleanField(default=False, editable=False)  # 标记是否为默认分类

    class Meta:
        unique_together = ('user', 'name')  # 确保每个用户的类别名称不重复
        ordering = ['sort_order', 'name']  # 按排序字段优先排序

    def __str__(self):
        return f"{self.sort_order}: {self.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

class Proficiency(models.Model):
    UNFAMILIAR = 0
    MASTERED = 1
    PROFICIENCY_DEGREE = (
        (UNFAMILIAR, 'Unfamiliar'),
        (MASTERED, 'Mastered'),
    )
    degree = models.IntegerField(choices=PROFICIENCY_DEGREE, default=UNFAMILIAR)

    def __str__(self):
        return self.get_degree_display()


class Item(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,editable=False)  # 关联用户
    item = models.CharField(max_length = 200)
    content = models.TextField(max_length=1000, null=True, blank=True)
    inputDate = models.DateField(auto_now = False, auto_now_add = False)
    initDate = models.DateField(auto_now = False, auto_now_add = False)
    proficiency = models.IntegerField(
        choices=Proficiency.PROFICIENCY_DEGREE, 
        default=Proficiency.UNFAMILIAR, 
        help_text="Select a mastery degree for this word or phrase"
    )
    category = models.ForeignKey(
        Category, 
        on_delete=models.CASCADE, 
        null=True,  # 数据库中允许为空
        blank=True,  # 表单中允许为空
        help_text="Choose the item type, word or phrase"
    )
    src_tts = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text="URL pointing to the TTS audio file (e.g., Baidu API TTS)"
    )
    us_phonetic = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        help_text="American Phonetic (optional)"
    )
    uk_phonetic = models.CharField(
        max_length=200, 
        null=True, 
        blank=True, 
        help_text="British Phonetic (optional)"
    )
    
    # 新的复习系统字段
    next_review_date = models.DateField(
        null=True,
        blank=True,
        help_text="Next scheduled review date"
    )
    current_interval = models.IntegerField(
        default=0,
        help_text="Current review interval in days (0,1,2,4,7,15,30,90,180,365)"
    )
    needs_extra_review = models.BooleanField(
        default=False,
        help_text="Needs extra review (marked after clicking NO)"
    )
    extra_review_since = models.DateField(
        null=True,
        blank=True,
        help_text="Extra review start date"
    )
    unfamiliar_history = models.JSONField(
        default=list,
        blank=True,
        help_text="History of unfamiliar markings"
    )
    
    def __str__(self):
        return f"{self.item} ({self.get_proficiency_display()}) in {self.category.name}"

    
    def get_absolute_url(self):
        """
        Returns the url to access a particular book instance.
        """
        return reverse('word-detail', args=[str(self.id)])
    def get_review_url(self, year, month, day):
        """
        Returns the url to access a particular book instance.
        """
        #print (str(self.id),year,month,day)
        #print (reverse('review-detail', args=[year, month, day, str(self.id)]))
        return reverse('review-view', args=[year, month, day, str(self.id)])
    class Meta:
        #unique_together = ('user', 'item')  # 确保每个用户的单词库中单词不重复
        pass
class ReviewDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,editable=False)  # 关联用户
    day = models.IntegerField()
    def __str__(self):
        return str(self.day)
    class Meta:
        unique_together = ('user', 'day')  # 确保每个用户的复习曲线不重复
        ordering = ['day']  # 默认按复习时间从小到大排序


class DeepSeekConfig(models.Model):
    """DeepSeek API 配置模型，每个用户一个配置"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, editable=False)
    model = models.CharField(
        max_length=50,
        default='deepseek-chat',
        help_text="DeepSeek 模型名称"
    )
    temperature = models.FloatField(
        default=1.0,
        help_text="生成温度 (0.0-2.0)，数据抽取、英语词典建议1.0，翻译建议1.3，创意写作建议1.5"
    )
    system_prompt = models.TextField(
        default='你是英语词典助手。输入：英文单词。输出：JSON格式包含uk_phonetic(英音标)、us_phonetic(美音标)、meaning(中文释义)、example_sentences(2-3个例句数组，每个包含english和chinese字段)。目标用户：小学5年级。严格按照JSON格式输出，不要添加任何其他文字或markdown代码块标记。',
        help_text="系统提示词，定义 DeepSeek 的行为和输出格式"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="是否启用 DeepSeek API"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"DeepSeek Config for {self.user.username}"

    class Meta:
        verbose_name = "DeepSeek Configuration"
        verbose_name_plural = "DeepSeek Configurations"

from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from dirtyfields import DirtyFieldsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models import Q

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
        # 禁止修改默认分类的 name
        if self.is_default and self.pk and 'name' in self.get_dirty_fields():
            raise ValidationError("Cannot modify the name of the default category.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # 禁止删除默认分类
        if self.is_default:
            raise ValidationError("Cannot delete the default category.")
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


# ==================== 积分系统模型 ====================

class UserPoints(models.Model):
    """用户积分账户模型"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='points_account'
    )
    current_points = models.IntegerField(
        default=0,
        help_text="当前可用积分"
    )
    total_earned = models.IntegerField(
        default=0,
        help_text="累计获得积分（历史总和）"
    )
    total_spent = models.IntegerField(
        default=0,
        help_text="累计消费积分"
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        help_text="最后更新时间"
    )

    class Meta:
        verbose_name = "User Points"
        verbose_name_plural = "User Points"

    def __str__(self):
        return f"{self.user.username} - {self.current_points} points"

    def add_points(self, points, reason, reference_id=None):
        """
        增加积分
        :param points: 积分数（正数）
        :param reason: 原因描述
        :param reference_id: 关联对象ID（如Item的ID）
        :return: 创建的PointHistory对象
        """
        if points <= 0:
            raise ValueError("Points must be positive")

        self.current_points += points
        self.total_earned += points
        self.save()

        return PointHistory.objects.create(
            user=self.user,
            change_type='EARN',
            points=points,
            reason=reason,
            reference_id=reference_id,
            balance_after=self.current_points
        )

    def spend_points(self, points, reason, reference_id=None):
        """
        消费积分
        :param points: 积分数（正数）
        :param reason: 原因描述
        :param reference_id: 关联对象ID
        :return: 创建的PointHistory对象
        """
        if points <= 0:
            raise ValueError("Points must be positive")
        if self.current_points < points:
            raise ValueError("Insufficient points")

        self.current_points -= points
        self.total_spent += points
        self.save()

        return PointHistory.objects.create(
            user=self.user,
            change_type='SPEND',
            points=-points,
            reason=reason,
            reference_id=reference_id,
            balance_after=self.current_points
        )


class PointHistory(models.Model):
    """积分变动历史记录"""
    CHANGE_TYPES = (
        ('EARN', '获得积分'),
        ('SPEND', '消费积分'),
        ('ADJUST', '管理员调整'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='point_history'
    )
    change_type = models.CharField(
        max_length=10,
        choices=CHANGE_TYPES,
        help_text="变动类型"
    )
    points = models.IntegerField(
        help_text="变动积分（正数为获得，负数为消费）"
    )
    reason = models.CharField(
        max_length=200,
        help_text="变动原因"
    )
    reference_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="关联对象ID（如Item ID或Redemption ID）"
    )
    balance_after = models.IntegerField(
        help_text="变动后余额"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="创建时间"
    )

    class Meta:
        verbose_name = "Point History"
        verbose_name_plural = "Point Histories"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['change_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.change_type} {self.points} points - {self.created_at}"


class UserPointsConfig(models.Model):
    """
    用户自定义积分兑换配置
    每个用户可以设置自己的兑换规则
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='points_config'
    )

    # 兑换规则：1积分可以兑换多少分钟游戏时长
    minutes_per_point = models.FloatField(
        default=1.0,
        help_text="1积分可以兑换的游戏时长（分钟）",
        validators=[MinValueValidator(0.1)]
    )

    # 兑换时的步长（用户加减按钮的每次变化量）
    redemption_step = models.IntegerField(
        default=10,
        help_text="兑换时加减按钮的步长（分钟）"
    )

    # 最小兑换时长（分钟）
    min_redemption_minutes = models.IntegerField(
        default=1,
        help_text="单次最少兑换多少分钟"
    )

    # 最大兑换时长（分钟）
    max_redemption_minutes = models.IntegerField(
        default=300,
        help_text="单次最多兑换多少分钟"
    )

    # 连续签到奖励配置
    daily_checkin_enabled = models.BooleanField(default=True)
    daily_checkin_points = models.IntegerField(
        default=1,
        help_text="每天签到奖励积分"
    )

    # 连续学习奖励配置
    streak_reward_enabled = models.BooleanField(default=True)
    streak_reward_points = models.IntegerField(
        default=5,
        help_text="连续学习N天后的额外奖励积分"
    )
    streak_reward_days = models.IntegerField(
        default=7,
        help_text="连续学习多少天触发奖励"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Points Config"
        verbose_name_plural = "User Points Configs"

    def __str__(self):
        return f"{self.user.username} - 1积分={self.minutes_per_point}分钟"


class PointRedemption(models.Model):
    """积分兑换记录"""
    STATUS_CHOICES = (
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='redemptions'
    )
    points_spent = models.IntegerField(
        help_text="消费积分"
    )
    game_minutes = models.IntegerField(
        help_text="兑换的游戏时长（分钟）"
    )
    exchange_rate = models.FloatField(
        help_text="兑换时的汇率（分钟/积分）"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='COMPLETED'
    )
    notes = models.TextField(
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Point Redemption"
        verbose_name_plural = "Point Redemptions"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.points_spent}积分兑换{self.game_minutes}分钟"


class UserStreak(models.Model):
    """
    用户连续学习记录
    用于跟踪连续签到和连续学习天数
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='streak'
    )

    # 连续学习相关
    current_streak = models.IntegerField(
        default=0,
        help_text="当前连续学习天数"
    )
    longest_streak = models.IntegerField(
        default=0,
        help_text="最长连续学习天数"
    )
    last_study_date = models.DateField(
        null=True,
        blank=True,
        help_text="最后一次学习日期"
    )

    # 连续签到相关
    current_checkin_streak = models.IntegerField(
        default=0,
        help_text="当前连续签到天数"
    )
    longest_checkin_streak = models.IntegerField(
        default=0,
        help_text="最长连续签到天数"
    )
    last_checkin_date = models.DateField(
        null=True,
        blank=True,
        help_text="最后一次签到日期"
    )

    # 最近一次获得连续学习奖励的日期
    last_streak_reward_date = models.DateField(
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "User Streak"
        verbose_name_plural = "User Streaks"

    def __str__(self):
        return f"{self.user.username} - 学习:{self.current_streak}天 签到:{self.current_checkin_streak}天"

    def update_study_streak(self, study_date):
        """
        更新连续学习天数
        :param study_date: 学习日期
        """
        from datetime import timedelta

        if self.last_study_date:
            # 计算与上次学习的日期差
            delta = study_date - self.last_study_date

            if delta.days == 0:
                # 今天已经学习过，不更新
                return
            elif delta.days == 1:
                # 连续学习，增加计数
                self.current_streak += 1
            else:
                # 中断了，重新开始
                if self.current_streak > self.longest_streak:
                    self.longest_streak = self.current_streak
                self.current_streak = 1
        else:
            # 第一次学习
            self.current_streak = 1

        self.last_study_date = study_date
        self.save()

    def update_checkin_streak(self, checkin_date):
        """
        更新连续签到天数
        :param checkin_date: 签到日期
        """
        from datetime import timedelta

        if self.last_checkin_date:
            # 计算与上次签到的日期差
            delta = checkin_date - self.last_checkin_date

            if delta.days == 0:
                # 今天已经签到过，不更新
                return
            elif delta.days == 1:
                # 连续签到，增加计数
                self.current_checkin_streak += 1
            else:
                # 中断了，重新开始
                if self.current_checkin_streak > self.longest_checkin_streak:
                    self.longest_checkin_streak = self.current_checkin_streak
                self.current_checkin_streak = 1
        else:
            # 第一次签到
            self.current_checkin_streak = 1

        self.last_checkin_date = checkin_date
        self.save()

    def check_streak_reward(self, config):
        """
        检查是否达到连续学习奖励条件
        :param config: UserPointsConfig对象
        :return: 应该奖励的积分数，0表示不奖励
        """
        if not config.streak_reward_enabled:
            return 0

        if self.current_streak > 0 and self.current_streak % config.streak_reward_days == 0:
            # 检查今天是否已经给过奖励
            from django.utils import timezone
            today = timezone.now().date()

            if self.last_streak_reward_date:
                # 如果上次奖励日期就是今天，不再奖励
                if self.last_streak_reward_date == today:
                    return 0

                # 检查是否是新的奖励周期
                from datetime import timedelta
                days_since_last_reward = (today - self.last_streak_reward_date).days
                if days_since_last_reward < config.streak_reward_days:
                    return 0

            # 给予奖励
            self.last_streak_reward_date = today
            self.save()
            return config.streak_reward_points

        return 0

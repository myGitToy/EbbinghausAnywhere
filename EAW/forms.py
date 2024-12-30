from django import forms
from .models import Category, Item, ReviewDay
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import User

# Category的ModelForm
# Category的ModelForm
class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and hasattr(self, 'request'):
            # 如果是新建Category实例且request存在，自动设置user为当前请求的user
            self.instance.user = self.request.user

    def clean_name(self):
        """
        验证默认分类是否被修改了 name。
        """
        if self.instance.is_default and self.cleaned_data['name'] != self.instance.name:
            raise forms.ValidationError("Cannot modify the name of the default category.")
        return self.cleaned_data['name']


# Item的ModelForm
class ItemAdminForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and hasattr(self, 'request'):
            # 如果是新建Item实例且request存在，自动设置user为当前请求的user
            self.instance.user = self.request.user

# ReviewDay的ModelForm
class ReviewDayAdminForm(forms.ModelForm):
    class Meta:
        model = ReviewDay
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk and hasattr(self, 'request'):
            # 如果是新建ReviewDay实例且request存在，自动设置user为当前请求的user
            self.instance.user = self.request.user

class InputForm(forms.Form):
    input_date = forms.DateField(input_formats=['%Y-%m-%d'])
    
    def clean_input_date(self):
        data = self.cleaned_data['input_date']
        return data
    
    # 限制类别只显示当前用户的类别
    category = forms.ModelChoiceField(queryset=Category.objects.none(), required=True)  

    input = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # 从视图传入当前用户
        super().__init__(*args, **kwargs)

        if user:
            # 仅显示当前用户的类别
            self.fields['category'].queryset = Category.objects.filter(user=user) 



class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True, 
        help_text="Please enter a valid email address."
    )
    first_name = forms.CharField(
        max_length=30, 
        required=False, 
        help_text="Enter a nickname or first name (optional)."
    )
    last_name = forms.CharField(
        max_length=30, 
        required=False, 
        help_text="Enter your last name (optional)."
    )
    def __init__(self, *args, **kwargs):
        # 从 kwargs 中获取随机 ID（视图传入）
        random_id = kwargs.pop('random_id', None)
        super().__init__(*args, **kwargs)

        # 动态修改字段名
        if random_id:
            self.fields['username'].widget.attrs['name'] = f'random_username_{random_id}'
            self.fields['password1'].widget.attrs['name'] = f'random_password1_{random_id}'
            self.fields['password2'].widget.attrs['name'] = f'random_password2_{random_id}'

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered, please use another one.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError("Username already exists, please choose another username.")
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 != password2:
            raise ValidationError('Passwords do not match.')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name')  # Save the nickname
        user.last_name = self.cleaned_data.get('last_name')  # Save the surname
        if commit:
            user.save()
        return user

class EmailUpdateForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label="New Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new email',
        })
    )
    current_password = forms.CharField(
        required=True,
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
        })
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_current_password(self):
        current_password = self.cleaned_data.get('current_password')
        if not self.user.check_password(current_password):
            raise forms.ValidationError("The current password is incorrect.")
        return current_password


class UpdateNameForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name',
            }),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter current password',
        })
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
        })
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
        })
    )
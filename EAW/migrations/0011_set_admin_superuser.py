from django.db import migrations


def set_admin_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    try:
        user_qs = User.objects.filter(username='admin')
        if user_qs.exists():
            user = user_qs.first()
            user.is_staff = True
            user.is_superuser = True
            user.save()
        else:
            # 如果不存在，则创建一个不可登录的超级用户（需随后设置密码）
            user = User.objects.create(username='admin', email='g.huiqiao@gmail.com', is_staff=True, is_superuser=True, is_active=True)
            try:
                user.set_unusable_password()
                user.save()
            except Exception:
                # 某些 Django 版本下通过 apps.get_model 返回的 User 可能不含 set_unusable_password
                pass
    except Exception:
        # 在迁移中尽量不要中断整个迁移流程
        return


def unset_admin_superuser(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    try:
        user_qs = User.objects.filter(username='admin')
        if user_qs.exists():
            user = user_qs.first()
            user.is_superuser = False
            user.is_staff = True
            user.save()
    except Exception:
        return


class Migration(migrations.Migration):

    dependencies = [
        ('EAW', '0010_item_current_interval_item_extra_review_since_and_more'),
    ]

    operations = [
        migrations.RunPython(set_admin_superuser, unset_admin_superuser),
    ]

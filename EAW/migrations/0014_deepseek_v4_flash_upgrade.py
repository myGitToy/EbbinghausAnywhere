from django.db import migrations, models


def migrate_deepseek_model_to_v4_flash(apps, schema_editor):
    DeepSeekConfig = apps.get_model("EAW", "DeepSeekConfig")
    DeepSeekConfig.objects.filter(model="deepseek-chat").update(
        model="deepseek-v4-flash"
    )


class Migration(migrations.Migration):

    dependencies = [
        ("EAW", "0013_change_daily_checkin_points_to_5"),
    ]

    operations = [
        migrations.AlterField(
            model_name="deepseekconfig",
            name="model",
            field=models.CharField(
                default="deepseek-v4-flash",
                help_text="DeepSeek 模型名称",
                max_length=50,
            ),
        ),
        migrations.RunPython(
            migrate_deepseek_model_to_v4_flash,
            migrations.RunPython.noop,
        ),
    ]

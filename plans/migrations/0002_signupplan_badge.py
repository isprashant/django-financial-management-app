from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='signupplan',
            name='badge',
            field=models.ImageField(blank=True, help_text='Badge image shown on join page.', null=True, upload_to='plans/'),
        ),
    ]

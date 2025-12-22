from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='redemption',
            name='shipping_address',
            field=models.TextField(default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='rewarditem',
            name='picture',
            field=models.ImageField(blank=True, null=True, upload_to='rewards/'),
        ),
    ]

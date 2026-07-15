from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[
                    ('patient', 'Patient'),
                    ('counselor', 'Counselor'),
                    ('admin', 'Admin'),
                ],
                default='patient',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='profile',
            name='verification_status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('approved', 'Approved'),
                    ('rejected', 'Rejected'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
    ]

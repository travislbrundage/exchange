# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0011_auto_20181022_1413'),
    ]

    def create_exchange_profiles(apps, schema_editor):
        ExchangeProfile = apps.get_model('core', 'ExchangeProfile')
        Profile = apps.get_model('people', 'Profile')
        user_profiles = [profile for profile in Profile.objects.all() if
                         profile.is_staff == False and
                         profile.is_superuser == False and
                         profile.is_anonymous() == False]
        for profile in user_profiles:
            ep = ExchangeProfile.objects.create(user=profile)
            ep.save()

    operations = [
        migrations.CreateModel(
            name='ExchangeProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False,
                                        auto_created=True, primary_key=True)),
                ('content_creator', models.BooleanField(
                    default=True,
                    help_text='User can upload layers and documents',
                    verbose_name='Content Creator')),
                ('service_manager', models.BooleanField(
                    default=True,
                    help_text='User can register remote services',
                    verbose_name='Service Manager')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL,
                                              null=True)),
            ],
        ),
        migrations.RunPython(create_exchange_profiles)
    ]
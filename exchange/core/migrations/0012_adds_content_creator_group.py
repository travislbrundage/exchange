# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_20181022_1413'),
    ]

    def change_name(apps, schema_editor):
        AuthGroup = apps.get_model("auth", "group")

        # Changing terminology: csw_manager -> service_manager
        group = AuthGroup.objects.get(name='csw_manager')
        group.name = 'service_manager'
        group.save()

    def create_group(apps, schema_editor):
        AuthGroup = apps.get_model("auth", "group")
        ContentType = apps.get_model("contenttypes", "contenttype")
        Permission = apps.get_model("auth", "permission")

        # Create the group
        AuthGroup(name='content_creator').save()
        group = AuthGroup.objects.get(name='content_creator')

        # Add layer, document, and map
        # Layer
        content_type = ContentType.objects.get(
            app_label='layers', model='layer')
        permissions = Permission.objects.filter(
            content_type=content_type)

        # Assign the permissions
        for perm in permissions:
            group.permissions.add(perm)

        # Map
        content_type = ContentType.objects.get(
            app_label='maps', model='map')
        permissions = Permission.objects.filter(
            content_type=content_type)

        # Assign the permissions
        for perm in permissions:
            group.permissions.add(perm)

        # Document
        content_type = ContentType.objects.get(
            app_label='documents', model='document')
        permissions = Permission.objects.filter(
            content_type=content_type)

        # Assign the permissions
        for perm in permissions:
            group.permissions.add(perm)

    operations = [
        migrations.RunPython(create_group),
        migrations.RunPython(change_name)
    ]

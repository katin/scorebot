# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-11-07 01:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sbehost', '0005_auto_20161107_0157'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gameteam',
            name='team_hosts',
        ),
    ]

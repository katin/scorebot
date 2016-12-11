# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-08-18 00:33
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessKey',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key_level', models.BigIntegerField(default=1, verbose_name=b'Key Access Level')),
                ('key_uuid', models.CharField(max_length=250, unique=True, verbose_name=b'Key UUID')),
            ],
            options={
                'verbose_name': 'SBE Access Key',
                'verbose_name_plural': 'SBE Access Keys',
            },
        ),
        migrations.CreateModel(
            name='HostServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('server_name', models.CharField(max_length=250, verbose_name=b'Host Server Name')),
                ('server_address', models.CharField(max_length=150, verbose_name=b'Host Server Address')),
            ],
            options={
                'verbose_name': 'SBE Host Server',
                'verbose_name_plural': 'SBE Host Servers',
            },
        ),
        migrations.CreateModel(
            name='MonitorJob',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('job_start', models.DateTimeField(auto_now_add=True, verbose_name=b'Job Start')),
                ('job_finish', models.DateTimeField(blank=True, null=True, verbose_name=b'Job End')),
            ],
            options={
                'verbose_name': 'SBE Monitor Job',
                'verbose_name_plural': 'SBE Monitor Jobs',
            },
        ),
        migrations.CreateModel(
            name='MonitorServer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monitor_name', models.CharField(max_length=250, verbose_name=b'Monitor Name')),
                ('monitor_address', models.CharField(blank=True, max_length=140, null=True, verbose_name=b'Monitor Last IP')),
                ('monitor_key', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='sbegame.AccessKey')),
            ],
            options={
                'verbose_name': 'SBE Monitor',
                'verbose_name_plural': 'SBE Monitors',
            },
        ),
        migrations.CreateModel(
            name='Player',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('player_score', models.BigIntegerField(default=0, verbose_name=b'Player Overall Score')),
                ('player_name', models.CharField(max_length=150, unique=True, verbose_name=b'Player Display Name')),
                ('player_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'SBE Player',
                'verbose_name_plural': 'SBE Players',
            },
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('team_score', models.BigIntegerField(default=0, verbose_name=b'Team Overall Score')),
                ('team_name', models.CharField(max_length=250, unique=True, verbose_name=b'Team Name')),
                ('team_color', models.IntegerField(default=16777215, verbose_name=b'Team Color')),
                ('team_registered', models.DateField(auto_now_add=True, verbose_name=b'Team Registration Date')),
                ('team_last_played', models.DateTimeField(blank=True, null=True, verbose_name=b'Team Last Played')),
                ('team_players', models.ManyToManyField(to='sbegame.Player')),
            ],
            options={
                'verbose_name': 'SBE Team',
                'verbose_name_plural': 'SBE Teams',
            },
        ),
    ]

import json
import random
import scorebot.utils.log as logger

from django.core import serializers
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from sbegame.models import Player, Team, MonitorJob
from scorebot.utils.general import val_auth, get_object_with_id, save_json_or_error
from django.http import HttpResponse, HttpResponseNotFound, HttpResponseBadRequest, HttpResponseForbidden

"""
    Methods supported

    GET - Requesting a object
    PUT - Creating an object (Objects with IDs will be rejected!)
    POST - Updating and object (Objects must have IDs!)
    DELETE - Removes an object.
"""
"""
    SBE Manage Views

    API Backend for SBE Management related stuff
"""


class ManageViews:
    """
        SBE Player API

        Methods: GET, PUT, POST

        GET  |  /player/
        GET  |  /player/<game_id>/
        PUT  |  /player/
        POST |  /player/<player_id>/

        Returns player info.  Deletes are not allowed
    """
    @staticmethod
    @csrf_exempt
    @val_auth
    def team(request, team_id=None):
        if request.method == 'GET':
            return get_object_with_id(request, Team, team_id)
        elif request.method == 'POST' or request.method == 'PUT':
            return save_json_or_error(request, team_id)
        return HttpResponseBadRequest()

    @staticmethod
    @csrf_exempt
    @val_auth
    def player(request, player_id=None):
        if request.method == 'GET':
            return get_object_with_id(request, Player, player_id)
        elif request.method == 'POST' or request.method == 'PUT':
            return save_json_or_error(request, player_id)
        return HttpResponseBadRequest()

    @staticmethod
    @csrf_exempt
    @val_auth
    def job(request):
        return HttpResponse(request.authkey.key_uuid)
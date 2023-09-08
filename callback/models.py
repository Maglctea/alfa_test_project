from django.db import models


class Player(models.Model):
    name = models.CharField(max_length=54, default="")
    email = models.EmailField(max_length=54)


class Game(models.Model):
    name = models.CharField(max_length=254, default="")
    players = models.ManyToManyField(Player, blank=True, related_name='player_games')

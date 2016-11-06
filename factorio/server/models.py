from __future__ import unicode_literals

from django.db import models

# a server instance can run a game
class Server(models.Model):
	name = models.CharField(max_length=255)

# a game includes a savefile and connected users
class Game(models.Model):
	name = models.CharField(max_length=255)

# a user has a name and a current game
class User(models.Model):
	name = models.CharField(max_length=255)

# a single user to game connection
class Connection(models.Model):
	user = models.ForeignKey(User, related_name='connections')
	game = models.ForeignKey(Game, related_name='connections')

	date_created = models.DateTimeField(auto_now_add=True)

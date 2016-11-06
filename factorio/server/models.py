from __future__ import unicode_literals

from django.db import models

# a version is downloaded from the factorio website ans placed in the right directory
class Version(models.Model):
	name = models.CharField(max_length=255)
	date_created = models.DateTimeField(auto_now_add=True)
	binary = models.CharField(max_length=255)

# a server instance can run a game
class Server(models.Model):
	name = models.CharField(max_length=255)
	date_created = models.DateTimeField(auto_now_add=True)

	def start(self):
		pass

	def stop(self):
		pass

# a game includes a savefile and connected users
class Game(models.Model):
	name = models.CharField(max_length=255)
	date_created = models.DateTimeField(auto_now_add=True)
	save_file = models.CharField(max_length=255)

# a user has a name and a current game
class User(models.Model):
	name = models.CharField(max_length=255)
	date_created = models.DateTimeField(auto_now_add=True)


# a single user to game connection
class Connection(models.Model):
	user = models.ForeignKey(User, related_name='connections')
	game = models.ForeignKey(Game, related_name='connections')
	date_created = models.DateTimeField(auto_now_add=True)

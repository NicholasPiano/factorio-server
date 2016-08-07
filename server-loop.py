
# import
import subprocess
from subprocess import call, Popen
from lxml import html
import requests
import re
import os
from os.path import exists, join, getmtime
import json
import time
from threading  import Thread
from Queue import Queue, Empty

# vars
download_url = 'https://www.factorio.com/download-headless/experimental'
version_download_template = 'https://www.factorio.com/get-download/{}.{}.{}/headless/linux64'
version_template = r'(?P<first>[0-9]{1})\.(?P<second>[0-9]{2})\.(?P<third>[0-9]{2}) \(headless\)'
previous_version = ()
current_version = (0, 13, 15)
download_target = '/home/npiano/factorio-download/{}.{}.{}/'
file_target = '{}.{}.{}.tar.gz'
store_path = '/opt/factorio/{}.{}.{}/'
execute_path = join(store_path, 'bin/x64/factorio')
peer_marker = r'Received peer info for peer\(([0-9]+)\) username\((.+)\)'
player_join_marker = r'adding peer\(([0-9]+)\) address\(.+\) sending connectionAccept\(true\)'
no_active_users_marker = r'removing peer\(1\) success\(true\)'
game_name = None

# main loop
while True:
	start_time = time.time()
	# set vars
	new_version_available = False
	peers = {}
	args = {}

	# 1. Git pull and load args.json
	print('1. pulling from git')
	call('git pull', shell=True)
	with open('./args.json') as args_file:
		args = json.load(args_file)

	# 2. check new software available by parsing download page
	######################################################################### CHECK NEW VERSION
	print('2. checking for new software')
	page = requests.get(download_url)
	tree = html.fromstring(page.content)

	# a. if available, download and prepare for running
	versions = tree.xpath('//h3/text()')
	for version in versions:
		match_dict = re.match(version_template, version).groupdict()
		version_tuple = int(match_dict['first']), int(match_dict['second']), int(match_dict['third'])
		gt = sum([cv >= vt for cv, vt in zip(current_version, version_tuple)]) != 3
		if gt:
			# there is a new version
			new_version_available = True
			previous_version = current_version
			current_version = version_tuple

	if new_version_available:
		print('2... new version available')
		new_version_available = False

		# download from url
		version_download_url = version_download_template.format(*current_version)
		version_target = download_target.format(*current_version) # just the directory
		version_file_target = file_target.format(*current_version) # just the filename
		complete_target = join(version_target, version_file_target) # both together

		if not exists(version_target):
			os.makedirs(version_target)

		call('wget --quiet -O {} {}'.format(complete_target, version_download_url), shell=True)

		# prepare for running
		# unpack
		call('tar -xzf {} -C {}'.format(complete_target, version_target), shell=True) # file to directory

		# move
		extract_target = join(version_target, 'factorio')
		store_target = store_path.format(*current_version)
		if not exists(store_target):
			os.makedirs(store_target)

		call('sudo mv {}/* {}'.format(extract_target, store_target), shell=True)

		# b. copy all savefiles to LATEST/saves
		print('2... copying saves')
		if exists(store_path.format(*previous_version)) and exists(join(store_path.format(*previous_version), 'saves')):
			save_target = join(store_path.format(*current_version), 'saves')
			if not exists(save_target):
				os.makedirs(save_target)

			call('sudo cp -r {} {}'.format(join(store_path.format(*previous_version), 'saves'), save_target), shell=True)

	######################################################################### CHECK NEW VERSION

	#	3. checks args.json for savefile name / 'new'.
	# 4. if 'new' in args, create new game
	previous_game_name = game_name
	game_name = args['game']['name']
	game_name_zip = '{}.zip'.format(game_name)
	print('3. game name: {}'.format(game_name))
	if game_name != previous_game_name and not exists(join(store_path.format(*current_version), 'saves', game_name_zip)):
		print('3... new game: {}'.format(game_name))
		call('sudo {} --create {}'.format(execute_path.format(*current_version), join(store_path.format(*current_version), 'saves', game_name_zip)), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

	# 5. run server and pipe to log
	def enqueue_output(out, queue):
		for line in iter(out.readline, b''):
			queue.put(line)
		out.close()

	server_process = Popen([execute_path.format(*current_version), '--start-server', join(store_path.format(*current_version), 'saves', game_name_zip)], bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, close_fds=True)
	print('4. starting server process {}'.format(server_process.pid))
	player_join = False
	running = True
	q = Queue()
	t = Thread(target=enqueue_output, args=(server_process.stdout, q))
	t.daemon = True # thread dies with the program
	t.start()

	# 6. enter check log loop
	line = ''
	while running:
		try:
			line = q.get_nowait() # or q.get(timeout=.1)
		except Empty:
			pass
		else: # got line
			if server_process.poll() is None:
				# a. if player join received, toggle player join
				player = re.search(player_join_marker, line)
				if player is not None and player.group(1) != '0' and player.group(1) not in peers:
					print('player_join')
					player_join = True

				peer = re.search(peer_marker, line)
				if peer is not None and peer.group(1) not in peers:
					peers[peer.group(1)] = peer.group(2)
					print('peers', peers)

				# b. if no active players received, and player join is true, send SIGINT to server process, set player join to false
				if re.search(no_active_users_marker, line) is not None and player_join:
					print('no active users')
					time.sleep(5) # allow time for last user to disconnect
					server_process.kill()
					running = False

		# c. if time is up and there is only the server peer, restart.
		if time.time() - start_time > 600 and not player_join:
			print('time is up, restarting.')
			server_process.kill()
			running = False

	# 10. get most recent autosave and set as save file.
	print('5. saving')
	if time.time() - start_time > 120 and player_join:
		paths = [f for f in ['_autosave1.zip','_autosave2.zip','_autosave3.zip'] if exists(join(store_path.format(*current_version), 'saves', f))]
		mtimes = [getmtime(join(store_path.format(*current_version), 'saves', path)) for path in paths]
		path = paths.index(min(mtimes))

		full_path = join(store_path.format(*current_version), 'saves', path)
		backup_path = join(store_path.format(*current_version), 'saves', '_{}.zip'.format(game_name))
		game_path = join(store_path.format(*current_version), 'saves', '{}.zip'.format(game_name))

		call('sudo cp {} {}'.format(game_path, backup_path), shell=True) # backup
		call('sudo cp {} {}'.format(full_path, game_path), shell=True) # save

	# 11. aaand repeat.

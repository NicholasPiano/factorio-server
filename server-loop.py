
# import
from subprocess import call
from lxml import html
import requests
import re
import os
from os.path import exists, join
import json

# vars
download_url = 'https://www.factorio.com/download-headless/experimental'
version_download_template = 'https://www.factorio.com/get-download/{}.{}.{}/headless/linux64'
version_template = r'(?P<first>[0-9]{1})\.(?P<second>[0-9]{2})\.(?P<third>[0-9]{2}) \(headless\)'
previous_version = ()
current_version = (0, 13, 14)
download_target = './factorio-download/{}.{}.{}/'
file_target = '{}.{}.{}.tar.gz'
store_path = '/opt/factorio/{}.{}.{}/'
execute_path = join(store_path, 'factorio/bin/x64/factorio')
args = {}

# main loop
# while True:
if True:
	# set vars
	new_version_available = False

	# 1. Git pull and load args.json
	call('git pull')
	with open('./args.json') as args_file:
		args = json.load(args_file)

	# 2. check new software available by parsing download page
	######################################################################### CHECK NEW VERSION
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

		call('sudo mv {} {}'.format(extract_target, store_target), shell=True)

		# b. copy all savefiles to LATEST/saves
		if exists(store_path.format(*previous_version)) and exists(join(store_path.format(*previous_version), 'saves')):
			save_target = join(store_path.format(*current_version), 'saves')
			if not exists(save_target):
				os.makedirs(save_target)

			call('sudo cp -r {} {}'.format(join(store_path.format(*previous_version), 'saves'), save_target), shell=True)

	######################################################################### CHECK NEW VERSION

	#	3. checks args.json for savefile name / 'new'.
	# 4. if 'new' in args, create new game
	new_game = bool(args['game']['new'])
	if new_game:
		call('sudo {} --create {}'.format(), shell=True)

	# 5. run server and pipe to log
	# 6. enter check log loop
	# 	a. if player join received, toggle player join
	# 	b. if no active players received, and player join is true, send SIGINT to server process, set player join to false
	# 	c. git pull, if game name arg has changed, send SIGINT
	# 9. wait for shutdown and exit log loop
	# 10. update server log and commit changes
	# 11. repeat.
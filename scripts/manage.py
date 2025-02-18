import os
from os.path import join
from functools import wraps
from color import error, warning, success, Styles, modify_words
from difflib import SequenceMatcher
import sys

root = os.path.abspath(".")
shared = join(root, "shared")
version_file = join("shared", "project_version.txt")
index_file = join(root, "docs", "index.html")

class App:
	def __init__(self):
		self.procedures = {}


	def command(self, *cli_args):
		def util(f):
			@wraps(f)
			def g(*args, **kwargs):
				f(self, *args, **kwargs)
			self.procedures[g.__name__] = (g, cli_args)
			return g
		return util

	def run(self, args):
		if len(args) == 0:
			error(f"No argument is passed.")
			return
		if len(args) > 2:
			error(f"No more than two args is required.")
			return
		command, *arg = args
		try:
			procedure, expected_args = self.get_command(command)
		except ValueError:
			return

		if not arg:
			try:
				procedure()
			except TypeError as e:
				raise e
				error(f"{command!r} command requires an argument but none were given.")
			return

		arg = arg[0]
		if arg in expected_args:
			procedure(arg)
		else:
			if not expected_args:
				error(f"{command!r} command takes no argument.")
				return
			match = self.find_similar(arg, expected_args)
			error(f"{command!r} command have no argument named {arg!r}.")
			if match is not None:
				error(f"Did you perhaps meant {match!r}?")

	@classmethod
	def find_similar(cls, name, pool):
		matcher = SequenceMatcher()
		matcher.set_seq1(name.casefold())
		ratios = {}
		for p in pool:
			matcher.set_seq2(p.casefold())
			ratio = matcher.ratio()
			ratios[ratio] = p
		m = max(ratios)
		if m > 0.6:
			return ratios[m]
		else:
			return None

	def get_command(self, name):
		try:
			return self.procedures[name]
		except KeyError:
			match = self.find_similar(name, self.procedures)
			error(f"No command named {name!r}.")
			if match is not None:
				error(f"Did you perhaps meant {match!r}?")
			raise ValueError()

	@classmethod
	def call(cls, cmd, jobname):
		import subprocess
		err = subprocess.PIPE
		out = subprocess.PIPE
		p = subprocess.run(cmd, shell=True, stdout=out, stderr=err)
		error(p.stderr.decode(), end = "")
		if not p.stderr:
			success(f"Built {jobname}.")
			return True
		else:
			warning(f"There were errors while building {jobname}.")
			return False

app = App()

@app.command("release", "dev")
def build(app, job = None):
	"""Builds the docs. 
	* Increases the project version if [release] argument is given.
	* Opens the docs/index.html in browser if [dev] argument is given.
	* Moves them to where they are needed if [release] or [dev] argument is given."""

	# should we do that at the start so that it affects this release or at the end so that it doesn't run if there is an exception?
	if job == "release":
		version('patch')

	print("Starting the build process.")
	p = app.call("make html", "HTML")
	p = app.call("make singlehtml", "HTML (single file)")
	p = app.call("make latexpdf", "PDF")
	p = app.call("make epub", "EPUB")

	if job is None:
		return

	import move_documents
	if job == "dev":
		view()

@app.command()
def view(app):
	"Opens the docs/index.html in browser."
	import webbrowser
	webbrowser.open(index_file, new=0, autoraise=True)
	success("Opened the docs/index.html in browser.")
	
@app.command()
def checklinks(app):
	"Check the links and fix them manually."
	print("Checking the links.")
	p = app.call("make linkcheck", "linkcheck")
	if p:
		import linkfix

@app.command("major", "minor", "patch", "downgrade")
def version(app, field):
	"Upgrades or downgrades the project version with respect to the specified argument ([major], [minor], [patch] or [downgrade])."
	with open(version_file, "r") as f:
		versions = list(map(lambda x: x[:-1] if x.endswith("\n") else x, f))
	if field == "downgrade":
		if len(versions) == 1:
			error("Can't downgrade when there is a single recorded version.")
			return
		versions.pop()
		success(f"Downgraded the version to {versions[-1]}.")
	else:
		version = list(map(int, versions[-1].split(".")))
		index = ("major", "minor", "patch").index(field)

		version[index] += 1
		for i in range(index + 1, 3):
			version[i] = 0
		version = ".".join(map(str, version))
		versions.append(version)
		success(f"Upgraded the version to {version}.")

	with open(version_file, "w") as f:
		f.write("\n".join(versions))

def highlight_arguments(procedure):
	return modify_words(procedure[0].__doc__, words = tuple(map(lambda x: f"[{x}]", procedure[1])), style = Styles.BOLD, replacement_rule = lambda x: x[1:-1])

@app.command(*app.procedures, "help")
def help(app, method = None):
	"Displays a help message for the given argument."
	if method is None:
		print("Valid arguments for the application:\n")
		for i in app.procedures:
			print(f"- {i:<20}" + highlight_arguments(app.procedures[i]))
	else:
		print(f"{method}:", highlight_arguments(app.procedures[method]))

if __name__ == "__main__":
	import sys
	args = sys.argv[1:]
	app.run(args)
else:
	raise ImportError("This file is not supposed to be imported.")
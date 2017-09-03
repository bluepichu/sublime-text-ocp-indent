"""
This module allows you to analyse OCaml source code, autocomplete,
and infer types while writing.
"""

import functools
import sublime
import sublime_plugin
import re
import os
import sys
import subprocess

def is_ocaml(view):
	return view.match_selector(view.sel()[0].begin(), "source.ocaml")

def indent_lines(view, edit, lines):
	if not is_ocaml(view):
		return

	# get the proper indentation from ocp-indent
	process = subprocess.Popen(
		["ocp-indent", "--numeric", "--indent-empty"],
		stdin = subprocess.PIPE,
		stdout = subprocess.PIPE,
		stderr = subprocess.PIPE,
		universal_newlines = True
	)

	content = view.substr(sublime.Region(0, view.size()))
	(result, _) = process.communicate(input = content)
	result = [int(r) for r in result[:-1].split("\n")]

	# add the new indents
	for line in lines:
		if line < 0:
			continue
		current_line = view.line(view.text_point(line, 0))
		current_line_content = view.substr(current_line)
		new_current_line_content = (" " * result[line]) + current_line_content.lstrip(" ")
		view.replace(edit, current_line, new_current_line_content)

class OcpIndentLinesOnInsert(sublime_plugin.TextCommand):
	def run(self, edit, key):
		# disable sublime's autoindent to prevent double-indenting
		self.view.settings().set("auto_indent", False)

		# insert the typed character
		self.view.run_command("insert", { "characters": key })

		# indent lines that are in the selection or are one line before a selection
		start_end_lines = [(self.view.rowcol(region.a)[0], self.view.rowcol(region.b)[0]) for region in self.view.sel()]
		lines = {line for (start, end) in start_end_lines for line in range(min(start, end) - 1, max(start, end) + 1)}
		indent_lines(self.view, edit, lines)

		# update selections - after typing a character, they should be empty
		selection_regions = [sublime.Region(region.b, region.b) for region in self.view.sel()]
		self.view.sel().clear()
		self.view.sel().add_all(selection_regions)

class OcpIndentSelection(sublime_plugin.TextCommand):
	def run(self, edit):
		# indent lines that are in the selection
		start_end_lines = [(self.view.rowcol(region.a)[0], self.view.rowcol(region.b)[0]) for region in self.view.sel()]
		lines = {line for (start, end) in start_end_lines for line in range(min(start, end), max(start, end) + 1)}
		indent_lines(self.view, edit, lines)

class OcpIndentFile(sublime_plugin.TextCommand):
	def run(self, edit):
		# indent all lines
		indent_lines(self.view, edit, [line for line in range(0, self.view.rowcol(self.view.size())[0] + 1)])

class OcpIndentEventListener(sublime_plugin.EventListener):
	def on_pre_save(self, view):
		if is_ocaml(view):
			view.run_command("ocp_indent_file")

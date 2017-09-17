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

def indent_lines(view, edit, lines, indent_empty = True):
	if not is_ocaml(view):
		return

	command = ["ocp-indent", "--numeric"]

	if indent_empty:
		command.append("--indent-empty")

	# get the proper indentation from ocp-indent
	process = subprocess.Popen(
		command,
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

def update_selection_regions(view):
	selection_regions = [sublime.Region(region.b, region.b) for region in view.sel()]
	view.sel().clear()
	view.sel().add_all(selection_regions)

class OcpIndentLinesOnInsert(sublime_plugin.TextCommand):
	def run(self, edit, key):
		print("indenting on insert")

		# disable sublime's autoindent to prevent double-indenting
		self.view.settings().set("auto_indent", False)

		# insert the typed character
		self.view.run_command("insert", { "characters": key })

		# indent lines that are in the selection or are one line before a selection
		start_end_lines = [(self.view.rowcol(region.a)[0], self.view.rowcol(region.b)[0]) for region in self.view.sel()]
		lines = {line for (start, end) in start_end_lines for line in range(min(start, end) - 1, max(start, end) + 1)}
		indent_lines(self.view, edit, lines)

		# update selections - after typing a character, they should be empty
		update_selection_regions(self.view)

class OcpIndentSelection(sublime_plugin.TextCommand):
	def run(self, edit):
		# indent lines that are in the selection
		start_end_lines = [(self.view.rowcol(region.a)[0], self.view.rowcol(region.b)[0]) for region in self.view.sel()]
		lines = {line for (start, end) in start_end_lines for line in range(min(start, end), max(start, end) + 1)}
		indent_lines(self.view, edit, lines)

class OcpIndentFile(sublime_plugin.TextCommand):
	def run(self, edit, indent_empty = True):
		# indent all lines
		indent_lines(self.view, edit, [line for line in range(0, self.view.rowcol(self.view.size())[0] + 1)], indent_empty = indent_empty)

class OcpIndentEventListener(sublime_plugin.EventListener):
	lines = 0
	rewriting = False

	def on_modified(self, view):
		if is_ocaml(view) and not self.rewriting:
			self.rewriting = True
			lines = len(view.substr(sublime.Region(0, view.size())).split("\n")) + 1

			if lines != self.lines:
				self.lines = lines
				view.run_command("ocp_indent_file")
				update_selection_regions(view)
		self.rewriting = False

	def on_pre_save(self, view):
		if is_ocaml(view):
			view.run_command("ocp_indent_file", { "indent_empty": False })

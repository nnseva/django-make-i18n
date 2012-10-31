django-make-i18n
================

Adopt Django project to use with django-i18n features.
Collects and replaces local strings from all project files
and creates django.po and djangojs.po files.

This project has been created when I've met a problem
converting the Django project into the internationalized form.

The lot of local (language-specific) strings was found in the
project, so I was boring looking into the lot of files to:
 - search every local string
 - replace it in the source code by international equivalent
 - put the translation into the django.po file

The only script present here does it all.

REQUIREMENTS

  - python 2.7
  - polib python library >= 0.7.0

USING

The script is intended to be used for django projects, although
may be used to translate pure python, html, or JavaScript project.
The script doesn't need django environment itself.

The project default parameter values have been created to use with
Russian language, although may be used with any language whose specific
might be recognized by one or several (or-ed) regular expressions.

The script has '-h' option self-describing almost all details.

The RECOMMENDED using scenario of the script consists of 3 STAGES.

1) COLLECTING (--stage=1). You are calling a script
initially, or passing the --stage=1 parameter to it in the
command line explicitly.

On this stage, the script analyzes all project files and collects
all local-language-specific strings to django.po file.

"Untranslated" version of every string (msgid) has initially a dumb
form "NEEDS TO BE EDITED [nnn]".

2) UNTRANSLATING. This stage is manual and optional.

You are free to replace dumb msgid values in the django.po file
collected by the script by any unique phrases (using pure ascii
character subset to avoid problems with django i18n features).

DON'T change msgstr values on this stage.

3) REPLACING (--stage=2). You are calling a script for the
second time (with presence of django.po file), or passing
the --stage=2 parameter to it in the command line
explicitly.

On this stage, the script analyzes project files and collects all
strings again, and then - compares them against existent
django.po content.

All strings found in the django.po file as msgstr values, are
replaced by i18n-ready code in source files. For every file,
where local strings are found, some preamble will be added
to make the i18n-ready code working.

By default, the script leaves initial code untouched, creating
a new project folder having .i18n additional extension.

Don't forget that django needs to compile django.po file
using compilemessages management command.

You probably should tune your code additionaly after script
to make your code working fine. Read django internalization
help to get details.

#!/usr/bin/env python

"""
Script to add texinfo targets in Sphinx Makefile

Just run the program at the root of the project::

    %(prog)s

Resources:

- (info "(sphinx) Options for Texinfo output")
- http://sphinx-doc.org/config.html#confval-texinfo_documents

"""

"""
License
=======

Copyright (c) 2013 Takafumi Arakaki
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os
import re


def one_of(candidates, predicate):
    for doc in candidates:
        if predicate(doc):
            return doc


def filter_dict(pred, d):
    if pred is None:
        pred = lambda k, v: v is not None
    return dict((k, v) for (k, v) in d.items() if pred(k, v))


def find_sphinx_dir():
    return one_of(['doc', 'docs'], os.path.isdir)


def find_sphinx_makefile():
    doc = find_sphinx_dir()
    return one_of(
        [os.path.join(doc, 'Makefile')],
        os.path.isfile)


def find_sphinx_conf():
    doc = find_sphinx_dir()
    return one_of(
        [os.path.join(doc, 'conf.py'),
         os.path.join(doc, 'source', 'conf.py')],
        os.path.isfile)


MAKEFILE_HELP_LINES = """\
\t@echo "  texinfo     to make Texinfo files"
\t@echo "  info        to make Texinfo files and run them through makeinfo"
"""

MAKEFILE_TARGETS_TEMPLATE = """
texinfo:
\tmkdir -p {builddir}/texinfo
\t$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) {builddir}/texinfo
\t@echo
\t@echo "Build finished. The Texinfo files are in {builddir}/texinfo."
\t@echo "Run \\`make' in that directory to run these through makeinfo" \\
\t      "(use \\`make info' here to do that automatically)."

info:
\tmkdir -p {builddir}/texinfo
\t$(SPHINXBUILD) -b texinfo $(ALLSPHINXOPTS) {builddir}/texinfo
\t@echo "Running Texinfo files through makeinfo..."
\tmake -C {builddir}/texinfo info
\t@echo "makeinfo finished; the Info files are in {builddir}/texinfo."
"""


def modify_makefile_lines(lines, builddir):
    n_help_lines = 0
    for l in lines:
        yield l
        if all(w in l for w in ['@echo', 'latex', 'to make LaTeX files,']):
            n_help_lines += 1
            yield MAKEFILE_HELP_LINES
    yield MAKEFILE_TARGETS_TEMPLATE.format(builddir=builddir)
    assert n_help_lines == 1


def get_makefile_builddir(path, lines):
    """
    Read Makefile and find appropriate build directory.

    :rtype: str
    :return: '$(BUILDDIR)', '_build' or 'build'

    """
    for l in lines:
        if '$(BUILDDIR)' in l:
            return '$(BUILDDIR)'
    for l in lines:
        if re.search(r'\b_build\b', l):
            return '_build'
        if re.search(r'\bbuild\b', l):
            return 'build'

    doc = os.path.dirname(path)
    build_path = one_of(
        [os.path.join(doc, 'build'),
         os.path.join(doc, '_build')],
        os.path.isdir)
    return os.path.relpath(build_path, doc)


CONF_PY_TEXINFO_DOCUMENTS_TEMPLATE = """
texinfo_documents = [
  ({startdocname}, '{targetname}', '{title}',
   '{author}',
   '{dir_entry}',
   '{description}',
   '{category}',
   {toctree_only}),
]
"""


def conf_py_texinfo_documents(
        project_name, startdocname,
        targetname=None, title=None, authors=[], dir_entry=None,
        description=None, category='Programming', toctree_only=True):
    """
    Generate "texinfo_documents = [...]" for conf.py.

    :rtype: str

    """
    targetname = targetname or project_name.lower()
    title = title or '{0} Documentation'.format(project_name)
    description = description or title
    dir_entry = dir_entry or project_name
    if authors:
        author = '@*'.join(authors)
    else:
        author = '{0} Development Team'.format(project_name)
    return CONF_PY_TEXINFO_DOCUMENTS_TEMPLATE.format(
        startdocname=startdocname,
        targetname=targetname,
        title=title,
        author=author,
        dir_entry=dir_entry,
        description=description,
        category=category,
        toctree_only=int(toctree_only))


def read_sphinx_conf(confpath):
    ns = {'__file__': confpath}
    execfile(confpath, ns)
    return ns


def params_for_texinfo_documents(conf):
    """
    Generate kwds for `conf_py_texinfo_documents` based on conf.py.

    :type ns: dict
    :arg  ns: conf.py loaded by `read_sphinx_conf`
    :rtype  : dict
    :return : keyword arguments for `conf_py_texinfo_documents`

    """
    project = conf['project']
    params = dict(project_name=project)

    if 'master_doc' in conf:
        params['startdocname'] = 'master_doc'
    else:
        latex_documents = conf['latex_documents']
        try:
            params['startdocname'] = repr(latex_documents[0][0])
        except IndexError:
            params['startdocname'] = 'index'

    return params


def sphinx_add_texinfo(**additional_params):

    makefile_path = find_sphinx_makefile()
    with open(makefile_path) as fp:
        makefile_orig_lines = fp.readlines()
    builddir = get_makefile_builddir(makefile_path, makefile_orig_lines)
    makefile_lines = list(modify_makefile_lines(makefile_orig_lines, builddir))

    conf_path = find_sphinx_conf()
    conf = read_sphinx_conf(conf_path)
    params = params_for_texinfo_documents(conf)
    params.update(filter_dict(None, additional_params))
    conf_addition = conf_py_texinfo_documents(**params)

    with open(makefile_path, 'w') as fp:
        fp.writelines(makefile_lines)
    with open(conf_path, 'a') as fp:
        fp.write(conf_addition)


def main(args=None):
    import argparse
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__)
    parser.add_argument('--project-name')
    parser.add_argument('--startdocname')
    parser.add_argument('--targetname')
    parser.add_argument('--title')
    parser.add_argument('--author', action='append')
    parser.add_argument('--dir-entry')
    parser.add_argument('--description')
    parser.add_argument('--category')
    parser.add_argument('--toctree-only', choices=[0, 1], type=int)
    ns = parser.parse_args(args)
    sphinx_add_texinfo(**vars(ns))


if __name__ == '__main__':
    main()

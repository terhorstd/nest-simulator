# -*- coding: utf-8 -*-
#
# extractor_userdocs.py
#
# This file is part of NEST.
#
# Copyright (C) 2004 The NEST Initiative
#
# NEST is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# NEST is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NEST.  If not, see <http://www.gnu.org/licenses/>.
"""
Extract user-documentation from C++ code files.

Usage: extract_userdocs list files
       extract_userdocs run

"""
import glob
import json
import logging
import os
import re
import sys
from collections import Counter
from itertools import chain, combinations
from math import comb
from pathlib import Path
from pprint import pformat
from typing import Dict, List, Optional

from tqdm import tqdm

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class NoUserDocsFound(AttributeError):
    pass


def relative_glob(*pattern, basedir=os.curdir, **kwargs):
    tobase = os.path.relpath(basedir, os.curdir)
    # prefix all patterns with basedir and expand
    names = chain.from_iterable(glob.glob(os.path.join(tobase, pat), **kwargs) for pat in pattern)
    # remove prefix from all expanded names
    return [name[len(tobase) + 1 :] for name in names]


class UserDoc:
    def __init__(self, document: str, tags: list, filename: Path):
        self._doc = document
        self._tags = tags.copy()
        self._filename = filename

    def save(self):
        """
        Write the raw document to disk.
        """
        log.debug("writing userdoc to %s", self._filename)
        with self._filename.open("w", encoding="utf8") as outfile:
            outfile.write(self._doc)

    @property
    def doc(self):
        return self._doc

    @property
    def tags(self):
        return self._tags.copy()

    @property
    def filename(self):
        return self._filename


class KeywordIndex:

    def __init__(self):
        self._documents: list[UserDoc] = []

    def add(self, userdoc: UserDoc):
        """
        Add the given document to the index.

        Parameters
        ----------
        userdoc : UserDoc
           Parsed document to be added.
        """
        self._documents.append(userdoc)

    @property
    def tagdict(self) -> dict[str, list[str]]:
        """
        Create a reverse index of tags to document names.

        Returns
        -------
        dict
           mapping tags to lists of documentation filenames (relative to `_outdir`).
        """
        tagdict: dict[str, list[str]] = dict()  # map tags to lists of documents
        for userdoc in self._documents:
            for tag in userdoc.tags:
                tagdict.setdefault(tag, list()).append(userdoc.filename.name)
        return tagdict


class UserDocExtractor:
    def __init__(self, basedir: str = ".."):
        """
        Create a userdoc extractor instance.

        Instanciation already prepares for all kinds of operations, so outdir
        is created, checks are being done, etc.

        Parameters
        ----------

        basedir : str, path
           Directory to which input `filenames` are relative.
        """
        self._basedir = Path(basedir)

    def extract_all(self, filenames: list[Path]) -> KeywordIndex:
        """
        Extract all user documentation from given files.

        This method calls ``extract()`` on all given files and stores documents
        in this instance.

        The extracted documentation is written to a file via `UserDoc.save()`.

        Parameters
        ----------

        filenames : iterable
           Any iterable with input file names (relative to `_basedir`).

        Returns
        -------
        KeywordIndex
           Index of successfully extraced UserDoc objects.
        """
        index = KeywordIndex()
        nfiles_total = 0  # count one-by-one to not exhaust iterators
        n_extracted = 0
        with tqdm(unit="files", total=len(filenames)) as progress:
            for filename in filenames:
                progress.set_postfix(file=os.path.basename(filename)[:15], refresh=False)
                progress.update(1)
                nfiles_total += 1
                try:
                    userdoc = self.extract(filename)
                    index.add(userdoc)
                    n_extracted += 1
                    userdoc.save()
                except NoUserDocsFound:
                    log.info("No user documentation found in %s", filename)

        tagdict = index.tagdict
        log.info("%4d tags found:\n%s", len(tagdict), pformat(list(tagdict.keys())))
        nfiles = len(set.union(*[set(x) for x in tagdict.values()]))
        log.info("%4d files in input", nfiles_total)
        log.info("%4d files with documentation", nfiles)
        return index

    def extract(self, filename: Path):
        """
        Extract user documentation from a file.

        This method searches for "BeginUserDocs" and "EndUserDocs" keywords and
        extracts all text inbetween as user-level documentation. The keyword
        "BeginUserDocs" may optionally be followed by a colon ":" and a comma
        separated list of tags till the end of the line. Note that this allows tags
        to contain spaces, i.e. you do not need to introduce underscores or hyphens
        for multi-word tags.

        Example
        -------

        /* BeginUserDocs: example, user documentation generator

        [...]

        EndUserDocs */

        This will extract "[...]" as documentation for the file and tag it with
        'example' and 'user documentation generator'.

        Parameters
        ----------

        filename : Path
           Source-code filename from which userdocs should be extracted.
           (relative to `_basedir`).

        Returns
        -------

        UserDoc
           Extracted user-documentation object.

        Raises
        ------
        NoUserDocsFound
           If no section "BeginUserDoc" … "EndUserDoc" could be found.
        """
        userdoc_re = re.compile(r"BeginUserDocs:?\s*(?P<tags>([\w -]+(,\s*)?)*)\n+(?P<doc>(.|\n)*)EndUserDocs")
        log.info("extracting user documentation from %s...", filename)
        match = None
        with (self._basedir / filename).open("r", encoding="utf8") as infile:
            match = userdoc_re.search(infile.read())
        if not match:
            raise NoUserDocsFound()
        outname = Path(filename).with_suffix(self._replace_ext).name
        tags = [t.strip() for t in match.group("tags").split(",")]
        doc = match.group("doc")
        try:
            doc = rewrite_short_description(doc, filename)
        except ValueError as e:
            log.warning("Documentation added unfixed: %s", e)
        try:
            doc = rewrite_see_also(doc, filename, tags)
        except ValueError as e:
            log.info("Failed to rebuild 'See also' section: %s", e)
        return UserDoc(doc, tags, self._outdir / outname)


class RstWriter:
    """
    Class holding all output methods for writing RST files.

    Handled objects are of internal types only: UserDoc, KeywordIndex.
    """
    def __init__(self, outdir: str = "userdocs/", replace_ext: str = ".rst"):
        """
        Parameters
        ----------
        replace_ext : str
           Replacement for the extension of the original filename when writing to `outdir`.

        outdir : str, path
           Directory where output files are created.
        """
        self._outdir = Path(outdir)
        self._replace_ext = replace_ext

        self._outdir = Path(outdir)
        if not self._outdir.exists() or not self._outdir.is_dir():
            log.info("creating output directory %s", self._outdir)
            self._outdir.mkdir()


    def CreateTagIndices(self, index: KeywordIndex) -> list[str]:
        """
        This function generates all combinations of tags and creates an index page
        for each combination using `rst_index`.

        Returns
        -------

        list
            list of names of generated files. (relative to `_outdir`)
        """
        tags = index.tagdict
        taglist = list(tags.keys())
        maxtaglen = max([len(t) for t in tags])
        for tag, count in sorted([(tag, len(lst)) for tag, lst in tags.items()], key=lambda x: x[1]):
            log.info("    %%%ds tag in %%d files" % maxtaglen, tag, count)
        if "NOINDEX" in taglist:
            taglist.remove("NOINDEX")
        if "" in taglist:
            taglist.remove("")
        indexfiles = list()
        depth = min(4, len(taglist))  # how many levels of indices to create at most
        nindices = sum([comb(len(taglist), L) for L in range(depth - 1)])
        log.info("indices down to level %d → %d possible keyword combinations", depth, nindices)
        for current_tags in tqdm(
            chain(*[combinations(taglist, L) for L in range(depth + 1)]),
            unit="idx",
            desc="keyword indices",
            total=nindices,
        ):
            current_tags = tuple(sorted(current_tags))
            indexname = "index%s.rst" % "".join(["_" + x for x in current_tags])
            log.debug("generating index level %d for %s", len(current_tags), current_tags)
            hier = make_hierarchy(tags.copy(), *current_tags)
            if not any(hier.values()):
                log.debug("index %s is empty!", str(current_tags))
                continue
            log.warning("generating index level %d for %s", len(current_tags), current_tags)
            log.warning(f"{hier=}")
            # subtags = [set(subtag) for subtag in hier.values()]
            # log.debug("subtags = %s", subtags)
            # nfiles = len(set.union(*chain([set(subtag) for subtag in hier.values()])))
            # log.debug("%3d docs in index for %s...", nfiles, str(current_tags))
            log.debug("generating index for %s...", str(current_tags))
            indextext = rst_index(hier, current_tags)
            with open(os.path.join(self._outdir, indexname), "w") as outfile:
                outfile.write(indextext)
            indexfiles.append(indexname)
        log.warning("%4d non-empty index files generated", len(indexfiles))
        return indexfiles


def rewrite_short_description(doc, filename, short_description="Short description"):
    """
    Modify a given text by replacing the first section named as given in
    `short_description` by the filename and content of that section.
    Parameters
    ----------
    doc : str
      restructured text with all sections
    filename : str, path
      name that is inserted in the replaced title (and used for useful error
      messages).
    short_description : str
      title of the section that is to be rewritten to the document title
    Returns
    -------
    str
        original parameter doc with short_description section replaced
    """

    titles = getTitles(doc)
    if not titles:
        raise ValueError("No sections found in '%s'!" % filename)
    name = os.path.splitext(os.path.basename(filename))[0]
    for title, nexttitle in zip(titles, titles[1:] + [None]):
        if title.group(1) != short_description:
            continue
        secstart = title.end()
        secend = len(doc) + 1  # last section ends at end of document
        if nexttitle:
            secend = nexttitle.start()
        sdesc = doc[secstart:secend].strip().replace("\n", " ")
        fixed_title = "%s – %s" % (name, sdesc)
        return doc[: title.start()] + fixed_title + "\n" + "=" * len(fixed_title) + "\n\n" + doc[secend:]
    raise ValueError("No section '%s' found in %s!" % (short_description, filename))


def rewrite_see_also(doc, filename, tags, see_also="See also"):
    """
    Replace the content of a section named `see_also` in the document `doc`
    with links to indices of all its tags.
    The original content of the section -if not empty- will discarded and
    logged as a warning.
    Parameters
    ----------
    doc : str
      restructured text with all sections
    filename : str, path
      name that is inserted in the replaced title (and used for useful error
      messages).
    tags : iterable (list or dict)
      all tags the given document is linked to. These are used to construct the
      links in the `see_also` section.
    see_also : str
      title of the section that is to be rewritten to the document title
    Returns
    -------
    str
        original parameter doc with see_also section replaced
    """

    titles = getTitles(doc)
    if not titles:
        raise ValueError("No sections found in '%s'!" % filename)

    def rightcase(text):
        """
        Make text title-case except for acronyms, where an acronym is
        identified simply by being all upper-case.
        This function operates on the whole string, so a text with mixed
        acronyms and non-acronyms will not be recognized and everything will be
        title-cased, including the embedded acronyms.
        Parameters
        ----------
        text : str
          text that needs to be changed to the right casing.
        Returns
        -------
        str
          original text with poentially different characters being
          upper-/lower-case.
        """
        if text != text.upper():
            return text.title()  # title-case any tag that is not an acronym
        return text  # return acronyms unmodified

    for title, nexttitle in zip(titles, titles[1:] + [None]):
        if title.group(1) != see_also:
            continue
        secstart = title.end()
        secend = len(doc) + 1  # last section ends at end of document
        if nexttitle:
            secend = nexttitle.start()
        original = doc[secstart:secend].strip().replace("\n", " ")
        if original:
            log.info("dropping manual 'see also' list in %s user docs: '%s'", filename, original)
        return (
            doc[:secstart]
            + "\n"
            + ", ".join([":doc:`{taglabel} <index_{tag}>`".format(tag=tag, taglabel=rightcase(tag)) for tag in tags])
            + "\n\n"
            + doc[secend:]
        )
    raise ValueError("No section '%s' found in %s!" % (see_also, filename))


def make_hierarchy(tags, *basetags):
    """
    This method adds a single level of hierachy to the given dictionary.

    First a list of items with given basetags is created (intersection). Then
    this list is subdivided into sections by creating intersections with all
    remaining tags.

    Parameters
    ----------
    tags : dict
       flat dictionary of tag to entry

    basetags : iterable
       iterable of a subset of tags.keys(), if no basetags are given the
       original tags list is returned unmodified.

    Returns
    -------

    dict
       A hierarchical dictionary of (dict or set) with items in the
       intersection of basetag.
    """
    if not basetags:
        return tags

    # items having all given basetags
    baseitems = set.intersection(*[set(items) for tag, items in tags.items() if tag in basetags])
    tree = dict()
    subtags = [t for t in tags.keys() if t not in basetags]
    for subtag in subtags:
        docs = set(tags[subtag]).intersection(baseitems)
        if docs:
            tree[subtag] = docs
    remaining = None
    if tree.values():
        remaining = baseitems.difference(set.union(*tree.values()))
    if remaining:
        tree[""] = remaining
    return {basetags: tree}


def rst_index(hierarchy, current_tags=[], underlines="=-~", top=True):
    """
    Create an index page from a given hierarchical dict of documents.

    The given `hierarchy` is pretty-printed and returned as a string.

    Parameters
    ----------
    hierarchy : dict
       dictionary or dict-of-dict returned from `make_hierarchy()`

    current_tags : list
       applied filters for the current index (parameters given to
       `make_hierarchy()`. Defaults to `[]`, which doesn't display any filters.

    underlines : iterable
       list of characters to use for underlining deeper levels of the generated
       index.

    top : bool
       optional argument keeping track of recursive calls. Calls from within
       `rst_index` itself will always call with `top=False`.

    Returns
    -------

    str
       formatted pretty index.
    """

    def mktitle(t: str, ul: str, link: Optional[str] = None) -> str:
        text = t
        if t != t.upper():
            text = t.title()  # title-case any tag that is not an acronym
        title = ":doc:`{text} <{filename}>`".format(text=text, filename=link or "index_" + t)
        text = title + "\n" + ul * len(title) + "\n\n"
        return text

    def mkitem(t) -> str:
        return "* :doc:`%s`" % os.path.splitext(t)[0]

    output = list()
    if top:
        # Prevent warnings by adding an orphan role so Sphinx does not expect it in toctrees
        orphan_text = ":orphan:" + "\n\n"
        page_title = "Model directory"
        description = """
                       The model directory is organized and autogenerated by keywords (e.g., adaptive threshold,
                       conductance-based etc.). Models that contain a specific keyword will be listed under that word.
                       For more information on models, see our :ref:`intro to NEST models <modelsmain>`.
                       """
        if len(hierarchy.keys()) == 1:
            page_title += ": " + ", ".join(current_tags)
        output.append(orphan_text + page_title)
        output.append(underlines[0] * len(page_title) + "\n")
        output.append(description + "\n")
        if len(hierarchy.keys()) != 1:
            underlines = underlines[1:]

    for tags, items in sorted(hierarchy.items()):
        if "NOINDEX" in tags:
            continue
        if isinstance(tags, str):
            title = tags
        else:
            title = " & ".join(tags)
        if title and not len(hierarchy) == 1:  # not print title if already selected by current_tags
            if isinstance(tags, str):
                subindex = "index_" + "_".join(sorted(chain([tags], current_tags)))
            else:
                subindex = "index_" + "_".join(sorted(chain(tags, current_tags)))
            if isinstance(items, list):
                title += f" ({len(items)})"
            output.append(mktitle(title, underlines[0], subindex))
        if isinstance(items, dict):
            output.append(rst_index(items, current_tags, underlines[1:], top=False))
        else:
            for item in sorted(items):
                output.append(mkitem(item))
            output.append("")
    return "\n".join(output)


def reverse_dict(tags):
    """
    Return the reversed dict-of-list

    Given a dictionary `keys:values`, this function creates the inverted
    dictionary `value:[key, key2, ...]` with one entry per value of the given
    dict. Since many keys can have the same value, the reversed dict must have
    list-of-keys as values.

    Parameters
    ----------

    tags : dict
       Values must be hashable to be used as keys for the result.

    Returns
    -------

    dict
       Mapping the original values to lists of original keys.
    """
    revdict = dict()
    for tag, items in tags.items():
        for item in items:
            revdict.setdefault(item, list()).append(tag)
    return revdict


class JsonWriter:
    """
    Helper class to have a unified data output interface.
    """

    def __init__(self, outdir):
        self.outdir = outdir
        log.info("writing JSON files to %s", self.outdir)

    def write(self, obj, name):
        """
        Store the given object with the given name.
        """
        outname = os.path.join(self.outdir, name + ".json")
        with open(outname, "w") as outfile:
            json.dump(obj, outfile)
            log.info("data saved as " + outname)


def getTitles(text):
    """
    extract all sections from the given RST file

    Parameters
    ----------

    text : str
      restructuredtext user documentation

    Returns
    -------

    list
      elements are the section title re.match objects
    """
    titlechar = r"\+"
    title_re = re.compile(r"^(?P<title>.+)\n(?P<underline>" + titlechar + r"+)$", re.MULTILINE)
    titles = []
    # extract all titles
    for match in title_re.finditer(text):
        log.debug("MATCH from %s to %s: %s", match.start(), match.end(), pformat(match.groupdict()))
        if len(match.group("title")) != len(match.group("underline")):
            log.warning(
                "Length of section title '%s' (%d) does not match length of underline (%d)",
                match.group("title"),
                len(match.group("title")),
                len(match.group("underline")),
            )
        titles.append(match)
    return titles


def got_args(*names):
    "Returns True if sys.argv contains the given strings."
    if len(sys.argv) < len(names):
        return False
    if all([arg == names[i] for i, arg in enumerate(sys.argv[1:])]):
        return True
    return False


def output_exit(result):
    json.dump(result, sys.stdout, indent="  ", check_circular=True)
    print()  # add \n at the end.
    if isinstance(result, list):
        log.info("result list with %d entries", len(result))
    sys.exit(0)


def ExtractUserDocs(listoffiles, basedir="..", outdir="userdocs/"):
    """
    Extract and build all user documentation and build tag indices.
    Writes extracted information to JSON files in outdir. In particular the
    list of seen tags mapped to files they appear in, and the indices generated
    from all combinations of tags.
    Parameters are the same as for `UserDocExtractor` and are handed to it
    unmodified.
    Returns
    -------
    None
    """
    data = JsonWriter(outdir)
    # Gather all information and write RSTs
    extractor = UserDocExtractor(outdir=outdir, basedir=basedir)
    index = extractor.extract_all(listoffiles)
    tags = extractor.tagdict
    data.write(tags, "tags")

    indexfiles = extractor.CreateTagIndices()

    data.write(indexfiles, "indexfiles")

    toc_list = [name[:-4] for names in tags.values() for name in names]
    idx_list = [indexfile[:-4] for indexfile in indexfiles]

    with open(os.path.join(outdir, "toc-tree.json"), "w") as tocfile:
        json.dump(list(set(toc_list)) + list(set(idx_list)), tocfile)


def config_inited_handler(app, config):
    """
    This is the entrypoint called by the registered Sphinx hook.
    """
    try:
        models_rst_dir = os.path.abspath("models")
        repo_root_dir = os.path.abspath("../..")
        ExtractUserDocs(
            listoffiles=relative_glob("models/*.h", "nestkernel/*.h", basedir=repo_root_dir),
            basedir=repo_root_dir,
            outdir=models_rst_dir,
        )
    except Exception as exc:
        log.exception(exc)
        raise


def setup(app):
    app.connect("config-inited", config_inited_handler)
    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


if __name__ == "__main__":
    #
    # NOTE: This code is only executed when called from the command line. The
    # normal mode of operation is to place a hook via `setup()` and then be
    # called by Sphinx at the appropriate point(s) in the process.
    #
    globs = ("models/*.h", "nestkernel/*.h")
    basedir = ".."
    outdir = "userdocs/"
    log.debug("args: %s", repr(sys.argv))

    output = JsonWriter(outdir)
    files = relative_glob(*globs, basedir=basedir)
    if got_args("list", "files"):
        output_exit(files)

    extractor = UserDocExtractor(outdir=outdir, basedir=basedir)
    extractor.extract_all(files)
    tags = extractor.tagdict
    if got_args("list", "tags"):
        output_exit(tags)
    output.write(tags, "tags")

    indexfiles = extractor.CreateTagIndices()
    if got_args("list", "indices"):
        output_exit(indexfiles)
    output.write(indexfiles, "indexfiles")

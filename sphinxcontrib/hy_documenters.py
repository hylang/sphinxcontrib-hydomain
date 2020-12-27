import logging
import re
import traceback
from inspect import getfullargspec
from itertools import starmap, islice
from pprint import pp
from typing import Any, Callable, List, Optional, TypeVar
from docutils.statemachine import StringList
import sys

import hy
from docutils.nodes import Node
from sphinx import version_info
from sphinx.ext.autodoc import Documenter as PyDocumenter
from sphinx.ext.autodoc import FunctionDocumenter as PyFunctionDocumenter
from sphinx.ext.autodoc import ModuleDocumenter as PyModuleDocumenter
from sphinx.ext.autodoc.directive import (
    AutodocDirective,
    DocumenterBridge,
    DummyOptionSpec,
    parse_generated_content,
    process_documenter_options,
)
from sphinx.ext.autodoc.importer import import_module
from sphinx.ext.autodoc.mock import mock
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util.inspect import safe_getattr
from sphinx.util.typing import is_system_TypeVar

logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger("hy-domain")


def plog(*args):
    for arg in args:
        pp(arg)


hy_ext_sig_re = re.compile(
    r"""^\(
           (?P<module>[\w.]+::)?                       # Explicit module name
           (?P<classes>.*\.)?                         # Module and/or class name(s)
           (?P<object>.*?) \s*                        # Thing name
           (?:\s*\^(?P<retann>.*?)\s*)?               # Optional: return annotation
           (?:                                        # Arguments and close or just close
            (?:\[(?:\s*(?P<arguments>.*)\s*\]\))?) | # Optional: arguments
            (?:\)))
        $""",
    re.VERBOSE,
)

hy_var_sig_re = re.compile(
    r"""^ (?P<module>[\w.]+::)?   # Explicit module name
          (?P<classes>.*\.)? # Module and/or class name(s)
          (?P<object>.+?)        # thing name
        $""",
    re.VERBOSE,
)


def match_hy_sig(s: str) -> tuple:
    match = hy_ext_sig_re.match(s)
    if match:
        return match.groups()

    match = hy_var_sig_re.match(s)
    if match:
        return *match.groups(), None, None

    raise AttributeError()


def import_object(
    modname: str,
    objpath: List[str],
    objtype: str = "",
    attrgetter: Callable[[Any, str], Any] = safe_getattr,
    warningiserror: bool = False,
) -> Any:
    if objpath:
        logger.debug("[autodoc] from %s import %s", modname, ".".join(objpath))
    else:
        logger.debug("[autodoc] import %s", modname)

    try:
        module = None
        exc_on_importing = None
        objpath = list(objpath)
        while module is None:
            try:
                module = import_module(modname, warningiserror=warningiserror)
                logger.debug("[autodoc] import %s => %r", modname, module)
            except ImportError as exc:
                logger.debug("[autodoc] import %s => failed", modname)
                exc_on_importing = exc
                if "." in modname:
                    # retry with parent module
                    modname, name = modname.rsplit(".", 1)
                    objpath.insert(0, name)
                else:
                    raise

        obj = module
        parent = None
        object_name = None
        for attrname in objpath:
            parent = obj
            logger.debug("[autodoc] getattr(_, %r)", attrname)
            # mangled_name = hy.mangle(obj, attrname)
            mangled_name = hy.mangle(attrname)
            obj = attrgetter(obj, mangled_name)
            logger.debug("[autodoc] => %r", obj)
            object_name = attrname
        return [module, parent, object_name, obj]
    except (AttributeError, ImportError) as exc:
        if isinstance(exc, AttributeError) and exc_on_importing:
            # restore ImportError
            exc = exc_on_importing

        if objpath:
            errmsg = "autodoc: failed to import %s %r from module %r" % (
                objtype,
                ".".join(objpath),
                modname,
            )
        else:
            errmsg = "autodoc: failed to import %s %r" % (objtype, modname)

        if isinstance(exc, ImportError):
            # import_module() raises ImportError having real exception obj and
            # traceback
            real_exc, traceback_msg = exc.args
            if isinstance(real_exc, SystemExit):
                errmsg += (
                    "; the module executes module level statement "
                    "and it might call sys.exit()."
                )
            elif isinstance(real_exc, ImportError) and real_exc.args:
                errmsg += "; the following exception was raised:\n%s" % real_exc.args[0]
            else:
                errmsg += "; the following exception was raised:\n%s" % traceback_msg
        else:
            errmsg += (
                "; the following exception was raised:\n%s" % traceback.format_exc()
            )

        logger.debug(errmsg)
        raise ImportError(errmsg) from exc


NoneType = type(None)

def stringify(annotation: Any) -> str:
    """Stringify type annotation object."""
    from sphinx.util import inspect  # lazy loading

    if isinstance(annotation, str):
        if annotation.startswith("'") and annotation.endswith("'"):
            # might be a double Forward-ref'ed type.  Go unquoting.
            return annotation[1:-1]
        else:
            return annotation
    elif isinstance(annotation, TypeVar):
        return annotation.__name__
    # elif inspect.isNewType(annotation):
    #     # Could not get the module where it defiend
    #     return annotation.__name__
    elif not annotation:
        return repr(annotation)
    elif annotation is NoneType:
        return 'None'
    elif (getattr(annotation, '__module__', None) == 'builtins' and
          hasattr(annotation, '__qualname__')):
        return annotation.__qualname__
    elif annotation is Ellipsis:
        return '...'

    if sys.version_info >= (3, 7):  # py37+
        return _stringify_py37(annotation)
    else:
        return _stringify_py36(annotation)


def _stringify_py37(annotation: Any) -> str:
    """stringify() for py37+."""
    module = getattr(annotation, '__module__', None)
    if module == 'typing':
        if getattr(annotation, '_name', None):
            qualname = annotation._name
        elif getattr(annotation, '__qualname__', None):
            qualname = annotation.__qualname__
        elif getattr(annotation, '__forward_arg__', None):
            qualname = annotation.__forward_arg__
        else:
            qualname = stringify(annotation.__origin__)  # ex. Union
    elif hasattr(annotation, '__qualname__'):
        qualname = '%s.%s' % (module, annotation.__qualname__)
    elif hasattr(annotation, '__origin__'):
        # instantiated generic provided by a user
        qualname = stringify(annotation.__origin__)
    else:
        # we weren't able to extract the base type, appending arguments would
        # only make them appear twice
        return repr(annotation)

    if getattr(annotation, '__args__', None):
        if not isinstance(annotation.__args__, (list, tuple)):
            # broken __args__ found
            pass
        elif qualname == 'Union':
            if len(annotation.__args__) > 1 and annotation.__args__[-1] is NoneType:
                if len(annotation.__args__) > 2:
                    args = ', '.join(stringify(a) for a in annotation.__args__[:-1])
                    return '(of Optional (of Union %s))' % args
                else:
                    return '(of Optional %s)' % stringify(annotation.__args__[0])
            else:
                args = ', '.join(stringify(a) for a in annotation.__args__)
                return '(of Union %s)' % args
        elif qualname == 'Callable':
            args = ', '.join(stringify(a) for a in annotation.__args__[:-1])
            returns = stringify(annotation.__args__[-1])
            return '%(of %s [%s] %s)' % (qualname, args, returns)
        elif str(annotation).startswith('typing.Annotated'):  # for py39+
            return stringify(annotation.__args__[0])
        elif all(is_system_TypeVar(a) for a in annotation.__args__):
            # Suppress arguments if all system defined TypeVars (ex. Dict[KT, VT])
            return qualname
        else:
            args = ' '.join(stringify(a) for a in annotation.__args__)
            return '(of %s %s)' % (qualname, args)

    return qualname


def signature(obj):
    argspec = getfullargspec(obj)
    args = [
        (arg,)
        for arg in argspec.args[: len(argspec.args) - (len(argspec.defaults or []))]
    ]
    defaults = islice(argspec.args, len(args or []), None)
    defaults = list(zip(defaults, argspec.defaults or []))

    kwonlydefaults = argspec.kwonlydefaults.items() if argspec.kwonlydefaults else []
    kwonly = [
        arg
        for arg in (argspec.kwonlyargs or [])
        if arg not in (argspec.kwonlydefaults or {})
    ]
    kwargs = [*map(tuple, kwonly), *kwonlydefaults]

    varargs = [[argspec.varargs]] if argspec.varargs else []
    varkwargs = [[argspec.varkw]] if argspec.varkw else []

    sections = [
        [args, None],
        [defaults, "&optional"],
        [varargs, "&rest"],
        [kwargs, "&kwonly"],
        [varkwargs, "&kwargs"],
    ]

    def render_arg(arg, default=None):
        ann = argspec.annotations.get(arg)
        ann = stringify(ann) if ann is not None else ""
        arg = hy.unmangle(str(arg))
        return (f"^{ann} {arg}" if ann else arg) if default is None else f"^{ann} [{arg} {default}]"

    def format_section(args, opener):
        if not args:
            return ""

        args = list(starmap(render_arg, args))
        opener = opener + " " if opener else ""
        return opener + " ".join(args)

    arg_string = " ".join(
        filter(None, (format_section(args, opener) for args, opener in sections))
    )

    retann = argspec.annotations.get("return")
    retann = stringify(retann) + " " if retann is not None else ""

    return f"^{retann} [{arg_string}]" if retann else f"[{arg_string}]"


class HyAutodocDirective(AutodocDirective):
    """A directive class for all autodoc directives. It works as a dispatcher of Documenters.
    It invokes a Documenter on running. After the processing, it parses and returns
    the generated content by Documenter.
    """

    option_spec = DummyOptionSpec()
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self) -> List[Node]:
        reporter = self.state.document.reporter

        try:
            source, lineno = reporter.get_source_and_line(self.lineno)  # type: ignore
        except AttributeError:
            source, lineno = (None, None)
        logger.debug(
            "[sphinxcontrib-hydomain] %s:%s: input:\n%s",
            source,
            lineno,
            self.block_text,
        )

        # look up target Documenter
        objtype = self.name.replace("auto", "")
        doccls = self.env.app.registry.documenters[objtype]

        # process the options with the selected documenter's option_spec
        try:
            documenter_options = process_documenter_options(
                doccls, self.config, self.options
            )
        except (KeyError, ValueError, TypeError) as exc:
            # an option is either unknown or has a wrong type
            logger.error(
                "An option to %s is either unknown or has an invalid value: %s"
                % (self.name, exc),
                location=(self.env.docname, lineno),
            )
            return []

        # generate the output
        params = DocumenterBridge(
            self.env, reporter, documenter_options, lineno, self.state
        )
        documenter = doccls(params, self.arguments[0])
        documenter.generate(more_content=self.content)
        if not params.result:
            return []

        logger.debug("[autodoc] output:\n%s", "\n".join(params.result))

        # record all filenames as dependencies -- this will at least
        # partially make automatic invalidation possible
        for fn in params.filename_set:
            self.state.document.settings.record_dependencies.add(fn)

        result = parse_generated_content(self.state, params.result, documenter)
        return result


class HyDocumenter(PyDocumenter):
    domain = "hy"

    def parse_name(self) -> bool:
        try:
            explicit_modname, path, base, args, retann = match_hy_sig(self.name)
        except AttributeError as e:
            self.directive.warn(
                "invalid signature for auto%s (%r)" % self.objtype, self.name
            )
            return False

        if explicit_modname is not None:
            modname = explicit_modname[:-2]
            parents = path and path.rstrip(".").split(".") or []
        else:
            modname = None
            parents = []

        self.modname, self.objpath = self.resolve_name(modname, parents, path, base)

        if not self.modname:
            return False

        self.args = args
        self.retann = retann
        self.fullname = (self.modname or "") + (
            self.objpath and "." + ".".join(self.objpath) or ""
        )

        return True

    def import_object(self, raiseerror: bool = False) -> bool:
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.
        Returns True if successful, False if an error occurred.
        """
        with mock(self.env.config.autodoc_mock_imports):
            try:
                ret = import_object(
                    self.modname,
                    self.objpath,
                    self.objtype,
                    attrgetter=self.get_attr,
                    warningiserror=self.env.config.autodoc_warningiserror,
                )
                self.module, self.parent, self.object_name, self.object = ret
                return True
            except ImportError as exc:
                if raiseerror:
                    raise
                else:
                    logger.warning(exc.args[0])
                    self.env.note_reread()
                    return False

    def format_signature(self, **kwargs: Any) -> str:
        args = ""
        retann = ""
        try:
            args = signature(self.object)
        except Exception as exc:
            logging.warning(
                ("error while formatting arguments for %s: %s"),
                self.fullname,
                exc,
            )
            args = None

        if args is not None:
            return ((" ^%s" % retann) if retann else " ") + args
        else:
            return ""

    def format_name(self) -> str:
        return hy.unmangle(".".join(self.objpath) or self.modname)

    def add_directive_header(self, sig: str) -> None:
        """Add the directive header and options to the generated content."""
        domain = getattr(self, "domain", "hy")
        directive = getattr(self, "directivetype", self.objtype)
        name = self.format_name()
        sourcename = self.get_sourcename()

        # one signature per line, indented by column
        prefix = ".. %s:%s:: " % (domain, directive)
        for i, sig_line in enumerate(sig.split("\n")):
            if sig:
                self.add_line("%s(%s%s)" % (prefix, name, sig_line), sourcename)
            else:
                self.add_line("%s%s%s" % (prefix, name, sig_line), sourcename)

            if i == 0:
                prefix = " " * len(prefix)

        if self.options.noindex:
            self.add_line("   :noindex:", sourcename)
        if self.objpath:
            # Be explicit about the module, this is necessary since .. class::
            # etc. don't support a prepended module name
            self.add_line("   :module: %s" % self.modname, sourcename)


class HyModuleDocumenter(HyDocumenter, PyModuleDocumenter):
    pass


class HyFunctionDocumenter(HyDocumenter, PyFunctionDocumenter):
    objtype = "function"
    member_order = 30

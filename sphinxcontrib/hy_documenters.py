import builtins
import re
import traceback
from inspect import getfullargspec
from itertools import islice, starmap
from typing import Any, Callable, Dict, List, TypeVar

import hy
import hy.core.macros
from docutils.nodes import Node
from sphinx.ext.autodoc import ALL
from sphinx.ext.autodoc import AttributeDocumenter as PyAttributeDocumenter
from sphinx.ext.autodoc import ClassDocumenter as PyClassDocumenter
from sphinx.ext.autodoc import DecoratorDocumenter as PyDecoratorDocumenter
from sphinx.ext.autodoc import Documenter as PyDocumenter
from sphinx.ext.autodoc import FunctionDocumenter as PyFunctionDocumenter
from sphinx.ext.autodoc import MethodDocumenter as PyMethodDocumenter
from sphinx.ext.autodoc import ModuleDocumenter as PyModuleDocumenter
from sphinx.ext.autodoc import ObjectMember
from sphinx.ext.autodoc import PropertyDocumenter as PyPropertyDocumenter
from sphinx.ext.autodoc import members_option
from sphinx.ext.autodoc.directive import (
    AutodocDirective,
    DocumenterBridge,
    DummyOptionSpec,
    parse_generated_content,
    process_documenter_options,
)
from sphinx.ext.autodoc.importer import Attribute, import_module
from sphinx.ext.autodoc.mock import mock
from sphinx.locale import __
from sphinx.util import inspect, logging
from sphinx.util.inspect import (
    getall,
    getannotations,
    getmro,
    getslots,
    isenumclass,
    safe_getattr,
)
from sphinx.util.typing import is_system_TypeVar

logger = logging.getLogger("sphinx.contrib.hylang.documenter")

hy_ext_sig_re = re.compile(
    r"""
^\(
    (?:\s*\^(?P<retann>\(.*?\) | .*?)\s+)?     # Optional: return annotation
    (?P<module>[\w.]+::)?                      # Explicit module name
    (?P<classes>.*\.)?                         # Module and/or class name(s)
    (?P<object>.+?) \s*                        # Thing name
    (?:                                        # Arguments/close or just close
      (?:\[(?:\s*(?P<arguments>.*)\s*\]\))?) | # Optional: arguments
      (?:\)))
$
""",
    re.VERBOSE,
)

hy_var_sig_re = re.compile(
    r"""^ (?P<module>[\w.]+::)?   # Explicit module name
          (?P<classes>.*\.)?      # Module and/or class name(s)
          (?P<object>.+?)         # thing name
        $""",
    re.VERBOSE,
)

NoneType = type(None)


def get_object_members(subject: Any, objpath: List[str], attrgetter, analyzer=None):
    """Get members and attributes of target object."""
    from sphinx.ext.autodoc import INSTANCEATTR

    # the members directly defined in the class
    obj_dict = attrgetter(subject, "__dict__", {})

    members = {}  # type: Dict[str, Attribute]

    # enum members
    if isenumclass(subject):
        for name, value in subject.__members__.items():
            if name not in members:
                members[name] = Attribute(name, True, value)

        superclass = subject.__mro__[1]
        for name in obj_dict:
            if name not in superclass.__dict__:
                value = safe_getattr(subject, name)
                members[name] = Attribute(name, True, value)

    # members in __slots__
    try:
        __slots__ = getslots(subject)
        if __slots__:
            from sphinx.ext.autodoc import SLOTSATTR

            for name in __slots__:
                members[name] = Attribute(name, True, SLOTSATTR)
    except (AttributeError, TypeError, ValueError):
        pass

    # other members
    for name in dir(subject):
        try:
            value = attrgetter(subject, name)
            directly_defined = name in obj_dict
            name = hy.unmangle(name)
            if name and name not in members:
                members[name] = Attribute(name, directly_defined, value)
        except AttributeError:
            continue

    # annotation only member (ex. attr: int)
    for i, cls in enumerate(getmro(subject)):
        try:
            for name in getannotations(cls):
                name = hy.unmangle(cls, name)
                if name and name not in members:
                    members[name] = Attribute(name, i == 0, INSTANCEATTR)
        except AttributeError:
            pass

    if analyzer:
        # append instance attributes (cf. self.attr1) if analyzer knows
        namespace = ".".join(objpath)
        for ns, name in analyzer.find_attr_docs():
            if namespace == ns and name not in members:
                members[name] = Attribute(name, True, INSTANCEATTR)

    return members


def match_hy_sig(s: str) -> tuple:
    match = hy_ext_sig_re.match(s)
    if match:
        return match.groups()

    match = hy_var_sig_re.match(s)
    if match:
        return (*match.groups(), None, None)

    raise AttributeError()


def import_object(
    modname: str,
    objpath: List[str],
    objtype: str = "",
    attrgetter: Callable[[Any, str], Any] = safe_getattr,
    warningiserror: bool = False,
    macro: bool = False,
    tag: bool = False,
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
        if macro or tag:
            attrname = objpath[0]
            mangled_name = hy.mangle(attrname) if not tag else attrname
            obj = getattr(obj, "__dict__", {}).get(
                "_hy_reader_macros" if tag else "_hy_macros", {}
            )[mangled_name]
            logger.debug("[autodoc] => %r", obj)
            object_name = attrname
            return [module, parent, object_name, obj]
        else:
            for attrname in objpath:
                parent = obj
                logger.debug("[autodoc] getattr(_, %r)", attrname)
                # mangled_name = hy.mangle(obj, attrname)
                mangled_name = hy.mangle(attrname)
                obj = attrgetter(obj, mangled_name)
                logger.debug("[autodoc] => %r", obj)
                object_name = attrname
            return [module, parent, object_name, obj]
    except (AttributeError, ImportError, KeyError) as exc:
        if isinstance(exc, AttributeError) and exc_on_importing:
            # restore ImportError
            exc = exc_on_importing

        if objpath:
            errmsg = "autodoc: failed to import {} {!r} from module {!r}".format(
                objtype,
                ".".join(objpath),
                modname,
            )
        else:
            errmsg = f"autodoc: failed to import {objtype} {modname!r}"

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


def stringify(annotation: Any) -> str:
    """Stringify type annotation object."""
    # from sphinx.util import inspect  # lazy loading

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
        return "None"
    elif getattr(annotation, "__module__", None) == "builtins" and hasattr(
        annotation, "__qualname__"
    ):
        return annotation.__qualname__
    elif annotation is Ellipsis:
        return "..."

    return _stringify_py37(annotation)


def _stringify_py37(annotation: Any) -> str:
    """stringify() for py37+."""
    module = getattr(annotation, "__module__", None)
    if module == "typing":
        if getattr(annotation, "_name", None):
            qualname = annotation._name
        elif getattr(annotation, "__qualname__", None):
            qualname = annotation.__qualname__
        elif getattr(annotation, "__forward_arg__", None):
            qualname = annotation.__forward_arg__
        else:
            qualname = stringify(annotation.__origin__)  # ex. Union
    elif hasattr(annotation, "__qualname__"):
        qualname = f"{module}.{annotation.__qualname__}"
    elif hasattr(annotation, "__origin__"):
        # instantiated generic provided by a user
        qualname = stringify(annotation.__origin__)
    else:
        # we weren't able to extract the base type, appending arguments would
        # only make them appear twice
        return repr(annotation)

    if getattr(annotation, "__args__", None):
        if not isinstance(annotation.__args__, (list, tuple)):
            # broken __args__ found
            pass
        elif qualname == "Union":
            if len(annotation.__args__) > 1 and annotation.__args__[-1] is NoneType:
                if len(annotation.__args__) > 2:
                    args = " ".join(stringify(a) for a in annotation.__args__[:-1])
                    return f"(get Optional (get Union (, {args})))"
                else:
                    return "(get Optional %s)" % stringify(annotation.__args__[0])
            else:
                args = " ".join(stringify(a) for a in annotation.__args__)
                return "(get Union (, %s))" % args
        elif qualname == "Callable":
            args = ", ".join(stringify(a) for a in annotation.__args__[:-1])
            returns = stringify(annotation.__args__[-1])
            return f"(get {qualname} (, [{args}] {returns}))"
        elif str(annotation).startswith("typing.Annotated"):  # for py39+
            return stringify(annotation.__args__[0])
        elif all(is_system_TypeVar(a) for a in annotation.__args__):
            # Suppress arguments if all system defined TypeVars (ex. Dict[KT, VT])
            return qualname
        else:
            args = " ".join(stringify(a) for a in annotation.__args__)
            return f"(get {qualname} (, {args}))"

    return qualname


def signature(obj, bound_method=False, macro=False):
    argspec = getfullargspec(obj)
    args = [
        (arg,)
        for arg in argspec.args[: len(argspec.args) - (len(argspec.defaults or []))]
    ]
    defaults = list(islice(argspec.args, len(args or []), None))
    defaults = list(zip(defaults, argspec.defaults or []))

    if bound_method and args and args[0][0] == "self":
        args.pop(0)
    while args and args[0][0] in map(hy.mangle, ("&compiler", "&reader", "&key")):
        args.pop(0)
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
        [defaults, None],
        [varargs, "#*"],
        [kwargs, "*"],
        [varkwargs, "#**"],
    ]

    def render_arg(arg, default=None):
        ann = argspec.annotations.get(arg)
        ann = f"^{stringify(ann)}" if ann is not None else ""
        arg = hy.unmangle(str(arg))
        return (
            (f"{ann} {arg}" if ann else arg)
            if default is None
            else f"{ann} [{arg} {default}]"
        )

    def render_vararg(arg, opener):
        ann = argspec.annotations.get(arg)
        ann = f"^{stringify(ann)}" if ann is not None else ""
        arg = hy.unmangle(str(arg))
        return f"{ann} {opener} {arg}" if ann else f"{opener} {arg}"

    def format_section(args, opener):
        if not args:
            return ""

        if opener in ["#*", "#**"]:
            return render_vararg(args[0][0], opener)
        else:
            args = list(starmap(render_arg, args))
            opener = f"{opener} " if opener else ""
            return opener + " ".join(args)

    arg_string = " ".join(
        filter(None, (format_section(args, opener) for args, opener in sections))
    )

    retann = argspec.annotations.get("return")
    retann = stringify(retann) if retann else ""
    return f"^{retann}" if retann else None, f"[{arg_string}]"


def get_module_members(module: Any):
    """Get members of target module."""
    from sphinx.ext.autodoc import INSTANCEATTR

    members = {}
    macros = safe_getattr(module, "_hy_macros", {})
    is_core_module = "hy.core" in module.__name__

    for name in dir(module):
        try:
            value = safe_getattr(module, name, None)
            name = hy.unmangle(name)
            members[name] = (name, value)
        except AttributeError:
            continue

    for name, value in macros.items():
        try:
            setattr(value, "_hy_macro", True)
            if name not in builtins._hy_macros or is_core_module:
                name = hy.unmangle(name)
                members[name] = (name, value)
        except AttributeError:
            continue

    ret = sorted(list(members.values()))

    # annotation only member (ex. attr: int)
    try:
        for name in getannotations(module):
            if name not in members:
                members[name] = (name, INSTANCEATTR)
    except AttributeError:
        pass

    return ret


def is_hy(member, membername, parent):
    return type(parent) in {
        HyDocumenter,
        HyModuleDocumenter,
        HyFunctionDocumenter,
        HyMethodDocumenter,
        HyClassDocumenter,
    }


class HyAutodocDirective(AutodocDirective):
    """A directive class for all autodoc directives. It works as a dispatcher
    of Documenters. It invokes a Documenter on running. After the processing,
    it parses and returns the generated content by Documenter.
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
                % (self.name, exc)
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
        for fn in params.record_dependencies:
            self.state.document.settings.record_dependencies.add(fn)

        result = parse_generated_content(self.state, params.result, documenter)
        return result


class HyDocumenter(PyDocumenter):
    domain = "hy"

    def parse_name(self) -> bool:
        try:
            explicit_modname, path, base, args, retann = match_hy_sig(self.name)
        except AttributeError:
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
            retann, args = signature(
                self.object,
                bound_method=isinstance(self, (HyMethodDocumenter, HyClassDocumenter)),
                macro=isinstance(self, HyMacroDocumenter),
            )
        except Exception as exc:
            logger.warning(
                ("error while formatting arguments for %s: %s"),
                self.fullname,
                exc,
            )
            args = None

        self.retann = retann
        if args is not None:
            return f" {args}"
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
        prefix = f".. {domain}:{directive}:: "
        for i, sig_line in enumerate(sig.split("\n")):
            if sig:
                retann = getattr(self, "retann", None)
                self.add_line(
                    f"{prefix}({retann + ' ' if retann else ''}{name}{sig_line})",
                    sourcename,
                )
            else:
                self.add_line(f"{prefix}{name}{sig_line}", sourcename)

            if i == 0:
                prefix = " " * len(prefix)

        if self.options.noindex:
            self.add_line("   :noindex:", sourcename)
        if self.objpath:
            # Be explicit about the module, this is necessary since .. class::
            # etc. don't support a prepended module name
            self.add_line("   :module: %s" % self.modname, sourcename)

    def document_members(self, all_members=False):
        """Generate reST for member documentation.
        If *all_members* is True, do all members, else those given by
        *self.options.members*.
        """
        # set current namespace for finding members
        self.env.temp_data["autodoc:module"] = self.modname
        if self.objpath:
            self.env.temp_data["autodoc:class"] = self.objpath[0]

        want_all = (
            all_members
            or self.options.inherited_members
            or (self.options.members is ALL and self.options.macros is ALL)
        )
        # find out which members are documentable
        members_check_module, members = self.get_object_members(want_all)

        # document non-skipped members
        memberdocumenters = []
        wanted_members = self.filter_members(members, want_all)
        # module_macros = [
        #     member for member in members if getattr(member, "_hy_macro", False)
        # ]
        for mname, member, isattr in wanted_members:
            classes = [
                cls
                for cls in self.documenters.values()
                if cls.can_document_member(member, mname, isattr, self)
            ]
            if not classes:
                # don't know how to document this member
                continue
            # prefer the documenter with the highest priority
            classes.sort(key=lambda cls: cls.priority)
            # give explicitly separated module name, so that members
            # of inner classes can be documented
            full_mname = self.modname + "::" + ".".join(self.objpath + [mname])
            documenter = classes[-1](self.directive, full_mname, self.indent)
            memberdocumenters.append((documenter, isattr))

        member_order = self.options.member_order or self.config.autodoc_member_order
        memberdocumenters = self.sort_members(memberdocumenters, member_order)

        for documenter, isattr in memberdocumenters:
            documenter.generate(
                all_members=True,
                real_modname=self.real_modname,
                check_module=members_check_module and not isattr,
            )

        # reset current objects
        self.env.temp_data["autodoc:module"] = None
        self.env.temp_data["autodoc:class"] = None

    def get_object_members(self, want_all: bool) -> tuple[bool, list[ObjectMember]]:
        return (False, [])


class HyModuleDocumenter(HyDocumenter, PyModuleDocumenter):
    option_spec = PyModuleDocumenter.option_spec.copy()
    option_spec.update({"macros": members_option, "readers": members_option})

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror)

        try:
            if not self.options.ignore_module_all:
                self.__all__ = getall(self.object)
        except AttributeError as exc:
            # __all__ raises an error.
            logger.warning(
                __("%s.__all__ raises an error. Ignored: %r"),
                (self.fullname, exc),
                # type="autodoc",
            )
        except ValueError as exc:
            # invalid __all__ found.
            logger.warning(
                __(
                    "__all__ should be a list of strings, not %r "
                    "(in module %s) -- ignoring __all__"
                )
                % (exc.args[0], self.fullname),
                # type="autodoc",
            )

        return ret

    def get_object_members(self, want_all: bool):
        if want_all:
            members = get_module_members(self.object)
            members = [
                member for member in members if not member[0].startswith("-hy-anon-var")
            ]
            if not self.__all__:
                # for implicit module members, check __module__ to avoid
                # documenting imported objects
                return True, members
            else:
                ret = []
                for name, value in members:
                    is_macro = getattr(value, "_hy_macro", False)

                    if (hy.mangle(name) in self.__all__) or (
                        is_macro and self.options.macros
                    ):
                        ret.append(ObjectMember(name, value))
                    else:
                        ret.append(ObjectMember(name, value, skipped=True))

                return False, ret
        else:
            memberlist = (
                dir(self.object)
                if self.options.members is ALL
                else (self.options.members or [])
            )
            memberlist = [
                hy.unmangle(member)
                for member in memberlist
                if not member.startswith("_hy_anon_var")
                and not (
                    self.options.members is ALL
                    and hasattr(self.object, "__all__")
                    and member not in self.object.__all__
                )
            ]
            logger.debug(memberlist)
            member_ret = []
            for name in memberlist:
                try:
                    value = safe_getattr(self.object, hy.mangle(name))
                    member_ret.append(ObjectMember(name, value))
                except AttributeError:
                    logger.warning(
                        __(
                            "missing attribute mentioned in :members: option: "
                            "module %s, attribute %s"
                        )
                        % (safe_getattr(self.object, "__name__", "???"), name),
                        # type="autodoc",
                    )
            macro_ret = []
            for option, module_attr in (
                ("macros", "_hy_macros"),
                ("readers", "_hy_reader_macros"),
            ):
                macromembers = (
                    safe_getattr(self.object, module_attr, {}).keys()
                    if getattr(self.options, option) is ALL
                    else getattr(self.options, option) or []
                )
                macros = safe_getattr(self.object, module_attr, {})
                for name in macromembers:
                    macro_obj = macros.get(
                        hy.mangle(name) if option != "readers" else name
                    )
                    if macro_obj:
                        setattr(
                            macro_obj,
                            "_hy_reader_macro" if option == "readers" else "_hy_macro",
                            True,
                        )
                        macro_ret.append(ObjectMember(name, macro_obj))
                    else:
                        logger.warning(
                            __(
                                "missing macro mentioned in :%s: option: "
                                "module %s, attribute %s"
                            )
                            % (
                                option,
                                safe_getattr(self.object, "__name__", "???"),
                                name,
                            ),
                            # type="autodoc",
                        )

            return False, member_ret + macro_ret


class HyFunctionDocumenter(HyDocumenter, PyFunctionDocumenter):
    objtype = "function"
    member_order = 30
    priority = 1

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return is_hy(member, membername, parent) and super().can_document_member(
            member, membername, isattr, parent
        )

    def add_directive_header(self, sig: str) -> None:
        sourcename = self.get_sourcename()
        super().add_directive_header(sig)

        if inspect.iscoroutinefunction(self.object):
            self.add_line("   :async:", sourcename)


class HyMacroDocumenter(HyFunctionDocumenter):
    objtype = "macro"
    member_order = 30
    priority = 3  # Above regular function documenter

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return super().can_document_member(
            member, membername, isattr, parent
        ) and getattr(member, "_hy_macro", False)

    def import_object(self, raiseerror: bool = False) -> bool:
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.
        Returns True if successful, False if an error occurred.
        """
        with mock(self.config.autodoc_mock_imports):
            try:
                ret = import_object(
                    self.modname,
                    self.objpath,
                    self.objtype,
                    attrgetter=self.get_attr,
                    warningiserror=self.config.autodoc_warningiserror,
                    macro=True,
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


class HyTagDocumenter(HyFunctionDocumenter):
    objtype = "tag"
    member_order = 30
    priority = 3  # Above regular function documenter

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return super().can_document_member(
            member, membername, isattr, parent
        ) and getattr(member, "_hy_reader_macro", False)

    def import_object(self, raiseerror: bool = False) -> bool:
        """Import the object given by *self.modname* and *self.objpath* and set
        it as *self.object*.
        Returns True if successful, False if an error occurred.
        """
        with mock(self.config.autodoc_mock_imports):
            try:
                ret = import_object(
                    self.modname,
                    self.objpath,
                    self.objtype,
                    attrgetter=self.get_attr,
                    warningiserror=self.config.autodoc_warningiserror,
                    tag=True,
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


class HyMethodDocumenter(HyDocumenter, PyMethodDocumenter):
    objtype = "method"
    priority = 2

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        return is_hy(member, membername, parent) and super().can_document_member(
            member, membername, isattr, parent
        )

    def format_args(self, **kwargs: Any) -> str:
        return super().format_args(**kwargs)

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)

        sourcename = self.get_sourcename()
        obj = self.parent.__dict__.get(self.object_name, self.object)
        if inspect.isabstractmethod(obj):
            self.add_line("   :abstractmethod:", sourcename)
        if inspect.iscoroutinefunction(obj):
            self.add_line("   :async:", sourcename)
        if inspect.isclassmethod(obj):
            self.add_line("   :classmethod:", sourcename)
        if inspect.isstaticmethod(obj, cls=self.parent, name=self.object_name):
            self.add_line("   :staticmethod:", sourcename)
        if self.analyzer and ".".join(self.objpath) in self.analyzer.finals:
            self.add_line("   :final:", sourcename)


class HyPropertyDocumenter(HyDocumenter, PyPropertyDocumenter):
    objtype = "property"
    diretivetype = "method"
    priority = PyAttributeDocumenter.priority + 2

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        return (
            is_hy(member, membername, parent)
            and inspect.isproperty(member)
            and isinstance(parent, HyClassDocumenter)
        )

    def add_directive_header(self, sig: str) -> None:
        super().add_directive_header(sig)
        sourcename = self.get_sourcename()
        if inspect.isabstractmethod(self.object):
            self.add_line("   :abstractmethod:", sourcename)
        self.add_line("   :property:", sourcename)


class HyDecoratorDocumenter(HyDocumenter, PyDecoratorDocumenter):
    """
    Specialized Documenter subclass for decorator functions.
    """

    objtype = "decorator"

    # must be lower than FunctionDocumenter
    priority = -1

    @classmethod
    def can_document_member(cls, member, membername, isattr, parent):
        return is_hy(member, membername, parent) and super().can_document_member(
            member, membername, isattr, parent
        )

    def format_args(self, **kwargs: Any) -> Any:
        args = super().format_args(**kwargs)
        if "," in args:
            return args
        else:
            return None


class HyClassDocumenter(HyDocumenter, PyClassDocumenter):
    objtype = "class"
    priority = 1

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        return is_hy(member, membername, parent) and super().can_document_member(
            member, membername, isattr, parent
        )

    def import_object(self, raiseerror: bool = False) -> bool:
        ret = super().import_object(raiseerror=raiseerror)

        if ret:
            if hasattr(self.object, "__name__"):
                self.doc_as_attr = self.objpath[-1] != self.object.__name__
            else:
                self.doc_as_attr = True

        return ret


class HyExceptionDocumenter(HyClassDocumenter):
    objtype = "exception"
    member_order = 10
    priority = 11

    @classmethod
    def can_document_member(
        cls, member: Any, membername: str, isattr: bool, parent: Any
    ) -> bool:
        return (
            is_hy(member, membername, parent)
            and isinstance(member, type)
            and issubclass(member, BaseException)
        )

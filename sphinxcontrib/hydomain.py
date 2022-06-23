"""
    sphinxcontrib.hydomain
    ~~~~~~~~~~~~~~~~~~~~~
    The Hy domain.

    Converted from the Python domain created by the Sphinx team
    by Allison Casey

    Original Sphinx Copyright

    :copyright: Copyright 2007-2020 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import ast
import inspect
import logging
import re
import sys
from inspect import Parameter
from typing import Any, Dict, Iterator, List, Tuple, cast

import hy
from docutils import nodes
from docutils.nodes import Element, Node
from sphinx import addnodes
from sphinx.addnodes import desc_signature, pending_xref
from sphinx.application import Sphinx
from sphinx.directives import directives
from sphinx.domains import Domain, ObjType
from sphinx.domains.python import (
    ModuleEntry,
    ObjectEntry,
    PyModule,
    PyObject,
    PythonModuleIndex,
    pairindextypes,
)
from sphinx.environment import BuildEnvironment
from sphinx.locale import _, __
from sphinx.pycode.ast import parse as ast_parse
from sphinx.roles import XRefRole
from sphinx.util.docutils import SphinxDirective
from sphinx.util.inspect import signature_from_ast
from sphinx.util.nodes import make_id, make_refnode

import sphinxcontrib.hy_documenters as doc

# ** Consts
logging.getLogger().setLevel(logging.DEBUG)

hy_sexp_sig_re = re.compile(
    r"""
^\(
    (?:\s*\^(?P<retann>\(.*?\) | .*?)\s+)?     # Optional: return annotation
    (?P<module>[\w.]+::)?                       # Explicit module name
    (?P<classes>.*\.)?                         # Module and/or class name(s)
    (?P<object>.+?) \s*                        # Thing name
    (?:                                        # Arguments/close or just close
      (?:\[(?:\s*(?P<arguments>.*)\s*\]\))?) | # Optional: arguments
      (?:\)))
$
""",
    re.VERBOSE,
)
hy_var_re = re.compile(r"^([\w.]*\.)?(.+?)$")


# ** Node Types
class desc_hyparameterlist(addnodes.desc_parameterlist):
    child_text_separator = " "


class desc_hyparameter(addnodes.desc_parameter):
    ...


class desc_hyannotation(addnodes.desc_annotation):
    def astext(self) -> str:
        return "^" + super().astext()


class desc_hyreturns(addnodes.desc_returns):
    def astext(self) -> str:
        return " -> ^" + super().astext()


# ** Helper methods
def bool_option(arg):
    return True


def hy2py(source: str) -> str:
    hst = hy.read(source)
    pyast = hy.compiler.hy_compile(hst, "__main__").body[1]
    return ast.unparse(pyast)


def signature_from_str(signature: str) -> inspect.Signature:
    # NOTE Likely where the crash on -sentinel bug is happening
    code = "(defn func" + signature + ")"
    hst = hy.read(code)
    module = hy.compiler.hy_compile(hst, "__main__")
    function = cast(ast.FunctionDef, module.body[1])

    return signature_from_ast(function)


def _parse_arglist(arglist: str, env: BuildEnvironment = None):
    params = desc_hyparameterlist(arglist)
    sig = signature_from_str("[%s]" % arglist)
    # first_default = True
    last_kind = None

    for param in sig.parameters.values():
        if param.kind != param.POSITIONAL_ONLY and last_kind == param.POSITIONAL_ONLY:
            # PEP-570: Separator for Positional Only Parameter: /
            params += desc_hyparameter("", "", addnodes.desc_sig_operator("", "/"))
        if param.kind == param.KEYWORD_ONLY and last_kind in (
            param.POSITIONAL_OR_KEYWORD,
            param.POSITIONAL_ONLY,
            None,
        ):
            # PEP-3102: Separator for Keyword Only Parameter: *
            params += desc_hyparameter("", "", addnodes.desc_sig_operator("", "*"))

        node = desc_hyparameter()
        # if param.default is not param.empty and first_default:
        #     params += desc_hyparameter(
        #         "", "", addnodes.desc_sig_operator("", "")
        #     )
        #     first_default = False

        def annotate(param):
            nonlocal node
            if param.annotation is not param.empty:
                children = _parse_annotation(param.annotation, env)
                node += desc_hyannotation(param.annotation, "", *children)
                node += nodes.Text(" ")

        if param.kind == param.VAR_POSITIONAL:
            node += addnodes.desc_sig_operator(" ", "#*")
            node += nodes.Text(" ")
            annotate(param)
            node += addnodes.desc_sig_name("", hy.unmangle(param.name))
        elif param.kind == param.VAR_KEYWORD:
            node += addnodes.desc_sig_operator("", "#**")
            node += nodes.Text(" ")
            annotate(param)
            node += addnodes.desc_sig_name("", hy.unmangle(param.name))
        else:
            annotate(param)
            if param.default is not param.empty:
                node += nodes.Text("[")
            node += addnodes.desc_sig_name("", hy.unmangle(param.name))

        if param.default is not param.empty:
            if param.annotation is not param.empty:
                node += nodes.Text(" ")
                node += addnodes.desc_sig_operator("", " ")
                node += nodes.Text(" ")
            else:
                node += addnodes.desc_sig_operator("", " ")
            node += nodes.inline(
                "", param.default, classes=["default_value"], support_smartquotes=False
            )
            node += nodes.Text("]")
        params += node
        last_kind = param.kind

    if last_kind == Parameter.POSITIONAL_ONLY:
        # PEP-570: Separator for Positional Only Parameter: /
        params += desc_hyparameter("", "", addnodes.desc_sig_operator("", "/"))

    return params


def _pseudo_parse_arglist(signode: desc_signature, arglist: str) -> None:
    """ "Parse" a list of arguments separated by commas.
    Arguments can have "optional" annotations given by enclosing them in
    brackets.  Currently, this will split at any comma, even if it's inside a
    string literal (e.g. default argument value).
    """
    paramlist = desc_hyparameterlist()
    # stack = [paramlist]  # type: List[Element]
    try:
        raise IndexError()
        # for argument in arglist.split(','):
        #     argument = argument.strip()
        #     ends_open = ends_close = 0
        #     while argument.startswith('['):
        #         stack.append(addnodes.desc_optional())
        #         stack[-2] += stack[-1]
        #         argument = argument[1:].strip()
        #     while argument.startswith(']'):
        #         stack.pop()
        #         argument = argument[1:].strip()
        #     while argument.endswith(']') and not argument.endswith('[]'):
        #         ends_close += 1
        #         argument = argument[:-1].strip()
        #     while argument.endswith('['):
        #         ends_open += 1
        #         argument = argument[:-1].strip()
        #     if argument:
        #         stack[-1] += addnodes.desc_parameter(argument, argument)
        #     while ends_open:
        #         stack.append(addnodes.desc_optional())
        #         stack[-2] += stack[-1]
        #         ends_open -= 1
        #     while ends_close:
        #         stack.pop()
        #         ends_close -= 1
        # if len(stack) != 1:
        #     raise IndexError
    except IndexError:
        # if there are too few or too many elements on the stack, just give up
        # and treat the whole argument list as one argument, discarding the
        # already partially populated paramlist node
        paramlist = desc_hyparameterlist()
        paramlist += desc_hyparameter(arglist, arglist)
        signode += paramlist
    else:
        signode += paramlist


def type_to_xref(text: str, env: BuildEnvironment = None) -> addnodes.pending_xref:
    """Convert a type string to a cross reference node."""
    if text == "None":
        reftype = "obj"
    else:
        reftype = "class"

    if env:
        kwargs = {
            "hy:module": env.ref_context.get("hy:module"),
            "hy:class": env.ref_context.get("hy:class"),
        }
    else:
        kwargs = {}

    return pending_xref(
        "", nodes.Text(text), refdomain="hy", reftype=reftype, reftarget=text, **kwargs
    )


def _parse_annotation(annotation: str, env: BuildEnvironment = None) -> List[Node]:
    """Parse type annotation."""

    def unparse(node: ast.AST, isslice=False) -> List[Node]:
        if isinstance(node, ast.Attribute):
            return [nodes.Text(f"{unparse(node.value)[0]}.{node.attr}")]
        elif isinstance(node, ast.Expr):
            return unparse(node.value)
        elif isinstance(node, ast.Index):
            return unparse(node.value)
        elif isinstance(node, ast.List):
            result = [addnodes.desc_sig_punctuation("", "[")]  # type: List[Node]
            for elem in node.elts:
                result.extend(unparse(elem))
                result.append(addnodes.desc_sig_punctuation("", " "))
            result.pop()
            result.append(addnodes.desc_sig_punctuation("", "]"))
            return result
        elif isinstance(node, ast.Module):
            return sum((unparse(e) for e in node.body), [])
        elif isinstance(node, ast.Name):
            return [nodes.Text(node.id)]
        elif isinstance(node, ast.Subscript):
            result = unparse(node.value)
            result = [
                addnodes.desc_sig_punctuation("", "("),
                nodes.Text("get "),
                *result,
                nodes.Text(" "),
            ]
            result.extend(unparse(node.slice, isslice=True))
            addnodes.desc_sig_punctuation("", ")"),
            result.append(addnodes.desc_sig_punctuation("", ")"))
            return result
        elif isinstance(node, ast.Tuple):
            if node.elts:
                result = []
                if not isslice:
                    result.append(addnodes.desc_sig_punctuation("", "(, "))
                if len(node.elts) > 1:
                    result.append(addnodes.desc_sig_punctuation("", "("))
                    result.append(nodes.Text(", "))
                for elem in node.elts:
                    result.extend(unparse(elem))
                    result.append(addnodes.desc_sig_punctuation("", " "))
                if len(node.elts) > 1:
                    result.append(addnodes.desc_sig_punctuation("", ")"))
                result.pop()
                if not isslice:
                    result.append(addnodes.desc_sig_punctuation("", ")"))
            else:
                result = [
                    addnodes.desc_sig_punctuation("", "(,"),
                    addnodes.desc_sig_punctuation("", ")"),
                ]

            return result
        else:
            if sys.version_info >= (3, 6):
                if isinstance(node, ast.Constant):
                    if node.value is Ellipsis:
                        return [addnodes.desc_sig_punctuation("", "...")]
                    else:
                        return [nodes.Text(node.value)]

            if sys.version_info < (3, 8):
                if isinstance(node, ast.Ellipsis):
                    return [addnodes.desc_sig_punctuation("", "...")]
                elif isinstance(node, ast.NameConstant):
                    return [nodes.Text(node.value)]

            raise SyntaxError  # unsupported syntax

    try:
        tree = ast_parse(annotation)
        result = unparse(tree)
        for i, node in enumerate(result):
            if isinstance(node, nodes.Text):
                result[i] = type_to_xref(str(node), env)
        return result
    except SyntaxError:
        return [type_to_xref(annotation, env)]


# ** Objects
class HyXRefRole(XRefRole):
    def process_link(
        self,
        env: BuildEnvironment,
        refnode: Element,
        has_explicit_title: bool,
        title: str,
        target: str,
    ) -> Tuple[str, str]:
        refnode["hy:module"] = env.ref_context.get("hy:module")
        refnode["hy:class"] = env.ref_context.get("hy:class")
        if not has_explicit_title:
            title = title.lstrip(".")  # only has a meaning for the target
            target = target.lstrip("~")  # only has a meaning for the title
            # if the first character is a tilde, don't display the module/class
            # parts of the contents
            if title[0:1] == "~":
                title = title[1:]
                dot = title.rfind(".")
                if dot != -1:
                    title = title[dot + 1 :]
        # if the first character is a dot, search more specific namespaces first
        # else search builtins first
        if target[0:1] == ".":
            target = target[1:]
            refnode["refspecific"] = True
        return title, target


class HyModuleIndex(PythonModuleIndex):
    """
    Index subclass to provide the Python module index.
    """

    localname = _("Hy Module Index")


class HyObject(PyObject):
    def handle_signature(self, sig: str, signode) -> Tuple[str, str]:
        isvar = False
        msexp = hy_sexp_sig_re.match(sig)
        mvar = hy_var_re.match(sig)
        if msexp is not None:
            retann, *prefix, name, arglist = msexp.groups()
            if prefix:
                prefix = ".".join(filter(None, prefix))
            else:
                prefix = None
        elif mvar is not None:
            isvar = True
            prefix, name = mvar.groups()
            retann, arglist = None, None
        else:
            raise ValueError

        # determine module and class name (if applicable), as well as full name
        modname = self.options.get("module", self.env.ref_context.get("hy:module"))
        classname = self.env.ref_context.get("hy:class")
        should_wrap = (
            not isvar or self.objtype in {"function", "method"}
        ) and "property" not in self.options

        if classname:
            add_module = False
            if prefix and (prefix == classname or prefix.startswith(classname + ".")):
                fullname = prefix + name
                # class name is given again in the signature
                prefix = prefix[len(classname) :].lstrip(".")
            elif prefix:
                # class name is given in the signature, but different
                # (shouldn't happen)
                fullname = classname + "." + prefix + name
            else:
                # class name is not given in the signature
                fullname = classname + "." + name
        else:
            add_module = True
            if prefix:
                classname = prefix.rstrip(".")
                fullname = prefix + name
            else:
                classname = ""
                fullname = name

        signode["module"] = modname
        signode["class"] = classname
        signode["fullname"] = fullname

        sig_prefix = self.get_signature_prefix(sig)
        if sig_prefix:
            signode += addnodes.desc_annotation(sig_prefix, sig_prefix)

        if should_wrap:
            signode += addnodes.desc_addname("(", "(")

        if prefix:
            signode += addnodes.desc_addname(prefix, prefix)
        elif add_module and self.env.config.add_module_names:
            if modname and modname != "exceptions":
                # exceptions are a special case, since they are documented in the
                # 'exceptions' module.
                nodetext = modname + "."
                signode += addnodes.desc_addname(nodetext, nodetext)

        signode += addnodes.desc_name(name, name)

        if arglist:
            try:
                signode += _parse_arglist(arglist, self.env)
            except SyntaxError:
                # fallback to parse arglist original parser.
                # it supports to represent optional arguments (ex. "func(foo [, bar])")
                _pseudo_parse_arglist(signode, arglist)
            except NotImplementedError as exc:
                logging.warning("could not parse arglist (%r): %s", exc)
                _pseudo_parse_arglist(signode, arglist)
        else:
            if self.needs_arglist():
                # for callables, add an empty parameter list
                signode += desc_hyparameterlist()

        anno = self.options.get("annotation")
        if anno:
            signode += addnodes.desc_annotation(" " + anno, " " + anno)

        if should_wrap:
            signode += addnodes.desc_addname(")", ")")

        if retann:
            pyretann = hy2py(retann)
            children = _parse_annotation(pyretann, self.env)
            signode += nodes.Text(" ")
            signode += desc_hyreturns(pyretann, "", *children)

        return fullname, prefix

    def add_target_and_index(self, name_cls: Tuple[str, str], sig: str, signode):
        modname = self.options.get("module", self.env.ref_context.get("hy:module"))
        fullname = (modname + "." if modname else "") + name_cls[0]
        # node_id = make_id(self.env, self.state.document, "", fullname)
        node_id = fullname
        signode["ids"].append(node_id)

        self.state.document.note_explicit_target(signode)

        domain = cast(HyDomain, self.env.get_domain("hy"))
        domain.note_object(fullname, self.objtype, node_id, location=signode)

        if "noindexentry" not in self.options:
            indextext = self.get_index_text(modname, name_cls)
            if indextext:
                self.indexnode["entries"].append(
                    ("single", indextext, node_id, "", None)
                )

    def before_content(self) -> None:
        """Handle object nesting before content
        :hy:class:`PyObject` represents Python language constructs. For
        constructs that are nestable, such as a Python classes, this method will
        build up a stack of the nesting hierarchy so that it can be later
        de-nested correctly, in :hy:meth:`after_content`.
        For constructs that aren't nestable, the stack is bypassed, and instead
        only the most recent object is tracked. This object prefix name will be
        removed with :hy:meth:`after_content`.
        """
        prefix = None
        if self.names:
            # fullname and name_prefix come from the `handle_signature` method.
            # fullname represents the full object name that is constructed using
            # object nesting and explicit prefixes. `name_prefix` is the
            # explicit prefix given in a signature
            (fullname, name_prefix) = self.names[-1]
            if self.allow_nesting:
                prefix = fullname
            elif name_prefix:
                prefix = name_prefix.strip(".")
        if prefix:
            self.env.ref_context["hy:class"] = prefix
            if self.allow_nesting:
                classes = self.env.ref_context.setdefault("hy:classes", [])
                classes.append(prefix)
        if "module" in self.options:
            modules = self.env.ref_context.setdefault("hy:modules", [])
            modules.append(self.env.ref_context.get("hy:module"))
            self.env.ref_context["hy:module"] = self.options["module"]

    def after_content(self) -> None:
        """Handle object de-nesting after content
        If this class is a nestable object, removing the last nested class prefix
        ends further nesting in the object.
        If this class is not a nestable object, the list of classes should not
        be altered as we didn't affect the nesting levels in
        :hy:meth:`before_content`.
        """
        classes = self.env.ref_context.setdefault("hy:classes", [])
        if self.allow_nesting:
            try:
                classes.pop()
            except IndexError:
                pass
        self.env.ref_context["hy:class"] = classes[-1] if len(classes) > 0 else None
        if "module" in self.options:
            modules = self.env.ref_context.setdefault("hy:modules", [])
            if modules:
                self.env.ref_context["hy:module"] = modules.pop()
            else:
                self.env.ref_context.pop("hy:module")


class HyFunction(HyObject):
    option_spec = HyObject.option_spec.copy()
    option_spec.update({"async": directives.flag})

    def get_index_text(self, modname: str, name: Tuple[str, str]) -> str:
        return None

    def needs_arglist(self):
        return True

    def get_signature_prefix(self, sig: str):
        if "async" in self.options:
            return "async "
        else:
            return ""

    def add_target_and_index(
        self, name: Any, sig: str, signode: desc_signature
    ) -> None:
        super().add_target_and_index(name, sig, signode)
        if "noindexentry" not in self.options:
            modname = self.options.get("module", self.env.ref_context.get("hy:module"))
            node_id = signode["ids"][0]

            name, cls = name
            if modname:
                text = _("%s() (in module %s)") % (name, modname)
                self.indexnode["entries"].append(("single", text, node_id, "", None))
            else:
                text = "{}; {}()".format(pairindextypes["builtin"], name)
                self.indexnode["entries"].append(("pair", text, node_id, "", None))


class HyMacro(HyFunction):
    def get_signature_prefix(self, sig: str) -> str:
        return self.objtype


class HyTag(HyFunction):
    def get_signature_prefix(self, sig: str) -> str:
        return self.objtype + " macro"

    def add_target_and_index(self, name_cls: Tuple[str, str], sig: str, signode):
        modname = self.options.get("module", self.env.ref_context.get("hy:module"))
        fullname = (modname + "." if modname else "") + name_cls[0]
        # node_id = make_id(self.env, self.state.document, "", fullname)
        node_id = fullname
        signode["ids"].append(node_id)

        self.state.document.note_explicit_target(signode)

        domain = cast(HyDomain, self.env.get_domain("hy"))
        domain.note_object(fullname, self.objtype, node_id, location=signode)

        if "noindexentry" not in self.options:
            indextext = self.get_index_text(modname, name_cls)
            if indextext:
                self.indexnode["entries"].append(
                    ("single", indextext, node_id, "", None)
                )

    def handle_signature(self, sig: str, signode) -> Tuple[str, str]:
        msexp = hy_sexp_sig_re.match(sig)
        mvar = hy_var_re.match(sig)
        if msexp is not None:
            prefix, name, retann, arglist = msexp.groups()
        elif mvar is not None:
            prefix, name = mvar.groups()
            retann, arglist = None, None
        else:
            raise ValueError

        # determine module and class name (if applicable), as well as full name
        modname = self.options.get("module", self.env.ref_context.get("hy:module"))
        classname = self.env.ref_context.get("hy:class")

        if classname:
            add_module = False
            if prefix and (prefix == classname or prefix.startswith(classname + ".")):
                fullname = prefix + name
                # class name is given again in the signature
                prefix = prefix[len(classname) :].lstrip(".")
            elif prefix:
                # class name is given in the signature, but different
                # (shouldn't happen)
                fullname = classname + "." + prefix + name
            else:
                # class name is not given in the signature
                fullname = classname + "." + name
        else:
            add_module = True
            if prefix:
                classname = prefix.rstrip(".")
                fullname = prefix + name
            else:
                classname = ""
                fullname = name

        signode["module"] = modname
        signode["class"] = classname
        signode["fullname"] = fullname

        sig_prefix = self.get_signature_prefix(sig)
        if sig_prefix:
            signode += addnodes.desc_annotation(sig_prefix, sig_prefix)

        # signode += addnodes.desc_addname("#", "#")

        if add_module and self.env.config.add_module_names:
            if modname and modname != "exceptions":
                # exceptions are a special case, since they are documented in the
                # 'exceptions' module.
                nodetext = modname + "."
                signode += addnodes.desc_addname(nodetext, nodetext)
        signode += addnodes.desc_name(name, name)

        if prefix:
            signode += addnodes.desc_addname(prefix, prefix)

        if retann:
            pyretann = hy2py(retann)
            children = _parse_annotation(pyretann, self.env)
            signode += nodes.Text(" ")
            signode += desc_hyannotation(pyretann, "", *children)

        if arglist:
            try:
                if arglist.startswith("&name"):
                    arglist = arglist[len("&name") :]
                signode += _parse_arglist(arglist, self.env)
            except NotImplementedError as exc:
                logging.warning("could not parse arglist (%r): %s", exc)
                # _pseudo_parse_arglist(signode, arglist)
        else:
            if self.needs_arglist():
                # for callables, add an empty parameter list
                signode += desc_hyparameterlist()

        anno = self.options.get("annotation")
        if anno:
            signode += addnodes.desc_annotation(" " + anno, " " + anno)

        return fullname, prefix


class HyVariable(HyObject):
    option_spec = HyObject.option_spec.copy()

    option_spec.update(
        {
            "type": directives.unchanged,
            "value": directives.unchanged,
        }
    )

    def handle_signature(self, sig: str, signode: desc_signature) -> Tuple[str, str]:
        fullname, prefix = super().handle_signature(sig, signode)

        typ = self.options.get("type")
        if typ:
            annotations = _parse_annotation(typ, self.env)
            signode += desc_hyannotation(typ, "", nodes.Text(": "), *annotations)

        value = self.options.get("value")
        if value:
            signode += desc_hyannotation(value, " = " + value)

        return fullname, prefix

    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
        name, cls = name_cls
        if modname:
            return _("%s (in module %s)") % (name, modname)
        else:
            return _("%s (built-in variable)") % name


class HyModule(PyModule):
    def run(self) -> List[Node]:
        domain = cast(HyDomain, self.env.get_domain("hy"))

        modname = self.arguments[0].strip()
        noindex = "noindex" in self.options
        self.env.ref_context["hy:module"] = modname
        ret = []  # type: List[Node]
        if not noindex:
            # note module to the domain
            node_id = make_id(self.env, self.state.document, "module", modname)
            target = nodes.target("", "", ids=[node_id], ismod=True)
            self.set_source_info(target)

            # Assign old styled node_id not to break old hyperlinks (if possible)
            # Note: Will removed in Sphinx-5.0  (RemovedInSphinx50Warning)
            old_node_id = self.make_old_id(modname)
            if node_id != old_node_id and old_node_id not in self.state.document.ids:
                target["ids"].append(old_node_id)

            self.state.document.note_explicit_target(target)

            domain.note_module(
                modname,
                node_id,
                self.options.get("synopsis", ""),
                self.options.get("platform", ""),
                "deprecated" in self.options,
            )
            domain.note_object(modname, "module", node_id, location=target)

            # the platform and synopsis aren't printed; in fact, they are only
            # used in the modindex currently
            ret.append(target)
            indextext = "{}; {}".format(pairindextypes["module"], modname)
            inode = addnodes.index(entries=[("pair", indextext, node_id, "", None)])
            ret.append(inode)
        return ret


class HyClass(HyObject):
    """
    Description of a class-like object (classes, interfaces, exceptions).
    """

    option_spec = HyObject.option_spec.copy()
    option_spec.update(
        {
            "final": directives.flag,
        }
    )

    allow_nesting = True

    def get_signature_prefix(self, sig: str) -> str:
        if "final" in self.options:
            return "final %s " % self.objtype
        else:
            return "%s " % self.objtype

    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
        if self.objtype == "class":
            if not modname:
                return _("%s (built-in class)") % name_cls[0]
            return _("%s (class in %s)") % (name_cls[0], modname)
        elif self.objtype == "exception":
            return name_cls[0]
        else:
            return ""


class HyMethod(HyObject):
    """Description of a method."""

    option_spec = PyObject.option_spec.copy()
    option_spec.update(
        {
            "abstractmethod": directives.flag,
            "async": directives.flag,
            "classmethod": directives.flag,
            "final": directives.flag,
            "property": directives.flag,
            "staticmethod": directives.flag,
        }
    )

    def needs_arglist(self) -> bool:
        if "property" in self.options:
            return False
        else:
            return True

    def get_signature_prefix(self, sig: str) -> str:
        prefix = []
        if "final" in self.options:
            prefix.append("final")
        if "abstractmethod" in self.options:
            prefix.append("abstract")
        if "async" in self.options:
            prefix.append("async")
        if "classmethod" in self.options:
            prefix.append("classmethod")
        if "property" in self.options:
            prefix.append("property")
        if "staticmethod" in self.options:
            prefix.append("static")

        if prefix:
            return " ".join(prefix) + " "
        else:
            return ""

    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
        name, cls = name_cls
        try:
            clsname, methname = name.rsplit(".", 1)
            if modname and self.env.config.add_module_names:
                clsname = ".".join([modname, clsname])
        except ValueError:
            if modname:
                return _("%s() (in module %s)") % (name, modname)
            else:
                return "%s()" % name

        if "classmethod" in self.options:
            return _("%s() (%s class method)") % (methname, clsname)
        elif "property" in self.options:
            return _("%s() (%s property)") % (methname, clsname)
        elif "staticmethod" in self.options:
            return _("%s() (%s static method)") % (methname, clsname)
        else:
            return _("%s() (%s method)") % (methname, clsname)


class HyCurrentModule(SphinxDirective):
    """
    This directive is just to tell Sphinx that we're documenting
    stuff in module foo, but links to module foo won't lead here.
    """

    has_content = False
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {}  # type: Dict

    def run(self) -> List[Node]:
        modname = self.arguments[0].strip()
        if modname == "None":
            self.env.ref_context.pop("hy:module", None)
        else:
            self.env.ref_context["hy:module"] = modname
        return []


class HyClassMethod(HyMethod):
    """Description of a classmethod."""

    option_spec = HyObject.option_spec.copy()

    def run(self) -> List[Node]:
        self.name = "hy:method"
        self.options["classmethod"] = True

        return super().run()


class HyStaticMethod(HyMethod):
    """Description of a classmethod."""

    option_spec = HyObject.option_spec.copy()

    def run(self) -> List[Node]:
        self.name = "hy:method"
        self.options["staticmethod"] = True

        return super().run()


class HyAttribute(HyObject):
    """Description of an attribute."""

    option_spec = PyObject.option_spec.copy()
    option_spec.update(
        {
            "type": directives.unchanged,
            "value": directives.unchanged,
        }
    )

    def handle_signature(self, sig: str, signode: desc_signature) -> Tuple[str, str]:
        fullname, prefix = super().handle_signature(sig, signode)

        typ = self.options.get("type")
        if typ:
            annotations = _parse_annotation(typ, self.env)
            signode += addnodes.desc_annotation(typ, "", nodes.Text(": "), *annotations)

        value = self.options.get("value")
        if value:
            signode += addnodes.desc_annotation(value, " = " + value)

        return fullname, prefix

    def get_index_text(self, modname: str, name_cls: Tuple[str, str]) -> str:
        name, cls = name_cls
        try:
            clsname, attrname = name.rsplit(".", 1)
            if modname and self.env.config.add_module_names:
                clsname = ".".join([modname, clsname])
        except ValueError:
            if modname:
                return _("%s (in module %s)") % (name, modname)
            else:
                return name

        return _("%s (%s attribute)") % (attrname, clsname)


class HyDecoratorFunction(HyFunction):
    """Description of a decorator."""

    def run(self) -> List[Node]:
        # a decorator function is a function after all
        self.name = "hy:function"
        return super().run()

    def handle_signature(self, sig: str, signode: desc_signature) -> Tuple[str, str]:
        ret = super().handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_addname("#@", "#@"))
        return ret

    def needs_arglist(self) -> bool:
        return False


class HyDecoratorMethod(HyMethod):
    """Description of a decoratormethod."""

    def run(self) -> List[Node]:
        self.name = "hy:method"
        return super().run()

    def handle_signature(self, sig: str, signode: desc_signature) -> Tuple[str, str]:
        ret = super().handle_signature(sig, signode)
        signode.insert(0, addnodes.desc_addname("#@", "#@"))
        return ret

    def needs_arglist(self) -> bool:
        return False


class HyDomain(Domain):
    name = "hy"
    label = "HY"

    object_types = {
        "function": ObjType(_("function"), "func", "obj"),
        "macro": ObjType(_("macro"), "func", "obj"),
        "tag": ObjType(_("tag"), "func", "obj"),
        "data": ObjType(_("data"), "data", "obj"),
        "class": ObjType(_("class"), "class", "exc", "obj"),
        "exception": ObjType(_("exception"), "exc", "class", "obj"),
        "method": ObjType(_("method"), "meth", "obj"),
        "classmethod": ObjType(_("class method"), "meth", "obj"),
        "staticmethod": ObjType(_("static method"), "meth", "obj"),
        "attribute": ObjType(_("attribute"), "attr", "obj"),
        "module": ObjType(_("module"), "mod", "obj"),
    }

    directives = {
        "function": HyFunction,
        "macro": HyMacro,
        "tag": HyTag,
        "data": HyVariable,
        "module": HyModule,
        "class": HyClass,
        "exception": HyClass,
        "method": HyMethod,
        "classmethod": HyClassMethod,
        "staticmethod": HyStaticMethod,
        "attribute": HyAttribute,
        "currentmodule": HyCurrentModule,
        "decorator": HyDecoratorFunction,
        "decoratormethod": HyDecoratorMethod,
    }

    roles = {
        "func": HyXRefRole(),
        "macro": HyXRefRole(),
        "tag": HyXRefRole(),
        "data": HyXRefRole(),
        "class": HyXRefRole(),
        "meth": HyXRefRole(),
        "attr": HyXRefRole(),
        "exc": HyXRefRole(),
        "const": HyXRefRole(),
        "mod": HyXRefRole(),
        "obj": HyXRefRole(),
    }

    initial_data = {"objects": {}, "modules": {}}

    indices = [HyModuleIndex]

    @property
    def objects(self):
        return self.data.setdefault("objects", {})

    def note_object(
        self,
        name: str,
        objtype: str,
        node_id: str,
        location=None,
        aliased: bool = False,
    ) -> None:
        if name in self.objects:
            other = self.objects[name]
            logging.warning(
                __(
                    "duplicate object description of %s, "
                    "other instance in %s, use :noindex: for one of them"
                ),
                name,
                other.docname,
            )
        self.objects[name] = ObjectEntry(self.env.docname, node_id, objtype, aliased)

    @property
    def modules(self) -> Dict[str, ModuleEntry]:
        return self.data.setdefault("modules", {})  # modname -> ModuleEntry

    def note_module(
        self, name: str, node_id: str, synopsis: str, platform: str, deprecated: bool
    ) -> None:
        """Note a python module for cross reference.
        .. versionadded:: 2.1
        """
        self.modules[name] = ModuleEntry(
            self.env.docname, node_id, synopsis, platform, deprecated
        )

    def clear_doc(self, docname: str) -> None:
        for fullname, obj in list(self.objects.items()):
            if obj.docname == docname:
                del self.objects[fullname]
        for modname, mod in list(self.modules.items()):
            if mod.docname == docname:
                del self.modules[modname]

    def merge_domaindata(self, docnames: List[str], otherdata: Dict) -> None:
        # XXX check duplicates?
        for fullname, obj in otherdata["objects"].items():
            if obj.docname in docnames:
                self.objects[fullname] = obj
        for modname, mod in otherdata["modules"].items():
            if mod.docname in docnames:
                self.modules[modname] = mod

    def find_obj(
        self,
        env: BuildEnvironment,
        modname: str,
        classname: str,
        name: str,
        type: str,
        searchmode: int = 0,
    ) -> List[Tuple[str, ObjectEntry]]:
        """Find a Python object for "name", perhaps using the given module
        and/or classname.  Returns a list of (name, object entry) tuples.
        """
        # skip parens
        if name[-2:] == "()":
            name = name[:-2]

        if not name:
            return []

        matches = []  # type: List[Tuple[str, ObjectEntry]]

        newname = None
        if searchmode == 1:
            if type is None:
                objtypes = list(self.object_types)
            else:
                objtypes = self.objtypes_for_role(type)
            if objtypes is not None:
                if modname and classname:
                    fullname = modname + "." + classname + "." + name
                    if (
                        fullname in self.objects
                        and self.objects[fullname].objtype in objtypes
                    ):
                        newname = fullname
                if not newname:
                    if (
                        modname
                        and modname + "." + name in self.objects
                        and self.objects[modname + "." + name].objtype in objtypes
                    ):
                        newname = modname + "." + name
                    elif (
                        name in self.objects and self.objects[name].objtype in objtypes
                    ):
                        newname = name
                    else:
                        # "fuzzy" searching mode
                        searchname = "." + name
                        matches = [
                            (oname, self.objects[oname])
                            for oname in self.objects
                            if oname.endswith(searchname)
                            and self.objects[oname].objtype in objtypes
                        ]
        else:
            # NOTE: searching for exact match, object type is not considered
            if name in self.objects:
                newname = name
            elif type == "mod":
                # only exact matches allowed for modules
                return []
            elif classname and classname + "." + name in self.objects:
                newname = classname + "." + name
            elif modname and modname + "." + name in self.objects:
                newname = modname + "." + name
            elif (
                modname
                and classname
                and modname + "." + classname + "." + name in self.objects
            ):
                newname = modname + "." + classname + "." + name
        if newname is not None:
            matches.append((newname, self.objects[newname]))
        return matches

    def resolve_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder,
        type: str,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> Element:
        modname = node.get("hy:module")
        clsname = node.get("hy:class")
        searchmode = 1 if node.hasattr("refspecific") else 0
        matches = self.find_obj(env, modname, clsname, target, type, searchmode)

        if not matches and type == "attr":
            # fallback to meth (for property)
            matches = self.find_obj(env, modname, clsname, target, "meth", searchmode)

        if not matches:
            return None
        elif len(matches) > 1:
            logging.warning(
                __("more than one target found for cross-reference %r: %s"),
                target,
                ", ".join(match[0] for match in matches),
            )
        name, obj = matches[0]

        if obj[2] == "module":
            return self._make_module_refnode(builder, fromdocname, name, contnode)
        else:
            return make_refnode(builder, fromdocname, obj[0], obj[1], contnode, name)

    def resolve_any_xref(
        self,
        env: BuildEnvironment,
        fromdocname: str,
        builder,
        target: str,
        node: pending_xref,
        contnode: Element,
    ) -> List[Tuple[str, Element]]:
        modname = node.get("hy:module")
        clsname = node.get("hy:class")
        results = []  # type: List[Tuple[str, Element]]

        # always search in "refspecific" mode with the :any: role
        matches = self.find_obj(env, modname, clsname, target, None, 1)
        for name, obj in matches:
            if obj[2] == "module":
                results.append(
                    (
                        "hy:mod",
                        self._make_module_refnode(builder, fromdocname, name, contnode),
                    )
                )
            else:
                results.append(
                    (
                        "hy:" + self.role_for_objtype(obj[2]),
                        make_refnode(
                            builder, fromdocname, obj[0], obj[1], contnode, name
                        ),
                    )
                )
        return results

    def _make_module_refnode(
        self, builder, fromdocname: str, name: str, contnode: Node
    ) -> Element:
        # get additional info for modules
        module = self.modules[name]
        title = name
        if module.synopsis:
            title += ": " + module.synopsis
        if module.deprecated:
            title += _(" (deprecated)")
        if module.platform:
            title += " (" + module.platform + ")"
        return make_refnode(
            builder, fromdocname, module.docname, module.node_id, contnode, title
        )

    def get_objects(self) -> Iterator[Tuple[str, str, str, str, str, int]]:
        for modname, mod in self.modules.items():
            yield (modname, modname, "module", mod.docname, mod.node_id, 0)
        for refname, obj in self.objects.items():
            if obj.objtype != "module":  # modules are already handled
                yield (refname, refname, obj.objtype, obj.docname, obj.node_id, 1)

    def get_full_qualified_name(self, node: Element) -> str:
        modname = node.get("hy:module")
        clsname = node.get("hy:class")
        target = node.get("reftarget")
        if target is None:
            return None
        else:
            return ".".join(filter(None, [modname, clsname, target]))


# ** Node Renderers
def v_hyreturns(self, node):
    self.body.append("  → ^")
    # self.first_param = True
    # if len(node):
    #     self.body.append(" ")
    #     # self.body.append("[")
    # self.param_separator = node.child_text_separator


def d_hyreturns(self, node):
    pass


def v_hyparameterlist(self, node):
    self.first_param = True
    if len(node):
        self.body.append(" ")
        # self.body.append("[")
    self.param_separator = node.child_text_separator


def d_hyparameterlist(self, node):
    pass
    # if len(node):
    #     self.body.append("]")


def v_html_hyparameter(self, node):
    if self.body[-1] != ("["):
        self.body.append(self.param_separator)
    if node.hasattr("lambda_keyword"):
        self.body.append('<em class="lambda_keyword text-muted">')
    elif node.hasattr("keyword"):
        self.body.append('<em class="keyword text-muted">')
    elif not node.hasattr("noemph"):
        self.body.append("<em>")


def d_html_hyparameter(self, node):
    if node.hasattr("lambda_keyword"):
        self.body.append("</em>")
    elif node.hasattr("keyword"):
        self.body.append("</em>")
    elif not node.hasattr("noemph"):
        self.body.append("</em>")


def v_html_hyannotation(self, node):
    self.param_separator = self.param_separator.replace(",", "")
    if self.body[-2] != ("["):
        self.body.append(self.param_separator)
    if node.hasattr("lambda_keyword"):
        self.body.append('<em class="lambda_keyword text-muted">^')
    elif node.hasattr("keyword"):
        self.body.append('<em class="keyword text-muted">^')
    elif not node.hasattr("noemph"):
        self.body.append("<em>^")


def d_html_hyannotation(self, node):
    if node.hasattr("lambda_keyword"):
        self.body.append("</em>")
    elif node.hasattr("keyword"):
        self.body.append("</em>")
    elif not node.hasattr("noemph"):
        self.body.append("</em>")


# ** Register with Sphinx
def setup(app: Sphinx):
    app.add_domain(HyDomain)
    app.add_node(desc_hyreturns, html=(v_hyreturns, d_hyreturns))
    app.add_node(desc_hyparameterlist, html=(v_hyparameterlist, d_hyparameterlist))
    app.add_node(desc_hyparameter, html=(v_html_hyparameter, d_html_hyparameter))
    app.add_node(desc_hyannotation, html=(v_html_hyannotation, d_html_hyannotation))

    app.registry.add_documenter("hy:function", doc.HyFunctionDocumenter)
    app.add_directive_to_domain("hy", "autofunction", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:macro", doc.HyMacroDocumenter)
    app.add_directive_to_domain("hy", "automacro", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:tag", doc.HyTagDocumenter)
    app.add_directive_to_domain("hy", "autotag", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:method", doc.HyMethodDocumenter)
    app.add_directive_to_domain("hy", "automethod", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:property", doc.HyPropertyDocumenter)
    app.add_directive_to_domain("hy", "autoproperty", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:decorator", doc.HyDecoratorDocumenter)
    app.add_directive_to_domain("hy", "autodecorator", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:module", doc.HyModuleDocumenter)
    app.add_directive_to_domain("hy", "automodule", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:class", doc.HyClassDocumenter)
    app.add_directive_to_domain("hy", "autoclass", doc.HyAutodocDirective)

    app.registry.add_documenter("hy:exception", doc.HyExceptionDocumenter)
    app.add_directive_to_domain("hy", "autoexception", doc.HyAutodocDirective)

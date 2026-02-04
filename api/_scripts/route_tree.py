"""Report FastAPI route tree."""

from __future__ import annotations

import argparse
import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.routing import APIRoute

HTTP_METHOD_DECORATORS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
    "trace",
    "api_route",
}

DEFAULT_IGNORED_DEPS = {
    "get_db",
    "get_project_db",
    "get_project_api",
    "get_async_db",
    "get_user_data_async",
}


@dataclass(frozen=True)
class RouterId:
    """Unique router identifier."""

    module: str
    name: str


@dataclass(frozen=True)
class RouterInfo:
    """Router metadata."""

    router_id: RouterId
    prefix: str
    dependencies: list[str]
    file_path: str


@dataclass(frozen=True)
class IncludeEdge:
    """Router include edge."""

    parent: RouterId
    child: RouterId
    prefix: str
    dependencies: list[str]
    file_path: str


@dataclass(frozen=True)
class EndpointInfo:
    """Endpoint metadata."""

    router_id: RouterId | None
    decorator_deps: list[str]
    param_deps: list[str]
    file_path: str


def module_path_from_file(*, file_path: Path, api_root: Path) -> str:
    """Convert a file path to a module path."""
    rel_path = file_path.relative_to(api_root)
    return ".".join(rel_path.with_suffix("").parts)


def resolve_relative_module(
    *, current_module: str, level: int, module: str | None
) -> str:
    """Resolve relative import modules to absolute module path."""
    if level <= 0:
        return module or ""
    current_parts = current_module.split(".")
    base_parts = current_parts[:-level]
    if module:
        return ".".join(base_parts + module.split("."))
    return ".".join(base_parts)


def expr_to_str(*, node: ast.AST, source: str) -> str:
    """Convert an AST node to a readable string."""
    segment = ast.get_source_segment(source, node)
    if segment:
        return segment.strip()
    return ast.unparse(node).strip()


def is_depends_call(*, node: ast.AST) -> bool:
    """Return True if node is a Depends(...) call."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name):
        return func.id == "Depends"
    if isinstance(func, ast.Attribute):
        return func.attr == "Depends"
    return False


def extract_dep_from_call(*, node: ast.Call, source: str) -> str:
    """Extract the dependency expression from Depends(...) call."""
    if not node.args:
        return "Depends(<missing>)"
    return expr_to_str(node=node.args[0], source=source)


def extract_dep_strings(*, node: ast.AST, source: str) -> list[str]:
    """Extract dependency strings from dependencies=... nodes."""
    deps: list[str] = []
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            deps.extend(extract_dep_strings(node=elt, source=source))
        return deps
    if isinstance(node, ast.Call) and is_depends_call(node=node):
        deps.append(extract_dep_from_call(node=node, source=source))
        return deps
    deps.append(expr_to_str(node=node, source=source))
    return deps


def extract_annotation_deps(*, node: ast.AST | None, source: str) -> list[str]:
    """Extract Depends(...) calls from annotations (e.g., Annotated)."""
    if node is None:
        return []
    deps: list[str] = []
    for sub_node in ast.walk(node):
        if isinstance(sub_node, ast.Call) and is_depends_call(node=sub_node):
            deps.append(extract_dep_from_call(node=sub_node, source=source))
    return deps


def unique_preserve_order(*, items: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def normalize_dep_name(*, dep: str) -> str:
    """Normalize a dependency string for ignore matching."""
    return dep.rsplit(".", maxsplit=1)[-1]


def filter_ignored(*, deps: list[str], ignored: set[str]) -> list[str]:
    """Filter out ignored dependencies."""
    filtered: list[str] = []
    for dep in deps:
        if dep in ignored:
            continue
        if normalize_dep_name(dep=dep) in ignored:
            continue
        filtered.append(dep)
    return filtered


def count_ignored(*, original: list[str], filtered: list[str]) -> int:
    """Count dependencies filtered out by ignore rules."""
    return max(len(original) - len(filtered), 0)


def use_color(*, disabled: bool) -> bool:
    """Return whether to use ANSI colors."""
    if disabled:
        return False
    return os.environ.get("NO_COLOR") is None


def colorize(*, text: str, color_code: str, enabled: bool) -> str:
    """Colorize text if enabled."""
    if not enabled:
        return text
    return f"\033[{color_code}m{text}\033[0m"


def parse_router_definitions(
    *, tree: ast.AST, module_path: str, source: str, file_path: Path
) -> dict[str, RouterInfo]:
    """Parse APIRouter definitions in the module."""
    routers: dict[str, RouterInfo] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if isinstance(func, ast.Name) and func.id == "APIRouter":
            pass
        elif isinstance(func, ast.Attribute) and func.attr == "APIRouter":
            pass
        else:
            continue
        deps: list[str] = []
        prefix = ""
        for keyword in node.value.keywords:
            if keyword.arg == "dependencies" and keyword.value:
                deps = extract_dep_strings(node=keyword.value, source=source)
                break
        for keyword in node.value.keywords:
            if keyword.arg == "prefix" and keyword.value:
                prefix = expr_to_str(node=keyword.value, source=source)
                prefix = prefix.strip("\"'")
                break
        for target in node.targets:
            if isinstance(target, ast.Name):
                router_id = RouterId(module=module_path, name=target.id)
                routers[target.id] = RouterInfo(
                    router_id=router_id,
                    prefix=prefix,
                    dependencies=unique_preserve_order(items=deps),
                    file_path=str(file_path),
                )
    return routers


def parse_imports(
    *, tree: ast.AST, module_path: str
) -> tuple[dict[str, str], dict[str, RouterId]]:
    """Parse import mappings for module and router aliases."""
    module_aliases: dict[str, str] = {}
    router_aliases: dict[str, RouterId] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                asname = alias.asname or alias.name.split(".")[-1]
                module_aliases[asname] = alias.name
        elif isinstance(node, ast.ImportFrom):
            full_module = resolve_relative_module(
                current_module=module_path,
                level=node.level,
                module=node.module,
            )
            for alias in node.names:
                asname = alias.asname or alias.name
                if alias.name == "router":
                    router_aliases[asname] = RouterId(
                        module=full_module,
                        name="router",
                    )
                else:
                    module_aliases[asname] = f"{full_module}.{alias.name}"
    return module_aliases, router_aliases


def resolve_router_ref(
    *,
    expr: ast.AST,
    module_aliases: dict[str, str],
    router_aliases: dict[str, RouterId],
    routers_in_module: dict[str, RouterInfo],
) -> RouterId | None:
    """Resolve an expression to a RouterId if possible."""
    if isinstance(expr, ast.Name):
        if expr.id in router_aliases:
            return router_aliases[expr.id]
        if expr.id in routers_in_module:
            return routers_in_module[expr.id].router_id
        return None
    if isinstance(expr, ast.Attribute) and expr.attr == "router":
        if isinstance(expr.value, ast.Name):
            module_name = module_aliases.get(expr.value.id)
            if module_name:
                return RouterId(module=module_name, name="router")
        return None
    return None


def parse_include_edges(
    *,
    tree: ast.AST,
    module_path: str,
    source: str,
    file_path: Path,
    module_aliases: dict[str, str],
    router_aliases: dict[str, RouterId],
    routers_in_module: dict[str, RouterInfo],
    router_infos: dict[RouterId, RouterInfo],
) -> list[IncludeEdge]:
    """Parse router.include_router(...) calls."""
    edges: list[IncludeEdge] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "include_router":
            continue
        parent_expr = node.func.value
        parent_router: RouterId | None = None
        if isinstance(parent_expr, ast.Name):
            if parent_expr.id == "app":
                parent_router = RouterId(module=module_path, name="app")
            elif parent_expr.id in routers_in_module:
                parent_router = routers_in_module[parent_expr.id].router_id
        if parent_router is None:
            continue
        if not node.args:
            continue
        child_router = resolve_router_ref(
            expr=node.args[0],
            module_aliases=module_aliases,
            router_aliases=router_aliases,
            routers_in_module=routers_in_module,
        )
        if child_router is None:
            continue
        if parent_router not in router_infos:
            router_infos[parent_router] = RouterInfo(
                router_id=parent_router,
                prefix="",
                dependencies=[],
                file_path=str(file_path),
            )
        deps: list[str] = []
        include_prefix = ""
        for keyword in node.keywords:
            if keyword.arg == "dependencies" and keyword.value:
                deps = extract_dep_strings(node=keyword.value, source=source)
                break
        for keyword in node.keywords:
            if keyword.arg == "prefix" and keyword.value:
                include_prefix = expr_to_str(node=keyword.value, source=source)
                include_prefix = include_prefix.strip("\"'")
                break
        edges.append(
            IncludeEdge(
                parent=parent_router,
                child=child_router,
                prefix=include_prefix,
                dependencies=unique_preserve_order(items=deps),
                file_path=str(file_path),
            )
        )
    return edges


def parse_endpoints(
    *,
    tree: ast.AST,
    module_path: str,
    source: str,
    file_path: Path,
    module_aliases: dict[str, str],
    router_aliases: dict[str, RouterId],
    routers_in_module: dict[str, RouterInfo],
) -> dict[tuple[str, str], EndpointInfo]:
    """Parse route decorators to map endpoint functions to routers."""
    endpoints: dict[tuple[str, str], EndpointInfo] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        router_id: RouterId | None = None
        decorator_deps: list[str] = []
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not isinstance(decorator.func, ast.Attribute):
                continue
            if decorator.func.attr not in HTTP_METHOD_DECORATORS:
                continue
            router_id = resolve_router_ref(
                expr=decorator.func.value,
                module_aliases=module_aliases,
                router_aliases=router_aliases,
                routers_in_module=routers_in_module,
            )
            for keyword in decorator.keywords:
                if keyword.arg == "dependencies" and keyword.value:
                    decorator_deps = extract_dep_strings(
                        node=keyword.value,
                        source=source,
                    )
                    break
            break
        if router_id is None:
            continue
        param_deps: list[str] = []
        args = node.args
        for arg in args.args:
            param_deps.extend(
                extract_annotation_deps(node=arg.annotation, source=source)
            )
        for arg in args.kwonlyargs:
            param_deps.extend(
                extract_annotation_deps(node=arg.annotation, source=source)
            )
        defaults = list(args.defaults)
        if defaults:
            default_pairs = zip(
                args.args[-len(defaults) :],
                defaults,
                strict=False,
            )
            for _, default in default_pairs:
                if isinstance(default, ast.Call) and is_depends_call(node=default):
                    param_deps.append(
                        extract_dep_from_call(node=default, source=source)
                    )
        for idx, _ in enumerate(args.kwonlyargs):
            default_value = args.kw_defaults[idx]
            if default_value is None:
                continue
            if isinstance(default_value, ast.Call) and is_depends_call(
                node=default_value
            ):
                param_deps.append(
                    extract_dep_from_call(node=default_value, source=source)
                )
        endpoints[(module_path, node.name)] = EndpointInfo(
            router_id=router_id,
            decorator_deps=unique_preserve_order(items=decorator_deps),
            param_deps=unique_preserve_order(items=param_deps),
            file_path=str(file_path),
        )
    return endpoints


def build_router_graph(
    *, app_root: Path, fast: bool
) -> tuple[
    dict[RouterId, RouterInfo],
    list[IncludeEdge],
    dict[tuple[str, str], EndpointInfo],
]:
    """Parse all app modules to build router graph and endpoints."""
    router_infos: dict[RouterId, RouterInfo] = {}
    include_edges: list[IncludeEdge] = []
    endpoints: dict[tuple[str, str], EndpointInfo] = {}
    if fast:
        scan_roots = [
            app_root / "v1",
            app_root / "main.py",
        ]
        file_paths: list[Path] = []
        for root in scan_roots:
            if root.is_file() and root.suffix == ".py":
                file_paths.append(root)
            elif root.is_dir():
                file_paths.extend(root.rglob("*.py"))
    else:
        file_paths = list(app_root.rglob("*.py"))
    for file_path in file_paths:
        if ".venv" in file_path.parts:
            continue
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        module_path = module_path_from_file(
            file_path=file_path,
            api_root=app_root.parent,
        )
        module_aliases, router_aliases = parse_imports(
            tree=tree,
            module_path=module_path,
        )
        routers_in_module = parse_router_definitions(
            tree=tree,
            module_path=module_path,
            source=source,
            file_path=file_path,
        )
        for router_info in routers_in_module.values():
            router_infos[router_info.router_id] = router_info
        include_edges.extend(
            parse_include_edges(
                tree=tree,
                module_path=module_path,
                source=source,
                file_path=file_path,
                module_aliases=module_aliases,
                router_aliases=router_aliases,
                routers_in_module=routers_in_module,
                router_infos=router_infos,
            )
        )
        endpoints.update(
            parse_endpoints(
                tree=tree,
                module_path=module_path,
                source=source,
                file_path=file_path,
                module_aliases=module_aliases,
                router_aliases=router_aliases,
                routers_in_module=routers_in_module,
            )
        )
    return router_infos, include_edges, endpoints


def build_parent_map(*, edges: list[IncludeEdge]) -> dict[RouterId, list[IncludeEdge]]:
    """Build a parent map from include edges."""
    parent_map: dict[RouterId, list[IncludeEdge]] = {}
    for edge in edges:
        parent_map.setdefault(edge.child, []).append(edge)
    return parent_map


def build_router_chain(
    *,
    router_id: RouterId,
    parent_map: dict[RouterId, list[IncludeEdge]],
) -> tuple[list[RouterId], list[IncludeEdge], bool]:
    """Build the router chain from root to leaf."""
    chain: list[RouterId] = [router_id]
    edge_chain: list[IncludeEdge] = []
    ambiguous = False
    current = router_id
    while current in parent_map:
        parents = parent_map[current]
        if len(parents) != 1:
            ambiguous = True
            break
        edge = parents[0]
        edge_chain.append(edge)
        current = edge.parent
        chain.append(current)
    chain.reverse()
    edge_chain.reverse()
    return chain, edge_chain, ambiguous


def format_router_id(*, router_id: RouterId) -> str:
    """Format a RouterId for display."""
    return f"{router_id.module}:{router_id.name}"


def collect_inherited_deps(
    *,
    chain: list[RouterId],
    edge_chain: list[IncludeEdge],
    router_infos: dict[RouterId, RouterInfo],
) -> list[str]:
    """Collect inherited dependencies from router chain."""
    deps: list[str] = []
    edge_map = {(edge.parent, edge.child): edge for edge in edge_chain}
    for idx, router_id in enumerate(chain):
        router_info = router_infos.get(router_id)
        if router_info and router_info.dependencies:
            deps.extend(router_info.dependencies)
        if idx + 1 < len(chain):
            edge = edge_map.get((router_id, chain[idx + 1]))
            if edge and edge.dependencies:
                deps.extend(edge.dependencies)
    return unique_preserve_order(items=deps)


def format_deps(*, deps: list[str], indent: str) -> list[str]:
    """Format a dependency list with indentation."""
    if not deps:
        return [f"{indent}none"]
    return [f"{indent}- {dep}" for dep in deps]


@dataclass
class TreeNode:
    """Tree node for router hierarchy."""

    router_id: RouterId
    children: dict[RouterId, TreeNode]
    routes: list[RouteEntry]


@dataclass
class RouteEntry:
    """Grouped route entry."""

    path: str
    method_endpoints: dict[str, Any]
    include_in_schema: bool = True

    @property
    def methods(self) -> list[str]:
        """Return sorted methods for display."""
        return sorted(self.method_endpoints.keys())

    @property
    def primary_endpoint(self) -> Any:
        """Return a representative endpoint for router placement."""
        return self.method_endpoints[self.methods[0]]


def collect_router_inherited_deps(
    *,
    chain: list[RouterId],
    edge_chain: list[IncludeEdge],
    router_infos: dict[RouterId, RouterInfo],
) -> list[str]:
    """Collect inherited deps for a router from its ancestors and edges."""
    if len(chain) <= 1:
        return []
    deps: list[str] = []
    for router_id in chain[:-1]:
        router_info = router_infos.get(router_id)
        if router_info and router_info.dependencies:
            deps.extend(router_info.dependencies)
    for edge in edge_chain:
        if edge.dependencies:
            deps.extend(edge.dependencies)
    return unique_preserve_order(items=deps)


def build_router_path(
    *,
    chain: list[RouterId],
    edge_chain: list[IncludeEdge],
    router_infos: dict[RouterId, RouterInfo],
) -> str:
    """Build a router path from prefixes in the router chain."""
    if not chain:
        return ""
    parts: list[str] = []
    edge_map = {(edge.parent, edge.child): edge for edge in edge_chain}
    for idx, router_id in enumerate(chain):
        if idx > 0:
            edge = edge_map.get((chain[idx - 1], router_id))
            if edge and edge.prefix:
                parts.append(edge.prefix)
        router_info = router_infos.get(router_id)
        if router_info and router_info.prefix:
            parts.append(router_info.prefix)
    combined = "/".join(part.strip("/") for part in parts if part)
    return f"/{combined}" if combined else ""


def build_tree(
    *,
    routes: list[RouteEntry],
    endpoints: dict[tuple[str, str], EndpointInfo],
    parent_map: dict[RouterId, list[IncludeEdge]],
) -> TreeNode:
    """Build a router tree from routes."""
    root_router = RouterId(module="app.main", name="app")
    root = TreeNode(router_id=root_router, children={}, routes=[])
    for route in routes:
        endpoint_key = (
            route.primary_endpoint.__module__,
            route.primary_endpoint.__name__,
        )
        endpoint_info = endpoints.get(endpoint_key)
        if endpoint_info is None or endpoint_info.router_id is None:
            root.routes.append(route)
            continue
        router_chain, _, _ = build_router_chain(
            router_id=endpoint_info.router_id,
            parent_map=parent_map,
        )
        if not router_chain:
            root.routes.append(route)
            continue
        node = root
        for router_id in router_chain[1:]:
            node = node.children.setdefault(
                router_id,
                TreeNode(router_id=router_id, children={}, routes=[]),
            )
        node.routes.append(route)
    return root


def print_tree(
    *,
    node: TreeNode,
    router_infos: dict[RouterId, RouterInfo],
    parent_map: dict[RouterId, list[IncludeEdge]],
    endpoints: dict[tuple[str, str], EndpointInfo],
    prefix: str,
    is_last: bool,
    color_enabled: bool,
    ignored_deps: set[str],
) -> None:
    """Print the router tree with dependencies."""
    router_chain, edge_chain, _ = build_router_chain(
        router_id=node.router_id,
        parent_map=parent_map,
    )
    inherited_all = collect_router_inherited_deps(
        chain=router_chain,
        edge_chain=edge_chain,
        router_infos=router_infos,
    )
    inherited_deps = filter_ignored(deps=inherited_all, ignored=ignored_deps)
    router_info = router_infos.get(
        node.router_id,
        RouterInfo(
            router_id=node.router_id,
            prefix="",
            dependencies=[],
            file_path="unknown",
        ),
    )
    defined_all = router_info.dependencies
    defined_deps = filter_ignored(deps=defined_all, ignored=ignored_deps)
    router_path = build_router_path(
        chain=router_chain,
        edge_chain=edge_chain,
        router_infos=router_infos,
    )
    router_label = router_path or format_router_id(router_id=node.router_id)
    router_label = colorize(
        text=router_label,
        color_code="36",
        enabled=color_enabled,
    )
    connector = "" if prefix == "" else ("└── " if is_last else "├── ")
    line_prefix = f"{prefix}{connector}"
    child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
    print(f"{line_prefix}{router_label}")
    dep_indent = f"{child_prefix}    "
    inherited_tag = colorize(text="I", color_code="35", enabled=color_enabled)
    defined_tag = colorize(text="E", color_code="34", enabled=color_enabled)
    combined: list[tuple[str, str]] = []
    combined.extend([("I", dep) for dep in inherited_deps])
    combined.extend([("E", dep) for dep in defined_deps])
    ignored_count = count_ignored(original=inherited_all, filtered=inherited_deps)
    ignored_count += count_ignored(original=defined_all, filtered=defined_deps)
    if combined:
        for origin, dep in combined:
            tag = inherited_tag if origin == "I" else defined_tag
            print(f"{dep_indent}{tag} {dep}")
    elif ignored_count:
        print(f"{dep_indent}{ignored_count} ignored")
    else:
        print(f"{dep_indent}none")

    items: list[tuple[str, TreeNode | RouteEntry]] = []
    items.extend([("router", child) for child in node.children.values()])
    items.extend([("route", route) for route in node.routes])

    for idx, (kind, item) in enumerate(items):
        child_last = idx == len(items) - 1
        if kind == "router":
            assert isinstance(item, TreeNode)  # noqa: S101
            print_tree(
                node=item,
                router_infos=router_infos,
                parent_map=parent_map,
                endpoints=endpoints,
                prefix=child_prefix,
                is_last=child_last,
                color_enabled=color_enabled,
                ignored_deps=ignored_deps,
            )
        else:
            assert isinstance(item, RouteEntry)  # noqa: S101
            print_route_leaf(
                route=item,
                endpoints=endpoints,
                router_infos=router_infos,
                parent_map=parent_map,
                prefix=child_prefix,
                is_last=child_last,
                color_enabled=color_enabled,
                ignored_deps=ignored_deps,
            )


def print_route_leaf(
    *,
    route: RouteEntry,
    endpoints: dict[tuple[str, str], EndpointInfo],
    router_infos: dict[RouterId, RouterInfo],
    parent_map: dict[RouterId, list[IncludeEdge]],
    prefix: str,
    is_last: bool,
    color_enabled: bool,
    ignored_deps: set[str],
) -> None:
    """Print a single route leaf with dependency detail."""
    endpoint_key = (
        route.primary_endpoint.__module__,
        route.primary_endpoint.__name__,
    )
    endpoint_info = endpoints.get(
        endpoint_key,
        EndpointInfo(
            router_id=None,
            decorator_deps=[],
            param_deps=[],
            file_path="unknown",
        ),
    )
    router_chain: list[RouterId] = []
    edge_chain: list[IncludeEdge] = []
    if endpoint_info.router_id:
        router_chain, edge_chain, _ = build_router_chain(
            router_id=endpoint_info.router_id,
            parent_map=parent_map,
        )
    inherited_all = collect_inherited_deps(
        chain=router_chain,
        edge_chain=edge_chain,
        router_infos=router_infos,
    )
    inherited_deps = filter_ignored(deps=inherited_all, ignored=ignored_deps)
    method_colors = {
        "GET": "32",
        "POST": "34",
        "PUT": "33",
        "PATCH": "35",
        "DELETE": "31",
        "OPTIONS": "36",
        "HEAD": "36",
        "TRACE": "36",
    }
    route_label = colorize(
        text=route.path,
        color_code="38;5;208",
        enabled=color_enabled,
    )
    connector = "└── " if is_last else "├── "
    line_prefix = f"{prefix}{connector}"
    child_prefix = f"{prefix}{'    ' if is_last else '│   '}"
    print(f"{line_prefix}{route_label}")
    method_items = route.methods
    for idx, method in enumerate(method_items):
        is_last_method = idx == len(method_items) - 1
        method_connector = "└── " if is_last_method else "├── "
        color = method_colors.get(method, "36")
        method_label = colorize(
            text=method,
            color_code=color,
            enabled=color_enabled,
        )
        print(f"{child_prefix}{method_connector}{method_label}")
        method_endpoint = route.method_endpoints[method]
        endpoint_key = (method_endpoint.__module__, method_endpoint.__name__)
        endpoint_info = endpoints.get(
            endpoint_key,
            EndpointInfo(
                router_id=None,
                decorator_deps=[],
                param_deps=[],
                file_path="unknown",
            ),
        )
        method_deps_all = unique_preserve_order(
            items=endpoint_info.decorator_deps + endpoint_info.param_deps
        )
        method_deps = filter_ignored(deps=method_deps_all, ignored=ignored_deps)
        dep_indent = f"{child_prefix}{'│   ' if not is_last_method else '    '}    "
        inherited_tag = colorize(text="I", color_code="35", enabled=color_enabled)
        endpoint_tag = colorize(text="E", color_code="33", enabled=color_enabled)
        combined: list[tuple[str, str]] = []
        combined.extend([("I", dep) for dep in inherited_deps])
        combined.extend([("E", dep) for dep in method_deps])
        ignored_count = count_ignored(
            original=inherited_all,
            filtered=inherited_deps,
        )
        ignored_count += count_ignored(
            original=method_deps_all,
            filtered=method_deps,
        )
        if not combined:
            if ignored_count:
                print(f"{dep_indent}{ignored_count} ignored")
            else:
                print(f"{dep_indent}none")
            continue
        for origin, dep in combined:
            tag = inherited_tag if origin == "I" else endpoint_tag
            print(f"{dep_indent}{tag} {dep}")


def build_router_deps(
    *,
    router_chain: list[RouterId],
    edge_chain: list[IncludeEdge],
    router_infos: dict[RouterId, RouterInfo],
    router_id: RouterId,
    ignored_deps: set[str],
) -> tuple[list[str], list[str], int]:
    """Return inherited deps, defined deps, and ignored count for a router."""
    inherited_all = collect_router_inherited_deps(
        chain=router_chain,
        edge_chain=edge_chain,
        router_infos=router_infos,
    )
    inherited_deps = filter_ignored(deps=inherited_all, ignored=ignored_deps)
    router_info = router_infos.get(
        router_id,
        RouterInfo(
            router_id=router_id,
            prefix="",
            dependencies=[],
            file_path="unknown",
        ),
    )
    defined_all = router_info.dependencies
    defined_deps = filter_ignored(deps=defined_all, ignored=ignored_deps)
    ignored_count = count_ignored(original=inherited_all, filtered=inherited_deps)
    ignored_count += count_ignored(original=defined_all, filtered=defined_deps)
    return inherited_deps, defined_deps, ignored_count


def build_method_deps(
    *,
    endpoint: Any,
    endpoints: dict[tuple[str, str], EndpointInfo],
    inherited_deps: list[str],
    inherited_all: list[str],
    ignored_deps: set[str],
) -> tuple[list[str], int]:
    """Return method deps and ignored count for a method."""
    endpoint_key = (endpoint.__module__, endpoint.__name__)
    endpoint_info = endpoints.get(
        endpoint_key,
        EndpointInfo(
            router_id=None,
            decorator_deps=[],
            param_deps=[],
            file_path="unknown",
        ),
    )
    method_deps_all = unique_preserve_order(
        items=endpoint_info.decorator_deps + endpoint_info.param_deps
    )
    method_deps = filter_ignored(deps=method_deps_all, ignored=ignored_deps)
    ignored_count = count_ignored(
        original=inherited_all,
        filtered=inherited_deps,
    )
    ignored_count += count_ignored(
        original=method_deps_all,
        filtered=method_deps,
    )
    return method_deps, ignored_count


def render_html(
    *,
    node: TreeNode,
    router_infos: dict[RouterId, RouterInfo],
    parent_map: dict[RouterId, list[IncludeEdge]],
    endpoints: dict[tuple[str, str], EndpointInfo],
    ignored_deps: set[str],
    repo_root: Path,
) -> str:
    """Render the dependency tree as HTML."""
    css = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: #0b1020;
        color: #e2e8f0;
        margin: 0;
        padding: 24px;
    }
    body.light {
        background: #f8fafc;
        color: #0f172a;
    }
    body.light .panel {
        background: #ffffff;
        border-color: #e2e8f0;
        box-shadow: 0 8px 24px rgba(148, 163, 184, 0.25);
    }
    body.light .route {
        color: #b45309;
    }
    body.light .router {
        color: #0369a1;
    }
    body.light .muted {
        color: #64748b;
    }
    body.light .method {
        background: #e2e8f0;
    }
    body.light .toolbar button {
        background: #e2e8f0;
        border-color: #cbd5f5;
        color: #0f172a;
    }
    body.light .toolbar button:hover {
        background: #cbd5f5;
    }
    body.light .ignored[data-tooltip]:hover::after {
        background: #f1f5f9;
        color: #0f172a;
        border-color: #e2e8f0;
    }
    h1 {
        font-size: 22px;
        margin-bottom: 16px;
    }
    .panel {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.35);
    }
    .toolbar {
        display: flex;
        gap: 8px;
        margin-top: 12px;
        flex-wrap: wrap;
    }
    .toolbar button {
        background: #1e293b;
        border: 1px solid #334155;
        color: #e2e8f0;
        padding: 6px 10px;
        border-radius: 6px;
        cursor: pointer;
        font-size: 12px;
    }
    .toolbar input {
        background: #0f172a;
        border: 1px solid #334155;
        color: #e2e8f0;
        padding: 6px 10px;
        border-radius: 6px;
        font-size: 12px;
        min-width: 220px;
    }
    body.light .toolbar input {
        background: #ffffff;
        border-color: #cbd5f5;
        color: #0f172a;
    }
    .file-links {
        margin-left: 6px;
        display: inline-flex;
        gap: 6px;
    }
    .file-links a {
        font-size: 11px;
        padding: 2px 6px;
        border-radius: 6px;
        border: 1px solid #334155;
        color: #e2e8f0;
        text-decoration: none;
        background: #111827;
    }
    .file-links a:hover {
        background: #1f2937;
    }
    body.light .file-links a {
        background: #e2e8f0;
        border-color: #cbd5f5;
        color: #0f172a;
    }
    body.light .file-links a:hover {
        background: #cbd5f5;
    }
    .toolbar button:hover {
        background: #334155;
    }
    details {
        margin-left: 16px;
    }
    summary {
        cursor: pointer;
        padding: 4px 0;
        list-style: none;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    summary::-webkit-details-marker {
        display: none;
    }
    summary::before {
        content: "";
        width: 10px;
        height: 10px;
        border-right: 2px solid #94a3b8;
        border-bottom: 2px solid #94a3b8;
        display: inline-block;
        transform: rotate(-45deg);
        margin-right: 4px;
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    details[open] > summary::before {
        transform: rotate(45deg);
        border-color: #e2e8f0;
    }
    body.light details[open] > summary::before {
        color: #0f172a;
    }
    summary:hover {
        color: #f8fafc;
    }
    body.light summary:hover {
        color: #0f172a;
    }
    .router {
        color: #7dd3fc;
        font-weight: 600;
    }
    .route {
        color: #fb923c;
        font-weight: 600;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    .icon {
        width: 16px;
        height: 16px;
        vertical-align: -2px;
        margin-right: 6px;
        flex-shrink: 0;
    }
    .icon text {
        font-size: 9px;
        font-weight: 700;
        text-anchor: middle;
        dominant-baseline: central;
        fill: currentColor;
    }
    .method {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-right: 6px;
        padding: 3px 8px;
        border-radius: 999px;
        background: #111827;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.02em;
        border: 1px solid #334155;
    }
    .method-name {
        font-size: 11px;
        opacity: 0.9;
    }
    .method-row {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .method-line {
        height: 1px;
        flex: 1 1 auto;
        background: #334155;
        opacity: 0.7;
    }
    body.light .method-line {
        background: #cbd5f5;
    }
    .method-get {
        color: #22c55e;
        border-color: rgba(34, 197, 94, 0.4);
        background: rgba(34, 197, 94, 0.12);
    }
    .method-post {
        color: #60a5fa;
        border-color: rgba(96, 165, 250, 0.4);
        background: rgba(96, 165, 250, 0.12);
    }
    .method-put {
        color: #f59e0b;
        border-color: rgba(245, 158, 11, 0.4);
        background: rgba(245, 158, 11, 0.12);
    }
    .method-patch {
        color: #d946ef;
        border-color: rgba(217, 70, 239, 0.4);
        background: rgba(217, 70, 239, 0.12);
    }
    .method-delete {
        color: #ef4444;
        border-color: rgba(239, 68, 68, 0.4);
        background: rgba(239, 68, 68, 0.12);
    }
    .method-default {
        color: #38bdf8;
        border-color: rgba(56, 189, 248, 0.4);
        background: rgba(56, 189, 248, 0.12);
    }
    body.light .method-get {
        color: #15803d;
        background: rgba(34, 197, 94, 0.18);
        border-color: rgba(34, 197, 94, 0.35);
    }
    body.light .method-post {
        color: #1d4ed8;
        background: rgba(96, 165, 250, 0.18);
        border-color: rgba(96, 165, 250, 0.35);
    }
    body.light .method-put {
        color: #b45309;
        background: rgba(245, 158, 11, 0.18);
        border-color: rgba(245, 158, 11, 0.35);
    }
    body.light .method-patch {
        color: #a21caf;
        background: rgba(217, 70, 239, 0.18);
        border-color: rgba(217, 70, 239, 0.35);
    }
    body.light .method-delete {
        color: #b91c1c;
        background: rgba(239, 68, 68, 0.18);
        border-color: rgba(239, 68, 68, 0.35);
    }
    body.light .method-default {
        color: #0284c7;
        background: rgba(56, 189, 248, 0.18);
        border-color: rgba(56, 189, 248, 0.35);
    }
    .dep-list {
        margin-left: 20px;
        font-size: 13px;
        line-height: 1.7;
        display: grid;
        gap: 6px;
    }
    .dep-inline {
        margin-left: 10px;
        display: inline-flex;
        flex-wrap: wrap;
        gap: 6px;
        align-items: center;
    }
    .tag-i {
        color: #f5d0fe;
        font-weight: 700;
        background: rgba(217, 70, 239, 0.18);
        border: 1px solid rgba(217, 70, 239, 0.45);
        border-radius: 999px;
        padding: 2px 6px;
        font-size: 11px;
        margin-right: 6px;
    }
    .tag-e {
        color: #fde68a;
        font-weight: 700;
        background: rgba(250, 204, 21, 0.18);
        border: 1px solid rgba(250, 204, 21, 0.45);
        border-radius: 999px;
        padding: 2px 6px;
        font-size: 11px;
        margin-right: 6px;
    }
    body.light .tag-i {
        color: #701a75;
        background: rgba(217, 70, 239, 0.12);
        border-color: rgba(217, 70, 239, 0.35);
    }
    body.light .tag-e {
        color: #854d0e;
        background: rgba(250, 204, 21, 0.12);
        border-color: rgba(250, 204, 21, 0.35);
    }
    .muted {
        color: #94a3b8;
    }
    .ignored {
        color: #f97316;
        font-weight: 600;
        cursor: help;
        position: relative;
    }
    .ignored[data-tooltip]:hover::after {
        content: attr(data-tooltip);
        position: absolute;
        left: 0;
        top: 18px;
        background: #1f2937;
        color: #e2e8f0;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 6px 8px;
        font-size: 12px;
        white-space: pre-wrap;
        max-width: 420px;
        z-index: 10;
    }
    .schema-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        margin-left: 8px;
    }
    .schema-visible {
        color: #22c55e;
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.4);
    }
    .schema-hidden {
        color: #ef4444;
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    body.light .schema-visible {
        color: #15803d;
        background: rgba(34, 197, 94, 0.12);
        border-color: rgba(34, 197, 94, 0.35);
    }
    body.light .schema-hidden {
        color: #b91c1c;
        background: rgba(239, 68, 68, 0.12);
        border-color: rgba(239, 68, 68, 0.35);
    }
    """
    html_parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        "<title>Route Tree</title>",
        f"<style>{css}</style></head><body>",
        "<h1>Route Tree</h1>",
        "<div class='panel'>"
        "<div class='muted'>Ignored deps: " + ", ".join(sorted(ignored_deps)) + "</div>"
        "<div class='toolbar'>"
        "<input id='search' type='search' placeholder='Search routes, deps, tags'/>"
        "<button id='expand-all'>Expand all</button>"
        "<button id='collapse-all'>Collapse all</button>"
        "<button id='toggle-theme'>Toggle theme</button>"
        "</div>"
        "</div>",
    ]

    def build_editor_links(*, abs_path: Path) -> str:
        encoded = quote(str(abs_path))
        cursor_link = f"cursor://file/{encoded}"
        zed_link = f"zed://file/{encoded}"
        return (
            "<span class='file-links'>"
            f"<a href='{cursor_link}'>Cursor</a>"
            f"<a href='{zed_link}'>Zed</a>"
            "</span>"
        )

    def render_node(*, current: TreeNode) -> None:
        router_chain, edge_chain, _ = build_router_chain(
            router_id=current.router_id,
            parent_map=parent_map,
        )
        router_path = build_router_path(
            chain=router_chain,
            edge_chain=edge_chain,
            router_infos=router_infos,
        )
        label = router_path or format_router_id(router_id=current.router_id)
        inherited, defined, ignored_count = build_router_deps(
            router_chain=router_chain,
            edge_chain=edge_chain,
            router_infos=router_infos,
            router_id=current.router_id,
            ignored_deps=ignored_deps,
        )
        ignored_router = collect_router_inherited_deps(
            chain=router_chain,
            edge_chain=edge_chain,
            router_infos=router_infos,
        )
        router_defined = router_infos.get(
            current.router_id,
            RouterInfo(
                router_id=current.router_id,
                prefix="",
                dependencies=[],
                file_path="unknown",
            ),
        ).dependencies
        ignored_router_list = []
        for dep in ignored_router + router_defined:
            if dep in ignored_deps or normalize_dep_name(dep=dep) in ignored_deps:
                ignored_router_list.append(dep)
        ignored_router_title = ", ".join(
            unique_preserve_order(items=ignored_router_list)
        )
        html_parts.append("<details open class='panel' data-node>")
        raw_path = router_infos.get(
            current.router_id,
            RouterInfo(
                router_id=current.router_id,
                prefix="",
                dependencies=[],
                file_path="unknown",
            ),
        ).file_path
        if raw_path == "unknown":
            file_path = raw_path
            link_html = ""
        else:
            abs_path = (repo_root / raw_path).resolve()
            link_html = build_editor_links(abs_path=abs_path)
            if "api/" in raw_path:
                file_path = raw_path.split("api/", 1)[1]
            else:
                file_path = raw_path
        deps_inline = ""
        if inherited or defined:
            deps_inline += " "
            deps_inline += " ".join(
                f"<span class='tag-i'>Inherited</span> {dep}" for dep in inherited
            )
            if inherited and defined:
                deps_inline += " "
            deps_inline += " ".join(
                f"<span class='tag-e'>Path</span> {dep}" for dep in defined
            )
        elif ignored_count:
            deps_inline = (
                " <span class='ignored' data-tooltip='"
                + ignored_router_title
                + f"'>{ignored_count} ignored</span>"
            )
        else:
            deps_inline = " <span class='muted'>none</span>"
        html_parts.append(
            "<summary>"
            "<span class='router'>"
            "<svg class='icon' viewBox='0 0 16 16' aria-hidden='true'>"
            "<circle cx='8' cy='8' r='7' stroke='currentColor' fill='none' "
            "stroke-width='1.5'/>"
            "<text x='8' y='8'>R</text>"
            "</svg>"
            "</span>"
            f"<span class='router'>{label}</span> "
            f"<span class='muted'>{file_path}</span>{link_html}"
            f"<span class='dep-inline'>{deps_inline}</span>"
            "</summary>"
        )

        for child in current.children.values():
            render_node(current=child)
        for route in current.routes:
            html_parts.append("<details data-node>")
            file_path = "unknown"
            link_html = ""
            primary_key = (
                route.primary_endpoint.__module__,
                route.primary_endpoint.__name__,
            )
            primary_info = endpoints.get(primary_key)
            if primary_info:
                raw_path = primary_info.file_path
                abs_path = (repo_root / raw_path).resolve()
                link_html = build_editor_links(abs_path=abs_path)
                if "api/" in raw_path:
                    file_path = raw_path.split("api/", 1)[1]
                else:
                    file_path = raw_path
            schema_badge = (
                "<span class='schema-badge schema-visible'>In Schema</span>"
                if route.include_in_schema
                else "<span class='schema-badge schema-hidden'>Hidden</span>"
            )
            html_parts.append(
                "<summary>"
                "<span class='route'>"
                "<svg class='icon' viewBox='0 0 16 16' aria-hidden='true'>"
                "<circle cx='8' cy='8' r='7' stroke='currentColor' fill='none' "
                "stroke-width='1.5'/>"
                "<text x='8' y='8'>P</text>"
                "</svg>"
                "</span>"
                f"<span class='route'>{route.path}</span> "
                f"<span class='muted'>{file_path}</span>{link_html}"
                f"{schema_badge}"
                "</summary>"
            )
            inherited_all = collect_inherited_deps(
                chain=router_chain,
                edge_chain=edge_chain,
                router_infos=router_infos,
            )
            inherited_deps = filter_ignored(
                deps=inherited_all,
                ignored=ignored_deps,
            )
            for method in route.methods:
                method_class = f"method method-{method.lower()}"
                if method.lower() not in {
                    "get",
                    "post",
                    "put",
                    "patch",
                    "delete",
                }:
                    method_class = "method method-default"
                html_parts.append(
                    "<div class='method-row'>"
                    f"<span class='{method_class}'>"
                    f"{method}</span>"
                    "<span class='method-line'></span>"
                    "</div>"
                )
                method_deps, ignored_count = build_method_deps(
                    endpoint=route.method_endpoints[method],
                    endpoints=endpoints,
                    inherited_deps=inherited_deps,
                    inherited_all=inherited_all,
                    ignored_deps=ignored_deps,
                )
                ignored_method_list = []
                method_endpoint = route.method_endpoints[method]
                method_key = (method_endpoint.__module__, method_endpoint.__name__)
                endpoint_info = endpoints.get(
                    method_key,
                    EndpointInfo(
                        router_id=None,
                        decorator_deps=[],
                        param_deps=[],
                        file_path="unknown",
                    ),
                )
                method_deps_all = unique_preserve_order(
                    items=endpoint_info.decorator_deps + endpoint_info.param_deps
                )
                for dep in inherited_all + method_deps_all:
                    if (
                        dep in ignored_deps
                        or normalize_dep_name(dep=dep) in ignored_deps
                    ):
                        ignored_method_list.append(dep)
                ignored_method_title = ", ".join(
                    unique_preserve_order(items=ignored_method_list)
                )
                html_parts.append("<div class='dep-list'>")
                if inherited_deps or method_deps:
                    for dep in inherited_deps:
                        html_parts.append(
                            f"<div><span class='tag-i'>Inherited</span> {dep}</div>"
                        )
                    for dep in method_deps:
                        html_parts.append(
                            f"<div><span class='tag-e'>Path</span> {dep}</div>"
                        )
                elif ignored_count:
                    html_parts.append(
                        "<div class='ignored' data-tooltip='"
                        + ignored_method_title
                        + f"'>{ignored_count} ignored</div>"
                    )
                else:
                    html_parts.append("<div class='muted'>none</div>")
                html_parts.append("</div>")
            html_parts.append("</details>")
        html_parts.append("</details>")

    render_node(current=node)
    html_parts.append(
        """
<script>
const expandAll = () => {
  document.querySelectorAll('details').forEach((el) => el.open = true);
};
const collapseAll = () => {
  document.querySelectorAll('details').forEach((el) => el.open = false);
};
const applySearch = (query) => {
  const q = query.trim().toLowerCase();
  const nodes = document.querySelectorAll('[data-node]');
  if (!q) {
    nodes.forEach((el) => el.style.display = '');
    return;
  }
  nodes.forEach((el) => {
    const text = el.textContent.toLowerCase();
    el.style.display = text.includes(q) ? '' : 'none';
  });
};
const toggleTheme = () => {
  document.body.classList.toggle('light');
};
document.getElementById('expand-all').addEventListener('click', expandAll);
document.getElementById('collapse-all').addEventListener('click', collapseAll);
document.getElementById('toggle-theme').addEventListener('click', toggleTheme);
document.getElementById('search').addEventListener('input', (event) => {
  applySearch(event.target.value);
});
</script>
"""
    )
    html_parts.append("</body></html>")
    return "\n".join(html_parts)


def main() -> int:
    """Run the dependency report."""
    parser = argparse.ArgumentParser(
        description="Report FastAPI route tree",
    )
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Parse all api/app modules (slower but more exhaustive).",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Dependency name to ignore (repeatable).",
    )
    parser.add_argument(
        "--output",
        default=".route-tree.html",
        help="Write the HTML report to this path.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    app_root = repo_root / "api" / "app"

    from app import settings

    # Set ENVIRONMENT to "production" so that get_include_in_schema() returns
    # False for routes that use it dynamically. This allows the route tree to
    # accurately show which routes would be hidden in the production API docs.
    settings.ENVIRONMENT = "production"

    router_infos, include_edges, endpoints = build_router_graph(
        app_root=app_root,
        fast=not args.full_scan,
    )
    parent_map = build_parent_map(edges=include_edges)

    from app.main import app  # pylint: disable=import-error

    routes: list[APIRoute] = [
        route for route in app.routes if isinstance(route, APIRoute)
    ]
    grouped: dict[str, RouteEntry] = {}
    for route in routes:
        entry = grouped.get(route.path)
        if entry is None:
            grouped[route.path] = RouteEntry(
                path=route.path,
                method_endpoints={method: route.endpoint for method in route.methods},
                include_in_schema=route.include_in_schema,
            )
        else:
            for method in route.methods:
                entry.method_endpoints.setdefault(method, route.endpoint)
            # If any method is not in schema, mark the entry as not in schema
            if not route.include_in_schema:
                entry.include_in_schema = False
    grouped_routes = sorted(
        grouped.values(),
        key=lambda entry: (entry.path, entry.methods),
    )

    ignored_deps = set(DEFAULT_IGNORED_DEPS)
    ignored_deps.update(args.ignore)
    tree = build_tree(
        routes=grouped_routes,
        endpoints=endpoints,
        parent_map=parent_map,
    )
    html_report = render_html(
        node=tree,
        router_infos=router_infos,
        parent_map=parent_map,
        endpoints=endpoints,
        ignored_deps=ignored_deps,
        repo_root=repo_root,
    )
    html_path = Path(args.output)
    html_path.write_text(html_report, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Isolated CPU import/schema probe. Never submits or executes a workflow."""
import argparse
import importlib.util
import json
import sys
import traceback
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin")
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preceding-plugin", action="append", default=[])
    opts = parser.parse_args()
    plugin = Path(opts.plugin).resolve()
    sys.path.insert(0, str(Path(opts.runtime).resolve()))
    sys.argv = ["creative-os-cpu-probe", "--cpu"]
    import comfy.options
    comfy.options.enable_args_parsing()
    import comfy.cli_args
    comfy.cli_args.args.cpu = True
    # Plugins register routes at import. Supply only an in-memory registry:
    # no server listener, queue, HTTP client or GPU execution is created.
    from types import SimpleNamespace
    from aiohttp import web
    import server
    server.PromptServer.instance = SimpleNamespace(routes=web.RouteTableDef())
    result = {"plugin": str(plugin), "cpu_only": True,
              "workflow_executed": False, "route_registry_fixture": True,
              "nodes": {}, "errors": []}
    try:
        for index, preceding in enumerate(opts.preceding_plugin):
            path = Path(preceding).resolve()
            prior_spec = importlib.util.spec_from_file_location(
                "creative_probe_prior_" + str(index), path / "__init__.py",
                submodule_search_locations=[str(path)])
            prior_module = importlib.util.module_from_spec(prior_spec)
            sys.modules[prior_spec.name] = prior_module
            prior_spec.loader.exec_module(prior_module)
        spec = importlib.util.spec_from_file_location(
            "creative_probe_" + plugin.name, plugin / "__init__.py",
            submodule_search_locations=[str(plugin)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        patch_module = sys.modules.get(spec.name + ".patches")
        if patch_module and hasattr(patch_module, "motion_context_patch_status"):
            ready, reason = patch_module.motion_context_patch_status()
            result["motion_context_compatible"] = ready
            if not ready: result["errors"].append({"compatibility":reason})
        for name, cls in module.NODE_CLASS_MAPPINGS.items():
            try:
                if hasattr(cls, "define_schema"):
                    schema = cls.define_schema()
                    info = schema.as_dict() if hasattr(schema, "as_dict") else repr(schema)
                else:
                    info = cls.INPUT_TYPES()
                result["nodes"][name] = {"inputs": info,
                    "return_types": getattr(cls, "RETURN_TYPES", []),
                    "function": getattr(cls, "FUNCTION", "execute")}
            except Exception:
                result["errors"].append({"node": name, "trace": traceback.format_exc()})
        result["import_pass"] = True
    except Exception:
        result["import_pass"] = False
        result["errors"].append({"trace": traceback.format_exc()})
    Path(opts.output).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"plugin": plugin.name, "import_pass": result["import_pass"],
                      "nodes": len(result["nodes"]), "errors": len(result["errors"])}))
    return 0 if result["import_pass"] and not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
